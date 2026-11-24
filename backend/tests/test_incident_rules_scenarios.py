from __future__ import annotations

import csv
import io
import logging
from pathlib import Path
from dataclasses import dataclass

import pytest

from app.schemas.emergency_analysis import EmergencyType, HelpRequired
from app.services.emergency_analysis_service import (
    EmergencyAnalysisService,
    _dispatch_reason,
)
from app.services.incident_rules import extract_incident_facts, services_for_facts
from app.services.scoring_policy import calculate_priority_score_raw


@dataclass(frozen=True)
class Scenario:
    id: str
    text_en: str
    text_hinglish: str
    expected_type: str
    sub_type: str
    help_must_have: str
    must_not_have: str
    victim_count: int | None
    victim_source: str
    min_level: str
    notes: str


_CATALOG_TEXT = """id|text_en|text_hinglish|expected_type|sub_type|help_must_have|must_not_have|victim_count|victim_source|min_level|notes
1|My father has severe chest pain and is sweating|Papa ko chest pain ho raha hai, bahut paseena aa raha hai|medical|heart_attack|ambulance+medical_assistance|-|1|any|C|
2|He collapsed and is not breathing, please come fast|Wo gir gaya hai aur saans nahi le raha, jaldi aao|medical|cardiac_arrest|ambulance+medical_assistance|-|1|any|C|
3|Her face is drooping, speech is slurred and one arm is weak|Uska chehra tedha ho gaya hai, bol nahi pa rahi, ek haath kaam nahi kar raha|medical|stroke|ambulance|-|1|any|C|
4|She is having a seizure, her body is shaking|Usko daura pad raha hai, mirgi jaisa|medical|seizure|ambulance|-|1|any|H|
5|My child is choking on food and cannot breathe|Bachcha khana khate hue ghut gaya, saans nahi le pa raha|medical|choking|ambulance|-|1|any|C|child involved
6|A pregnant woman is in labour pain and bleeding|Pregnant aurat ko labour pain hai aur khoon beh raha hai|medical|pregnancy_emergency|ambulance|-|1|any|H|
7|He drank phenyl and is vomiting|Usne phenyl pi liya hai aur ulti kar raha hai|medical|poisoning|ambulance|-|1|any|C|
8|A snake bit my brother on the leg|Bhai ko saanp ne paer mein kaat liya|medical|snake_bite|ambulance|-|1|any|H|
9|A stray dog bit a boy and he is bleeding|Kutte ne ladke ko kaat liya, khoon beh raha hai|medical|animal_attack|ambulance|-|1|any|M|
10|He got an electric shock and is not moving|Usko current laga hai aur hil nahi raha|medical|electrical_emergency|ambulance|-|1|any|C|
11|A boy is drowning in the river|Ek ladka nadi mein doob raha hai|medical|drowning|ambulance+rescue+fire_service|-|1|any|C|
12|He fell from the third floor and cannot move|Wo teesri manzil se gir gaya, hil nahi pa raha|medical|trauma|ambulance|-|1|any|H|
13|My grandmother fell in the bathroom and cannot get up|Dadi bathroom mein gir gayi hain, uth nahi pa rahi|medical|fall|ambulance|-|1|any|H|elderly_involved true
14|She got burned by boiling oil|Garam tel se jal gayi hai|medical|burn|ambulance|-|1|any|H|
15|He has an asthma attack and difficulty breathing|Usko asthma attack aaya hai, saans lene mein dikkat hai|medical|asthma|ambulance|-|1|any|C|
16|I have fever and vomiting since morning|Subah se bukhar aur ulti ho rahi hai|medical|minor_illness|medical_assistance|ambulance|1|default|M|no ambulance for minor illness
17|He is threatening to jump from the roof|Wo chhat se kudne ki dhamki de raha hai|medical|self_harm_crisis|police+ambulance|-|1|any|C|never echo any method or means in output
18|A person was hit by a car and is unconscious|Ek aadmi ko gaadi ne takkar maari, wo behosh hai|accident|road_accident!|police+ambulance+medical_assistance|-|1|any|C|the original failing case
19|A bike skidded and the rider is bleeding|Bike slip ho gayi, rider ko khoon beh raha hai|accident|road_accident|police+ambulance|-|1|any|H|
20|Two cars collided, nobody is injured|Do gaadiyan takra gayi, kisi ko chot nahi aayi|accident|road_accident!|police|ambulance+rescue|0|explicit|L|explicit no-injury gives 0
21|A bus overturned and around 30 people are injured|Bus palat gayi, lagbhag 30 log ghayal hain|accident|road_accident|police+ambulance|-|30|explicit|C|approximate true
22|A car hit a man and ran away|Gaadi ek aadmi ko takkar maar ke bhaag gayi|accident|hit_and_run!|police+ambulance|-|1|any|H|
23|A truck driver is trapped in the cabin on the highway|Highway par truck ka driver cabin mein fansa hai|accident|road_accident|police+rescue+fire_service+ambulance|-|1|any|C|numbers include 1033
24|A car caught fire after the crash|Takkar ke baad car mein aag lag gayi|accident or fire|-|police+fire_service|-|1|default|C|
25|A car fell into the canal with a family inside|Car nahar mein gir gayi, andar parivar hai|accident or disaster|-|rescue+fire_service+ambulance+police|-|2|plural_estimate|C|
26|A person was hit by a train at the railway station|Railway station par ek aadmi train se kat gaya|accident|railway_accident!|police+ambulance|-|1|any|C|numbers include 139
27|A train derailed and many people are injured|Train patri se utar gayi, bahut log ghayal hain|accident|railway_accident!|police+ambulance+rescue|-|5|plural_estimate|C|numbers include 139
28|A drunk driver is driving dangerously but there is no crash|Sharabi driver khatarnak tarike se gaadi chala raha hai, accident nahi hua|police|reckless_driving|police|ambulance|1|default|M|
29|The house is on fire and the family is trapped inside|Ghar mein aag lagi hai aur parivar andar fansa hai|fire|-|fire_service+rescue+ambulance|-|2|plural_estimate|C|
30|Factory fire, workers are stuck inside|Factory mein aag lagi hai, mazdoor andar fanse hain|fire|industrial_fire|fire_service+rescue+ambulance|-|2|plural_estimate|C|
31|Cylinder blast in the kitchen, two people are injured|Kitchen mein cylinder phat gaya, do log ghayal hain|lpg|lpg_gas_explosion|fire_service+ambulance+rescue+lpg|-|2|explicit|C|
32|There is a smell of gas in the kitchen, no fire|Kitchen mein gas ki smell aa rahi hai, aag nahi hai|lpg|gas_leak|lpg|ambulance+fire_service|1|default|H|priority >= 51
33|Sparks and fire from the electric transformer|Transformer se chingari aur aag nikal rahi hai|fire|electrical_fire|fire_service|ambulance|1|default|H|
34|Smoke is coming from my neighbour's flat|Padosi ke flat se dhuan nikal raha hai|fire|suspected_fire|fire_service|ambulance|1|default|H|
35|A grass fire is spreading near the village|Gaon ke paas ghaas mein aag fail rahi hai|fire|wildfire|fire_service|-|1|default|H|
36|A firecracker burst and his hand is injured|Patakha phat gaya, uska haath ghayal ho gaya|fire or medical|-|fire_service+ambulance|-|1|any|H|
37|The building collapsed and people are under the debris|Building gir gayi, log malbe ke neeche hain|disaster|structural_collapse|rescue+fire_service+ambulance|-|2|plural_estimate|C|
38|A child fell into a borewell|Bachcha borewell mein gir gaya|disaster|borewell_rescue|rescue+fire_service+ambulance|-|1|any|C|
39|Flood water is entering the house and old people are inside|Ghar mein baadh ka paani aa raha hai, bujurg andar hain|disaster|flood|rescue|-|2|plural_estimate|H|elderly_involved true
40|A cloudburst and landslide hit the village, houses are damaged|Gaon mein badal phata aur landslide hua, ghar toot gaye|disaster|natural_disaster|multiple_services|-|1|default|H|
41|Stampede at the temple, many people are hurt|Mandir mein bhagdad mach gayi, bahut log ghayal hain|disaster|crowd_emergency|police+ambulance+rescue|-|5|plural_estimate|C|
42|I am stuck in the lift and feel dizzy|Main lift mein fans gaya hoon, chakkar aa raha hai|disaster|rescue|rescue|-|1|default|M|
43|Lightning struck farmers in the field, they are unconscious|Khet mein bijli giri, kisaan behosh hain|medical or disaster|-|ambulance|-|2|plural_estimate|C|
44|Someone just snatched my gold chain|Abhi kisi ne meri sone ki chain cheen li|robbery|chain_snatching|police|ambulance|1|default|M|
45|Someone is breaking into my house right now|Mere ghar mein koi ghus raha hai abhi|crime_police|burglary_home_intrusion!|police|ambulance|1|default|H|
46|A man with a gun is firing shots|Ek aadmi bandook se goliyan chala raha hai|assault|shooting|police+ambulance|-|1|any|C|
47|Someone kidnapped my child|Kisi ne mere bachche ko kidnap kar liya|child_safety|kidnapping|police+child_protection|-|1|any|C|
48|A man is following me at night and I am scared|Raat ko ek aadmi mera peecha kar raha hai, mujhe darr lag raha hai|women_safety|stalking|police+women_safety_support|-|1|default|H|
49|There is a bomb threat at the railway station, police please come|Railway station par bomb ki dhamki hai, police bhejo|police|security_threat|police|-|1|default|H|
50|A mob is fighting and throwing stones on the road|Sadak par bheed ladai kar rahi hai aur patthar phenk rahi hai|police|riot|police|-|5|plural_estimate|H|
51|My husband is beating me|Mera pati mujhe maar raha hai|domestic_violence|-|police+women_safety_support|-|1|default|H|
52|A woman is being sexually assaulted in the lane|Gali mein ek aurat ke saath balatkar ho raha hai|women_safety|sexual_assault|police+women_safety_support+ambulance|-|1|default|C|
53|Acid was thrown on her face|Uske chehre par tezaab phenk diya|assault|acid_attack|police+ambulance|-|1|default|C|
54|Boys are teasing girls outside the college|College ke bahar ladke ladkiyon ko chhed rahe hain|harassment|-|police+women_safety_support|ambulance|2|plural_estimate|M|
55|A child is being beaten at home|Ghar mein bachche ko maara ja raha hai|child_safety|child_abuse|police+child_protection|-|1|default|H|
56|My child is lost in the market|Mera bachcha bazaar mein kho gaya hai|child_safety|missing_child!|police+child_protection|-|1|default|H|
57|My grandfather has dementia and went missing|Dada ji ko bhoolne ki bimari hai aur wo gum ho gaye|police|missing_person|police|ambulance|1|default|M|
58|Money was just debited from my account through an OTP fraud|OTP fraud se abhi mere account se paisa kat gaya|cybercrime|online_fraud|cybercrime+police|ambulance|1|default|M|numbers include 1930
59|Someone is blackmailing me with my morphed photos|Koi meri morphed photos se blackmail kar raha hai|cybercrime|sextortion|cybercrime+police|ambulance|1|default|H|numbers include 1930
60|...||unknown|-|unknown|-|None|none|L|priority 0, flag human verification, no crash
61|This is a test call, please ignore|Yeh test call hai, ignore karo|unknown or other|-|-|all services|None|none|L|
62|What is the fire brigade number|Fire brigade ka number kya hai|unknown or other|-|-|fire_service|None|none|L|information request, not a fire
63|What should I do if there is a fire|Agar aag lag jaye to kya karna chahiye|unknown|-|-|all services|None|none|L|context_state hypothetical, priority 0
64|My phone was stolen yesterday|Mera phone kal chori ho gaya tha|police or unknown|-|-|ambulance|None|none|L|context_state historical, priority 0
65|The fire is out and everyone is safe|Aag bujh gayi hai aur sab surakshit hain|any|-|-|all services|None|none|L|context_state resolved, priority 0
66|I think someone fell down|Mujhe lagta hai koi gir gaya|any|-|-|all services|None|none|L|context_state uncertain, priority 0
67|The car crashed and caught fire, the driver is unconscious|Car takra gayi aur aag lag gayi, driver behosh hai|accident or fire|-|police+fire_service+ambulance|-|1|any|C|one record, union of services
68|Brother, there has been an accident, one man is unconscious and bleeding|Bhai accident ho gaya, ek aadmi behosh hai, khoon beh raha hai|accident|road_accident|police+ambulance|-|1|any|C|
69a|Nobody is injured, only smoke|Koi ghayal nahi hai, sirf dhuan hai|fire|suspected_fire|fire_service|ambulance|0|explicit|H|
69b|He cannot move, he is unconscious|Wo hil nahi sakta, behosh hai|medical|-|ambulance|-|1|any|C|
69c|He is unconscious and not breathing|Wo behosh hai aur saans nahi le raha|medical|cardiac_arrest|ambulance|-|1|any|C|
70|There is a fire in the college canteen|College canteen mein aag lagi hai|fire|-|fire_service|-|1|default|C|context_state current; Hindi variant checks कालेज bug
"""

SCENARIOS = tuple(
    Scenario(
        id=row[0],
        text_en=row[1],
        text_hinglish=row[2],
        expected_type=row[3],
        sub_type=row[4],
        help_must_have=row[5],
        must_not_have=row[6],
        victim_count=None if row[7] == "None" else int(row[7]),
        victim_source=row[8],
        min_level=row[9],
        notes=row[10],
    )
    for row in csv.reader(io.StringIO(_CATALOG_TEXT), delimiter="|")
    if row and row[0] != "id"
)

# Generated translations need native review. The supplied human-written anchors
# for rows 1, 18, and 29 are used verbatim.
_TRANSLATIONS = {
    "1": {
        "hi": "मेरे पिता के सीने में तेज दर्द है और पसीना आ रहा है",
        "gu": "મારા પિતાને છાતીમાં સખત દુખાવો થાય છે અને પરસેવો આવે છે",
        "mr": "माझ्या वडिलांच्या छातीत तीव्र दुखत आहे आणि घाम येत आहे",
    },
    "2": {
        "hi": "वह गिर गया है और सांस नहीं ले रहा, कृपया जल्दी आइए",
        "gu": "તે પડી ગયો છે અને શ્વાસ લઈ રહ્યો નથી, કૃપા કરીને જલ્દી આવો",
        "mr": "तो पडला आहे आणि श्वास घेत नाही, कृपया लवकर या",
    },
    "3": {
        "hi": "उसका चेहरा लटक रहा है, बोली अस्पष्ट है और एक हाथ कमजोर है",
        "gu": "તેનો ચહેરો ઢળી ગયો છે, બોલી અસ્પષ્ટ છે અને એક હાથ નબળો છે",
        "mr": "तिचा चेहरा वाकडा झाला आहे, बोलणे अस्पष्ट आहे आणि एक हात कमजोर आहे",
    },
    "4": {
        "hi": "उसे दौरा पड़ रहा है और उसका शरीर कांप रहा है",
        "gu": "તેને આંચકી આવી રહી છે અને તેનું શરીર ધ્રૂજી રહ્યું છે",
        "mr": "तिला झटका येत आहे आणि तिचे शरीर थरथरत आहे",
    },
    "5": {
        "hi": "मेरा बच्चा खाना खाते समय घुट रहा है और सांस नहीं ले पा रहा",
        "gu": "મારું બાળક જમતી વખતે ગૂંગળાઈ ગયું છે અને શ્વાસ લઈ શકતું નથી",
        "mr": "माझे मूल खाताना गुदमरले आहे आणि श्वास घेऊ शकत नाही",
    },
    "6": {
        "hi": "एक गर्भवती महिला को प्रसव पीड़ा है और खून बह रहा है",
        "gu": "એક ગર્ભવતી મહિલાને પ્રસવ પીડા છે અને લોહી વહી રહ્યું છે",
        "mr": "एका गर्भवती महिलेला प्रसूती वेदना होत आहेत आणि रक्तस्राव होत आहे",
    },
    "7": {
        "hi": "उसने फिनाइल पी लिया है और उसे उल्टी हो रही है",
        "gu": "તેણે ફિનાઇલ પી લીધું છે અને તેને ઊલટી થઈ રહી છે",
        "mr": "त्याने फिनाइल प्यायले आहे आणि त्याला उलटी होत आहे",
    },
    "8": {
        "hi": "मेरे भाई को पैर पर सांप ने काट लिया",
        "gu": "મારા ભાઈને પગમાં સાપે ડંખ માર્યો",
        "mr": "माझ्या भावाला पायावर सापाने चावा घेतला",
    },
    "9": {
        "hi": "एक आवारा कुत्ते ने लड़के को काटा है और उसे खून बह रहा है",
        "gu": "એક રખડતા કૂતરાએ છોકરાને કરડ્યો છે અને તેને લોહી વહી રહ્યું છે",
        "mr": "एका भटक्या कुत्र्याने मुलाला चावा घेतला आणि त्याला रक्त येत आहे",
    },
    "10": {
        "hi": "उसे बिजली का झटका लगा है और वह हिल नहीं रहा",
        "gu": "તેને વીજળીનો ઝટકો લાગ્યો છે અને તે હલતો નથી",
        "mr": "त्याला विजेचा धक्का बसला आहे आणि तो हालचाल करत नाही",
    },
    "11": {
        "hi": "एक लड़का नदी में डूब रहा है",
        "gu": "એક છોકરો નદીમાં ડૂબી રહ્યો છે",
        "mr": "एक मुलगा नदीत बुडत आहे",
    },
    "12": {
        "hi": "वह तीसरी मंजिल से गिरा और हिल नहीं पा रहा",
        "gu": "તે ત્રીજા માળેથી પડ્યો અને હલી શકતો નથી",
        "mr": "तो तिसऱ्या मजल्यावरून पडला आणि हालचाल करू शकत नाही",
    },
    "13": {
        "hi": "मेरी दादी बाथरूम में गिर गई हैं और उठ नहीं पा रही हैं",
        "gu": "મારા દાદી બાથરૂમમાં પડી ગયા છે અને ઊભા થઈ શકતા નથી",
        "mr": "माझी आजी बाथरूममध्ये पडली आहे आणि उठू शकत नाही",
    },
    "14": {
        "hi": "वह उबलते तेल से जल गई है",
        "gu": "તે ઉકળતા તેલથી દાઝી ગઈ છે",
        "mr": "ती उकळत्या तेलाने भाजली आहे",
    },
    "15": {
        "hi": "उसे अस्थमा का दौरा पड़ा है और सांस लेने में तकलीफ हो रही है",
        "gu": "તેને અસ્થમાનો હુમલો આવ્યો છે અને શ્વાસ લેવામાં તકલીફ થઈ રહી છે",
        "mr": "त्याला दम्याचा झटका आला आहे आणि श्वास घेण्यास त्रास होत आहे",
    },
    "16": {
        "hi": "मुझे सुबह से बुखार और उल्टी हो रही है",
        "gu": "મને સવારથી તાવ અને ઊલટી થઈ રહી છે",
        "mr": "मला सकाळपासून ताप आणि उलटी होत आहे",
    },
    "17": {
        "hi": "वह छत से कूदने की धमकी दे रहा है",
        "gu": "તે છત પરથી કૂદવાની ધમકી આપી રહ્યો છે",
        "mr": "तो छतावरून उडी मारण्याची धमकी देत आहे",
    },
    "18": {
        "hi": "एक आदमी को कार ने टक्कर मार दी है और वह बेहोश है",
        "gu": "એક માણસને કારે ટક્કર મારી છે અને તે બેભાન છે",
        "mr": "एका माणसाला कारने धडक दिली आहे आणि तो बेशुद्ध आहे",
    },
    "19": {
        "hi": "बाइक फिसल गई और सवार को खून बह रहा है",
        "gu": "બાઈક લપસી ગઈ અને સવારને લોહી વહી રહ્યું છે",
        "mr": "बाईक घसरली आणि चालकाला रक्त येत आहे",
    },
    "20": {
        "hi": "दो कारें टकराईं, किसी को चोट नहीं आई",
        "gu": "બે કાર અથડાઈ, કોઈને ઈજા થઈ નથી",
        "mr": "दोन गाड्या धडकल्या, कोणालाही दुखापत झाली नाही",
    },
    "21": {
        "hi": "एक बस पलट गई और लगभग 30 लोग घायल हैं",
        "gu": "એક બસ પલટી ગઈ અને લગભગ 30 લોકો ઘાયલ છે",
        "mr": "एक बस उलटली आणि जवळपास 30 लोक जखमी झाले आहेत",
    },
    "22": {
        "hi": "एक कार ने आदमी को टक्कर मारी और भाग गई",
        "gu": "એક કારે એક માણસને ટક્કર મારી અને ભાગી ગઈ",
        "mr": "एका कारने माणसाला धडक दिली आणि ती पळून गेली",
    },
    "23": {
        "hi": "हाईवे पर ट्रक का ड्राइवर केबिन में फंसा है",
        "gu": "હાઈવે પર ટ્રકનો ડ્રાઈવર કેબિનમાં ફસાયો છે",
        "mr": "महामार्गावर ट्रकचा चालक केबिनमध्ये अडकला आहे",
    },
    "24": {
        "hi": "टक्कर के बाद कार में आग लग गई",
        "gu": "અકસ્મતા પછી કારમાં આગ લાગી",
        "mr": "धडकेनंतर कारला आग लागली",
    },
    "25": {
        "hi": "एक कार नहर में गिर गई और परिवार अंदर है",
        "gu": "એક કાર નહેરમાં પડી ગઈ અને પરિવાર અંદર છે",
        "mr": "एक कार कालव्यात पडली आणि कुटुंब आत आहे",
    },
    "29": {
        "hi": "घर में आग लगी है और परिवार अंदर फंसा है",
        "gu": "ઘરમાં આગ લાગી છે અને પરિવાર અંદર ફસાયેલો છે",
        "mr": "घराला आग लागली आहे आणि कुटुंब आत अडकले आहे",
    },
    "70": {"hi": "कालेज की कैंटीन में आग लगी है"},
}


def _scenario_inputs() -> list[tuple[Scenario, str, str, str]]:
    inputs: list[tuple[Scenario, str, str, str]] = []
    for scenario in SCENARIOS:
        inputs.append((scenario, "en", scenario.text_en, "text_en"))
        inputs.append((scenario, "en", scenario.text_hinglish, "text_hinglish"))
        if scenario.id in _TRANSLATIONS:
            inputs.extend(
                (scenario, language, text, "translation")
                for language, text in _TRANSLATIONS[scenario.id].items()
            )
    return inputs


SCENARIO_INPUTS = _scenario_inputs()
_LEVEL_FLOORS = {"C": 76, "H": 51, "M": 26, "L": 0}
_ALL_HELP_VALUES = {
    "police", "ambulance", "fire_service", "rescue", "medical_assistance",
    "women_safety_support", "child_protection", "multiple_services", "unknown",
}
_KNOWN_XFAILS: dict[str, str] = {}


def write_postman_export(path: Path) -> None:
    fields = [
        "text", "language", "expected_type", "expected_help",
        "expected_victim_count", "expected_min_level",
    ]
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for scenario, language, text, _variant in SCENARIO_INPUTS:
            writer.writerow(
                {
                    "text": text,
                    "language": language,
                    "expected_type": scenario.expected_type,
                    "expected_help": scenario.help_must_have,
                    "expected_victim_count": (
                        "None" if scenario.victim_count is None else scenario.victim_count
                    ),
                    "expected_min_level": scenario.min_level,
                }
            )


def test_postman_export_contains_every_catalog_input(tmp_path: Path) -> None:
    output = tmp_path / "scenarios.csv"
    write_postman_export(output)

    with output.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        assert reader.fieldnames == [
            "text", "language", "expected_type", "expected_help",
            "expected_victim_count", "expected_min_level",
        ]
        rows = list(reader)

    assert len(SCENARIOS) == 72
    assert len(rows) == len(SCENARIO_INPUTS) == 223


@pytest.mark.parametrize(
    ("text", "language", "victims", "approximate", "source"),
    [
        ("someone is unconscious", "en", 1, False, "default"),
        ("a man is unconscious", "en", 1, False, "explicit"),
        ("both people are injured", "en", 2, False, "explicit"),
        ("a family of four is trapped", "en", 4, False, "explicit"),
        ("people are trapped", "en", 2, True, "plural_estimate"),
        ("many people are injured", "en", 5, True, "plural_estimate"),
        ("dozens of people are injured", "en", 24, True, "plural_estimate"),
        ("nobody is injured", "en", 0, False, "explicit"),
        ("કોઈ ઘાયલ નથી", "gu", 0, False, "explicit"),
        ("पंचवीस लोक जखमी झाले आहेत", "mr", 25, False, "explicit"),
        ("what should I do if there is a fire", "en", None, False, "none"),
        ("the fire was out yesterday", "en", None, False, "none"),
    ],
)
def test_victim_count_source_and_non_live_defaults(
    text: str,
    language: str,
    victims: int | None,
    approximate: bool,
    source: str,
) -> None:
    facts = extract_incident_facts(text, language)
    assert facts.victim_count == victims
    assert facts.victim_count_approximate is approximate
    assert facts.victim_count_source == source


@pytest.mark.parametrize(
    ("text", "language", "expected_type", "expected_subtype", "expected_help"),
    [
        (
            "person hit by a car and is unconscious",
            "en",
            "accident",
            "road_accident",
            {HelpRequired.POLICE, HelpRequired.AMBULANCE, HelpRequired.MEDICAL_ASSISTANCE},
        ),
        (
            "two cars collided, nobody is injured",
            "en",
            "accident",
            "road_accident",
            {HelpRequired.POLICE},
        ),
        (
            "car caught fire after crash",
            "en",
            "accident",
            "road_accident",
            {HelpRequired.POLICE, HelpRequired.FIRE_SERVICE, HelpRequired.AMBULANCE},
        ),
        (
            "person hit by train at station",
            "en",
            "accident",
            "railway_accident",
            {HelpRequired.POLICE, HelpRequired.AMBULANCE, HelpRequired.RESCUE},
        ),
        (
            "कालेज में आग",
            "hi",
            "fire",
            "fire_or_explosion",
            {HelpRequired.FIRE_SERVICE},
        ),
    ],
)
def test_accident_and_context_scenarios(
    text: str,
    language: str,
    expected_type: str,
    expected_subtype: str,
    expected_help: set[HelpRequired],
) -> None:
    facts = extract_incident_facts(text, language)
    assert facts.emergency_type == expected_type
    assert facts.sub_type == expected_subtype
    assert facts.context_state == "current"
    assert set(services_for_facts(facts)) == expected_help


def test_negation_is_scoped_to_its_clause() -> None:
    facts = extract_incident_facts("no fire, person is unconscious")
    assert facts.current_emergency is True
    assert facts.unconscious_person is True
    assert facts.fire_present is False
    assert HelpRequired.AMBULANCE in services_for_facts(facts)

    facts = extract_incident_facts("unconscious and not breathing")
    assert facts.unconscious_person is True
    assert facts.medical_emergency is True


def test_past_tense_attack_is_classified_as_assault() -> None:
    facts = extract_incident_facts("someone attacked me")
    assert facts.emergency_type == "assault"
    assert facts.assault_in_progress is True
    assert HelpRequired.POLICE in services_for_facts(facts)


def test_default_assumed_victim_does_not_increase_priority() -> None:
    kwargs = {
        "emergency_type": EmergencyType.MEDICAL,
        "immediate_threat": False,
        "people_at_risk": 0,
        "transcript": "medical emergency",
    }
    no_count = calculate_priority_score_raw(**kwargs)
    assumed = calculate_priority_score_raw(
        **kwargs, victim_count=1, victim_count_source="default"
    )
    explicit = calculate_priority_score_raw(
        **kwargs, victim_count=1, victim_count_source="explicit"
    )
    assert assumed == no_count
    assert explicit == no_count + 10


def test_dispatch_copy_distinguishes_assumed_and_explicit_counts() -> None:
    assumed = extract_incident_facts("someone is unconscious")
    explicit = extract_incident_facts("one person is unconscious")
    assumed_reason = _dispatch_reason(assumed, EmergencyType.MEDICAL, ["ambulance"])
    explicit_reason = _dispatch_reason(explicit, EmergencyType.MEDICAL, ["ambulance"])
    assert "at least 1 person assumed (no count stated)" in assumed_reason
    assert "1 explicitly reported people" in explicit_reason


def test_postman_scenario_export_has_the_expected_columns() -> None:
    scenario_file = Path(__file__).parents[2] / "postman" / "scenarios.csv"
    with scenario_file.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        assert reader.fieldnames == [
            "text",
            "language",
            "expected_type",
            "expected_help",
            "expected_victim_count",
            "expected_min_level",
        ]
        rows = list(reader)
    assert len(SCENARIOS) == 72
    assert len(SCENARIO_INPUTS) == 223
    assert len(rows) == len(SCENARIO_INPUTS)
    assert all(row["expected_type"] for row in rows)


@pytest.mark.parametrize(
    ("scenario", "language", "text", "variant"),
    [
        pytest.param(
            scenario,
            language,
            text,
            variant,
            id=f"{scenario.id}-{language}-{variant}",
            marks=(
                (pytest.mark.xfail(
                    reason=_KNOWN_XFAILS[scenario.id],
                    strict=True,
                ),)
                if scenario.id in _KNOWN_XFAILS
                else ()
            ),
        )
        for scenario, language, text, variant in SCENARIO_INPUTS
    ],
)
def test_incident_rule_catalog(
    scenario: Scenario, language: str, text: str, variant: str
) -> None:
    analysis = EmergencyAnalysisService()._parse_and_validate(
        '{"emergency_type":"unknown"}',
        transcript=text,
        language=language,
    )

    accepted_types = {
        expected.strip()
        for expected in scenario.expected_type.split(" or ")
    }
    if "any" not in accepted_types:
        assert analysis.emergency_type.value in accepted_types

    actual_help = {item.value for item in analysis.help_required}
    expected_help = (
        set()
        if scenario.help_must_have == "-"
        else set(scenario.help_must_have.split("+"))
    )
    assert expected_help <= actual_help
    forbidden_help = (
        _ALL_HELP_VALUES
        if scenario.must_not_have == "all services"
        else set()
        if scenario.must_not_have == "-"
        else set(scenario.must_not_have.split("+"))
    )
    assert not (forbidden_help & actual_help)

    assert analysis.victim_count == scenario.victim_count
    if scenario.victim_source != "any":
        assert analysis.victim_count_source == scenario.victim_source
    assert analysis.priority_score >= _LEVEL_FLOORS[scenario.min_level]

    if scenario.sub_type.endswith("!"):
        assert analysis.sub_type == scenario.sub_type[:-1]
    elif scenario.sub_type != "-" and analysis.sub_type != scenario.sub_type:
        logging.getLogger(__name__).warning(
            "Scenario %s (%s/%s): subtype expected %s, got %s",
            scenario.id,
            language,
            variant,
            scenario.sub_type,
            analysis.sub_type,
        )

    current_ids = {str(number) for number in range(1, 60)} | {"67", "68", "70", "69a", "69b", "69c"}
    if scenario.id in current_ids:
        assert analysis.context_state == "current"
        assert analysis.victim_count is not None
        if scenario.id not in {"20", "69a"}:
            assert analysis.victim_count >= 1

    if scenario.id in {"60", "61"}:
        assert analysis.priority_score <= 25
    if scenario.id == "60":
        assert analysis.priority_score == 0
        assert analysis.human_confirmation_required is True
    if scenario.id in {"62", "63", "64", "65", "66"}:
        assert analysis.priority_score == 0
    if scenario.id == "63":
        assert analysis.context_state == "hypothetical"
    if scenario.id == "64":
        assert analysis.context_state == "historical"
    if scenario.id == "65":
        assert analysis.context_state == "resolved"
    if scenario.id == "66":
        assert analysis.context_state == "uncertain"
    if scenario.id == "21":
        assert analysis.victim_count_approximate is True
    if scenario.id in {"13", "39"}:
        assert analysis.elderly_involved is True
    if scenario.id == "5":
        assert analysis.child_involved is True
    if scenario.id == "17":
        output = " ".join(
            (
                analysis.incident_description,
                analysis.dispatch_recommendation.reason,
                analysis.dispatch_recommendation.priority_reason,
                analysis.dispatch_recommendation.dispatcher_action,
                *analysis.emergency_keywords,
            )
        ).casefold()
        assert "roof" not in output
        assert "jump" not in output
    expected_number = {"23": "1033", "26": "139", "27": "139", "58": "1930", "59": "1930"}.get(scenario.id)
    if expected_number is not None:
        assert expected_number in analysis.dispatch_recommendation.emergency_numbers
