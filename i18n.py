"""Ukulima internationalisation.

A tiny, dependency-free translator. Strings live in TRANSLATIONS keyed by an id;
each id maps to {"en": ..., "sw": ...}. The active language is stored in the
Flask session and read through t(). Missing translations fall back to English
and then to the key itself, so a typo can never crash a page.
"""

LANGS = {"en": "English", "sw": "Kiswahili"}
DEFAULT_LANG = "en"

TRANSLATIONS = {
    # brand / nav
    "nav.map": {"en": "Outbreak map", "sw": "Ramani ya magonjwa"},
    "nav.library": {"en": "Pest library", "sw": "Maktaba ya wadudu"},
    "nav.alerts": {"en": "Alerts", "sw": "Tahadhari"},
    "nav.new_report": {"en": "New report", "sw": "Ripoti mpya"},
    "nav.my_reports": {"en": "My reports", "sw": "Ripoti zangu"},
    "nav.review": {"en": "Review queue", "sw": "Foleni ya uhakiki"},
    "nav.admin": {"en": "Admin", "sw": "Msimamizi"},
    "nav.ask": {"en": "Ask Ukulima", "sw": "Uliza Ukulima"},
    "nav.login": {"en": "Log in", "sw": "Ingia"},
    "nav.signup": {"en": "Sign up", "sw": "Jisajili"},
    "nav.logout": {"en": "Log out", "sw": "Toka"},

    # hero
    "hero.eyebrow": {"en": "For Kenyan smallholder farmers", "sw": "Kwa wakulima wadogo wa Kenya"},
    "hero.title": {"en": "Spot it early. Report it. Protect your harvest.",
                   "sw": "Tambua mapema. Ripoti. Linda mavuno yako."},
    "hero.subtitle": {
        "en": "Photograph a sick crop, tell Ukulima what you see, and get AI-assisted advice in seconds - checked by agricultural officers and shared on a live outbreak map.",
        "sw": "Piga picha ya zao lililouguka, ambia Ukulima unachokiona, na upate ushauri wa AI kwa sekunde chache - ukikaguliwa na maofisa wa kilimo na kushirikiwa kwenye ramani hai ya magonjwa."},
    "hero.cta.report": {"en": "Report a problem", "sw": "Ripoti tatizo"},
    "hero.cta.join": {"en": "Create a free account", "sw": "Fungua akaunti bure"},
    "hero.cta.map": {"en": "See the outbreak map", "sw": "Tazama ramani"},

    # stats
    "stat.reports": {"en": "reports submitted", "sw": "ripoti zilizotumwa"},
    "stat.verified": {"en": "reviewed by officers", "sw": "zimehakikiwa na maofisa"},
    "stat.counties": {"en": "counties reporting", "sw": "kaunti zinazoripoti"},

    # how it works
    "how.title": {"en": "How it works", "sw": "Jinsi inavyofanya kazi"},
    "how.1.title": {"en": "Report", "sw": "Ripoti"},
    "how.1.body": {"en": "Choose your crop, tick the symptoms, add a photo and share your location.",
                   "sw": "Chagua zao lako, weka alama kwenye dalili, ongeza picha na shiriki eneo lako."},
    "how.2.title": {"en": "Get advice", "sw": "Pata ushauri"},
    "how.2.body": {"en": "The AI suggests the most likely pest or disease with a confidence score and practical, safe control steps.",
                   "sw": "AI inapendekeza mdudu au ugonjwa unaowezekana zaidi pamoja na kiwango cha uhakika na hatua salama za kudhibiti."},
    "how.3.title": {"en": "Protect your area", "sw": "Linda eneo lako"},
    "how.3.body": {"en": "Officers verify tricky cases. When cases cluster, nearby farmers get an early warning.",
                   "sw": "Maofisa huhakiki kesi ngumu. Kesi zikijilimbikiza, wakulima wa karibu hupata tahadhari ya mapema."},

    # alerts block
    "alerts.latest": {"en": "Latest alerts", "sw": "Tahadhari za hivi karibuni"},

    # forms / report
    "report.title": {"en": "Report a crop problem", "sw": "Ripoti tatizo la zao"},
    "report.crop": {"en": "Crop", "sw": "Zao"},
    "report.county": {"en": "County", "sw": "Kaunti"},
    "report.symptoms": {"en": "Symptoms you see", "sw": "Dalili unazoziona"},
    "report.describe": {"en": "Describe in your own words", "sw": "Eleza kwa maneno yako"},
    "report.photo": {"en": "Photo of the crop", "sw": "Picha ya zao"},
    "report.location": {"en": "Farm location", "sw": "Eneo la shamba"},
    "report.use_gps": {"en": "Use my GPS", "sw": "Tumia GPS yangu"},
    "report.growth": {"en": "Growth stage", "sw": "Hatua ya ukuaji"},
    "report.severity": {"en": "How severe?", "sw": "Kali kiasi gani?"},
    "report.submit": {"en": "Submit report", "sw": "Tuma ripoti"},
    "sev.low": {"en": "Low", "sw": "Ndogo"},
    "sev.medium": {"en": "Medium", "sw": "Wastani"},
    "sev.high": {"en": "High", "sw": "Kali"},

    # auth
    "auth.email": {"en": "Email", "sw": "Barua pepe"},
    "auth.password": {"en": "Password", "sw": "Nenosiri"},
    "auth.name": {"en": "Full name", "sw": "Jina kamili"},
    "auth.phone": {"en": "Phone (optional)", "sw": "Simu (si lazima)"},
    "auth.login_title": {"en": "Welcome back", "sw": "Karibu tena"},
    "auth.register_title": {"en": "Create your account", "sw": "Fungua akaunti yako"},

    # generic
    "common.language": {"en": "Language", "sw": "Lugha"},
    "common.advice": {"en": "Advisory", "sw": "Ushauri"},
    "common.confidence": {"en": "Confidence", "sw": "Uhakika"},
    "common.status": {"en": "Status", "sw": "Hali"},
    "common.back": {"en": "Back", "sw": "Rudi"},

    # map
    "map.intro": {"en": "Kenya only — all 47 counties. Each pin is a report (location rounded to ~1 km). Counties are shaded by report counts; click a county for details.",
                  "sw": "Kenya pekee — kaunti zote 47. Kila pini ni ripoti (eneo limekadiria hadi ~1 km). Kaunti zimepakwa rangi kulingana na idadi ya ripoti; bofya kaunti kwa maelezo."},
    "map.controls": {"en": "Map controls", "sw": "Vidhibiti vya ramani"},
    "map.all_crops": {"en": "All crops", "sw": "Mazao yote"},
    "map.period": {"en": "Period", "sw": "Kipindi"},
    "map.d14": {"en": "Last 14 days", "sw": "Siku 14 zilizopita"},
    "map.d30": {"en": "Last 30 days", "sw": "Siku 30 zilizopita"},
    "map.d60": {"en": "Last 60 days", "sw": "Siku 60 zilizopita"},
    "map.d180": {"en": "Last 6 months", "sw": "Miezi 6 iliyopita"},
    "map.fill": {"en": "County shading", "sw": "Rangi ya kaunti"},
    "map.fill_count": {"en": "Report count", "sw": "Idadi ya ripoti"},
    "map.fill_high": {"en": "High severity", "sw": "kali sana"},
    "map.fill_none": {"en": "No shading", "sw": "Bila rangi"},
    "map.heatmap": {"en": "Heatmap", "sw": "Ramani joto"},
    "map.pins": {"en": "Pins", "sw": "Pini"},
    "map.labels": {"en": "Labels", "sw": "Lebo"},
    "map.zoom_in": {"en": "Zoom in", "sw": "Kuza ndani"},
    "map.zoom_out": {"en": "Zoom out", "sw": "Kuza nje"},
    "map.reset": {"en": "Reset view", "sw": "Rudisha mwonekano"},
    "map.export": {"en": "Export CSV", "sw": "Pakua CSV"},
    "map.kenya_only": {"en": "Kenya only · 47 counties", "sw": "Kenya pekee · kaunti 47"},
    "map.reports": {"en": "reports", "sw": "ripoti"},
    "map.high_sev": {"en": "high severity", "sw": "kali sana"},
    "map.top_pests": {"en": "Most reported here", "sw": "Zilizoripotiwa zaidi hapa"},
    "map.no_reports": {"en": "No reports in this period.", "sw": "Hakuna ripoti katika kipindi hiki."},
    "map.verified": {"en": "Verified by officer", "sw": "Imethibitishwa na afisa"},
    "map.ramp": {"en": "Fewer → more reports", "sw": "Chache → ripoti nyingi"},
    "map.trend": {"en": "Reports over time", "sw": "Ripoti kwa wakati"},

    # assistant
    "assistant.title": {"en": "Ask Ukulima", "sw": "Uliza Ukulima"},
    "assistant.subtitle": {"en": "Your AI crop advisory assistant — describe what you see and get safe, practical control steps from our expert-reviewed library.",
                           "sw": "Msaidizi wako wa ushauri wa mazao wa AI — eleza unachokiona na upate hatua salama za kudhibiti kutoka maktaba yetu iliyokaguliwa na wataalamu."},
    "assistant.online": {"en": "Online · expert library", "sw": "Mtandaoni · maktaba ya wataalamu"},
    "assistant.new": {"en": "New conversation", "sw": "Mazungumzo mapya"},
    "assistant.placeholder": {"en": "Type your question… e.g. maize leaves with holes and sawdust",
                              "sw": "Andika swali lako… mf. majani ya mahindi yenye matundu na unga wa mbao"},
    "assistant.send": {"en": "Send", "sw": "Tuma"},
    "assistant.q1": {"en": "My maize has holes and sawdust", "sw": "Mahindi yangu yana matundu na unga wa mbao"},
    "assistant.q2": {"en": "How do I report a problem?", "sw": "Ninawezaje kuripoti tatizo?"},
    "assistant.q3": {"en": "Organic control for aphids", "sw": "Kudhibiti vidukari kwa njia asilia"},
    "assistant.q4": {"en": "Any alerts in my county?", "sw": "Kuna tahadhari katika kaunti yangu?"},
    "assistant.disclaimer": {"en": "AI advice is advisory — severe cases are checked by an officer.",
                             "sw": "Ushauri wa AI ni mwongozo — kesi kali hukaguliwa na afisa."},
    "assistant.help_title": {"en": "What I can do", "sw": "Ninachoweza kufanya"},
    "assistant.cap1_t": {"en": "Identify problems", "sw": "Tambua matatizo"},
    "assistant.cap1_b": {"en": "Describe crop + symptoms, get the likely pest or disease.", "sw": "Eleza zao + dalili, pata mdudu au ugonjwa unaowezekana."},
    "assistant.cap2_t": {"en": "Safe control steps", "sw": "Hatua salama za kudhibiti"},
    "assistant.cap2_b": {"en": "Cultural, biological and PCPB-registered chemical guidance.", "sw": "Mwongozo wa kilimo, kibiolojia na kemikali zilizosajiliwa na PCPB."},
    "assistant.cap3_t": {"en": "Alerts near you", "sw": "Tahadhari karibu nawe"},
    "assistant.cap3_b": {"en": "What's been reported in your county lately.", "sw": "Yaliyoripotiwa katika kaunti yako hivi karibuni."},
    "assistant.cap4_t": {"en": "Reporting help", "sw": "Msaada wa kuripoti"},
    "assistant.cap4_b": {"en": "How to submit a photo report for officer review.", "sw": "Jinsi ya kutuma ripoti ya picha kwa uhakiki wa afisa."},
    "assistant.crops_title": {"en": "Crops I cover", "sw": "Mazao ninayoshughulikia"},
    "assistant.crops_hint": {"en": "Tap a crop to browse its pest library.", "sw": "Gusa zao kuvinjari maktaba yake ya wadudu."},
    "assistant.safety": {"en": "Never mix chemicals without label guidance. When in doubt, ask your county extension officer.",
                         "sw": "Usichanganye kemikali bila mwongozo wa lebo. Ukiwa na shaka, uliza afisa wa ugani wa kaunti yako."},
    "assistant.welcome": {"en": "Habari {name}! 🌱 I'm **Ukulima**, your crop advisory assistant.{county}\n\nTell me your **crop** and **what you see** — for example *\"maize leaves with holes and sawdust\"* — and I'll suggest what it is and how to control it safely. Try one of the prompts below to begin.",
                          "sw": "Habari {name}! 🌱 Mimi ni **Ukulima**, msaidizi wako wa ushauri wa mazao.{county}\n\nNiambie **zao** lako na **unachokiona** — kwa mfano *\"majani ya mahindi yenye matundu na unga wa mbao\"* — nami nitapendekeza ni nini na jinsi ya kudhibiti kwa usalama. Jaribu mojawapo ya vidokezo hapa chini kuanza."},
    "assistant.thinking": {"en": "Thinking…", "sw": "Ninafikiria…"},
    "assistant.error": {"en": "Could not reach the assistant. Check your connection and try again.",
                        "sw": "Imeshindikana kufikia msaidizi. Angalia mtandao wako na ujaribu tena."},
    "assistant.retry": {"en": "Retry", "sw": "Jaribu tena"},
    "assistant.related": {"en": "From the library", "sw": "Kutoka maktaba"},

    # admin
    "admin.title": {"en": "Admin dashboard", "sw": "Dashibodi ya msimamizi"},
    "admin.subtitle": {"en": "Manage user roles and keep an eye on platform activity.",
                       "sw": "Dhibiti majukumu ya watumiaji na fuatilia shughuli za jukwaa."},
    "admin.users": {"en": "Registered users", "sw": "Watumiaji waliosajiliwa"},
    "admin.staff": {"en": "Officers & admins", "sw": "Maafisa na wasimamizi"},
    "admin.reports": {"en": "Total reports", "sw": "Jumla ya ripoti"},
    "admin.pending": {"en": "pending", "sw": "zinasubiri"},
    "admin.alerts": {"en": "Alerts issued", "sw": "Tahadhari zilizotolewa"},
    "admin.search": {"en": "Search name, email or county…", "sw": "Tafuta jina, barua pepe au kaunti…"},
    "admin.search_btn": {"en": "Search", "sw": "Tafuta"},
    "admin.clear": {"en": "Clear", "sw": "Futa"},
    "admin.role": {"en": "Role", "sw": "Jukumu"},
    "admin.joined": {"en": "Joined", "sw": "Alijiunga"},
    "admin.change_role": {"en": "Change role", "sw": "Badilisha jukumu"},
    "admin.you": {"en": "you", "sw": "wewe"},
    "admin.save": {"en": "Save", "sw": "Hifadhi"},
    "admin.no_users": {"en": "No users match your search.", "sw": "Hakuna watumiaji wanaolingana na utafutaji wako."},
    "admin.recent": {"en": "Recent reports", "sw": "Ripoti za hivi karibuni"},
    "admin.farmer": {"en": "Farmer", "sw": "Mkulima"},
    "admin.date": {"en": "Date", "sw": "Tarehe"},
    "admin.no_reports": {"en": "No reports yet.", "sw": "Hakuna ripoti bado."},
}


def t(key, lang=DEFAULT_LANG):
    """Return the translated string for key in lang, falling back safely."""
    entry = TRANSLATIONS.get(key)
    if not entry:
        return key
    return entry.get(lang) or entry.get(DEFAULT_LANG) or key


def translator(lang):
    """Return a t()-like function bound to a specific language."""
    def _t(key):
        return t(key, lang)
    return _t