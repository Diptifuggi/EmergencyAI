"""Reviewed multilingual evidence vocabulary for deterministic triage."""
from __future__ import annotations

import re
from functools import lru_cache

from .emergency_lexicon import supporting_evidence

_W = r"[\w\u0900-\u097F\u0A80-\u0AFF]"
_CLAUSE_BREAK = re.compile(
    r"[,.;!?।]|\b(?:and|but|ane|aur)\b|और|लेकिन|आणि|पण|અને|પણ",
    re.IGNORECASE,
)
_NEGATION_WORDS = (
    "not", "no", "never", "didn't", "did not", "wasn't", "was not",
    "without", "nobody", "no one", "नहीं", "नही", "कोई नहीं", "न कोई",
    "નથી", "નહીં", "નાહી", "नाही", "nahi", "nahin", "nathi",
)

KEYWORDS: dict[str, dict[str, tuple[str, ...]]] = {
    "en": {
        "accident": ("accident", "accident ho gaya", "crash", "collision", "pile-up", "hit and run", "overturned", "aksident", "apghat", "apghaat", "thokar", "takra", "takkar maari", "gaadi ne uda diya", "kuchal diya", "bike slip"),
        "major": ("major", "serious", "severe", "multiple casualties", "mass casualty"),
        "injury": ("injured", "injury", "wounded", "hurt", "fracture", "broken bone", "burn", "casualties", "ghayal", "jakhmi", "jakhmi hain"),
        "bleeding": ("bleeding", "severe bleeding", "blood", "khoon beh raha"),
        "unconscious": ("unconscious", "passed out", "not responding", "behosh"),
        "medical": ("medical", "medical help", "medical assistance", "chest pain", "heart pain", "pain in chest", "chest pressure", "cannot breathe", "difficulty breathing", "shortness of breath", "heart attack", "ambulance", "behosh", "saans nahi", "sans nahi"),
        "fire": ("fire", "flames", "burning", "aag lag gayi"), "smoke": ("smoke",),
        "explosion": ("explosion", "exploded", "blast", "bomb blast"),
        "trapped": ("trapped", "entrapment", "stuck", "cannot escape", "under debris", "vehicle trapped", "train trapped"),
        "rescue": ("rescue", "rescue needed", "people trapped", "technical rescue", "building collapse", "collapsed building", "rubble", "debris"),
        "railway": ("railway", "railroad", "train", "railway station", "rail station", "platform", "derailment", "derailed", "railway track", "train accident", "rail ve station", "train patri"),
        "road": ("road accident", "car accident", "bike accident", "motorcycle accident", "truck accident", "bus accident", "vehicle collision", "highway accident", "traffic accident", "major collision", "cars collided", "two cars hit", "vehicles crashed"),
        "highway": ("highway", "expressway", "national highway"),
        "police": ("police", "robbery", "theft", "assault", "fight", "violence", "threat", "kidnapping", "missing person", "following me", "being followed"),
        "weapon": ("gun", "pistol", "rifle", "knife", "weapon", "shooting", "gunshot", "firearm", "revolver", "bomb", "armed person"),
        "domestic_violence": ("husband beating", "wife beating", "domestic abuse", "domestic violence", "partner beating", "family violence", "beating me", "hitting me", "my husband beat", "save me from husband"),
        "child_missing": ("child is missing", "missing child", "kid is missing", "son is missing", "daughter is missing"),
        "cybercrime": ("cyber fraud", "online fraud", "online scam", "money stolen online", "bank account hacked", "hacked", "phishing", "cyber crime"),
        "lpg": ("gas leakage", "gas leak", "lpg leak", "lpg cylinder", "gas from my lpg cylinder", "cylinder leak", "cooking gas", "smell gas", "cylinder phat gaya"),
        "immediate": ("immediate", "urgent", "help now", "please send", "send help", "hurry", "hurry up", "ambulance immediately", "following me", "being followed", "jaldi", "bachao"),
        "request": ("help me", "i need help", "send help", "please help", "madad chahiye", "mujhe madad chahiye", "madad bhejo", "ambulance bhejo", "mane madad joie chhe", "madad moklo", "mala madat havi aahe", "madat pathva"),
        "no_injury": ("nobody is injured", "no one is injured", "no injuries", "not injured"),
        "high_risk_medical": (
            "unconscious", "passed out", "not responding", "not breathing",
            "cannot breathe", "can't breathe", "difficulty breathing",
            "shortness of breath", "chest pain", "चेस्ट में दर्द",
            "छाती में दर्द", "सीने में दर्द", "severe bleeding",
            "heavy bleeding", "heart attack", "cardiac arrest", "stroke",
        ),
    },
    "hi": {
        "accident": ("दुर्घटना", "हादसा", "हादसे", "अकस्मात", "एक्सीडेंट", "एक्सिडेंट", "टक्कर", "भिड़ गए", "भिड़ गई", "टक्कर मारी", "गाड़ी ने उड़ा दिया", "कुचल दिया", "बाइक स्लिप"), "major": ("बड़ी", "गंभीर"), "injury": ("घायल", "घायल हैं", "चोट", "जख्मी"),
        "bleeding": ("खून", "खून बह रहा", "खून बह रहा है"), "unconscious": ("बेहोश",), "medical": ("चिकित्सा", "छाती में दर्द", "सांस नहीं", "हार्ट अटैक", "एम्बुलेंस", "ऐम्बुलेंस"),
        "fire": ("आग", "जल रहा", "आग लग गई", "फायर ब्रिगेड"), "smoke": ("धुआं",), "explosion": ("विस्फोट", "धमाका", "सिलेंडर फट गया"), "trapped": ("फंसे", "फंसा", "अटक"),
        "rescue": ("बचाव",), "trapped": ("फंसे", "फंसा", "फंस गए", "फंस गया", "अंदर फंसे"), "railway": ("रेलवे", "ट्रेन", "रेल हादसा", "पटरी से उतर", "स्टेशन"), "road": ("सड़क हादसा", "गाड़ी टकर", "गाड़ियां टकर", "हाईवे", "भिड़ गए", "भिड़ गई"), "police": ("पुलिस", "चोरी", "धमकी"),
        "weapon": ("हथियार", "बंदूक", "चाकू"), "child": ("बच्चा", "बच्चे", "बच्चों", "बालक"), "domestic_violence": ("घरेलू हिंसा", "पति मार"), "child_missing": ("बच्चा लापता", "बच्चा गुम"),
        "cybercrime": ("साइबर अपराध", "ऑनलाइन धोखाधड़ी"), "lpg": ("गैस रिसाव", "सिलेंडर लीक"),
        "no_injury": ("कोई घायल नहीं", "कोई चोट नहीं"),
        "high_risk_medical": (
            "बेहोश", "सांस नहीं ले", "सांस नहीं आ", "सांस लेने में तकलीफ",
            "सांस लेने में कठिनाई", "सीने में दर्द", "छाती में दर्द",
            "चेस्ट में दर्द",
            "दिल का दौरा", "हार्ट अटैक", "बहुत खून बह", "खून बह रहा है",
        ),
    },
    "gu": {
        "accident": ("અકસ્મત", "અકસ્માત", "ટક્કર"), "major": ("મોટો", "ગંભીર"), "injury": ("ઇજા", "ઘાયલ"),
        "bleeding": ("લોહી",), "medical": ("તબીબી", "છાતીમાં દુખાવો", "શ્વાસ"), "fire": ("આગ",), "smoke": ("ધુમાડો",),
        "explosion": ("વિસ્ફોટ",), "trapped": ("ફસાયેલા", "ફસાયેલ"), "rescue": ("બચાવ",),
        "railway": ("રેલવે", "ટ્રેન", "સ્ટેશન"), "police": ("પોલીસ", "ચોરી", "ધમકી"), "weapon": ("હથિયાર",),
        "domestic_violence": ("ઘરેલું હિંસા", "પતિ માર"), "child_missing": ("બાળક ગુમ",), "cybercrime": ("સાયબર છેતરપિંડી",), "lpg": ("ગેસ લીક",),
        "high_risk_medical": (
            "બેભાન", "શ્વાસ નથી", "શ્વાસ લેવામાં તકલીફ", "છાતીમાં દુખાવો",
            "હાર્ટ એટેક", "હૃદયરોગનો હુમલો", "ખૂબ લોહી વહી રહ્યું",
            "લોહી વહી રહ્યું છે",
        ),
    },
    "mr": {
        "accident": ("अपघात", "धडक"), "major": ("मोठा", "गंभीर"), "injury": ("जखमी", "दुखापत"),
        "bleeding": ("रक्त",), "medical": ("वैद्यकीय", "छातीत दुखणे", "श्वास"), "fire": ("आग",), "smoke": ("धूर",),
        "explosion": ("स्फोट",), "trapped": ("अडकले", "अडकलेले"), "rescue": ("बचाव",),
        "railway": ("रेल्वे", "ट्रेन", "स्थानक"), "police": ("पोलीस", "चोरी", "धमकी"), "weapon": ("शस्त्र",),
        "domestic_violence": ("घरगुती हिंसा", "पती मार"), "child_missing": ("मूल हरवले",), "cybercrime": ("सायबर फसवणूक",), "lpg": ("गॅस गळती",),
        "high_risk_medical": (
            "बेशुद्ध", "श्वास घेत नाही", "श्वास घेण्यास त्रास", "छातीत दुखणे",
            "हृदयविकाराचा झटका", "हार्ट अटॅक", "जास्त रक्तस्त्राव", "रक्तस्राव",
        ),
    },
}

KEYWORDS["en"]["accident"] += (
    "accident ho gaya", "takkar maari", "gaadi ne uda diya", "kuchal diya", "bike slip",
)
KEYWORDS["en"]["bleeding"] += ("khoon beh raha",)
KEYWORDS["en"]["unconscious"] += ("behosh",)
KEYWORDS["en"]["fire"] += ("aag lag gayi",)
KEYWORDS["en"]["lpg"] += ("cylinder phat gaya",)
KEYWORDS["hi"]["accident"] += (
    "एक्सीडेंट", "एक्सिडेंट", "टक्कर मारी", "गाड़ी ने उड़ा दिया", "कुचल दिया",
    "बाइक स्लिप",
)
KEYWORDS["hi"]["medical"] += ("हार्ट अटैक", "एम्बुलेंस", "ऐम्बुलेंस",)
KEYWORDS["hi"]["fire"] += ("आग लग गई", "फायर ब्रिगेड",)
KEYWORDS["hi"]["explosion"] += ("सिलेंडर फट गया",)
KEYWORDS["hi"]["bleeding"] += ("खून बह रहा है",)
KEYWORDS["hi"]["no_injury"] = ("कोई घायल नहीं", "कोई चोट नहीं")
KEYWORDS["gu"]["accident"] += ("અકસમાત", "એક્સિડન્ટ", "ટક્કર મારી", "બાઇક સ્લિપ")
KEYWORDS["gu"]["medical"] += ("હાર્ટ એટેક", "એમ્બ્યુલન્સ")
KEYWORDS["gu"]["fire"] += ("આગ લાગી ગઈ", "ફાયર બ્રિગેડ")
KEYWORDS["gu"]["no_injury"] = ("કોઈ ઘાયલ નથી", "કોઈ ઇજા નથી")
KEYWORDS["mr"]["accident"] += ("एक्सिडेंट", "टक्कर मारली", "गाडीने उडवले", "बाईक घसरली")
KEYWORDS["mr"]["medical"] += ("हार्ट अटॅक", "रुग्णवाहिका")
KEYWORDS["mr"]["fire"] += ("आग लागली", "फायर ब्रिगेड")
KEYWORDS["mr"]["no_injury"] = ("कोणी जखमी नाही", "कोणतीही दुखापत नाही")

KEYWORDS["en"]["accident"] += (
    "bike skidded", "hit by a car", "car hit a man", "hit by a train",
    "train hit someone", "car and bike collided", "cars collided",
    "takkar ho gayi", "takra gayi", "road par takkar",
    "bus palat gayi", "bus palat gaya", "gaadi takra gayi",
)
KEYWORDS["en"]["injury"] += (
    "bleeding", "bleeding heavily", "is bleeding",
    "bahut log ghayal", "kai log ghayal", "hit by a car", "hit by a train",
    "car hit a man", "takkar maar", "gaadi ne takkar",
)
KEYWORDS["en"]["medical"] += (
    "choking", "choked", "not breathing", "stroke", "face drooping",
    "speech is slurred", "slurred speech", "one arm is weak", "weak arm",
    "seizure", "body shaking", "poisoning", "phenyl",
    "snake bite", "snake bit", "dog bite", "dog bit", "electric shock",
    "asthma attack", "fever", "vomiting", "labour pain", "labor pain",
    "fell from", "fall from", "fell in the bathroom", "burned by",
    "burnt by", "stuck in the elevator",
    "stuck in the lift", "feeling dizzy", "can't move", "cannot move",
    "saans nahi le raha", "saans nahi le pa raha", "saans nahi aa rahi",
    "saans lene mein dikkat", "saans lene mein takleef", "dil ka daura",
    "chehra tedha", "bolne mein dikkat", "haath kamzor", "daura pad",
    "jhatke aa rahe", "ghut raha", "gala ghut", "phenyl pi li",
    "zehar pi liya", "saanp ne kaata", "kutta kaat", "current laga",
    "asthma attack aaya", "bukhar", "ulti", "chakkar aa rahe",
    "labour pain", "teesri manzil se gir", "dadi gir", "uth nahi pa",
    "chhat se kudne ki dhamki", "saanp ne paer mein kaata",
    "kutta kaat liya", "garm tel se jal", "garam tel se jal",
    "face is drooping", "one arm is weak", "speech is slurred",
)
KEYWORDS["en"]["high_risk_medical"] += (
    "choking", "choked", "cardiac arrest", "seizure", "poisoning",
    "not responding", "unable to move", "asthma attack", "snake bite",
    "electric shock", "saans nahi le raha", "saans nahi le pa raha",
    "saans nahi aa rahi", "saans lene mein dikkat", "saans lene mein takleef",
    "behosh", "hil nahi raha", "hil nahi rahi", "daura pad raha",
    "jhatke aa rahe", "bahut khoon beh", "khoon beh raha",
    "speech is slurred", "one arm is weak", "face is drooping",
    "fell from the third floor", "electric shock", "cannot move",
    "hit by a train", "train se kat", "train derailed", "train patri se utar",
    "teesri manzil se gir", "chhat se kudne ki dhamki", "phenyl",
    "phenyl pi liya", "poisoning",
)
KEYWORDS["en"]["fire"] += ("aag", "aag lag", "dhuan", "dhua", "smoke")
KEYWORDS["en"]["smoke"] += ("dhuan", "dhua", "धुआं")
KEYWORDS["en"]["trapped"] += (
    "fansa", "fansi", "fanse", "cabin mein fansa", "family andar fansa",
    "mazdoor andar fanse", "parivar andar fansa", "lift mein fans",
)
KEYWORDS["en"]["explosion"] += (
    "cylinder blast", "cylinder exploded", "cylinder phat",
    "silinder phat", "patakha phat", "firecracker burst",
)
KEYWORDS["en"]["lpg"] += (
    "cylinder blast", "cylinder exploded", "cylinder phat",
    "silinder phat gaya", "cylinder se gas", "gas ki smell",
)
KEYWORDS["en"]["police"] += (
    "bomb threat", "reckless driving", "rash driving", "dangerous driving",
    "riot", "mob is attacking", "stone pelting", "shots fired",
    "firing shots", "kidnapped", "chain snatching", "snatched my chain",
    "child is being beaten", "child abuse", "stalking", "harassment",
    "ghar mein koi ghus", "koi ghar mein ghus", "kidnap kar liya",
    "peecha kar raha", "peecha kar rahi", "goliyan chala",
    "otp fraud", "blackmailing", "morphed photos", "balatkar",
    "pati mujhe maar raha", "chain cheen li", "ghar mein koi ghus raha",
)
KEYWORDS["en"]["road"] += (
    "hit by a car", "car hit a man", "bike skidded", "car and bike collided",
    "takkar ho gayi", "takra gayi", "gaadi takra", "bike phisal",
    "car se takkar", "car ne takkar maari",
)
KEYWORDS["en"]["railway"] += (
    "train hit someone", "person hit by train", "hit by train",
    "train derailed", "train patri se utar", "railway track par",
)
KEYWORDS["en"]["no_injury"] += (
    "kisi ko chot nahi", "kisi ko chot nahi aayi", "koi ghayal nahi",
    "koi chot nahi", "no one got hurt", "nobody got hurt",
)
KEYWORDS["en"]["cybercrime"] += (
    "otp fraud", "blackmailing me", "morphed photos",
    "money debited through an otp", "paisa kat gaya",
)
KEYWORDS["en"]["rescue"] += (
    "borewell", "child fell into a borewell", "stuck in the lift",
    "stuck in a lift", "stuck in elevator", "family is trapped inside",
    "workers are stuck inside", "old people are inside",
)
KEYWORDS["en"]["high_risk_medical"] += (
    "सीने में तेज दर्द", "छाती में तेज दर्द", "ચાતીમાં સખત દુખાવો",
    "છાતીમાં સખત દુખાવો", "છાતીમાં તીવ્ર દુખાવો", "छातीत तीव्र दुखत",
    "छातीत खूप दुखत", "छातीमध्ये तीव्र वेदना",
)

KEYWORDS["hi"]["medical"] += (
    "सीने में तेज दर्द", "छाती में तेज दर्द", "चेहरा लटक", "बोल अस्पष्ट",
    "हाथ कमजोर", "दौरा पड़", "शरीर कांप", "घुट रहा", "गर्भवती महिला",
    "प्रसव पीड़ा", "लेबर पेन", "रक्तस्राव", "फिनाइल पी", "सांप ने काट",
    "सांप ने पैर पर काट", "कुत्ते ने काट",
    "करंट लगा", "दमा का दौरा", "बुखार", "उल्टी", "कुएं में गिर",
    "तीसरी मंजिल से गिर", "गरम तेल से जल", "उबलते तेल से जल",
    "दादी bathroom में गिर", "दादी बाथरूम में गिर", "उठ नहीं पा", "लिफ्ट में फंसे",
    "चक्कर आ रहे", "बहुत लोग घायल", "कई लोग घायल", "सांप ने काट लिया",
    "कुत्ते ने काट लिया", "सांस नहीं ले रहा", "तीसरी मंजिल से गिरा",
)
KEYWORDS["hi"]["high_risk_medical"] += (
    "सीने में तेज दर्द", "छाती में तेज दर्द", "सांस नहीं ले रहा",
    "सांस नहीं ले पा रहा", "बेहोश", "दौरा पड़ रहा", "घुट रहा",
    "फिनाइल पी", "सांप ने काटा", "बिजली का झटका", "कुएं में गिरा",
    "तीसरी मंजिल से गिरा", "चेहरा लटक", "बोली अस्पष्ट", "हाथ कमजोर",
    "सांप ने पैर पर काट", "फिनाइल पी लिया", "चेहरा टेढ़ा",
    "बोल नहीं पा", "एक हाथ काम नहीं कर रहा",
)
KEYWORDS["en"]["medical"] += ("saanp ne paer mein kaat liya",)
KEYWORDS["en"]["high_risk_medical"] += (
    "chehra tedha", "bol nahi pa", "ek haath kaam nahi kar raha",
    "saanp ne paer mein kaat liya",
)
KEYWORDS["hi"]["fire"] += ("धुआं", "आग बुझ गई")
KEYWORDS["hi"]["smoke"] += ("धुआं",)
KEYWORDS["hi"]["explosion"] += ("सिलेंडर ब्लास्ट", "पटाखा फटा")
KEYWORDS["hi"]["lpg"] += ("सिलेंडर ब्लास्ट", "सिलेंडर फटा")
KEYWORDS["hi"]["no_injury"] += ("किसी को चोट नहीं आई", "कोई घायल नहीं")
KEYWORDS["hi"]["railway"] += ("ट्रेन ने टक्कर मारी", "ट्रेन पटरी से उतर")
KEYWORDS["hi"]["police"] += (
    "बम की धमकी", "लापरवाही से गाड़ी चला", "दंगा", "पत्थर फेंक",
    "गोली चला", "बच्चे को मार", "बच्चा गायब", "अपहरण", "घर में घुस",
    "बलात्कार", "पीछा कर रहा", "ओटीपी फ्रॉड", "ब्लैकमेल",
)
KEYWORDS["hi"]["cybercrime"] += ("ओटीपी फ्रॉड", "ओटीपी धोखाधड़ी", "ब्लैकमेल")
KEYWORDS["hi"]["no_injury"] += ("कोई घायल नहीं है", "कोई चोट नहीं आई")
KEYWORDS["hi"]["rescue"] += ("बोरवेल", "परिवार अंदर फंसा", "मजदूर अंदर फंसे", "बुजुर्ग अंदर")
KEYWORDS["gu"]["medical"] += (
    "છાતીમાં સખત દુખાવો", "ચહેરો ઢળી ગયો", "બોલી અસ્પષ્ટ",
    "હાથ નબળો", "આંચકી", "ગૂંગળાઈ", "ગર્ભવતી મહિલા", "પ્રસવ પીડા",
    "રક્તસ્રાવ", "ફિનાઇલ પી", "સાપે ડંખ માર્યો", "કૂતરાએ કરડ્યો",
    "વીજળીનો ઝટકો", "અસ્થમાનો હુમલો", "તાવ", "ઉલટી",
    "કૂવામાં પડી", "ત્રીજા માળેથી પડી", "ગરમ તેલથી દાઝી",
    "લિફ્ટમાં ફસાઈ", "ચક્કર આવે", "ઘણા લોકો ઘાયલ",
    "શ્વાસ લઈ રહ્યો નથી", "સાપે પગમાં ડંખ માર્યો",
    "ઉકળતા તેલથી દાઝી", "દાદી બાથરૂમમાં પડી", "ઊભા થઈ શકતા નથી",
    "ત્રીજા માળેથી પડ્યો", "સાપે પગમાં ડંખ માર્યો",
    "શ્વાસ લઈ શકતું નથી", "કૂતરાએ કરડ્યો છે",
)
KEYWORDS["gu"]["high_risk_medical"] += (
    "છાતીમાં સખત દુખાવો", "શ્વાસ લઈ રહ્યો નથી", "બેભાન",
    "આંચકી આવી", "ગૂંગળાઈ", "ફિનાઇલ પી", "સાપે ડંખ માર્યો",
    "વીજળીનો ઝટકો", "કૂવામાં પડી", "ચહેરો ઢળી ગયો",
    "બોલી અસ્પષ્ટ", "હાથ નબળો", "ફિનાઇલ પી લીધું",
    "ત્રીજા માળેથી પડ્યો", "વીજળીનો ઝટકો લાગ્યો",
    "શ્વાસ લઈ શકતું નથી",
)
KEYWORDS["gu"]["fire"] += ("ધુમાડો", "આગ બુઝાઈ ગઈ")
KEYWORDS["gu"]["smoke"] += ("ધુમાડો",)
KEYWORDS["gu"]["explosion"] += ("સિલિન્ડર બ્લાસ્ટ", "ફટાકડો ફાટ્યો")
KEYWORDS["gu"]["lpg"] += ("સિલિન્ડર બ્લાસ્ટ", "સિલિન્ડર ફાટ્યો")
KEYWORDS["gu"]["no_injury"] += ("કોઈને ઈજા થઈ નથી", "કોઈ ઘાયલ નથી")
KEYWORDS["gu"]["police"] += (
    "બોમ્બની ધમકી", "બેદરકારીથી ડ્રાઇવિંગ", "હુલ્લડ", "પથ્થરમારો",
    "ગોળીબાર", "બાળક ગુમ", "ઘરમાં ઘૂસ્યો", "બળાત્કાર", "પીછો કરી રહ્યો",
    "ઓટીપી ફ્રોડ", "બ્લેકમેલ",
)
KEYWORDS["gu"]["cybercrime"] += ("ઓટીપી ફ્રોડ", "ઓટીપી છેતરપિંડી", "બ્લેકમેલ")
KEYWORDS["gu"]["no_injury"] += ("કોઈને ઈજા થઈ નથી", "કોઈ ઘાયલ નથી")
KEYWORDS["gu"]["rescue"] += ("બોરવેલ", "પરિવાર અંદર ફસાયો", "વૃદ્ધ અંદર")
KEYWORDS["mr"]["medical"] += (
    "छातीत तीव्र दुखत", "चेहरा वाकडा", "बोलणे अस्पष्ट",
    "हात कमजोर", "झटका येत", "गुदमर", "गर्भवती महिला",
    "प्रसूती वेदना", "रक्तस्राव", "फिनाइल प्यायली", "साप चावला",
    "कुत्रा चावला", "वीज लागली", "दम्याचा झटका", "ताप", "उलटी",
    "विहिरीत पडली", "तिसऱ्या मजल्यावरून पडली", "गरम तेलाने भाजली",
    "लिफ्टमध्ये अडकली", "चक्कर येत", "अनेक लोक जखमी",
    "श्वास घेत नाही", "सापाने चावा घेतला", "सापाने चावा घेतला",
    "कुत्र्याने चावा घेतला",
    "उकळत्या तेलाने भाजली", "आजी bathroom मध्ये पडली",
    "आजी बाथरूममध्ये पडली", "उठू शकत नाही",
    "तिसऱ्या मजल्यावरून पडला", "तिसऱ्या मजल्यावरून पडली",
    "गुदमरले आहे", "श्वास घेऊ शकत नाही",
    "ताप आणि उलटी", "फिनाइल प्यायले", "सापाने चावा घेतला",
    "कुत्र्याने चावा घेतला", "कुत्र्याने मुलाला चावा घेतला",
    "वीजेचा धक्का बसला", "विजेचा धक्का बसला",
    "तिसऱ्या मजल्यावरून पडला", "श्वास घेत नाही",
)
KEYWORDS["mr"]["high_risk_medical"] += (
    "छातीत तीव्र दुखत", "श्वास घेत नाही", "बेशुद्ध", "झटका येत",
    "गुदमर", "फिनाइल प्यायली", "साप चावला", "वीज लागली",
    "विहिरीत पडली", "चेहरा वाकडा", "बोलणे अस्पष्ट", "हात कमजोर",
    "तिसऱ्या मजल्यावरून पडला", "वीजेचा धक्का बसला",
    "विजेचा धक्का बसला",
    "फिनाइल प्यायले", "गुदमरले आहे", "श्वास घेऊ शकत नाही",
    "तिसऱ्या मजल्यावरून पडला", "वीजेचा धक्का बसला",
)
KEYWORDS["en"]["child"] = (
    "child", "children", "kid", "kids", "baby", "bachcha", "bachche",
)
KEYWORDS["gu"]["child"] = ("બાળક", "બાળકો", "મારું બાળક")
KEYWORDS["mr"]["child"] = ("मूल", "मुलगा", "मुलगी", "माझे मूल")
KEYWORDS["hi"]["highway"] = ("हाईवे", "राजमार्ग")
KEYWORDS["gu"]["highway"] = ("હાઈવે", "ધોરીમાર્ગ")
KEYWORDS["mr"]["highway"] = ("महामार्ग", "महामार्गावर")
KEYWORDS["en"]["trapped"] += (
    "family inside", "family is inside", "andar parivar hai", "parivar andar hai",
)
KEYWORDS["en"]["rescue"] += (
    "family inside", "family is inside", "andar parivar hai", "parivar andar hai",
)
KEYWORDS["hi"]["trapped"] += ("परिवार अंदर है", "ड्राइवर केबिन में फंसा")
KEYWORDS["hi"]["rescue"] += ("परिवार अंदर है", "ड्राइवर केबिन में फंसा")
KEYWORDS["gu"]["trapped"] += ("પરિવાર અંદર છે", "ડ્રાઈવર કેબિનમાં ફસાયો")
KEYWORDS["gu"]["rescue"] += ("પરિવાર અંદર છે", "ડ્રાઈવર કેબિનમાં ફસાયો")
KEYWORDS["mr"]["trapped"] += ("कुटुंब आत आहे", "चालक केबिनमध्ये अडकला")
KEYWORDS["mr"]["rescue"] += ("कुटुंब आत आहे", "चालक केबिनमध्ये अडकला")
KEYWORDS["mr"]["fire"] += ("धूर", "आग विझली")
KEYWORDS["mr"]["smoke"] += ("धूर",)
KEYWORDS["mr"]["explosion"] += ("सिलेंडर ब्लास्ट", "फटाका फुटला")
KEYWORDS["mr"]["lpg"] += ("सिलेंडर ब्लास्ट", "सिलेंडर फुटला")
KEYWORDS["mr"]["no_injury"] += ("कोणी जखमी नाही", "कोणालाही दुखापत नाही")
KEYWORDS["mr"]["police"] += (
    "बॉम्बची धमकी", "बेपर्वाईने गाडी चालव", "दंगल", "दगडफेक",
    "गोळीबार", "मुल हरवले", "घरात घुसला", "बलात्कार", "पाठलाग करत",
    "ओटीपी फ्रॉड", "ब्लॅकमेल",
)
KEYWORDS["mr"]["cybercrime"] += ("ओटीपी फ्रॉड", "ओटीपी फसवणूक", "ब्लॅकमेल")
KEYWORDS["mr"]["no_injury"] += ("कोणीही जखमी नाही", "कोणालाही दुखापत नाही")
KEYWORDS["mr"]["rescue"] += ("बोरवेल", "कुटुंब आत अडकले", "वृद्ध आत")
KEYWORDS["en"]["critical_threat"] = (
    "kidnapping", "kidnapped", "sexual assault", "sexually assaulted",
    "rape", "acid attack", "acid thrown", "acid was thrown",
    "blackmailing with morphed photos",
    "blackmailing me with my morphed photos", "morphed photos",
    "kidnap kar liya", "balatkar", "tezaab phenk",
    "threatening to jump from the roof", "threatening to jump from a roof",
)
KEYWORDS["hi"]["critical_threat"] = (
    "अपहरण", "किडनैप", "बलात्कार", "यौन हमला", "तेजाब हमला", "तेजाब फेंका",
    "छत से कूदने की धमकी",
)
KEYWORDS["gu"]["critical_threat"] = (
    "અપહરણ", "બળાત્કાર", "યૌન હુમલો", "એસિડ હુમલો", "એસિડ ફેંક્યો",
    "છત પરથી કૂદવાની ધમકી",
)
KEYWORDS["mr"]["critical_threat"] = (
    "अपहरण", "बलात्कार", "लैंगिक अत्याचार", "अॅसिड हल्ला", "ॲसिड फेकला",
    "छतावरून उडी मारण्याची धमकी",
)
KEYWORDS["gu"]["self_harm"] = ("છત પરથી કૂદવાની ધમકી",)
KEYWORDS["mr"]["self_harm"] = ("छतावरून उडी मारण्याची धमकी",)
KEYWORDS["en"]["hit_and_run"] = (
    "hit and run", "ran away", "bhaag gaya", "bhaag gayi", "भाग गया",
    "भाग गई", "ભાગી ગઈ", "पळून गेली", "पळून गेला",
)
KEYWORDS["hi"]["accident"] += (
    "बाइक फिसल गई", "दो कारें टकराईं", "दो गाड़ियां टकराईं",
    "कार ने आदमी को टक्कर मारी", "कार नहर में गिर गई",
)
KEYWORDS["hi"]["road"] += (
    "बाइक फिसल गई", "दो कारें टकराईं", "दो गाड़ियां टकराईं",
    "कार ने आदमी को टक्कर मारी", "कार नहर में गिर गई",
)
KEYWORDS["hi"]["accident"] += ("टकराईं", "टक्कर मारकर भाग गई")
KEYWORDS["hi"]["road"] += ("टकराईं", "टक्कर मारकर भाग गई")
KEYWORDS["hi"]["no_injury"] += ("किसी को चोट नहीं आई", "कोई घायल नहीं")
KEYWORDS["hi"]["high_risk_medical"] += (
    "कार ने आदमी को टक्कर मारी", "ट्रेन ने टक्कर मारी",
    "ट्रेन पटरी से उतर गई",
)
KEYWORDS["hi"]["rescue"] += (
    "ड्राइवर केबिन में फंसा", "परिवार अंदर फंसा",
    "कार नहर में गिर गई",
)
KEYWORDS["hi"]["trapped"] += ("ड्राइवर केबिन में फंसा", "परिवार अंदर फंसा")
KEYWORDS["gu"]["accident"] += (
    "બે કાર અથડાઈ", "કાર અથડાઈ", "કાર નહેરમાં પડી ગઈ",
    "અકસ્મતા પછી", "બાઈક લપસી ગઈ",
)
KEYWORDS["gu"]["road"] = (
    "બે કાર અથડાઈ", "કાર અથડાઈ", "કાર નહેરમાં પડી ગઈ",
    "અકસ્મતા પછી", "બાઈક લપસી ગઈ",
)
KEYWORDS["gu"]["medical"] += ("શ્વાસ લઈ રહ્યો નથી",)
KEYWORDS["gu"]["road"] += ("ટ્રેનથી કચડાયો", "કારને ટક્કર મારી")
KEYWORDS["gu"]["no_injury"] += ("કોઈને ઈજા થઈ નથી", "કોઈ ઘાયલ નથી")
KEYWORDS["gu"]["trapped"] += ("ડ્રાઈવર કેબિનમાં ફસાયો", "કારમાં પરિવાર અંદર")
KEYWORDS["gu"]["rescue"] += (
    "ડ્રાઈવર કેબિનમાં ફસાયો", "કાર નહેરમાં પડી ગઈ",
    "પરિવાર અંદર ફસાયેલો છે",
)
KEYWORDS["mr"]["accident"] += (
    "दोन गाड्या धडकल्या", "कार धडकली", "कार कालव्यात पडली",
    "धडकेनंतर", "बाईक घसरली",
)
KEYWORDS["mr"]["road"] = (
    "दोन गाड्या धडकल्या", "कार धडकली", "कार कालव्यात पडली",
    "धडकेनंतर", "बाईक घसरली",
)
KEYWORDS["mr"]["medical"] += ("गुदमरले आहे", "ताप आणि उलटी")
KEYWORDS["mr"]["road"] += ("ट्रेनने धडक दिली", "कारने धडक दिली")
KEYWORDS["mr"]["no_injury"] += (
    "कोणालाही दुखापत झाली नाही", "कोणालाही दुखापत झाली नाही",
    "कोणी जखमी नाही",
)
KEYWORDS["mr"]["trapped"] += ("चालक केबिनमध्ये अडकला", "कुटुंब आत अडकले")
KEYWORDS["mr"]["rescue"] += (
    "चालक केबिनमध्ये अडकला", "कार कालव्यात पडली", "कुटुंब आत अडकले",
)


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
    # The structured lexicon contributes only supporting evidence.  Incident
    # classification, context state, and dispatch remain deterministic rules.
    for category, matched in supporting_evidence(text, language).items():
        result[category] = result.get(category, False) or matched
    return result


@lru_cache(maxsize=4096)
def _phrase_pattern(phrase: str) -> re.Pattern[str]:
    words = r"\s+".join(re.escape(word) for word in phrase.split())
    return re.compile(rf"(?<!{_W}){words}(?!{_W})", re.IGNORECASE)


def _phrase_is_affirmed(text: str, phrase: str) -> bool:
    pattern = _phrase_pattern(phrase)
    for clause in _CLAUSE_BREAK.split(text):
        for match in pattern.finditer(clause):
            before, after = clause[:match.start()], clause[match.end():]
            negated = any(
                re.search(rf"(?<!{_W}){re.escape(marker)}(?!{_W})", before[-48:], re.IGNORECASE)
                or re.search(rf"(?<!{_W}){re.escape(marker)}(?!{_W})", after[:32], re.IGNORECASE)
                for marker in _NEGATION_WORDS
            )
            if not negated:
                return True
    return False
