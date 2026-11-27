// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Marathi (`mr`).
class AppLocalizationsMr extends AppLocalizations {
  AppLocalizationsMr([String locale = 'mr']) : super(locale);

  @override
  String get appTitle => 'EmergencyIQ';

  @override
  String get bannerTagline => 'EmergencyIQ सुरक्षा केंद्र';

  @override
  String get bannerLine1 => 'सर्व आपत्कालीन गरजांसाठी एक अॅप';

  @override
  String get bannerLine2 => 'कधीही मदतीची विनंती करा';

  @override
  String get bannerLine3 => 'थेट स्थिती अद्यतने';

  @override
  String get bannerLine4 => 'जलद मदतीसाठी लोकेशन शेअर करा';

  @override
  String get shortcutProfile => 'प्रोफाइल';

  @override
  String get shortcutSosHistory => 'SOS इतिहास';

  @override
  String get shortcutNotification => 'सूचना';

  @override
  String get shortcutAboutUs => 'आमच्याबद्दल';

  @override
  String get shortcutDial112 => '112 डायल करा';

  @override
  String get shortcutChatUs => 'चॅट करा';

  @override
  String get shortcutTrackMe => 'TrackMe';

  @override
  String get shortcutEmergencySos => 'आपत्कालीन';

  @override
  String get sectionContactEmergencyServices => 'आपत्कालीन सेवांशी संपर्क साधा';

  @override
  String get servicePolice => 'पोलीस';

  @override
  String get serviceFire => 'अग्निशमन';

  @override
  String get serviceMedical => 'वैद्यकीय';

  @override
  String get serviceDisaster => 'आपत्ती';

  @override
  String get serviceWomen => 'महिला';

  @override
  String get serviceChild => 'बाल मदत';

  @override
  String get serviceElderly => 'ज्येष्ठ नागरिक';

  @override
  String get serviceRailway => 'रेल्वे';

  @override
  String get locationOffTapToEnable =>
      'लोकेशन बंद आहे - सुरू करण्यासाठी टॅप करा';

  @override
  String get locationResolving => 'पत्ता शोधत आहे...';

  @override
  String get locationUnavailable => 'लोकेशन उपलब्ध नाही';

  @override
  String get integratedHelplineTitle => 'एकात्मिक हेल्पलाइन';

  @override
  String get integratedHelplineClose => 'बंद करा';

  @override
  String get helplineDescPolice =>
      'पोलीस SOS पोलीस सेवांमध्ये त्वरित मदत पुरवते.';

  @override
  String get helplineDescFire => 'फायर SOS आग आणि बचावासाठी त्वरित मदत पुरवते.';

  @override
  String get helplineDescMedical =>
      'वैद्यकीय SOS तुम्हाला रुग्णवाहिका आणि वैद्यकीय मदतीशी जोडते.';

  @override
  String get helplineDescDisaster =>
      'आपत्ती SOS नैसर्गिक आपत्तींसाठी बचाव पथकांना सतर्क करते.';

  @override
  String get helplineDescWomen =>
      'महिला SOS समर्पित सुरक्षा आणि हेल्पलाइन मदत पुरवते.';

  @override
  String get helplineDescChild => 'बाल SOS बाल संरक्षण आणि बचावाशी जोडते.';

  @override
  String get helplineDescElderly =>
      'ज्येष्ठ नागरिक SOS ज्येष्ठांसाठी समर्पित मदत पुरवते.';

  @override
  String get helplineDescRailway =>
      'रेल्वे SOS रेल्वे सुरक्षा आणि मदतीशी जोडते.';

  @override
  String get helplineDescEmergency =>
      'कोणत्याही तातडीच्या परिस्थितीसाठी आपत्कालीन SOS.';

  @override
  String sendServiceSosTitle(String service) {
    return '$service SOS पाठवा';
  }

  @override
  String get holdToSendSos => 'SOS पाठवण्यासाठी 2 सेकंद धरून ठेवा';

  @override
  String callNumberBtn(String number) {
    return '$number वर कॉल करा';
  }

  @override
  String get cancelBtn => 'रद्द करा';

  @override
  String sendingInSeconds(int seconds) {
    return '$seconds सेकंदात पाठवत आहे... रद्द करण्यासाठी टॅप करा';
  }

  @override
  String get sosSentConfirmed => 'सर्व्हरला SOS प्राप्त झाला';

  @override
  String get sosQueuedOffline => 'ऑफलाइन रांगेत — आपोआप पुन्हा प्रयत्न होईल';

  @override
  String get dial112Title => '112 वर कॉल करायचा?';

  @override
  String get dial112Message =>
      'हे 112 वर कॉल करण्यासाठी तुमचा फोन डायलर उघडेल. EmergencyIQ आपोआप कॉल करत नाही.';

  @override
  String get dialNowBtn => 'डायलर उघडा';

  @override
  String get drawerHome => 'होम';

  @override
  String get drawerProfile => 'प्रोफाइल';

  @override
  String get drawerEContact => 'आपत्कालीन संपर्क';

  @override
  String get drawerSosHistory => 'SOS इतिहास';

  @override
  String get drawerSettings => 'सेटिंग्ज';

  @override
  String get drawerAppInfo => 'अॅप माहिती';

  @override
  String get drawerTopQuestions => 'महत्त्वाचे प्रश्न';

  @override
  String get drawerLogout => 'लॉग आउट';

  @override
  String versionLabel(String version) {
    return 'आवृत्ती $version';
  }

  @override
  String get logoutConfirmTitle => 'लॉग आउट';

  @override
  String get logoutConfirmMessage =>
      'तुम्हाला खात्रीने लॉग आउट करायचे आहे का? स्थानिक ऑफलाइन SOS रांगही साफ करायची का?';

  @override
  String get logoutKeepQueue => 'लॉग आउट (रांग ठेवा)';

  @override
  String get logoutClearQueue => 'लॉग आउट आणि रांग साफ करा';

  @override
  String get eContactTitle => 'आपत्कालीन संपर्क';

  @override
  String get eContactEmpty =>
      'अद्याप कोणताही आपत्कालीन संपर्क जोडलेला नाही (कमाल 5).';

  @override
  String get eContactAddBtn => 'संपर्क जोडा';

  @override
  String get eContactLimitReached => 'कमाल 5 आपत्कालीन संपर्कांना परवानगी आहे.';

  @override
  String get eContactSuggestionTitle => 'प्रोफाइलमधून त्वरित जोडा';

  @override
  String get eContactAddSuggested => 'आपत्कालीन संपर्क म्हणून जोडा';

  @override
  String get sosHistoryTitle => 'SOS इतिहास';

  @override
  String get sosHistoryEmpty => 'अद्याप कोणताही SOS अलर्ट पाठवलेला नाही.';

  @override
  String get notificationsTitle => 'सूचना';

  @override
  String get notificationsEmpty => 'अद्याप कोणत्याही सूचना नाहीत.';

  @override
  String get markAllRead => 'सर्व वाचलेले म्हणून चिन्हांकित करा';

  @override
  String get trackMeTitle => 'TrackMe थेट शेअरिंग';

  @override
  String get trackMeStart => 'TrackMe सुरू करा';

  @override
  String get trackMeStop => 'सत्र थांबवा';

  @override
  String get trackMeShareLink => 'लिंक शेअर करा';

  @override
  String get settingsTitle => 'सेटिंग्ज';

  @override
  String get appInfoTitle => 'अॅप माहिती';

  @override
  String get appInfoDisclaimer =>
      'यशस्वी पाठवण्याचा अर्थ असा आहे की आमच्या सर्व्हरला तो मिळाला आहे. ही अधिकृत आपत्कालीन सेवा पाठवल्याची पुष्टी नाही.';

  @override
  String get topQuestionsTitle => 'महत्त्वाचे प्रश्न';

  @override
  String get aboutUsTitle => 'आमच्याबद्दल';
}
