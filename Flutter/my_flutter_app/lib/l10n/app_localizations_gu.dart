// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Gujarati (`gu`).
class AppLocalizationsGu extends AppLocalizations {
  AppLocalizationsGu([String locale = 'gu']) : super(locale);

  @override
  String get appTitle => 'EmergencyIQ';

  @override
  String get bannerTagline => 'EmergencyIQ સુરક્ષા કેન્દ્ર';

  @override
  String get bannerLine1 => 'તમામ કટોકટીની જરૂરિયાતો માટે એક એપ';

  @override
  String get bannerLine2 => 'ગમે ત્યારે મદદ માટે વિનંતી કરો';

  @override
  String get bannerLine3 => 'લાઇવ સ્થિતિ અપડેટ્સ';

  @override
  String get bannerLine4 => 'ઝડપી મદદ માટે લોકેશન શેર કરો';

  @override
  String get shortcutProfile => 'પ્રોફાઇલ';

  @override
  String get shortcutSosHistory => 'SOS ઇતિહાસ';

  @override
  String get shortcutNotification => 'સૂચનાઓ';

  @override
  String get shortcutAboutUs => 'અમારા વિશે';

  @override
  String get shortcutDial112 => '112 ડાયલ કરો';

  @override
  String get shortcutChatUs => 'ચેટ કરો';

  @override
  String get shortcutTrackMe => 'TrackMe';

  @override
  String get shortcutEmergencySos => 'કટોકટી';

  @override
  String get sectionContactEmergencyServices => 'કટોકટી સેવાઓનો સંપર્ક કરો';

  @override
  String get servicePolice => 'પોલીસ';

  @override
  String get serviceFire => 'ફાયર';

  @override
  String get serviceMedical => 'તબીબી';

  @override
  String get serviceDisaster => 'આપત્તિ';

  @override
  String get serviceWomen => 'મહિલા';

  @override
  String get serviceChild => 'બાળ સહાય';

  @override
  String get serviceElderly => 'વડીલ';

  @override
  String get serviceRailway => 'રેલ્વે';

  @override
  String get locationOffTapToEnable => 'લોકેશન બંધ છે - ચાલુ કરવા ટૅપ કરો';

  @override
  String get locationResolving => 'સરનામું શોધી રહ્યું છે...';

  @override
  String get locationUnavailable => 'લોકેશન ઉપલબ્ધ નથી';

  @override
  String get integratedHelplineTitle => 'સંકલિત હેલ્પલાઇન';

  @override
  String get integratedHelplineClose => 'બંધ કરો';

  @override
  String get helplineDescPolice =>
      'પોલીસ SOS પોલીસ સેવાઓમાં ત્વરિત મદદ પૂરી પાડે છે.';

  @override
  String get helplineDescFire =>
      'ફાયર SOS આગ અને બચાવ માટે ત્વરિત મદદ પૂરી પાડે છે.';

  @override
  String get helplineDescMedical =>
      'મેડિકલ SOS તમને એમ્બ્યુલન્સ અને તબીબી સહાય સાથે જોડે છે.';

  @override
  String get helplineDescDisaster =>
      'આપત્તિ SOS કુદરતી આપત્તિઓ માટે બચાવ ટીમોને સચેત કરે છે.';

  @override
  String get helplineDescWomen =>
      'મહિલા SOS સમર્પિત સુરક્ષા અને હેલ્પલાઇન સહાય પૂરી પાડે છે.';

  @override
  String get helplineDescChild =>
      'ચાઇલ્ડ SOS બાળ સુરક્ષા અને બચાવ સાથે જોડે છે.';

  @override
  String get helplineDescElderly =>
      'વડીલ SOS વરિષ્ઠ નાગરિકો માટે સમર્પિત સહાય પૂરી પાડે છે.';

  @override
  String get helplineDescRailway =>
      'રેલ્વે SOS રેલ્વે સુરક્ષા અને સહાય સાથે જોડે છે.';

  @override
  String get helplineDescEmergency =>
      'કોઈપણ તાત્કાલિક પરિસ્થિતિ માટે કટોકટી SOS.';

  @override
  String sendServiceSosTitle(String service) {
    return '$service SOS મોકલો';
  }

  @override
  String get holdToSendSos => 'SOS મોકલવા માટે 2 સેકન્ડ દબાવી રાખો';

  @override
  String callNumberBtn(String number) {
    return '$number પર કૉલ કરો';
  }

  @override
  String get cancelBtn => 'રદ કરો';

  @override
  String sendingInSeconds(int seconds) {
    return '$seconds સેકન્ડમાં મોકલાઈ રહ્યું છે... રદ કરવા ટૅપ કરો';
  }

  @override
  String get sosSentConfirmed => 'સર્વર દ્વારા SOS પ્રાપ્ત થયો';

  @override
  String get sosQueuedOffline => 'ઑફલાઇન કતારમાં — આપમેળે ફરી પ્રયાસ થશે';

  @override
  String get dial112Title => '112 પર કૉલ કરવો?';

  @override
  String get dial112Message =>
      'આ 112 પર કૉલ કરવા માટે તમારો ફોન ડાયલર ખોલશે. EmergencyIQ આપમેળે કૉલ કરતું નથી.';

  @override
  String get dialNowBtn => 'ડાયલર ખોલો';

  @override
  String get drawerHome => 'હોમ';

  @override
  String get drawerProfile => 'પ્રોફાઇલ';

  @override
  String get drawerEContact => 'ઇમરજન્સી સંપર્ક';

  @override
  String get drawerSosHistory => 'SOS ઇતિહાસ';

  @override
  String get drawerSettings => 'સેટિંગ્સ';

  @override
  String get drawerAppInfo => 'એપ માહિતી';

  @override
  String get drawerTopQuestions => 'મુખ્ય પ્રશ્નો';

  @override
  String get drawerLogout => 'લૉગ આઉટ';

  @override
  String versionLabel(String version) {
    return 'વર્ઝન $version';
  }

  @override
  String get logoutConfirmTitle => 'લૉગ આઉટ';

  @override
  String get logoutConfirmMessage =>
      'શું તમે ખરેખર લૉગ આઉટ કરવા માંગો છો? સ્થાનિક ઑફલાઇન SOS કતાર પણ સાફ કરવી?';

  @override
  String get logoutKeepQueue => 'લૉગ આઉટ (કતાર રાખો)';

  @override
  String get logoutClearQueue => 'લૉગ આઉટ અને કતાર સાફ કરો';

  @override
  String get eContactTitle => 'કટોકટી સંપર્કો';

  @override
  String get eContactEmpty =>
      'હજી સુધી કોઈ કટોકટી સંપર્ક ઉમેર્યો નથી (મહત્તમ 5).';

  @override
  String get eContactAddBtn => 'સંપર્ક ઉમેરો';

  @override
  String get eContactLimitReached => 'મહત્તમ 5 કટોકટી સંપર્કોની મંજૂરી છે.';

  @override
  String get eContactSuggestionTitle => 'પ્રોફાઇલમાંથી ઝડપી ઉમેરો';

  @override
  String get eContactAddSuggested => 'કટોકટી સંપર્ક તરીકે ઉમેરો';

  @override
  String get sosHistoryTitle => 'SOS ઇતિહાસ';

  @override
  String get sosHistoryEmpty => 'હજી સુધી કોઈ SOS એલર્ટ મોકલવામાં આવ્યું નથી.';

  @override
  String get notificationsTitle => 'સૂચનાઓ';

  @override
  String get notificationsEmpty => 'હજી સુધી કોઈ સૂચના નથી.';

  @override
  String get markAllRead => 'બધા વાંચેલા તરીકે ચિહ્નિત કરો';

  @override
  String get trackMeTitle => 'TrackMe લાઇવ શેરિંગ';

  @override
  String get trackMeStart => 'TrackMe શરૂ કરો';

  @override
  String get trackMeStop => 'સત્ર બંધ કરો';

  @override
  String get trackMeShareLink => 'લિંક શેર કરો';

  @override
  String get settingsTitle => 'સેટિંગ્સ';

  @override
  String get appInfoTitle => 'એપ માહિતી';

  @override
  String get appInfoDisclaimer =>
      'સફળ પ્રેષણનો અર્થ એ છે કે અમારા સર્વરે તે પ્રાપ્ત કર્યું છે. તે સત્તાવાર કટોકટી સેવા મોકલવામાં આવી હોવાની પુષ્ટિ નથી.';

  @override
  String get topQuestionsTitle => 'મુખ્ય પ્રશ્નો';

  @override
  String get aboutUsTitle => 'અમારા વિશે';
}
