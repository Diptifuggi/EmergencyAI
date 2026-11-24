"""Structured multilingual emergency evidence lexicon.

This is a high-recall evidence resource, not a classifier.  Terms are grouped
by semantic domain and language/script so callers can combine them with
negation, temporal state, uncertainty, and sentence-level extraction.

The resource intentionally does not claim to contain every Indian expression;
regional dialects, slang, and speech-recognition variants evolve continually.
"""
from __future__ import annotations

from functools import lru_cache
import re
from dataclasses import dataclass, replace
from typing import Iterable

LANGUAGES = (
    "english", "hindi", "gujarati", "marathi", "romanized", "code_mixed", "stt_variants"
)
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


@dataclass(frozen=True)
class EmergencyLexicon:
    english: tuple[str, ...] = ()
    hindi: tuple[str, ...] = ()
    gujarati: tuple[str, ...] = ()
    marathi: tuple[str, ...] = ()
    romanized: tuple[str, ...] = ()
    code_mixed: tuple[str, ...] = ()
    stt_variants: tuple[str, ...] = ()

    def terms(self, language: str = "en") -> tuple[str, ...]:
        """Return language-aware terms plus safe mixed-script fallbacks."""
        language_key = language.casefold().split("-")[0]
        selected = {
            "en": self.english,
            "hi": self.hindi,
            "gu": self.gujarati,
            "mr": self.marathi,
        }.get(language_key, ())
        return tuple(dict.fromkeys((*selected, *self.code_mixed, *self.romanized, *self.stt_variants)))


# Categories are deliberately descriptive.  They are mapped to existing
# deterministic evidence flags below; the lexicon itself never chooses a type.
LEXICON: dict[str, EmergencyLexicon] = {
    "fire": EmergencyLexicon(
        english=("fire", "flames", "burning", "burnt", "building fire", "house fire", "shop fire", "school fire", "college fire", "hospital fire", "factory fire", "warehouse fire", "office fire", "hotel fire", "restaurant fire", "kitchen fire", "canteen fire", "forest fire", "wildfire", "vehicle fire", "car fire", "bus fire", "truck fire", "bike fire", "electrical fire", "short circuit fire", "fire broke out", "fire erupted", "fire spreading", "fire everywhere", "building on fire", "smoke and fire", "huge flames", "heavy flames", "fire emergency", "need fire brigade", "send fire brigade", "fire service required"),
        hindi=("आग", "आग लग गई", "आग लग गयी", "आग लगी है", "आग लग गई है", "आग भड़क गई", "आग भड़क रही है", "आग फैल रही है", "बहुत बड़ी आग", "भीषण आग", "भयंकर आग", "धधकती आग", "ज्वाला", "लपट", "लपटें", "आग की लपटें", "धुआं और आग", "इमारत में आग", "घर में आग", "दुकान में आग", "होटल में आग", "स्कूल में आग", "कॉलेज में आग", "अस्पताल में आग", "फैक्टरी में आग", "गोदाम में आग", "कैंटीन में आग", "रसोई में आग", "जंगल में आग", "गाड़ी में आग", "बस में आग", "कार में आग", "बाइक में आग", "बिजली से आग", "शॉर्ट सर्किट से आग", "आग बुझाओ", "फायर ब्रिगेड भेजो", "दमकल भेजो", "दमकल की जरूरत है", "फायर ब्रिगेड चाहिए", "जल्दी दमकल भेजो"),
        gujarati=("આગ", "આગ લાગી છે", "આગ લાગી ગઈ છે", "આગ ભભૂકી રહી છે", "આગ ફેલાઈ રહી છે", "ભીષણ આગ", "ભયંકર આગ", "મોટી આગ", "આગની જ્વાળા", "આગની લપટ", "ધુમાડો અને આગ", "મકાનમાં આગ", "ઘરમાં આગ", "દુકાનમાં આગ", "હોટેલમાં આગ", "સ્કૂલમાં આગ", "કોલેજમાં આગ", "હોસ્પિટલમાં આગ", "ફેક્ટરીમાં આગ", "ગોડાઉનમાં આગ", "કેન્ટીનમાં આગ", "રસોડામાં આગ", "જંગલમાં આગ", "ગાડીમાં આગ", "બસમાં આગ", "કારમાં આગ", "બાઇકમાં આગ", "શોર્ટ સર્કિટથી આગ", "ફાયર બ્રિગેડ મોકલો", "ફાયર બ્રિગેડ જોઈએ", "દમકલ મોકલો", "જલ્દી ફાયર બ્રિગેડ મોકલો"),
        marathi=("आग", "आग लागली आहे", "आग लागली", "आग भडकली आहे", "आग पसरत आहे", "मोठी आग", "भीषण आग", "भयंकर आग", "आगीच्या ज्वाळा", "धूर आणि आग", "इमारतीत आग", "घरात आग", "दुकानात आग", "हॉटेलमध्ये आग", "शाळेत आग", "कॉलेजमध्ये आग", "रुग्णालयात आग", "कारखान्यात आग", "गोदामात आग", "कॅन्टीनमध्ये आग", "स्वयंपाकघरात आग", "जंगलात आग", "गाडीला आग लागली", "बसला आग लागली", "कारला आग लागली", "बाईकला आग लागली", "शॉर्ट सर्किटमुळे आग", "फायर ब्रिगेड पाठवा", "दमकल पाठवा", "लवकर दमकल पाठवा", "फायर ब्रिगेड हवी आहे"),
        romanized=("aag", "aag lagi", "aag lag gayi", "aag lag gyi", "aag lagi hai", "aag bhadak rahi", "dhuaan aur aag", "ghar mein aag", "factory mein aag", "damkal bhejo", "fire brigade bhejo"),
        code_mixed=("fire lagi hai", "fire lag gayi", "building mein fire", "canteen mein fire", "fire brigade bhejo", "jaldi fire service", "aag ka emergency"),
        stt_variants=("fayar", "fayr", "firee", "aag lagi he", "aag lag gyi he", "damkal", "dhamkal"),
    ),
    "gas_lpg": EmergencyLexicon(
        english=("lpg", "gas leak", "gas leakage", "lpg leak", "lpg leakage", "gas cylinder", "lpg cylinder", "cylinder leak", "cylinder leakage", "gas cylinder exploded", "gas cylinder explosion", "cylinder exploded", "cylinder burst", "cylinder blasted", "gas blast", "lpg blast", "gas explosion", "gas smell", "smell of gas", "gas spreading", "gas coming out", "leaking cylinder", "cylinder is leaking", "cylinder caught fire", "gas pipeline leak", "gas pipe burst", "gas pipeline burst", "commercial gas leak", "kitchen gas leak"),
        hindi=("गैस", "गैस लीक", "गैस लीक हो रही है", "गैस रिस रही है", "गैस का रिसाव", "एलपीजी", "एलपीजी गैस", "एलपीजी लीक", "एलपीजी का रिसाव", "गैस सिलेंडर", "एलपीजी सिलेंडर", "सिलेंडर लीक", "सिलेंडर से गैस निकल रही है", "गैस की बदबू", "गैस की गंध", "गैस फैल रही है", "गैस पाइप लीक", "गैस पाइप फट गया", "गैस सिलेंडर फट गया", "सिलेंडर फट गया", "सिलेंडर ब्लास्ट", "गैस ब्लास्ट", "एलपीजी ब्लास्ट", "गैस विस्फोट", "गैस का धमाका", "सिलेंडर का धमाका", "गैस में आग लग गई", "सिलेंडर में आग", "गैस पाइपलाइन फट गई"),
        gujarati=("ગેસ", "ગેસ લીક", "ગેસ લીક થઈ રહી છે", "ગેસનો લીકેજ", "ગેસનો ગંધ", "ગેસની વાસ", "lpg", "એલપીજી", "ગેસ સિલિન્ડર", "એલપીજી સિલિન્ડર", "સિલિન્ડર લીક", "સિલિન્ડરમાંથી ગેસ નીકળે છે", "ગેસ ફેલાઈ રહ્યો છે", "ગેસની પાઇપ લીક", "ગેસની પાઇપ ફાટી ગઈ", "ગેસ સિલિન્ડર ફાટી ગયો", "સિલિન્ડર ફાટી ગયો", "ગેસ બ્લાસ્ટ", "lpg બ્લાસ્ટ", "ગેસનો વિસ્ફોટ", "ગેસનો ધડાકો", "સિલિન્ડરનો ધડાકો", "સિલિન્ડરમાં આગ", "ગેસમાં આગ લાગી"),
        marathi=("गॅस", "गॅस गळती", "गॅस गळत आहे", "गॅसचा वास", "गॅसची गळती", "एलपीजी", "एलपीजी गॅस", "गॅस सिलेंडर", "एलपीजी सिलेंडर", "सिलेंडर गळत आहे", "सिलेंडरमधून गॅस निघत आहे", "गॅस पसरत आहे", "गॅस पाइप गळती", "गॅस पाइप फुटली", "गॅस सिलेंडर फुटला", "सिलेंडर फुटला", "गॅस ब्लास्ट", "एलपीजी ब्लास्ट", "गॅसचा स्फोट", "गॅसचा मोठा स्फोट", "सिलेंडरचा स्फोट", "सिलेंडरला आग लागली", "गॅसमध्ये आग लागली"),
        romanized=("gas", "gass", "gaas", "gas leek", "gas lik", "gas liq", "cylinder leak", "gas ki badbu", "gas phail rahi", "lpg gas"),
        code_mixed=("gas leak ho rahi", "lpg cylinder leak", "gas cylinder phat gaya", "gas blast hua", "lpg blast thayo", "lpg gas blast", "gas mein fire", "cylinder mein fire"),
        stt_variants=("gass leek", "gas lik", "gas liq", "silendar leak", "sylendar leak", "elpeji", "lpg gas leak"),
    ),
    "explosion": EmergencyLexicon(
        english=("explosion", "exploded", "exploding", "blast", "blasted", "bomb blast", "bomb explosion", "massive explosion", "loud explosion", "huge blast", "chemical explosion", "industrial explosion", "factory explosion", "building explosion", "vehicle explosion", "gas explosion", "cylinder explosion", "pipeline explosion", "firecracker explosion", "cracker blast", "unknown explosion", "suspicious blast", "explosive", "explosives", "detonation", "detonated"),
        hindi=("विस्फोट", "विस्फोट हुआ", "विस्फोट हो गया", "धमाका", "धमाका हुआ", "जोरदार धमाका", "बहुत बड़ा धमाका", "तेज धमाका", "बम धमाका", "बम विस्फोट", "बम फटा", "बम फट गया", "गैस विस्फोट", "सिलेंडर विस्फोट", "सिलेंडर धमाका", "फैक्टरी में धमाका", "कारखाने में धमाका", "इमारत में धमाका", "जोरदार विस्फोट", "कुछ फट गया", "फट गया", "फटने की आवाज"),
        gujarati=("વિસ્ફોટ", "વિસ્ફોટ થયો", "ધડાકો", "મોટો ધડાકો", "જોરદાર ધડાકો", "બોમ્બ વિસ્ફોટ", "બોમ્બ બ્લાસ્ટ", "બોમ્બ ફાટ્યો", "ગેસ વિસ્ફોટ", "સિલિન્ડરનો વિસ્ફોટ", "ફેક્ટરીમાં ધડાકો", "મોટો વિસ્ફોટ", "કંઈક ફાટ્યું", "ફાટવાનો અવાજ"),
        marathi=("स्फोट", "स्फोट झाला", "मोठा स्फोट", "जोरदार स्फोट", "धडाका", "मोठा धडाका", "बॉम्बस्फोट", "बॉम्ब फुटला", "गॅसचा स्फोट", "सिलेंडरचा स्फोट", "कारखान्यात स्फोट", "इमारतीत स्फोट", "काहीतरी फुटले", "फुटल्याचा आवाज"),
        romanized=("blast", "blest", "blst", "blass", "blast hua", "blast thayo", "blast zala", "blast jhala", "dhamaka", "visfot", "sphot"),
        code_mixed=("gas blast hua", "cylinder blast", "factory blast", "bomb blast hua", "blast thayo che", "sphota zala"),
        stt_variants=("blest", "blst", "blass", "dhamka", "visfot hua", "sphot zala"),
    ),
    "road_accident": EmergencyLexicon(
        english=("accident", "road accident", "traffic accident", "vehicle accident", "car accident", "bike accident", "motorcycle accident", "truck accident", "bus accident", "auto accident", "collision", "crash", "vehicle crashed", "hit by vehicle", "pedestrian hit", "hit and run", "overturned vehicle", "vehicle overturned", "car overturned", "bus overturned", "truck overturned", "pile-up", "multiple vehicle collision", "head-on collision", "road crash", "highway accident", "highway crash", "truck collision", "bike collision"),
        hindi=("एक्सीडेंट", "एक्सीडेंट हुआ", "एक्सीडेंट हो गया", "दुर्घटना", "सड़क दुर्घटना", "सड़क हादसा", "सड़क हादसे", "हादसा", "वाहन हादसा", "गाड़ी का एक्सीडेंट", "कार एक्सीडेंट", "बाइक एक्सीडेंट", "मोटरसाइकिल एक्सीडेंट", "बस एक्सीडेंट", "ट्रक एक्सीडेंट", "ऑटो एक्सीडेंट", "टक्कर", "गाड़ी टकरा गई", "दो गाड़ियां टकरा गई", "गाड़ी पलट गई", "बस पलट गई", "ट्रक पलट गया", "बाइक गिर गई", "गाड़ी ने टक्कर मार दी", "हिट एंड रन", "सड़क पर हादसा", "हाईवे पर हादसा", "कई गाड़ियों की टक्कर"),
        gujarati=("અકસમાત", "અકસ્મત", "અકસ્મત થયો", "અકસ્મત થઈ ગયો", "અકાયત", "રોડ અકસ્માત", "રસ્તા પર અકસ્માત", "હાદસો", "ગાડીનો અકસ્માત", "કાર અકસ્માત", "બાઈક અકસ્માત", "મોટરસાયકલ અકસ્માત", "બસ અકસ્માત", "ટ્રક અકસ્માત", "ઓટો અકસ્માત", "ટક્કર", "બે ગાડીઓ અથડાઈ", "ગાડી પલટી ગઈ", "બસ પલટી ગઈ", "ટ્રક પલટી ગયો", "ગાડી અથડાઈ", "હિટ એન્ડ રન", "હાઇવે અકસ્માત", "રસ્તા પર હાદસો"),
        marathi=("अपघात", "अपघात झाला", "अपघात झाला आहे", "दुर्घटना", "रस्ते अपघात", "रस्त्यावर अपघात", "हादसा", "गाडीचा अपघात", "कार अपघात", "बाईक अपघात", "मोटरसायकल अपघात", "बस अपघात", "ट्रक अपघात", "ऑटो अपघात", "धडक", "दोन गाड्या धडकल्या", "गाडी उलटली", "बस उलटली", "ट्रक उलटला", "गाडीने धडक दिली", "हिट अँड रन", "महामार्गावर अपघात"),
        romanized=("accident", "aksident", "accidant", "akshident", "aksident hua", "takra", "thokar", "gaadi palat gayi", "gaadi takra gayi"),
        code_mixed=("road par accident", "highway pe accident", "gaadi ka crash", "car takra gayi", "bike accident hua", "road accident thayo", "road accident zala"),
        stt_variants=("aksidant", "aksident", "accidant", "akshident", "aksdent"),
    ),
    "railway": EmergencyLexicon(
        english=("train accident", "railway accident", "train crash", "train collision", "train derailment", "train derailed", "train overturned", "railway collision", "railway crash", "railway emergency", "train emergency", "railway track accident", "train hit someone", "person hit by train", "train fire", "train explosion", "railway station accident", "platform accident", "railway track problem", "train stuck", "train trapped", "multiple coaches derailed"),
        hindi=("ट्रेन हादसा", "ट्रेन दुर्घटना", "ट्रेन एक्सीडेंट", "रेल हादसा", "रेल दुर्घटना", "रेलवे दुर्घटना", "ट्रेन टकरा गई", "ट्रेन पटरी से उतर गई", "ट्रेन पलट गई", "ट्रेन में आग", "ट्रेन में धमाका", "ट्रेन दुर्घटनाग्रस्त", "रेलवे स्टेशन पर हादसा", "प्लेटफॉर्म पर हादसा", "रेल की पटरी पर हादसा", "ट्रेन ने टक्कर मार दी", "ट्रेन की चपेट में", "ट्रेन फंस गई", "रेलवे ट्रैक पर दुर्घटना"),
        gujarati=("ટ્રેન અકસ્માત", "રેલવે અકસ્માત", "ટ્રેન હાદસો", "ટ્રેન અથડાઈ", "ટ્રેન પાટા પરથી ઉતરી ગઈ", "ટ્રેન પલટી ગઈ", "ટ્રેનમાં આગ", "ટ્રેનમાં ધડાકો", "રેલવે સ્ટેશન પર અકસ્માત", "પ્લેટફોર્મ પર અકસ્માત", "રેલવે ટ્રેક પર અકસ્માત", "ટ્રેનની અડફેટે", "ટ્રેન ફસાઈ ગઈ"),
        marathi=("रेल्वे अपघात", "ट्रेन अपघात", "रेल्वे दुर्घटना", "ट्रेनचा अपघात", "ट्रेन धडकली", "ट्रेन रुळावरून घसरली", "ट्रेन रुळावरून उतरली", "ट्रेन उलटली", "ट्रेनमध्ये आग", "ट्रेनमध्ये स्फोट", "रेल्वे स्टेशनवर अपघात", "प्लॅटफॉर्मवर अपघात", "रेल्वे ट्रॅकवर अपघात", "ट्रेनच्या धडकेत", "ट्रेन अडकली"),
        romanized=("train accident", "railway accident", "train crash", "train patri se utar gayi", "train atak gayi", "railway station par hadsa", "train takra gayi"),
        code_mixed=("train ka accident", "railway station pe accident", "train derail ho gayi", "train mein fire", "railway track par hadsa"),
        stt_variants=("rail ve", "railway stesan", "train patri", "tren accident", "trayn hadsa"),
    ),
    "medical": EmergencyLexicon(
        english=("medical emergency", "medical help", "medical assistance", "ambulance needed", "ambulance required", "person unconscious", "unconscious", "collapsed", "not breathing", "difficulty breathing", "breathing problem", "breathlessness", "chest pain", "heart attack", "cardiac arrest", "stroke", "seizure", "fits", "convulsion", "fainted", "fainting", "severe pain", "heavy bleeding", "bleeding", "blood loss", "serious injury", "critical condition", "vomiting blood", "poisoning", "overdose", "burn injury", "electric shock", "snake bite", "dog bite", "animal bite", "allergic reaction", "pregnancy emergency", "pregnant woman", "delivery emergency", "child emergency", "baby emergency", "newborn emergency", "elderly person emergency"),
        hindi=("मेडिकल इमरजेंसी", "चिकित्सा सहायता", "डॉक्टर चाहिए", "एम्बुलेंस चाहिए", "एम्बुलेंस भेजो", "एम्बुलेंस की जरूरत है", "बेहोश", "बेहोश हो गया", "सांस नहीं ले रहा", "सांस नहीं आ रही", "सांस लेने में दिक्कत", "दम घुट रहा है", "सीने में दर्द", "छाती में दर्द", "चेस्ट में दर्द", "दिल का दौरा", "हार्ट अटैक", "दिल रुक गया", "लकवा", "स्ट्रोक", "दौरा पड़ा", "मिर्गी का दौरा", "गिर गया", "बेहोश होकर गिर गया", "बहुत दर्द", "बहुत ज्यादा खून बह रहा", "खून बह रहा", "खून नहीं रुक रहा", "गंभीर चोट", "गंभीर हालत", "जहर खा लिया", "जहर पी लिया", "ओवरडोज", "सांप ने काट लिया", "कुत्ते ने काट लिया", "जानवर ने काट लिया", "बिजली का झटका", "जल गया", "जलने की चोट", "गर्भवती महिला", "डिलीवरी की समस्या", "बच्चा बीमार है", "बच्चा बेहोश है", "बुजुर्ग की तबीयत खराब"),
        gujarati=("મેડિકલ ઇમરજન્સી", "તબીબી મદદ", "એમ્બ્યુલન્સ જોઈએ", "એમ્બ્યુલન્સ મોકલો", "એમ્બ્યુલન્સની જરૂર છે", "બેભાન", "બેભાન થઈ ગયો", "શ્વાસ નથી લઈ રહ્યો", "શ્વાસ લેવામાં તકલીફ", "છાતીમાં દુખાવો", "હાર્ટ એટેક", "સ્ટ્રોક", "આંચકો", "લોહી વહી રહ્યું છે", "ખૂબ લોહી નીકળે છે", "લોહી બંધ થતું નથી", "ગંભીર ઈજા", "ઝેર પી લીધું", "ઓવરડોઝ", "સાપે ડંખ માર્યો", "કૂતરાએ કરડ્યો", "વીજળીનો ઝટકો", "દાઝી ગયો", "સગર્ભા મહિલા", "ડિલિવરીની ઇમરજન્સી", "બાળકની તબિયત ખરાબ", "વૃદ્ધની તબિયત ખરાબ"),
        marathi=("वैद्यकीय आणीबाणी", "मेडिकल इमर्जन्सी", "वैद्यकीय मदत", "रुग्णवाहिका हवी", "रुग्णवाहिका पाठवा", "रुग्णवाहिकेची गरज आहे", "बेशुद्ध", "बेशुद्ध झाला", "श्वास घेत नाही", "श्वास घेण्यास त्रास", "श्वास घेता येत नाही", "छातीत दुखत आहे", "हृदयविकाराचा झटका", "हार्ट अटॅक", "स्ट्रोक", "झटका आला", "फिट आली", "बेशुद्ध पडला", "खूप वेदना", "खूप रक्त वाहत आहे", "रक्तस्त्राव", "रक्त थांबत नाही", "गंभीर दुखापत", "गंभीर अवस्था", "विष घेतले", "ओव्हरडोस", "साप चावला", "कुत्र्याने चावले", "वीज लागली", "भाजले", "गर्भवती महिला", "प्रसूतीची आणीबाणी", "बाळ आजारी आहे", "वृद्ध व्यक्तीची तब्येत खराब"),
        romanized=("behosh", "behosh ho gaya", "saans nahi aa rahi", "saans lene mein dikkat", "seene mein dard", "chhati mein dard", "dil ka daura", "ambulance chahiye", "ambulance bhejo", "khoon beh raha", "zehar kha liya", "saanp ne kaata", "bachcha behosh"),
        code_mixed=("chest mein pain", "chest mein dard", "चेस्ट में दर्द", "breathing mein problem", "ambulance bhejo", "heart attack hua", "medical help chahiye", "saans nahi le raha", "patient critical hai"),
        stt_variants=("ambalance", "ambulans", "ambyulance", "behos", "sans nahi", "saans nhi", "breth problem", "heartatak"),
    ),
    "police_crime": EmergencyLexicon(
        english=("police", "police help", "police needed", "police required", "crime", "crime in progress", "criminal activity", "attack", "assault", "fight", "violent fight", "stabbing", "knife attack", "shooting", "gunshot", "gunfire", "armed person", "weapon", "gun", "knife", "robbery", "robbery in progress", "theft", "stealing", "burglary", "break-in", "breaking into my house", "breaking into my home", "house break-in", "intruder", "intrusion", "kidnapping", "abduction", "hostage", "threat", "death threat", "murder", "attempted murder", "rape", "sexual assault", "molestation", "harassment", "domestic violence", "beating", "someone is attacking me", "someone is following me", "someone is threatening me"),
        hindi=("पुलिस", "पुलिस चाहिए", "पुलिस बुलाओ", "पुलिस भेजो", "अपराध", "अपराध हो रहा है", "मारपीट", "लड़ाई", "झगड़ा", "हमला", "हमला हो रहा है", "चाकू से हमला", "चाकू मार दिया", "गोली चली", "गोली चल रही है", "फायरिंग", "बंदूक", "बंदूकधारी", "हथियार", "चाकू", "लूट", "लूट हो रही है", "डकैती", "चोरी", "चोरी हो रही है", "घर में चोरी", "घर में घुस आया", "कोई घर में घुस गया", "घुसपैठिया", "अपहरण", "किडनैप", "बंधक", "जान से मारने की धमकी", "धमकी", "हत्या", "बलात्कार", "यौन हमला", "छेड़छाड़", "उत्पीड़न", "घरेलू हिंसा", "मार रहा है", "मुझे मार रहा है", "कोई पीछा कर रहा है", "कोई धमकी दे रहा है"),
        gujarati=("પોલીસ", "પોલીસ જોઈએ", "પોલીસ બોલાવો", "પોલીસ મોકલો", "ગુનો", "ગુનો થઈ રહ્યો છે", "મારામારી", "ઝઘડો", "હુમલો", "હુમલો થઈ રહ્યો છે", "છરીથી હુમલો", "ગોળી ચાલી", "ફાયરિંગ", "બંદૂક", "હથિયાર", "છરી", "લૂંટ", "લૂંટ થઈ રહી છે", "ચોરી", "ઘરમાં ચોરી", "ઘરમાં કોઈ ઘૂસી આવ્યું", "ઘુસણખોર", "અપહરણ", "કિડનેપ", "બંધક", "ધમકી", "મારી નાખવાની ધમકી", "હત્યા", "બળાત્કાર", "યૌન હુમલો", "હેરાનગતિ", "ઘરેલું હિંસા", "મને મારી રહ્યો છે", "મારો પીછો કરી રહ્યો છે"),
        marathi=("पोलीस", "पोलीस हवे", "पोलीस बोलवा", "पोलीस पाठवा", "गुन्हा", "गुन्हा सुरू आहे", "मारामारी", "भांडण", "हल्ला", "हल्ला होत आहे", "चाकूने हल्ला", "गोळीबार", "गोळी चालली", "बंदूक", "शस्त्र", "चाकू", "लूट", "दरोडा", "चोरी", "घरात चोरी", "घरात कोणी घुसले", "घुसखोर", "अपहरण", "किडनॅप", "बंधक", "धमकी", "जीव मारण्याची धमकी", "खून", "बलात्कार", "लैंगिक अत्याचार", "छेडछाड", "त्रास देणे", "घरगुती हिंसाचार", "मला मारत आहे", "माझा पाठलाग करत आहे"),
        romanized=("police", "polise", "polis", "police bulao", "police moklo", "police pathva", "maar raha", "jhagda", "chori", "lut", "dhamki", "picha kar raha", "banduk", "chaku"),
        code_mixed=("police help chahiye", "police bhejo", "ghar mein chori", "someone ghar mein ghus gaya", "gun lekar aaya", "mujhe attack kar raha", "police moklo", "police pathva"),
        stt_variants=("polise", "polis", "polic", "bandook", "chaku attack", "goli bar", "kidnep"),
    ),
    "women_safety": EmergencyLexicon(
        english=("woman in danger", "woman unsafe", "women safety", "female safety", "harassment", "stalking", "molestation", "sexual assault", "sexual harassment", "rape", "attempted rape", "domestic abuse", "domestic violence", "forced entry", "threatening woman", "woman being attacked", "woman is being followed", "woman being followed"),
        hindi=("महिला खतरे में", "महिला सुरक्षित नहीं", "महिला को खतरा", "महिला के साथ छेड़छाड़", "छेड़छाड़ हो रही है", "यौन उत्पीड़न", "यौन हमला", "बलात्कार", "बलात्कार की कोशिश", "महिला पर हमला", "महिला को धमकी", "महिला का पीछा कर रहा है", "महिला का पीछा किया जा रहा है", "मेरा पीछा कर रहा है", "घर में जबरदस्ती घुस आया", "पति मार रहा है", "घरेलू हिंसा"),
        gujarati=("મહિલા જોખમમાં છે", "મહિલાને ખતરો છે", "મહિલા સાથે છેડતી", "હેરાનગતિ", "યૌન ઉત્પીડન", "યૌન હુમલો", "બળાત્કાર", "બળાત્કારની કોશિશ", "મહિલા પર હુમલો", "મહિલાને ધમકી", "મારો પીછો કરે છે", "ઘરમાં જબરદસ્તી ઘૂસ્યો"),
        marathi=("महिला धोक्यात आहे", "महिलेला धोका आहे", "महिलेची छेडछाड", "लैंगिक छळ", "लैंगिक अत्याचार", "बलात्कार", "बलात्काराचा प्रयत्न", "महिलेवर हल्ला", "महिलेला धमकी", "महिलेचा पाठलाग होत आहे", "माझा पाठलाग करत आहे", "घरात जबरदस्तीने घुसला"),
        romanized=("mahila khatre mein", "mera picha kar raha", "mujhe follow kar raha", "woman ko follow kar raha", "stalking", "ghar mein ghus aaya", "pati maar raha"),
        code_mixed=("woman danger mein hai", "someone is following me", "mahila ko threat", "domestic violence ho raha"),
        stt_variants=("mahila khatre me", "picha", "follow karra", "harasment", "molestation"),
    ),
    "domestic_violence": EmergencyLexicon(
        english=("domestic violence", "domestic abuse", "husband beating wife", "wife being beaten", "family violence", "family fight", "beating at home", "physical abuse", "threatening at home", "partner attacking", "partner violence"),
        hindi=("घरेलू हिंसा", "घरेलू मारपीट", "पति मार रहा है", "पति ने मारा", "पत्नी को मार रहा है", "घर में मारपीट", "घर में झगड़ा", "घर में हिंसा", "परिवार में मारपीट", "मुझे घर में मार रहे हैं", "मुझे पति मार रहा है", "मुझे जान से मारने की धमकी"),
        gujarati=("ઘરેલું હિંસા", "ઘરમાં મારામારી", "પતિ મારી રહ્યો છે", "પત્નીને મારી રહ્યો છે", "ઘરમાં ઝઘડો", "ઘરમાં હિંસા", "પરિવારમાં મારામારી", "મને મારી રહ્યા છે", "મને જાનથી મારી નાખવાની ધમકી"),
        marathi=("घरगुती हिंसाचार", "घरात मारामारी", "पती मारत आहे", "पत्नीला मारत आहे", "घरात भांडण", "घरात हिंसा", "कुटुंबात मारामारी", "मला मारत आहेत", "मला जीवे मारण्याची धमकी"),
        romanized=("ghar mein maarpeet", "pati maar raha", "mujhe ghar mein maar rahe", "ghar mein jhagda", "ghar mein hinsa"),
        code_mixed=("husband maar raha", "ghar mein domestic violence", "partner attack kar raha", "family fight ho rahi"),
        stt_variants=("gharilu hinsa", "marpit", "maar peet", "pati marra"),
    ),
    "missing_person": EmergencyLexicon(
        english=("missing person", "missing child", "child missing", "my child is missing", "kid missing", "lost child", "lost person", "person missing", "cannot find child", "cannot find my child", "child disappeared", "person disappeared", "kidnapped child", "elderly person missing", "elderly missing"),
        hindi=("लापता", "लापता व्यक्ति", "व्यक्ति लापता", "बच्चा लापता", "बच्चा गायब", "बच्चा खो गया", "बच्चा नहीं मिल रहा", "बच्चा कहीं चला गया", "व्यक्ति गायब", "कोई मिल नहीं रहा", "बुजुर्ग लापता", "बुजुर्ग गायब", "अपहरण हुआ", "बच्चे का अपहरण"),
        gujarati=("ગુમ વ્યક્તિ", "વ્યક્તિ ગુમ છે", "બાળક ગુમ છે", "બાળક મળી રહ્યું નથી", "બાળક ખોવાઈ ગયું", "વ્યક્તિ ગુમ થઈ ગયો", "વ્યક્તિ ગુમ થઈ ગઈ", "બાળક ક્યાંક ચાલ્યું ગયું", "વૃદ્ધ વ્યક્તિ ગુમ", "અપહરણ"),
        marathi=("हरवलेली व्यक्ती", "व्यक्ती हरवली", "मुलगा हरवला", "मुलगी हरवली", "मूल हरवले", "मुलगा सापडत नाही", "मुलगी सापडत नाही", "व्यक्ती बेपत्ता", "बेपत्ता व्यक्ती", "वृद्ध व्यक्ती बेपत्ता", "अपहरण"),
        romanized=("lapata", "bachcha gum", "bachcha kho gaya", "bacha nahi mil raha", "missing person", "kid missing", "cannot find child"),
        code_mixed=("child gum hai", "bachcha missing hai", "kid nahi mil raha", "person lapata hai"),
        stt_variants=("lapta", "gum person", "bacha mising", "missing bacha"),
    ),
    "natural_disaster": EmergencyLexicon(
        english=("earthquake", "earthquake happening", "earthquake damage", "flood", "flash flood", "flooding", "water rising", "heavy rain", "cloudburst", "landslide", "mudslide", "cyclone", "storm", "thunderstorm", "lightning", "lightning strike", "tornado", "tsunami", "earthquake trapped", "flood trapped", "landslide trapped", "building collapsed", "bridge collapsed", "road washed away"),
        hindi=("भूकंप", "भूकंप आ रहा है", "भूकंप आया है", "बाढ़", "बाढ़ आ गई", "पानी भर गया", "पानी बढ़ रहा है", "अचानक बाढ़", "भारी बारिश", "बादल फटना", "बादल फट गया", "भूस्खलन", "पहाड़ गिर गया", "चक्रवात", "तूफान", "आंधी", "बिजली गिरना", "आसमान से बिजली गिरी", "सुनामी", "इमारत गिर गई", "पुल गिर गया", "सड़क बह गई", "मलबे में फंसे"),
        gujarati=("ભૂકંપ", "ભૂકંપ આવ્યો છે", "પૂર", "પૂર આવ્યું છે", "પાણી ભરાઈ ગયું", "પાણી વધી રહ્યું છે", "અચાનક પૂર", "ભારે વરસાદ", "વાદળ ફાટ્યું", "ભૂસ્ખલન", "પહાડ ધસી પડ્યો", "વાવાઝોડું", "તોફાન", "વીજળી પડી", "સુનામી", "મકાન ધરાશાયી", "પુલ તૂટી પડ્યો", "રસ્તો ધોવાઈ ગયો", "કાટમાળમાં ફસાયા"),
        marathi=("भूकंप", "भूकंप झाला", "पूर", "पूर आला आहे", "पाणी भरले", "पाणी वाढत आहे", "अचानक पूर", "मुसळधार पाऊस", "ढगफुटी", "भूस्खलन", "दरड कोसळली", "चक्रीवादळ", "वादळ", "वीज पडली", "त्सुनामी", "इमारत कोसळली", "पूल कोसळला", "रस्ता वाहून गेला", "ढिगाऱ्यात अडकले"),
        romanized=("bhukamp", "baadh", "paani bhar gaya", "baarish", "baadal phat gaya", "bhooskhalan", "toofan", "bijli gir gayi", "pul gir gaya"),
        code_mixed=("flood aa gaya", "heavy rain se road wash", "building gir gayi", "earthquake aaya", "paani badh raha"),
        stt_variants=("bhukam", "baadh", "land slide", "cloud burst", "cyclon"),
    ),
    "structural_collapse": EmergencyLexicon(
        english=("building collapse", "building collapsed", "house collapsed", "wall collapsed", "roof collapsed", "ceiling collapsed", "bridge collapse", "tower collapse", "structure collapse", "building falling", "building damaged", "cracks in building", "major structural damage", "trapped under rubble", "buried under rubble"),
        hindi=("इमारत गिर गई", "इमारत ढह गई", "मकान गिर गया", "दीवार गिर गई", "छत गिर गई", "छत टूट गई", "पुल गिर गया", "इमारत ढहने वाली है", "इमारत में दरार", "बड़ी दरार", "इमारत क्षतिग्रस्त", "मलबे में फंसा", "मलबे में दबा", "मलबे के नीचे लोग", "इमारत के नीचे लोग फंसे"),
        gujarati=("મકાન ધરાશાયી", "ઇમારત પડી ગઈ", "દિવાલ પડી ગઈ", "છત પડી ગઈ", "પુલ પડી ગયો", "મકાનમાં તિરાડ", "મોટી તિરાડ", "મકાન નુકસાનગ્રસ્ત", "કાટમાળમાં ફસાયેલા", "કાટમાળ નીચે લોકો"),
        marathi=("इमारत कोसळली", "घर कोसळले", "भिंत पडली", "छत पडले", "पूल कोसळला", "इमारतीला भेगा", "मोठी भेग", "इमारत खराब झाली", "ढिगाऱ्यात अडकले", "ढिगाऱ्याखाली लोक"),
        romanized=("building gir gayi", "makaan gir gaya", "deewar gir gayi", "chhat gir gayi", "malbe mein fase", "building mein crack"),
        code_mixed=("building collapse ho gaya", "roof gir gayi", "wall collapse", "rubble mein people trapped"),
        stt_variants=("buildng collapse", "makaan colapse", "malba", "debries"),
    ),
    "rescue": EmergencyLexicon(
        english=("trapped", "stuck", "cannot get out", "unable to escape", "locked inside", "trapped inside", "buried", "stuck under debris", "stuck in lift", "elevator stuck", "lift stuck", "people trapped", "child trapped", "person trapped", "rescue needed", "rescue team needed", "send rescue", "rescue required", "help us get out"),
        hindi=("फंस गया", "फंस गए", "फंसे हुए हैं", "फंसा हुआ है", "बाहर नहीं निकल पा रहे", "अंदर फंस गए", "कमरे में फंस गए", "लिफ्ट में फंस गए", "लिफ्ट अटक गई", "मलबे में फंस गए", "मलबे के नीचे फंस गए", "लोग फंसे हुए हैं", "बच्चा फंस गया", "व्यक्ति फंस गया", "बचाव चाहिए", "रेस्क्यू चाहिए", "रेस्क्यू टीम भेजो", "बचाव दल भेजो", "बाहर निकालो", "मदद करो बाहर नहीं निकल पा रहे"),
        gujarati=("ફસાઈ ગયા", "ફસાઈ ગયો", "ફસાઈ ગઈ", "બહાર નીકળી શકતા નથી", "અંદર ફસાયા છે", "લિફ્ટમાં ફસાયા", "લિફ્ટ અટકી ગઈ", "કાટમાળમાં ફસાયા", "કાટમાળ નીચે ફસાયા", "લોકો ફસાયા છે", "બાળક ફસાયું છે", "બચાવ જોઈએ", "રેસ્ક્યુ જોઈએ", "રેસ્ક્યુ ટીમ મોકલો", "બહાર કાઢો"),
        marathi=("अडकले", "अडकला", "अडकली", "अडकले आहेत", "बाहेर पडता येत नाही", "आत अडकले", "लिफ्टमध्ये अडकले", "लिफ्ट अडकली", "ढिगाऱ्यात अडकले", "ढिगाऱ्याखाली अडकले", "लोक अडकले आहेत", "मूल अडकले", "बचाव हवा", "रेस्क्यू हवा", "रेस्क्यू टीम पाठवा", "बाहेर काढा"),
        romanized=("phans gaya", "andar phans gaye", "bahar nahi nikal pa rahe", "lift mein phans gaye", "rescue chahiye", "bachao", "bahar nikalo"),
        code_mixed=("people andar trapped", "lift mein stuck", "rescue team bhejo", "help us bahar nikalo", "child trapped hai"),
        stt_variants=("phans", "fans gaye", "reskyu", "rescue moklo", "lift atak"),
    ),
    "drowning": EmergencyLexicon(
        english=("drowning", "drowning person", "person drowning", "child drowning", "fell into water", "fell into river", "fell into lake", "fell into well", "fell into pond", "swept away", "washed away", "person in water", "cannot swim", "water rescue", "boat accident", "boat capsized"),
        hindi=("डूब रहा है", "डूब गया", "डूब गई", "डूबने लगा", "डूबने वाली है", "पानी में गिर गया", "नदी में गिर गया", "तालाब में गिर गया", "कुएं में गिर गया", "नहर में गिर गया", "पानी में बह गया", "बह गया", "बह गई", "डूबता हुआ व्यक्ति", "बचाओ डूब रहा है", "नाव पलट गई", "नाव डूब गई", "नदी में हादसा"),
        gujarati=("ડૂબી રહ્યો છે", "ડૂબી રહ્યું છે", "ડૂબી ગયો", "પાણીમાં પડી ગયો", "પાણીમાં પડી ગયું", "નદીમાં પડી ગયો", "નદીમાં પડી ગયું", "તળાવમાં પડી ગયો", "કૂવામાં પડી ગયો", "પાણીમાં વહી ગયો", "વહી ગઈ", "ડૂબતો માણસ", "બચાવો ડૂબી રહ્યો છે", "નાવ પલટી ગઈ", "નાવ ડૂબી ગઈ"),
        marathi=("बुडत आहे", "बुडाला", "बुडाली", "पाण्यात पडला", "नदीत पडला", "तलावात पडला", "विहिरीत पडला", "पाण्यात वाहून गेला", "बुडणारी व्यक्ती", "वाचवा बुडत आहे", "नाव उलटली", "नाव बुडाली"),
        romanized=("doob raha", "paani mein gir gaya", "nadi mein gir gaya", "doob gaya", "bachao doob raha", "naav palat gayi"),
        code_mixed=("river mein gir gaya", "person drowning hai", "water rescue chahiye", "boat capsized hai"),
        stt_variants=("dub raha", "doobra", "paani me gir", "nav dubli"),
    ),
    "electrical": EmergencyLexicon(
        english=("electric shock", "electrocution", "electrical accident", "electric wire fallen", "live wire", "high voltage", "power line fallen", "transformer explosion", "transformer fire", "electrical fire", "short circuit", "sparking", "electric spark", "electric pole fallen"),
        hindi=("बिजली का झटका", "करंट लग गया", "बिजली का करंट", "बिजली का तार गिर गया", "खुला बिजली का तार", "बिजली की तार", "हाई वोल्टेज", "बिजली का पोल गिर गया", "ट्रांसफार्मर फट गया", "ट्रांसफार्मर में आग", "शॉर्ट सर्किट", "चिंगारी", "बिजली की चिंगारी"),
        gujarati=("વીજળીનો ઝટકો", "કરંટ લાગ્યો", "વીજળીનો તાર પડી ગયો", "ખુલ્લો વીજળીનો તાર", "હાઈ વોલ્ટેજ", "વીજળીનો થાંભલો પડી ગયો", "ટ્રાન્સફોર્મર ફાટ્યું", "ટ્રાન્સફોર્મરમાં આગ", "શોર્ટ સર્કિટ", "ચિંગારી"),
        marathi=("वीज लागली", "वीजेचा धक्का", "करंट लागला", "वीज पडली", "वीजेची तार पडली", "उघडी वीजेची तार", "हाय व्होल्टेज", "वीजेचा खांब पडला", "ट्रान्सफॉर्मर फुटला", "ट्रान्सफॉर्मरला आग", "शॉर्ट सर्किट", "ठिणगी", "वीजेची ठिणगी"),
        romanized=("bijli ka jhatka", "current lag gaya", "karant lag gaya", "short circuit", "chingaari", "wire gir gaya"),
        code_mixed=("electric shock laga", "live wire gir gaya", "transformer mein fire", "short circuit se aag"),
        stt_variants=("karent", "curent", "bijli jatka", "short circut", "transformer fat"),
    ),
    "chemical_hazmat": EmergencyLexicon(
        english=("chemical leak", "chemical spill", "toxic gas", "poisonous gas", "toxic fumes", "chemical explosion", "hazardous material", "hazmat", "dangerous chemical", "chemical exposure", "gas fumes", "chemical smell", "poison leak", "industrial chemical leak"),
        hindi=("केमिकल लीक", "रासायनिक रिसाव", "जहरीली गैस", "विषैली गैस", "जहरीला धुआं", "विषैला धुआं", "केमिकल फैल गया", "रसायन फैल गया", "खतरनाक केमिकल", "जहरीली गैस निकल रही है", "केमिकल की बदबू", "रासायनिक हादसा", "फैक्टरी से गैस निकल रही है"),
        gujarati=("કેમિકલ લીક", "રાસાયણિક લીકેજ", "ઝેરી ગેસ", "ઝેરી ધુમાડો", "કેમિકલ ફેલાયું", "ખતરનાક કેમિકલ", "કેમિકલની વાસ", "ફેક્ટરીમાંથી ગેસ નીકળે છે"),
        marathi=("केमिकल गळती", "रासायनिक गळती", "विषारी वायू", "विषारी धूर", "केमिकल सांडले", "धोकादायक केमिकल", "केमिकलचा वास", "कारखान्यातून गॅस बाहेर येत आहे"),
        romanized=("chemical leak", "zehri gas", "toxic gas", "chemical spill", "factory se gas", "zehreela dhuaan"),
        code_mixed=("factory mein chemical leak", "toxic gas aa rahi", "chemical spill ho gaya", "hazmat emergency"),
        stt_variants=("kemikal", "chemical leek", "toxic fume", "haz mat", "zehri gas"),
    ),
    "traffic_obstruction": EmergencyLexicon(
        english=("road blocked", "road closed", "highway blocked", "traffic jam due to accident", "major traffic obstruction", "bridge blocked", "road damaged", "road collapsed", "vehicle blocking road", "fallen tree blocking road"),
        hindi=("रास्ता बंद", "सड़क बंद", "सड़क जाम", "हाईवे बंद", "रास्ता ब्लॉक", "सड़क पर गाड़ी फंसी", "सड़क पर पेड़ गिर गया", "पुल बंद", "पुल टूट गया", "सड़क टूट गई", "सड़क बह गई", "हाईवे पर बड़ा जाम"),
        gujarati=("રસ્તો બંધ", "રસ્તો બ્લોક", "ટ્રાફિક જામ", "હાઇવે બંધ", "રસ્તા પર ગાડી ફસાઈ", "રસ્તા પર ઝાડ પડ્યું", "પુલ બંધ", "પુલ તૂટી ગયો", "રસ્તો તૂટી ગયો"),
        marathi=("रस्ता बंद", "रस्ता ब्लॉक", "वाहतूक कोंडी", "ट्रॅफिक जाम", "महामार्ग बंद", "रस्त्यावर गाडी अडकली", "रस्त्यावर झाड पडले", "पूल बंद", "पूल तुटला", "रस्ता तुटला"),
        romanized=("rasta band", "sadak band", "road block", "highway jam", "traffic jam", "gaadi rasta rok rahi"),
        code_mixed=("road blocked hai", "highway par jam", "traffic bahut hai", "bridge block ho gaya"),
        stt_variants=("rasta blak", "trafic jam", "hwy blocked", "road blok"),
    ),
    "animal_attack": EmergencyLexicon(
        english=("snake bite", "snake attack", "dog bite", "dog attack", "animal attack", "wild animal attack", "leopard attack", "tiger attack", "elephant attack", "wild boar attack", "monkey attack", "bee attack", "wasp attack"),
        hindi=("सांप ने काट लिया", "सांप का हमला", "सांप दिखा", "कुत्ते ने काट लिया", "कुत्ते का हमला", "जानवर ने हमला किया", "जंगली जानवर का हमला", "तेंदुए का हमला", "बाघ का हमला", "हाथी का हमला", "बंदर का हमला", "मधुमक्खियों का हमला"),
        gujarati=("સાપે ડંખ માર્યો", "સાપનો હુમલો", "કૂતરાએ કરડ્યું", "કૂતરાનો હુમલો", "પ્રાણીનો હુમલો", "જંગલી પ્રાણીનો હુમલો", "દીપડાનો હુમલો", "વાઘનો હુમલો", "હાથીનો હુમલો", "વાંદરાનો હુમલો", "મધમાખીનો હુમલો"),
        marathi=("साप चावला", "सापाचा हल्ला", "कुत्र्याने चावले", "कुत्र्याने चावा घेतला", "कुत्र्याचा हल्ला", "प्राण्याचा हल्ला", "वन्य प्राण्याचा हल्ला", "बिबट्याचा हल्ला", "वाघाचा हल्ला", "हत्तीचा हल्ला", "माकडाचा हल्ला", "मधमाशांचा हल्ला"),
        romanized=("saanp ne kaata", "saap ne kata", "kutte ne kaata", "dog bite", "jaanwar ka hamla", "snake attack"),
        code_mixed=("snake ne bite kiya", "dog attack hua", "animal attack ho raha", "saanp ka bite"),
        stt_variants=("sanp", "samp bite", "kutta kata", "animal atak"),
    ),
    "cyber_crime": EmergencyLexicon(
        english=("cyber attack", "cyber crime", "online fraud", "bank fraud", "upi fraud", "upi scam", "otp fraud", "otp scam", "online scam", "account hacked", "phone hacked", "email hacked", "identity theft", "money stolen online", "financial fraud", "digital fraud", "phishing", "ransomware", "blackmail online"),
        hindi=("साइबर क्राइम", "साइबर अपराध", "ऑनलाइन ठगी", "ऑनलाइन धोखाधड़ी", "बैंक फ्रॉड", "बैंक से पैसे निकल गए", "यूपीआई फ्रॉड", "यूपीआई स्कैम", "ओटीपी फ्रॉड", "ओटीपी स्कैम", "ऑनलाइन स्कैम", "अकाउंट हैक हो गया", "फोन हैक हो गया", "ईमेल हैक हो गया", "पैसे ऑनलाइन चोरी हो गए", "साइबर ठगी", "फिशिंग", "ऑनलाइन ब्लैकमेल"),
        gujarati=("સાયબર ક્રાઇમ", "સાયબર ગુનો", "ઓનલાઇન છેતરપિંડી", "ઓનલાઇન છેતરપિંડીમાં", "ઓનલાઈન છેતરપિંડી", "ઓનલાઈન છેતરપિંડીમાં", "બેંક ફ્રોડ", "upi ફ્રોડ", "upi સ્કેમ", "otp ફ્રોડ", "ઓનલાઇન સ્કેમ", "એકાઉન્ટ હેક થઈ ગયું", "ફોન હેક થઈ ગયો", "પૈસા ઓનલાઇન ચોરાઈ ગયા", "સાયબર છેતરપિંડી"),
        marathi=("सायबर क्राईम", "सायबर गुन्हा", "ऑनलाइन फसवणूक", "ऑनलाइन फसवणुकीत", "बँक फ्रॉड", "upi फ्रॉड", "upi स्कॅम", "otp फ्रॉड", "ऑनलाइन स्कॅम", "अकाउंट हॅक झाले", "फोन हॅक झाला", "ऑनलाइन पैसे चोरीला गेले", "सायबर फसवणूक"),
        romanized=("cyber crime", "online thagi", "online fraud", "upi fraud", "otp scam", "account hack", "paise chori online"),
        code_mixed=("online paise chori", "bank account hack ho gaya", "upi fraud hua", "phone hack hai", "cyber complaint"),
        stt_variants=("cybercrim", "onlain fraud", "upi frad", "otipi scam", "hack ho gya"),
    ),
    "crowd_emergency": EmergencyLexicon(
        english=("stampede", "crowd crush", "crowd panic", "crowd emergency", "large crowd", "people running", "mass casualty", "mass injury", "public disturbance", "riot", "violent protest", "crowd fighting"),
        hindi=("भगदड़", "भगदड़ मच गई", "भीड़ में भगदड़", "भीड़ कुचल रही है", "बहुत भीड़", "भीड़ बेकाबू", "लोग भाग रहे हैं", "भीड़ में लोग फंसे", "सामूहिक चोट", "दंगा", "हिंसक प्रदर्शन", "भीड़ में मारपीट"),
        gujarati=("નાસભાગ", "નાસભાગ મચી ગઈ", "ભીડમાં નાસભાગ", "ખૂબ મોટી ભીડ", "ભીડ બેકાબૂ", "લોકો ભાગી રહ્યા છે", "ભીડમાં લોકો ફસાયા", "તોફાન", "હિંસક વિરોધ"),
        marathi=("चेंगराचेंगरी", "चेंगराचेंगरी झाली", "गर्दीत चेंगराचेंगरी", "मोठी गर्दी", "गर्दी नियंत्रणाबाहेर", "लोक पळत आहेत", "गर्दीत लोक अडकले", "दंगल", "हिंसक आंदोलन"),
        romanized=("bhagdad", "bheed mein bhagdad", "bheed bekabu", "log bhaag rahe", "stampede", "danga"),
        code_mixed=("crowd bahut hai", "bheed mein people trapped", "stampede ho gaya", "public disturbance hai"),
        stt_variants=("stampid", "bhagdar", "bheed crush", "crowd panik"),
    ),
    "self_harm_crisis": EmergencyLexicon(
        english=("suicide", "suicidal", "kill myself", "want to die", "going to die", "self harm", "harm myself", "attempted suicide", "suicide attempt", "person trying to kill themselves", "threatening to jump from the roof", "threatening to jump from a roof"),
        hindi=("आत्महत्या", "आत्महत्या करने वाला", "मैं मरना चाहता हूं", "मैं मरना चाहती हूं", "मैं खुद को मारना चाहता हूं", "मैं खुद को मारना चाहती हूं", "खुद को नुकसान पहुंचाना", "जान देने की कोशिश", "आत्महत्या की कोशिश", "खुद को मारने की कोशिश", "छत से कूदने की धमकी"),
        gujarati=("આત્મહત્યા", "મારે મરી જવું છે", "હું મારી જાતને મારી નાખીશ", "પોતાને નુકસાન પહોંચાડવું", "આત્મહત્યાનો પ્રયાસ", "પોતાને મારી નાખવાની કોશિશ", "છત પરથી કૂદવાની ધમકી"),
        marathi=("आत्महत्या", "मला मरायचे आहे", "मी स्वतःला मारून घेईन", "स्वतःला इजा करणे", "आत्महत्येचा प्रयत्न", "स्वतःला मारण्याचा प्रयत्न", "छतावरून उडी मारण्याची धमकी"),
        romanized=("aatmahatya", "marna chahta", "marna chahti", "khud ko maar dunga", "khud ko nuksan", "suicide karunga", "chhat se kudne ki dhamki"),
        code_mixed=("I want marna", "khud ko harm karunga", "suicide karne wala", "self harm karna hai", "chhat se kudne ki dhamki de raha"),
        stt_variants=("suicid", "self harm", "marna he", "atmahatya", "khudko maar"),
    ),
    "injury": EmergencyLexicon(
        english=("injury", "injuries", "injured", "wounded", "hurt", "fracture", "broken bone", "burn injury", "casualty", "casualties"),
        hindi=("चोट", "चोट लगी", "घायल", "जख्मी", "हड्डी टूट", "फ्रैक्चर", "जल गया", "जल गई"),
        gujarati=("ઇજા", "ઇજા થઈ", "ઘાયલ", "જખ્મી", "હાડકું તૂટ્યું", "ફ્રેક્ચર", "દાઝી ગયા"),
        marathi=("इजा", "जखमी", "दुखापत", "हाड मोडले", "फ्रॅक्चर", "भाजले"),
        romanized=("chot lagi", "ghayal", "zakhmi", "haddi tuti", "fracture"),
        code_mixed=("injury hui", "hurt ho gaya", "bone fracture", "burn injury"),
        stt_variants=("injurd", "ghayal hai", "jakhmi", "chot lagi hai"),
    ),
    "bleeding": EmergencyLexicon(
        english=("bleeding", "blood loss", "blood is flowing", "heavy bleeding", "severe bleeding", "blood pouring"),
        hindi=("खून बह रहा", "खून बहना", "खून निकल रहा", "भारी रक्तस्राव", "रक्तस्राव"),
        gujarati=("લોહી વહી રહ્યું", "લોહી નીકળી રહ્યું", "ખૂબ લોહી", "રક્તસ્રાવ"),
        marathi=("रक्त वाहत", "रक्तस्राव", "खूप रक्त", "रक्त येत"),
        romanized=("khoon beh raha", "khoon nikal raha", "bahut khoon", "bleeding ho rahi"),
        code_mixed=("heavy bleeding", "blood aa raha hai"),
        stt_variants=("bleedin", "khoon beh rha", "blood loss"),
    ),
    "unconscious": EmergencyLexicon(
        english=("unconscious", "passed out", "fainted", "not responding", "not waking up"),
        hindi=("बेहोश", "होश नहीं", "जवाब नहीं दे रहे", "जवाब नहीं दे रही"),
        gujarati=("બેભાન", "ભાન નથી", "જવાબ આપતા નથી", "જવાબ આપતી નથી"),
        marathi=("बेशुद्ध", "शुद्धीत नाही", "उत्तर देत नाही", "शुद्ध हरपली"),
        romanized=("behosh", "hosh nahi", "jawab nahi de raha"),
        code_mixed=("unconscious hai", "not responding"),
        stt_variants=("behos", "behosh hai", "fainted"),
    ),
}

# Existing deterministic flags are intentionally narrower than the public
# domains.  Several domains contribute evidence to one established flag while
# preserving the original schema and policy layer.
LEXICON["road_accident"] = replace(
    LEXICON["road_accident"],
    hindi=(*LEXICON["road_accident"].hindi, "एक्सिडेंट", "एक्सीडेंट", "टक्कर मारी", "गाड़ी ने उड़ा दिया", "कुचल दिया", "बाइक स्लिप"),
    gujarati=(*LEXICON["road_accident"].gujarati, "એક્સિડન્ટ", "અકસ્મત", "અકસમાત", "ટક્કર મારી", "બાઇક સ્લિપ"),
    marathi=(*LEXICON["road_accident"].marathi, "एक्सिडेंट", "टक्कर मारली", "गाडीने उडवले", "चिरडले", "बाईक घसरली"),
    romanized=(*LEXICON["road_accident"].romanized, "accident ho gaya", "takkar maari", "gaadi ne uda diya", "kuchal diya", "bike slip"),
)
LEXICON["medical"] = replace(
    LEXICON["medical"],
    hindi=(*LEXICON["medical"].hindi, "हार्ट अटैक", "एम्बुलेंस", "ऐम्बुलेंस", "सांस नहीं"),
    gujarati=(*LEXICON["medical"].gujarati, "હાર્ટ એટેક", "એમ્બ્યુલન્સ", "શ્વાસ નથી"),
    marathi=(*LEXICON["medical"].marathi, "हार्ट अटॅक", "रुग्णवाहिका", "श्वास घेत नाही"),
    romanized=(*LEXICON["medical"].romanized, "behosh", "saans nahi", "sans nahi"),
)
LEXICON["fire"] = replace(
    LEXICON["fire"],
    hindi=(*LEXICON["fire"].hindi, "फायर ब्रिगेड", "आग लग गई"),
    gujarati=(*LEXICON["fire"].gujarati, "ફાયર બ્રિગેડ", "આગ લાગી ગઈ"),
    marathi=(*LEXICON["fire"].marathi, "फायर ब्रिगेड", "आग लागली"),
    romanized=(*LEXICON["fire"].romanized, "aag lag gayi"),
)
LEXICON["gas_lpg"] = replace(
    LEXICON["gas_lpg"],
    romanized=(*LEXICON["gas_lpg"].romanized, "cylinder phat gaya"),
)
LEXICON["police_crime"] = replace(
    LEXICON["police_crime"],
    romanized=(*LEXICON["police_crime"].romanized, "chori ho rahi hai", "chain snatching"),
)


EVIDENCE_FLAG_DOMAINS: dict[str, tuple[str, ...]] = {
    "fire": ("fire",),
    "explosion": ("explosion",),
    "lpg": ("gas_lpg",),
    "accident": ("road_accident", "railway"),
    "road": ("road_accident", "traffic_obstruction"),
    "railway": ("railway",),
    "medical": ("medical", "animal_attack", "electrical", "drowning", "self_harm_crisis"),
    "injury": ("injury", "animal_attack", "crowd_emergency"),
    "bleeding": ("bleeding",),
    "unconscious": ("unconscious",),
    "trapped": ("rescue", "structural_collapse", "natural_disaster", "crowd_emergency"),
    "rescue": ("rescue", "drowning", "structural_collapse", "natural_disaster"),
    "police": ("police_crime", "women_safety", "domestic_violence", "missing_person", "crowd_emergency"),
    # Weapons require explicit weapon terms; general police/crime language
    # must never manufacture a weapon signal.
    "domestic_violence": ("domestic_violence", "women_safety"),
    "child_missing": ("missing_person",),
    "missing": ("missing_person",),
    "child": ("missing_person",),
    "cybercrime": ("cyber_crime",),
    "smoke": ("fire", "chemical_hazmat"),
}


@lru_cache(maxsize=4096)
def _term_pattern(term: str) -> re.Pattern[str]:
    words = r"\s+".join(re.escape(word) for word in term.split())
    return re.compile(rf"(?<!{_W}){words}(?!{_W})", re.IGNORECASE)


def _affirmed_term(text: str, term: str) -> bool:
    """Match a reviewed term; do not fuzzy-match arbitrary user text."""
    pattern = _term_pattern(term)
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


def lexicon_matches(text: str, language: str = "en") -> dict[str, tuple[str, ...]]:
    """Return matched domain terms for audit/debugging, without classification."""
    normalized = " ".join(text.casefold().split())
    matches: dict[str, tuple[str, ...]] = {}
    for domain, resource in LEXICON.items():
        found = tuple(term for term in resource.terms(language) if _affirmed_term(normalized, term.casefold()))
        if found:
            matches[domain] = found
    return matches


def supporting_evidence(text: str, language: str = "en") -> dict[str, bool]:
    """Project lexicon domain matches onto the existing evidence flags."""
    matches = lexicon_matches(text, language)
    result = {
        flag: any(domain in matches for domain in domains)
        for flag, domains in EVIDENCE_FLAG_DOMAINS.items()
    }
    # Generic words such as “accident” are intentionally ambiguous.  A
    # railway sentence must not acquire road evidence merely because the road
    # domain contains that generic term.
    if "railway" in matches:
        result["road"] = False
    return result


def iter_terms() -> Iterable[tuple[str, str, str]]:
    """Yield ``(domain, bucket, term)`` records for tests and evaluation."""
    for domain, resource in LEXICON.items():
        for bucket in LANGUAGES:
            for term in getattr(resource, bucket):
                yield domain, bucket, term
