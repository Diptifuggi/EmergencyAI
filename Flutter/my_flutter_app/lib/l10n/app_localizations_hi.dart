// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Hindi (`hi`).
class AppLocalizationsHi extends AppLocalizations {
  AppLocalizationsHi([String locale = 'hi']) : super(locale);

  @override
  String get appTitle => 'EmergencyIQ';

  @override
  String get bannerTagline => 'EmergencyIQ सुरक्षा केंद्र';

  @override
  String get bannerLine1 => 'सभी आपातकालीन जरूरतों के लिए एक ऐप';

  @override
  String get bannerLine2 => 'कभी भी मदद का अनुरोध करें';

  @override
  String get bannerLine3 => 'लाइव स्थिति अपडेट';

  @override
  String get bannerLine4 => 'तेज़ मदद के लिए लोकेशन साझा करें';

  @override
  String get shortcutProfile => 'प्रोफ़ाइल';

  @override
  String get shortcutSosHistory => 'SOS इतिहास';

  @override
  String get shortcutNotification => 'सूचनाएं';

  @override
  String get shortcutAboutUs => 'हमारे बारे में';

  @override
  String get shortcutDial112 => '112 डायल करें';

  @override
  String get shortcutChatUs => 'चैट करें';

  @override
  String get shortcutTrackMe => 'TrackMe';

  @override
  String get shortcutEmergencySos => 'आपातकाल';

  @override
  String get sectionContactEmergencyServices =>
      'आपातकालीन सेवाओं से संपर्क करें';

  @override
  String get servicePolice => 'पुलिस';

  @override
  String get serviceFire => 'अग्निशमन';

  @override
  String get serviceMedical => 'चिकित्सा';

  @override
  String get serviceDisaster => 'आपदा';

  @override
  String get serviceWomen => 'महिला';

  @override
  String get serviceChild => 'बाल सहायता';

  @override
  String get serviceElderly => 'वरिष्ठ नागरिक';

  @override
  String get serviceRailway => 'रेलवे';

  @override
  String get locationOffTapToEnable =>
      'लोकेशन बंद है - चालू करने के लिए टैप करें';

  @override
  String get locationResolving => 'पता खोजा जा रहा है...';

  @override
  String get locationUnavailable => 'लोकेशन उपलब्ध नहीं है';

  @override
  String get integratedHelplineTitle => 'एकीकृत हेल्पलाइन';

  @override
  String get integratedHelplineClose => 'बंद करें';

  @override
  String get helplineDescPolice =>
      'पुलिस SOS पुलिस सेवाओं में त्वरित मदद प्रदान करता है।';

  @override
  String get helplineDescFire =>
      'फायर SOS आग और बचाव के लिए त्वरित मदद प्रदान करता है।';

  @override
  String get helplineDescMedical =>
      'मेडिकल SOS आपको एम्बुलेंस और चिकित्सा सहायता से जोड़ता है।';

  @override
  String get helplineDescDisaster =>
      'आपदा SOS प्राकृतिक आपदाओं के लिए टीमों को सचेत करता है।';

  @override
  String get helplineDescWomen =>
      'महिला SOS समर्पित सुरक्षा और हेल्पलाइन सहायता प्रदान करता है।';

  @override
  String get helplineDescChild =>
      'चाइल्ड SOS बाल सुरक्षा और बचाव से जोड़ता है।';

  @override
  String get helplineDescElderly =>
      'वरिष्ठ नागरिक SOS बुजुर्गों के लिए सहायता प्रदान करता है।';

  @override
  String get helplineDescRailway =>
      'रेलवे SOS रेलवे सुरक्षा और सहायता से जोड़ता है।';

  @override
  String get helplineDescEmergency =>
      'किसी भी तत्काल स्थिति के लिए आपातकालीन SOS।';

  @override
  String sendServiceSosTitle(String service) {
    return '$service SOS भेजें';
  }

  @override
  String get holdToSendSos => 'SOS भेजने के लिए 2 सेकंड दबाए रखें';

  @override
  String callNumberBtn(String number) {
    return '$number पर कॉल करें';
  }

  @override
  String get cancelBtn => 'रद्द करें';

  @override
  String sendingInSeconds(int seconds) {
    return '$seconds सेकंड में भेजा जा रहा है... रद्द करने के लिए टैप करें';
  }

  @override
  String get sosSentConfirmed => 'सर्वर द्वारा SOS प्राप्त हुआ';

  @override
  String get sosQueuedOffline => 'ऑफ़लाइन कतार में — स्वतः पुनः प्रयास होगा';

  @override
  String get dial112Title => '112 पर कॉल करें?';

  @override
  String get dial112Message =>
      'यह 112 पर कॉल करने के लिए आपका फ़ोन डायलर खोलेगा। EmergencyIQ स्वतः कॉल नहीं करता है।';

  @override
  String get dialNowBtn => 'डायलर खोलें';

  @override
  String get drawerHome => 'होम';

  @override
  String get drawerProfile => 'प्रोफ़ाइल';

  @override
  String get drawerEContact => 'आपातकालीन संपर्क';

  @override
  String get drawerSosHistory => 'SOS इतिहास';

  @override
  String get drawerSettings => 'सेटिंग्स';

  @override
  String get drawerAppInfo => 'ऐप जानकारी';

  @override
  String get drawerTopQuestions => 'प्रमुख प्रश्न';

  @override
  String get drawerLogout => 'लॉग आउट';

  @override
  String versionLabel(String version) {
    return 'संस्करण $version';
  }

  @override
  String get logoutConfirmTitle => 'लॉग आउट';

  @override
  String get logoutConfirmMessage =>
      'क्या आप लॉग आउट करना चाहते हैं? स्थानीय ऑफ़लाइन SOS कतार भी साफ़ करें?';

  @override
  String get logoutKeepQueue => 'लॉग आउट (कतार रखें)';

  @override
  String get logoutClearQueue => 'लॉग आउट और कतार साफ़ करें';

  @override
  String get eContactTitle => 'आपातकालीन संपर्क';

  @override
  String get eContactEmpty =>
      'अभी तक कोई आपातकालीन संपर्क नहीं जोड़ा गया (अधिकतम 5)।';

  @override
  String get eContactAddBtn => 'संपर्क जोड़ें';

  @override
  String get eContactLimitReached => 'अधिकतम 5 आपातकालीन संपर्क अनुमत हैं।';

  @override
  String get eContactSuggestionTitle => 'प्रोफ़ाइल से त्वरित जोड़ें';

  @override
  String get eContactAddSuggested => 'आपातकालीन संपर्क के रूप में जोड़ें';

  @override
  String get sosHistoryTitle => 'SOS इतिहास';

  @override
  String get sosHistoryEmpty => 'अभी तक कोई SOS अलर्ट नहीं भेजा गया है।';

  @override
  String get notificationsTitle => 'सूचनाएं';

  @override
  String get notificationsEmpty => 'अभी तक कोई सूचना नहीं है।';

  @override
  String get markAllRead => 'सभी को पढ़ा हुआ मानें';

  @override
  String get trackMeTitle => 'TrackMe लाइव शेयरिंग';

  @override
  String get trackMeStart => 'TrackMe शुरू करें';

  @override
  String get trackMeStop => 'सत्र रोकें';

  @override
  String get trackMeShareLink => 'लिंक साझा करें';

  @override
  String get settingsTitle => 'सेटिंग्स';

  @override
  String get appInfoTitle => 'ऐप जानकारी';

  @override
  String get appInfoDisclaimer =>
      'सफल प्रेषण का अर्थ है कि हमारे सर्वर को यह प्राप्त हुआ। यह आधिकारिक आपातकालीन सेवा भेजे जाने की पुष्टि नहीं है।';

  @override
  String get topQuestionsTitle => 'प्रमुख प्रश्न';

  @override
  String get aboutUsTitle => 'हमारे बारे में';
}
