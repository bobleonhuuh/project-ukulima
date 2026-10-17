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