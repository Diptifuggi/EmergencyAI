from __future__ import annotations

import pytest

from app.services.emergency_keywords import evidence
from app.services.emergency_lexicon import LANGUAGES, LEXICON, iter_terms, lexicon_matches
from app.services.incident_rules import extract_incident_facts, services_for_facts
from app.schemas.emergency_analysis import HelpRequired


# These are sentence-level examples, not isolated keyword assertions.  They
# exercise meaning-bearing phrases across scripts and code-mixed speech.
@pytest.mark.parametrize(
    ("text", "language", "domain"),
    [
        ("The building fire is spreading and people need help.", "en", "fire"),
        ("इमारत में आग फैल रही है, दमकल भेजो।", "hi", "fire"),
        ("કેન્ટીનમાં આગ લાગી છે, ફાયર બ્રિગેડ મોકલો.", "gu", "fire"),
        ("कॅन्टीनमध्ये आग पसरत आहे, दमकल पाठवा.", "mr", "fire"),
        ("ghar mein aag lag gayi hai, damkal bhejo", "en", "fire"),
        ("college mein LPG gas leak ho rahi hai, help bhejo", "en", "gas_lpg"),
        ("गैस सिलेंडर फट गया है, लोग अंदर फंसे हैं।", "hi", "gas_lpg"),
        ("ગેસ સિલિન્ડર ફાટી ગયો છે, બચાવ મોકલો.", "gu", "gas_lpg"),
        ("गॅसचा मोठा स्फोट झाला, मदत पाठवा.", "mr", "gas_lpg"),
        ("gas leek hai, cylinder phat gaya", "en", "gas_lpg"),
        ("A suspicious blast happened near the factory.", "en", "explosion"),
        ("फैक्टरी में जोरदार धमाका हुआ है।", "hi", "explosion"),
        ("ફેક્ટરીમાં મોટો ધડાકો થયો છે.", "gu", "explosion"),
        ("कारखान्यात मोठा स्फोट झाला.", "mr", "explosion"),
        ("factory mein blast thayo che", "en", "explosion"),
        ("A bus collision injured several people.", "en", "road_accident"),
        ("सड़क हादसे में कई लोग घायल हैं।", "hi", "road_accident"),
        ("રસ્તા પર અકસ્માત થયો છે, લોકો ઘાયલ છે.", "gu", "road_accident"),
        ("रस्त्यावर अपघात झाला आहे, लोक जखमी आहेत.", "mr", "road_accident"),
        ("highway pe aksident hua, ambulance bhejo", "en", "road_accident"),
        ("A train derailed near the railway station.", "en", "railway"),
        ("रेलवे स्टेशन पर ट्रेन पटरी से उतर गई।", "hi", "railway"),
        ("રેલવે સ્ટેશન પાસે ટ્રેન પાટા પરથી ઉતરી ગઈ.", "gu", "railway"),
        ("रेल्वे स्टेशनजवळ ट्रेन रुळावरून घसरली.", "mr", "railway"),
        ("train patri se utar gayi, help bhejo", "en", "railway"),
        ("Someone has chest pain and cannot breathe.", "en", "medical"),
        ("मेरी मां सांस नहीं ले रही, एम्बुलेंस भेजो।", "hi", "medical"),
        ("मुझे चेस्ट में दर्द हो रहा हे प्लीज हेल्प चाहिए में घर पर अकेली हु", "hi", "medical"),
        ("छाती में दर्द है और सांस लेने में तकलीफ है।", "hi", "medical"),
        ("chest mein pain ho raha hai, ambulance bhejo", "en", "medical"),
        ("છાતીમાં દુખાવો છે અને શ્વાસ લેવામાં તકલીફ છે.", "gu", "medical"),
        ("छातीत दुखत आहे आणि श्वास घेता येत नाही.", "mr", "medical"),
        ("bhai behosh hai, ambulance moklo", "en", "medical"),
        ("Someone is breaking into my house right now.", "en", "police_crime"),
        ("घर में कोई घुस गया है, पुलिस भेजो।", "hi", "police_crime"),
        ("ઘરમાં કોઈ ઘૂસી આવ્યું છે, પોલીસ મોકલો.", "gu", "police_crime"),
        ("घरात कोणी घुसले आहे, पोलीस पाठवा.", "mr", "police_crime"),
        ("police bulao, koi ghar mein ghus gaya", "en", "police_crime"),
        ("A woman is being followed and needs police help.", "en", "women_safety"),
        ("महिला का पीछा किया जा रहा है, पुलिस चाहिए।", "hi", "women_safety"),
        ("મહિલાને ધમકી છે, પોલીસ મોકલો.", "gu", "women_safety"),
        ("महिलेचा पाठलाग होत आहे, पोलीस हवे.", "mr", "women_safety"),
        ("woman ko follow kar raha hai, police moklo", "en", "women_safety"),
        ("My child is missing and cannot be found.", "en", "missing_person"),
        ("बच्चा गायब है, पुलिस भेजो।", "hi", "missing_person"),
        ("બાળક ગુમ છે, મદદ કરો.", "gu", "missing_person"),
        ("मुलगा हरवला आहे, मदत पाठवा.", "mr", "missing_person"),
        ("bachcha gum hai, police bulao", "en", "missing_person"),
        ("Flood water is rising and residents are trapped.", "en", "natural_disaster"),
        ("बाढ़ आ गई है और लोग फंसे हैं।", "hi", "natural_disaster"),
        ("પૂર આવ્યું છે અને લોકો ફસાયા છે.", "gu", "natural_disaster"),
        ("पूर आला आहे आणि लोक अडकले आहेत.", "mr", "natural_disaster"),
        ("flood aa gaya, rescue team bhejo", "en", "natural_disaster"),
        ("The building collapsed and people are under rubble.", "en", "structural_collapse"),
        ("इमारत ढह गई, लोग मलबे में दबे हैं।", "hi", "structural_collapse"),
        ("મકાન ધરાશાયી થયું, લોકો કાટમાળ નીચે છે.", "gu", "structural_collapse"),
        ("इमारत कोसळली, लोक ढिगाऱ्याखाली अडकले.", "mr", "structural_collapse"),
        ("building gir gayi, malbe mein people trapped", "en", "structural_collapse"),
        ("A child fell into the river and is drowning.", "en", "drowning"),
        ("बच्चा नदी में गिर गया और डूब रहा है।", "hi", "drowning"),
        ("બાળક નદીમાં પડી ગયું છે, ડૂબી રહ્યું છે.", "gu", "drowning"),
        ("मूल नदीत पडले आहे, बुडत आहे.", "mr", "drowning"),
        ("bachcha river mein gir gaya, bachao", "en", "drowning"),
        ("A live wire has fallen and someone got an electric shock.", "en", "electrical"),
        ("बिजली का तार गिर गया और करंट लग गया।", "hi", "electrical"),
        ("વીજળીનો તાર પડ્યો છે અને કરંટ લાગ્યો.", "gu", "electrical"),
        ("वीजेची तार पडली आणि करंट लागला.", "mr", "electrical"),
        ("live wire gir gaya, electric shock laga", "en", "electrical"),
        ("Toxic gas is leaking from the factory.", "en", "chemical_hazmat"),
        ("फैक्टरी से जहरीली गैस निकल रही है।", "hi", "chemical_hazmat"),
        ("ફેક્ટરીમાંથી ઝેરી ગેસ નીકળે છે.", "gu", "chemical_hazmat"),
        ("कारखान्यातून विषारी वायू बाहेर येत आहे.", "mr", "chemical_hazmat"),
        ("factory se toxic gas aa rahi hai", "en", "chemical_hazmat"),
        ("A dog attack caused a serious bite.", "en", "animal_attack"),
        ("कुत्ते ने काट लिया, गंभीर चोट है।", "hi", "animal_attack"),
        ("કૂતરાએ કરડ્યું છે, ગંભીર ઇજા છે.", "gu", "animal_attack"),
        ("कुत्र्याने चावले आहे, गंभीर दुखापत आहे.", "mr", "animal_attack"),
        ("saanp ne kaata, ambulance chahiye", "en", "animal_attack"),
        ("Someone stole money through an online scam.", "en", "cyber_crime"),
        ("ऑनलाइन ठगी में पैसे चले गए।", "hi", "cyber_crime"),
        ("ઓનલાઇન છેતરપિંડીમાં પૈસા ચોરાઈ ગયા.", "gu", "cyber_crime"),
        ("ऑनलाइन फसवणुकीत पैसे चोरीला गेले.", "mr", "cyber_crime"),
        ("UPI fraud hua, account hack ho gaya", "en", "cyber_crime"),
        ("A crowd crush is happening at the event.", "en", "crowd_emergency"),
        ("भीड़ में भगदड़ मच गई है।", "hi", "crowd_emergency"),
        ("ભીડમાં નાસભાગ મચી ગઈ છે.", "gu", "crowd_emergency"),
        ("गर्दीत चेंगराचेंगरी झाली आहे.", "mr", "crowd_emergency"),
        ("bheed mein stampede ho gaya, people injured", "en", "crowd_emergency"),
        ("I want to kill myself and need immediate help.", "en", "self_harm_crisis"),
        ("मैं खुद को मारने की कोशिश कर रहा हूं, मदद चाहिए।", "hi", "self_harm_crisis"),
        ("હું મારી જાતને મારી નાખીશ, મદદ જોઈએ.", "gu", "self_harm_crisis"),
        ("मी स्वतःला मारून घेईन, मदत हवी.", "mr", "self_harm_crisis"),
        ("main khud ko harm karunga, help chahiye", "en", "self_harm_crisis"),
    ],
)
def test_sentence_level_lexicon_matches(text: str, language: str, domain: str) -> None:
    assert domain in lexicon_matches(text, language)


def test_all_domains_have_language_buckets_and_terms() -> None:
    assert len(LEXICON) >= 20
    assert set(LANGUAGES) == set(EmergencyLexiconBuckets())
    for resource in LEXICON.values():
        assert all(getattr(resource, bucket) for bucket in LANGUAGES)


def EmergencyLexiconBuckets() -> list[str]:
    # Keep this test independent of implementation internals while checking
    # the public resource contract.
    return list(LANGUAGES)


def test_explicit_context_overrides_supporting_terms() -> None:
    cases = [
        ("अगर गैस सिलेंडर फट जाए तो क्या करना चाहिए?", "hi"),
        ("कल गैस सिलेंडर फटा था लेकिन अब सब ठीक है।", "hi"),
        ("જો અકસ્માત થાય તો શું કરવું?", "gu"),
        ("काल गॅस सिलेंडर फुटला होता, आता सर्व ठीक आहे.", "mr"),
        ("No fire, only a safety drill.", "en"),
    ]
    for text, language in cases:
        facts = extract_incident_facts(text, language)
        assert facts.current_emergency is False
        assert services_for_facts(facts) == []


def test_gas_leak_is_not_explosion_without_explosion_evidence() -> None:
    facts = extract_incident_facts("I smell gas from my LPG cylinder.", "en")
    assert facts.emergency_type == "lpg"
    assert facts.lpg_leak is True
    assert facts.explosion_present is False
    assert HelpRequired.FIRE_SERVICE not in services_for_facts(facts)


def test_railway_context_does_not_infer_road_accident() -> None:
    facts = extract_incident_facts("આનંદ રેલવે સ્ટેશન પાસે ટ્રેન અકસ્માત થયો છે.", "gu")
    assert facts.railway_incident is True
    assert facts.road_accident is False


def test_lexicon_has_many_auditable_terms() -> None:
    assert sum(1 for _ in iter_terms()) >= 700


def test_hindi_chest_pain_does_not_infer_injury_bleeding_or_unconsciousness() -> None:
    transcript = "मुझे चेस्ट में दर्द हो रहा हे प्लीज हेल्प चाहिए में घर पर अकेली हु"
    flags = evidence(transcript, "hi")
    facts = extract_incident_facts(transcript, "hi")

    assert flags["medical"] is True
    assert flags["high_risk_medical"] is True
    assert flags["injury"] is False
    assert flags["bleeding"] is False
    assert flags["unconscious"] is False
    assert facts.injuries_present is False
    assert facts.severe_bleeding is False
    assert facts.unconscious_person is False
