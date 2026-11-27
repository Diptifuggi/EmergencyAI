// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for English (`en`).
class AppLocalizationsEn extends AppLocalizations {
  AppLocalizationsEn([String locale = 'en']) : super(locale);

  @override
  String get appTitle => 'EmergencyIQ';

  @override
  String get bannerTagline => 'EmergencyIQ Safety Hub';

  @override
  String get bannerLine1 => 'One app for all emergency needs';

  @override
  String get bannerLine2 => 'Request help anytime';

  @override
  String get bannerLine3 => 'Live status updates';

  @override
  String get bannerLine4 => 'Share location for faster help';

  @override
  String get shortcutProfile => 'Profile';

  @override
  String get shortcutSosHistory => 'SOS History';

  @override
  String get shortcutNotification => 'Notification';

  @override
  String get shortcutAboutUs => 'About Us';

  @override
  String get shortcutDial112 => 'Dial 112';

  @override
  String get shortcutChatUs => 'Chat Us';

  @override
  String get shortcutTrackMe => 'TrackMe';

  @override
  String get shortcutEmergencySos => 'Emergency';

  @override
  String get sectionContactEmergencyServices => 'Contact Emergency Services';

  @override
  String get servicePolice => 'Police';

  @override
  String get serviceFire => 'Fire';

  @override
  String get serviceMedical => 'Medical';

  @override
  String get serviceDisaster => 'Disaster';

  @override
  String get serviceWomen => 'Woman';

  @override
  String get serviceChild => 'Child';

  @override
  String get serviceElderly => 'Elderly';

  @override
  String get serviceRailway => 'Railway';

  @override
  String get locationOffTapToEnable => 'Location off - tap to enable';

  @override
  String get locationResolving => 'Resolving address...';

  @override
  String get locationUnavailable => 'Location unavailable';

  @override
  String get integratedHelplineTitle => 'Integrated Helpline';

  @override
  String get integratedHelplineClose => 'Close';

  @override
  String get helplineDescPolice =>
      'Police SOS provides instant help in police services.';

  @override
  String get helplineDescFire =>
      'Fire SOS provides instant help for fire and rescue.';

  @override
  String get helplineDescMedical =>
      'Medical SOS connects you for ambulance and medical aid.';

  @override
  String get helplineDescDisaster =>
      'Disaster SOS alerts response teams for natural disasters.';

  @override
  String get helplineDescWomen =>
      'Woman SOS provides dedicated safety and helpline support.';

  @override
  String get helplineDescChild =>
      'Child SOS connects to child protection and rescue.';

  @override
  String get helplineDescElderly =>
      'Elderly SOS provides dedicated assistance for senior citizens.';

  @override
  String get helplineDescRailway =>
      'Railway SOS connects to railway security and assistance.';

  @override
  String get helplineDescEmergency => 'Emergency SOS for any urgent situation.';

  @override
  String sendServiceSosTitle(String service) {
    return 'Send $service SOS';
  }

  @override
  String get holdToSendSos => 'Hold 2s to Send SOS';

  @override
  String callNumberBtn(String number) {
    return 'Call $number';
  }

  @override
  String get cancelBtn => 'Cancel';

  @override
  String sendingInSeconds(int seconds) {
    return 'Sending in ${seconds}s... Tap to Cancel';
  }

  @override
  String get sosSentConfirmed => 'SOS received by server';

  @override
  String get sosQueuedOffline => 'Queued offline — will retry automatically';

  @override
  String get dial112Title => 'Call 112?';

  @override
  String get dial112Message =>
      'This will open your phone dialer to call 112. EmergencyIQ does not auto-call.';

  @override
  String get dialNowBtn => 'Open Dialer';

  @override
  String get drawerHome => 'Home';

  @override
  String get drawerProfile => 'Profile';

  @override
  String get drawerEContact => 'E-Contact';

  @override
  String get drawerSosHistory => 'SOS History';

  @override
  String get drawerSettings => 'Settings';

  @override
  String get drawerAppInfo => 'App Info';

  @override
  String get drawerTopQuestions => 'Top Questions';

  @override
  String get drawerLogout => 'Logout';

  @override
  String versionLabel(String version) {
    return 'Version $version';
  }

  @override
  String get logoutConfirmTitle => 'Logout';

  @override
  String get logoutConfirmMessage =>
      'Are you sure you want to log out? Clear local offline SOS queue too?';

  @override
  String get logoutKeepQueue => 'Logout (Keep Queue)';

  @override
  String get logoutClearQueue => 'Logout & Clear Queue';

  @override
  String get eContactTitle => 'Emergency Contacts';

  @override
  String get eContactEmpty => 'No emergency contacts added yet (max 5).';

  @override
  String get eContactAddBtn => 'Add Contact';

  @override
  String get eContactLimitReached => 'Maximum 5 emergency contacts allowed.';

  @override
  String get eContactSuggestionTitle => 'Quick Add from Profile';

  @override
  String get eContactAddSuggested => 'Add as emergency contact';

  @override
  String get sosHistoryTitle => 'SOS History';

  @override
  String get sosHistoryEmpty => 'No SOS alerts sent yet.';

  @override
  String get notificationsTitle => 'Notifications';

  @override
  String get notificationsEmpty => 'No notifications yet.';

  @override
  String get markAllRead => 'Mark all read';

  @override
  String get trackMeTitle => 'TrackMe Live Sharing';

  @override
  String get trackMeStart => 'Start TrackMe';

  @override
  String get trackMeStop => 'Stop Session';

  @override
  String get trackMeShareLink => 'Share Link';

  @override
  String get settingsTitle => 'Settings';

  @override
  String get appInfoTitle => 'App Info';

  @override
  String get appInfoDisclaimer =>
      'A successful send means our server received it. It is not confirmation that an official emergency service has been dispatched.';

  @override
  String get topQuestionsTitle => 'Top Questions';

  @override
  String get aboutUsTitle => 'About Us';
}
