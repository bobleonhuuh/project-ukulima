"""Ukulima AI module.

Two layers:
1. Offline symptom matcher over data/knowledge.json (always available, no key).
2. Optional vision step using the Anthropic API when ANTHROPIC_API_KEY is set
   and a photo was uploaded. The model may only choose from knowledge-base IDs,
   so advice always comes from the curated, expert-reviewable knowledge base.

Everything here degrades gracefully: if the network or key fails, diagnosis and
chat fall back to the offline matcher and never raise.
"""
import base64, json, os, re, urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(BASE, "data", "knowledge.json"), encoding="utf-8") as f:
    KB = json.load(f)
KB_BY_ID = {k["id"]: k for k in KB}
CROPS = sorted({c for k in KB for c in k["crops"]} | {"Other"})

SYMPTOM_TAGS = [
    "Holes in leaves", "Yellowing", "Wilting", "Dark spots or patches",
    "Orange/brown powder", "Curled or distorted leaves", "Sticky leaves",
    "Rotting fruit or tubers", "Visible insects or caterpillars",
    "Stunted growth", "Stem tunnels or dead heart",
]
TAG_WORDS = {
    "Holes in leaves": "holes windowing chewed",
    "Yellowing": "yellowing chlorotic yellow patches",
    "Wilting": "wilt",
    "Dark spots or patches": "dark patches black spots brown lesions water-soaked",
    "Orange/brown powder": "rust orange powder pustules",
    "Curled or distorted leaves": "curled distorted twisted mosaic",
    "Sticky leaves": "sticky honeydew sooty",
    "Rotting fruit or tubers": "rot tuber rot fruit holes",
    "Visible insects or caterpillars": "caterpillar worm insects clusters",
    "Stunted growth": "stunted",
    "Stem tunnels or dead heart": "dead heart stem tunnel bore",
}


def _score(crop, text):
    """Rank knowledge-base entries by keyword overlap, boosted when crop matches."""
    text = (text or "").lower()
    out = []
    for k in KB:
        hits = sum(1 for w in k["keywords"] if w in text)
        if hits == 0:
            continue
        s = float(hits)
        s *= 1.6 if crop in k["crops"] else 0.35
        out.append((s, k["id"]))
    out.sort(reverse=True)
    return out


def _claude_vision(crop, text, image_path):
    """Optional photo diagnosis. Returns (id, confidence) or None."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key or not image_path or not os.path.exists(image_path):
        return None
    ext = image_path.rsplit(".", 1)[-1].lower()
    media = {"jpg": "image/jpeg", "jpeg": "image/jpeg",
             "png": "image/png", "webp": "image/webp"}.get(ext)
    if not media:
        return None
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    options = "; ".join(f'{k["id"]} = {k["name"]} ({", ".join(k["crops"])})' for k in KB)
    prompt = (
        f"You help diagnose crop problems for smallholder farmers in Kenya. Crop: {crop}. "
        f"Farmer's description: {text or 'none'}. Choose the single best match from this list, "
        f"or 'unknown' if none fits: {options}. "
        'Reply with JSON only: {"id": "<id or unknown>", "confidence": <0..1>}'
    )
    body = json.dumps({
        "model": os.environ.get("UKULIMA_MODEL", "claude-sonnet-4-6"),
        "max_tokens": 200,
        "messages": [{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": media, "data": b64}},
            {"type": "text", "text": prompt},
        ]}],
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=body,
        headers={"content-type": "application/json", "x-api-key": key,
                 "anthropic-version": "2023-06-01"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            data = json.loads(r.read())
        txt = "".join(b.get("text", "") for b in data.get("content", []))
        m = re.search(r"\{.*\}", txt, re.S)
        j = json.loads(m.group(0))
        if j.get("id") in KB_BY_ID or j.get("id") == "unknown":
            return j["id"], max(0.0, min(1.0, float(j.get("confidence", 0.5))))
    except Exception as e:  # network/key problems must never break reporting
        print("Vision step skipped:", e)
    return None


def diagnose(crop, tags, text, image_path=None):
    """Return dict(label, confidence, source, alternatives)."""
    blob = " ".join([text or ""] + [TAG_WORDS.get(t, "") for t in tags])
    ranked = _score(crop, blob)
    label, conf, source = "unknown", 0.0, "symptom-matcher"
    if ranked:
        top = ranked[0][0]
        second = ranked[1][0] if len(ranked) > 1 else 0
        label = ranked[0][1]
        conf = round(min(0.92, top / (top + second + 2.0)), 2)
    alts = [i for _, i in ranked[1:3]]

    v = _claude_vision(crop, blob, image_path)
    if v:
        vid, vconf = v
        if vid != "unknown":
            if vid == label:
                conf = round(min(0.97, max(conf, vconf) + 0.05), 2)
            else:
                if label != "unknown":
                    alts.insert(0, label)
                label, conf = vid, round(vconf * 0.9, 2)
        source = "ai-vision+matcher"
    return {"label": label, "confidence": conf, "source": source,
            "alternatives": [a for a in alts if a != label]}


SWAHILI_WORDS = {
    "mahindi": "maize", "viazi": "potato", "nyanya": "tomato", "kahawa": "coffee",
    "ndizi": "banana", "muhogo": "cassava", "maharagwe": "beans", "sukuma": "kale",
    "kabichi": "cabbage", "mtama": "sorghum", "ulezi": "millet", "mdudu": "pest",
    "wadudu": "pests", "ugonjwa": "disease", "majani": "leaves", "shamba": "farm",
    "dawa": "chemical", "kinga": "prevention", "ripoti": "report", "tahadhari": "alert",
}


def _normalise(question):
    q = (question or "").lower()
    for sw, en in SWAHILI_WORDS.items():
        q = re.sub(r"\b" + sw + r"\b", en, q)
    return q


def _match(q):
    """Rank KB entries by word overlap with names, keywords and crops."""
    tokens = set(re.findall(r"[a-z]+", q))
    out = []
    for k in KB:
        s = 2.0 * len(tokens & set(re.findall(r"[a-z]+", k["name"].lower())))
        for w in k["keywords"]:
            if " " in w:
                s += 1.5 if w in q else 0
            elif w in tokens:
                s += 1.0
        for c in k["crops"]:
            if c.lower() in tokens:
                s += 0.75
        if s > 0:
            out.append((s, k))
    out.sort(key=lambda x: -x[0])
    return out


def _kb_answer(k, focus=None):
    """Format one KB entry as a chat reply (markdown-lite)."""
    a = k["advice"]
    lines = [f"**{k['name']}** ({k['type'].lower()} · {', '.join(k['crops'])})", k["description"], ""]
    if focus == "prevent":
        lines.append("**Prevention:**")
        lines += ["- " + x for x in a["prevention"]]
        lines += ["", "**Early action:**", "- " + a["cultural"][0]]
    elif focus == "organic":
        lines.append("**Cultural & biological control:**")
        lines += ["- " + x for x in a["cultural"][:2]]
        lines += ["- " + x for x in a["biological"]]
    elif focus == "chemical":
        lines.append("**Chemical guidance (safety first):**")
        lines += ["- " + x for x in a["chemical"]]
        lines += ["- Always read the label, wear protective clothing and observe the pre-harvest interval."]
    else:
        lines.append("**What to do now:**")
        lines += ["- " + x for x in a["cultural"][:2]]
        lines += ["", "**Prevent it next time:**", "- " + a["prevention"][0],
                  "", "For chemicals, ask your extension officer for a PCPB-registered product."]
    lines += ["", f"[Read the full guide](/knowledge/{k['id']})"]
    return "\n".join(lines)


def _claude_chat(question, context):
    """Optional LLM layer. Returns text or None; never raises."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    ctx = json.dumps([{"name": k["name"], "crops": k["crops"],
                       "description": k["description"], "advice": k["advice"]} for k in KB])
    who = ""
    if context:
        who = (f"The farmer's name is {context.get('name') or 'unknown'} and their county is "
               f"{context.get('county') or 'unknown'}. Recent alerts: "
               f"{json.dumps(context.get('alerts') or [])}. ")
    body = json.dumps({
        "model": os.environ.get("UKULIMA_MODEL", "claude-sonnet-4-6"),
        "max_tokens": 500,
        "system": ("You are Ukulima, a warm, practical crop advisory assistant for Kenyan smallholders. "
                   "Answer briefly in simple English (greet in Kiswahili if the farmer writes Kiswahili). "
                   "Use ONLY this knowledge base for pest and disease control; never invent product names "
                   "or doses; refer to PCPB-registered products and extension officers for chemicals. "
                   "If the answer is not in the knowledge base, say so and suggest submitting a report. "
                   + who + "Knowledge base: " + ctx),
        "messages": [{"role": "user", "content": question}],
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=body,
        headers={"content-type": "application/json", "x-api-key": key,
                 "anthropic-version": "2023-06-01"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return "".join(b.get("text", "") for b in json.loads(r.read()).get("content", []))
    except Exception as e:
        print("Chat fallback:", e)
    return None


DEFAULT_SUGGESTIONS = [
    "My maize has holes and sawdust in the funnel",
    "How do I report a crop problem?",
    "Organic control for aphids",
    "Any alerts in my county?",
]


def chat_reply(question, context=None):
    """Return {"answer", "related", "suggestions"} for the chatbox.

    Works fully offline from the knowledge base; uses the Anthropic API only
    when a key is configured, and falls back silently if the call fails.
    """
    context = context or {}
    raw = (question or "").strip()
    q = _normalise(raw)
    tokens = set(re.findall(r"[a-z]+", q))
    name = context.get("name")
    county = context.get("county")

    llm = _claude_chat(raw, context)
    if llm:
        return {"answer": llm, "related": [], "suggestions": DEFAULT_SUGGESTIONS}

    # greetings / thanks / help
    if tokens & {"hi", "hello", "hey", "habari", "jambo", "mambo", "hujambo", "good"} and len(tokens) <= 4:
        greet = f"Hello{', ' + name if name else ''}! 🌱 "
        if county:
            greet += f"I see you farm in **{county}**. "
        return {"answer": greet + "I'm Ukulima, your crop advisory assistant. Tell me your crop and what you see "
                 "(for example: *maize leaves with holes and sawdust*), and I'll suggest what it is and how to "
                 "control it safely. You can also ask about prevention, organic options, alerts or how to report.",
                "related": [], "suggestions": DEFAULT_SUGGESTIONS}
    if tokens & {"thanks", "asante", "thank"}:
        return {"answer": "Karibu! 🌾 Remember: scout your fields twice a week and report anything unusual early — "
                 "your neighbours benefit too. Ask me anything else about your crops.",
                "related": [], "suggestions": DEFAULT_SUGGESTIONS}
    if ("what can you do" in q or q in ("help", "msaada") or "capabilities" in q):
        return {"answer": "Here's how I can help:\n"
                 "- **Identify problems** — describe the crop and symptoms, get the likely pest or disease.\n"
                 "- **Control advice** — cultural, biological and safe chemical options from our expert library.\n"
                 "- **Prevention** — stop problems before they start.\n"
                 "- **Alerts** — what's been reported near you.\n"
                 "- **Reporting** — how to submit a photo report for officer review.\n\n"
                 "I cover maize, potato, tomato, coffee, banana, cassava, kale, cabbage and beans.",
                "related": [], "suggestions": DEFAULT_SUGGESTIONS}

    # how to report
    if ("report" in q and ("how" in q or "submit" in q or "steps" in q or q == "report")) or "how do i report" in q:
        return {"answer": "Reporting takes about a minute:\n"
                 "1. Open **[New report](/report/new)**.\n"
                 "2. Choose your **crop** and **county**, tick the symptoms you see.\n"
                 "3. Add a **photo** and a short description — photos make the AI much more accurate.\n"
                 "4. Share your location (GPS button) or we use your county centre.\n"
                 "5. Submit. The AI suggests a diagnosis; tricky or severe cases go to an **extension officer**.\n\n"
                 "Track everything under **[My reports](/reports)**.",
                "related": [], "suggestions": ["What alerts are near me?", "My maize has holes and sawdust"]}

    # alerts / outbreaks
    if tokens & {"alert", "alerts", "outbreak", "outbreaks", "warning"} or "near me" in q or "my county" in q:
        alerts = context.get("alerts") or []
        if county:
            local = [a for a in alerts if a.get("county") in (county, "All counties")]
            if local:
                lines = [f"**Active alerts for {county}:**"]
                lines += [f"- {a['message']} ({a['created'][:10]})" for a in local[:3]]
                lines += ["", "Scout your fields now and open the **[pest library](/knowledge)** for control advice."]
                return {"answer": "\n".join(lines), "related": [],
                        "suggestions": ["How do I report a crop problem?", "See the outbreak map"]}
        if alerts:
            lines = ["**Latest alerts across Kenya:**"]
            lines += [f"- **{a['county']}**: {a['message']} ({a['created'][:10]})" for a in alerts[:3]]
            lines += ["", "See the live **[outbreak map](/map)** for clusters and trends."]
            return {"answer": "\n".join(lines), "related": [], "suggestions": DEFAULT_SUGGESTIONS}
        return {"answer": "There are **no active alerts** right now — good news! 🎉 Alerts fire automatically when "
                 "3 or more reports of the same pest appear in one county within 14 days. Check the "
                 "**[outbreak map](/map)** any time to see what's being reported.",
                "related": [], "suggestions": DEFAULT_SUGGESTIONS}
    if "map" in q and ("see" in q or "open" in q or "where" in q):
        return {"answer": "The **[outbreak map](/map)** shows Kenya's 47 counties shaded by report counts, with pins "
                 "for each report, a heatmap of clusters and a trend chart. Filter by crop and period, and click any "
                 "county for its top pests.",
                "related": [], "suggestions": DEFAULT_SUGGESTIONS}

    # focus intents + pest matching
    ranked = _match(q)
    focus = None
    if tokens & {"prevent", "prevention", "avoid", "stop", "kinga"}:
        focus = "prevent"
    elif tokens & {"organic", "neem", "natural", "biological", "bio", "home"}:
        focus = "organic"
    elif tokens & {"chemical", "chemicals", "pesticide", "pesticides", "spray", "spraying", "dawa", "fungicide", "insecticide"}:
        focus = "chemical"

    if ranked:
        k = ranked[0][1]
        suggestions = [f"How do I prevent {k['name'].lower()}?",
                       f"Organic control for {k['name'].lower()}",
                       "How do I report a crop problem?"]
        related = [k["id"]] + [kk["id"] for _, kk in ranked[1:3]]
        return {"answer": _kb_answer(k, focus), "related": related, "suggestions": suggestions}

    # crop-only question: list what affects it
    crops_in_q = [c for c in CROPS if c.lower() in tokens and c != "Other"]
    if crops_in_q:
        crop = crops_in_q[0]
        entries = [k for k in KB if crop in k["crops"]]
        lines = [f"**Problems we track on {crop.lower()}:**"]
        lines += [f"- **{k['name']}** — {k['description'].split('.')[0]}." for k in entries]
        lines += ["", "Tell me what you see on your crop (holes, yellowing, wilting, powder…) and I'll narrow it down."]
        return {"answer": "\n".join(lines), "related": [k["id"] for k in entries[:3]],
                "suggestions": [f"What eats holes in {crop.lower()} leaves?", f"How do I prevent problems in {crop.lower()}?"]}

    # general safety question without a match
    if focus == "chemical":
        return {"answer": "**Chemical safety, always:**\n"
                 "- Use only products registered by the **Pest Control Products Board (PCPB)** for your crop and pest.\n"
                 "- Follow the label exactly: dose, timing, protective clothing and pre-harvest interval.\n"
                 "- Rotate active ingredients to slow resistance; never spray during flowering to protect bees.\n"
                 "- Ask your **county extension officer** to recommend a product — I can't name brands or doses.\n\n"
                 "Tell me the crop and symptoms and I'll point you to the right library guide.",
                "related": [], "suggestions": DEFAULT_SUGGESTIONS}

    return {"answer": "I couldn't match that to a pest or disease in my library yet. 🌱 Try telling me:\n"
             "- the **crop** (maize, potato, tomato, coffee, banana, cassava, kale, cabbage, beans), and\n"
             "- **what you see** (holes, yellowing, wilting, orange powder, sticky leaves…).\n\n"
             "For example: *\"my maize leaves have ragged holes and sawdust in the funnel\"*. "
             "Or **[submit a report with a photo](/report/new)** — an officer will review tricky cases.",
            "related": [], "suggestions": DEFAULT_SUGGESTIONS}