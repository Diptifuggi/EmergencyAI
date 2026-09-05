"""Reviewed multilingual evidence vocabulary for deterministic triage."""
from __future__ import annotations

KEYWORDS: dict[str, dict[str, tuple[str, ...]]] = {
    "en": {
        "accident": ("accident", "crash", "collision", "pile-up", "hit and run", "overturned"),
        "major": ("major", "serious", "severe", "multiple casualties", "mass casualty"),
        "injury": ("injured", "injury", "wounded", "hurt", "fracture", "broken bone", "burn", "casualties"),
        "bleeding": ("bleeding", "severe bleeding", "blood"),
        "unconscious": ("unconscious", "passed out", "not responding"),
        "medical": ("medical", "chest pain", "heart pain", "pain in chest", "chest pressure", "cannot breathe", "difficulty breathing", "shortness of breath", "heart attack", "ambulance"),
        "fire": ("fire", "smoke", "flames", "burning"),
        "explosion": ("explosion", "exploded", "blast", "bomb blast"),
        "trapped": ("trapped", "entrapment", "stuck", "cannot escape", "under debris", "vehicle trapped", "train trapped"),
        "rescue": ("rescue", "rescue needed", "people trapped", "technical rescue", "building collapse", "collapsed building", "rubble", "debris"),
        "railway": ("railway", "railroad", "train", "railway station", "rail station", "platform", "derailment", "railway track"),
        "road": ("road accident", "car accident", "bike accident", "motorcycle accident", "truck accident", "bus accident", "vehicle collision", "highway accident", "traffic accident", "major collision"),
        "highway": ("highway", "expressway", "national highway"),
        "police": ("police", "robbery", "theft", "assault", "fight", "violence", "threat", "kidnapping", "missing person", "following me", "being followed"),
        "weapon": ("gun", "pistol", "rifle", "knife", "weapon", "shooting", "gunshot", "firearm", "revolver", "bomb", "armed person"),
        "domestic_violence": ("husband beating", "wife beating", "domestic abuse", "domestic violence", "partner beating", "family violence", "beating me", "hitting me", "my husband beat", "save me from husband"),
        "child_missing": ("child is missing", "missing child", "kid is missing", "son is missing", "daughter is missing"),
        "cybercrime": ("cyber fraud", "online fraud", "online scam", "money stolen online", "bank account hacked", "hacked", "phishing", "cyber crime"),
        "lpg": ("gas leakage", "gas leak", "lpg leak", "lpg cylinder", "gas from my lpg cylinder", "cylinder leak", "cooking gas", "smell gas"),
        "immediate": ("immediate", "urgent", "help now", "please send", "hurry", "hurry up", "ambulance immediately", "following me", "being followed"),
        "no_injury": ("nobody is injured", "no one is injured", "no injuries", "not injured"),
    },
    "hi": {
        "accident": ("दुर्घटना", "हादसा", "टक्कर"), "major": ("बड़ी", "गंभीर"), "injury": ("घायल", "चोट", "जख्मी"),
        "bleeding": ("खून", "खून बह रहा"), "unconscious": ("बेहोश",), "medical": ("चिकित्सा", "छाती में दर्द", "सांस नहीं"),
        "fire": ("आग", "धुआं", "जल रहा"), "explosion": ("विस्फोट", "धमाका"), "trapped": ("फंसे", "फंसा", "अटक"),
        "rescue": ("बचाव",), "railway": ("रेलवे", "ट्रेन", "स्टेशन"), "police": ("पुलिस", "चोरी", "धमकी"),
        "weapon": ("हथियार", "बंदूक", "चाकू"), "domestic_violence": ("घरेलू हिंसा", "पति मार"), "child_missing": ("बच्चा लापता", "बच्चा गुम"),
        "cybercrime": ("साइबर अपराध", "ऑनलाइन धोखाधड़ी"), "lpg": ("गैस रिसाव", "सिलेंडर लीक"),
    },
    "gu": {
        "accident": ("અકસ્મત", "અકસ્માત", "ટક્કર"), "major": ("મોટો", "ગંભીર"), "injury": ("ઇજા", "ઘાયલ"),
        "bleeding": ("લોહી",), "medical": ("તબીબી", "છાતીમાં દુખાવો", "શ્વાસ"), "fire": ("આગ", "ધુમાડો"),
        "explosion": ("વિસ્ફોટ",), "trapped": ("ફસાયેલા", "ફસાયેલ"), "rescue": ("બચાવ",),
        "railway": ("રેલવે", "ટ્રેન", "સ્ટેશન"), "police": ("પોલીસ", "ચોરી", "ધમકી"), "weapon": ("હથિયાર",),
        "domestic_violence": ("ઘરેલું હિંસા", "પતિ માર"), "child_missing": ("બાળક ગુમ"), "cybercrime": ("સાયબર છેતરપિંડી",), "lpg": ("ગેસ લીક",),
    },
    "mr": {
        "accident": ("अपघात", "धडक"), "major": ("मोठा", "गंभीर"), "injury": ("जखमी", "दुखापत"),
        "bleeding": ("रक्त",), "medical": ("वैद्यकीय", "छातीत दुखणे", "श्वास"), "fire": ("आग", "धूर"),
        "explosion": ("स्फोट",), "trapped": ("अडकले", "अडकलेले"), "rescue": ("बचाव",),
        "railway": ("रेल्वे", "ट्रेन", "स्थानक"), "police": ("पोलीस", "चोरी", "धमकी"), "weapon": ("शस्त्र",),
        "domestic_violence": ("घरगुती हिंसा", "पती मार"), "child_missing": ("मूल हरवले",), "cybercrime": ("सायबर फसवणूक",), "lpg": ("गॅस गळती",),
    },
}


def evidence(text: str, language: str = "en") -> dict[str, bool]:
    lowered = text.casefold()
    dictionaries = [KEYWORDS.get(language, {}), KEYWORDS["en"]]
    result: dict[str, bool] = {}
    for category in {key for dictionary in dictionaries for key in dictionary}:
        result[category] = any(
            _phrase_is_affirmed(lowered, phrase.casefold())
            for dictionary in dictionaries
            for phrase in dictionary.get(category, ())
        )
    return result


def _phrase_is_affirmed(text: str, phrase: str) -> bool:
    start = text.find(phrase)
    while start >= 0:
        context = text[max(0, start - 18):start]
        if not any(marker in context for marker in ("no ", "nobody is ", "no one is ", "not ", "without ", "never ")):
            return True
        start = text.find(phrase, start + len(phrase))
    return False
