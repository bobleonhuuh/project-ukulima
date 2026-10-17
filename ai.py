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


def chat_answer(question):
    """Answer a farmer question from the knowledge base; LLM-enhanced if a key is set."""
    q = (question or "").lower()
    best = None
    for k in KB:
        s = sum(1 for w in k["keywords"] + [k["name"].lower()] + [c.lower() for c in k["crops"]] if w in q)
        if s and (not best or s > best[0]):
            best = (s, k)

    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        ctx = json.dumps([{"name": k["name"], "crops": k["crops"],
                           "description": k["description"], "advice": k["advice"]} for k in KB])
        body = json.dumps({
            "model": os.environ.get("UKULIMA_MODEL", "claude-sonnet-4-6"),
            "max_tokens": 500,
            "system": ("You are Ukulima, a crop advisory assistant for Kenyan smallholders. "
                       "Answer briefly in simple English using ONLY this knowledge base for pest "
                       "and disease control; never invent product names or doses; refer to "
                       "PCPB-registered products and extension officers for chemicals. If the "
                       "answer is not in the knowledge base, say so. Knowledge base: " + ctx),
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

    if not best:
        return ("I could not match that to a pest or disease in my library. Try naming the crop "
                "and what you see (for example: 'maize leaves with holes and sawdust'), or submit "
                "a report with a photo.")
    k = best[1]
    a = k["advice"]
    return (f"{k['name']} ({k['type'].lower()}). {k['description']} "
            f"Cultural control: {a['cultural'][0]} Prevention: {a['prevention'][0]} "
            f"For chemicals, ask your extension officer for a PCPB-registered product.")