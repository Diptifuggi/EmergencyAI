import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/intl.dart' as intl;

import 'app_localizations_en.dart';
import 'app_localizations_gu.dart';
import 'app_localizations_hi.dart';
import 'app_localizations_mr.dart';

// ignore_for_file: type=lint

/// Callers can lookup localized strings with an instance of AppLocalizations
/// returned by `AppLocalizations.of(context)`.
///
/// Applications need to include `AppLocalizations.delegate()` in their app's
/// `localizationDelegates` list, and the locales they support in the app's
/// `supportedLocales` list. For example:
///
/// ```dart
/// import 'l10n/app_localizations.dart';
///
/// return MaterialApp(
///   localizationsDelegates: AppLocalizations.localizationsDelegates,
///   supportedLocales: AppLocalizations.supportedLocales,
///   home: MyApplicationHome(),
/// );
/// ```
///
/// ## Update pubspec.yaml
///
/// Please make sure to update your pubspec.yaml to include the following
/// packages:
///
/// ```yaml
/// dependencies:
///   # Internationalization support.
///   flutter_localizations:
///     sdk: flutter
///   intl: any # Use the pinned version from flutter_localizations
///
///   # Rest of dependencies
/// ```
///
/// ## iOS Applications
///
/// iOS applications define key application metadata, including supported
/// locales, in an Info.plist file that is built into the application bundle.
/// To configure the locales supported by your app, you’ll need to edit this
/// file.
///
/// First, open your project’s ios/Runner.xcworkspace Xcode workspace file.
/// Then, in the Project Navigator, open the Info.plist file under the Runner
/// project’s Runner folder.
///
/// Next, select the Information Property List item, select Add Item from the
/// Editor menu, then select Localizations from the pop-up menu.
///
/// Select and expand the newly-created Localizations item then, for each
/// locale your application supports, add a new item and select the locale
/// you wish to add from the pop-up menu in the Value field. This list should
/// be consistent with the languages listed in the AppLocalizations.supportedLocales
/// property.
abstract class AppLocalizations {
  AppLocalizations(String locale)
      : localeName = intl.Intl.canonicalizedLocale(locale.toString());

  final String localeName;

  static AppLocalizations? of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations);
  }

  static const LocalizationsDelegate<AppLocalizations> delegate =
      _AppLocalizationsDelegate();

  /// A list of this localizations delegate along with the default localizations
  /// delegates.
  ///
  /// Returns a list of localizations delegates containing this delegate along with
  /// GlobalMaterialLocalizations.delegate, GlobalCupertinoLocalizations.delegate,
  /// and GlobalWidgetsLocalizations.delegate.
  ///
  /// Additional delegates can be added by appending to this list in
  /// MaterialApp. This list does not have to be used at all if a custom list
  /// of delegates is preferred or required.
  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates =
      <LocalizationsDelegate<dynamic>>[
    delegate,
    GlobalMaterialLocalizations.delegate,
    GlobalCupertinoLocalizations.delegate,
    GlobalWidgetsLocalizations.delegate,
  ];

  /// A list of this localizations delegate's supported locales.
  static const List<Locale> supportedLocales = <Locale>[
    Locale('en'),
    Locale('gu'),
    Locale('hi'),
    Locale('mr')
  ];

  /// No description provided for @appTitle.
  ///
  /// In en, this message translates to:
  /// **'EmergencyIQ'**
  String get appTitle;

  /// No description provided for @bannerTagline.
  ///
  /// In en, this message translates to:
  /// **'EmergencyIQ Safety Hub'**
  String get bannerTagline;

  /// No description provided for @bannerLine1.
  ///
  /// In en, this message translates to:
  /// **'One app for all emergency needs'**
  String get bannerLine1;

  /// No description provided for @bannerLine2.
  ///
  /// In en, this message translates to:
  /// **'Request help anytime'**
  String get bannerLine2;

  /// No description provided for @bannerLine3.
  ///
  /// In en, this message translates to:
  /// **'Live status updates'**
  String get bannerLine3;

  /// No description provided for @bannerLine4.
  ///
  /// In en, this message translates to:
  /// **'Share location for faster help'**
  String get bannerLine4;

  /// No description provided for @shortcutProfile.
  ///
  /// In en, this message translates to:
  /// **'Profile'**
  String get shortcutProfile;

  /// No description provided for @shortcutSosHistory.
  ///
  /// In en, this message translates to:
  /// **'SOS History'**
  String get shortcutSosHistory;

  /// No description provided for @shortcutNotification.
  ///
  /// In en, this message translates to:
  /// **'Notification'**
  String get shortcutNotification;

  /// No description provided for @shortcutAboutUs.
  ///
  /// In en, this message translates to:
  /// **'About Us'**
  String get shortcutAboutUs;

  /// No description provided for @shortcutDial112.
  ///
  /// In en, this message translates to:
  /// **'Dial 112'**
  String get shortcutDial112;

  /// No description provided for @shortcutChatUs.
  ///
  /// In en, this message translates to:
  /// **'Chat Us'**
  String get shortcutChatUs;

  /// No description provided for @shortcutTrackMe.
  ///
  /// In en, this message translates to:
  /// **'TrackMe'**
  String get shortcutTrackMe;

  /// No description provided for @shortcutEmergencySos.
  ///
  /// In en, this message translates to:
  /// **'Emergency'**
  String get shortcutEmergencySos;

  /// No description provided for @sectionContactEmergencyServices.
  ///
  /// In en, this message translates to:
  /// **'Contact Emergency Services'**
  String get sectionContactEmergencyServices;

  /// No description provided for @servicePolice.
  ///
  /// In en, this message translates to:
  /// **'Police'**
  String get servicePolice;

  /// No description provided for @serviceFire.
  ///
  /// In en, this message translates to:
  /// **'Fire'**
  String get serviceFire;

  /// No description provided for @serviceMedical.
  ///
  /// In en, this message translates to:
  /// **'Medical'**
  String get serviceMedical;

  /// No description provided for @serviceDisaster.
  ///
  /// In en, this message translates to:
  /// **'Disaster'**
  String get serviceDisaster;

  /// No description provided for @serviceWomen.
  ///
  /// In en, this message translates to:
  /// **'Woman'**
  String get serviceWomen;

  /// No description provided for @serviceChild.
  ///
  /// In en, this message translates to:
  /// **'Child'**
  String get serviceChild;

  /// No description provided for @serviceElderly.
  ///
  /// In en, this message translates to:
  /// **'Elderly'**
  String get serviceElderly;

  /// No description provided for @serviceRailway.
  ///
  /// In en, this message translates to:
  /// **'Railway'**
  String get serviceRailway;

  /// No description provided for @locationOffTapToEnable.
  ///
  /// In en, this message translates to:
  /// **'Location off - tap to enable'**
  String get locationOffTapToEnable;

  /// No description provided for @locationResolving.
  ///
  /// In en, this message translates to:
  /// **'Resolving address...'**
  String get locationResolving;

  /// No description provided for @locationUnavailable.
  ///
  /// In en, this message translates to:
  /// **'Location unavailable'**
  String get locationUnavailable;

  /// No description provided for @integratedHelplineTitle.
  ///
  /// In en, this message translates to:
  /// **'Integrated Helpline'**
  String get integratedHelplineTitle;

  /// No description provided for @integratedHelplineClose.
  ///
  /// In en, this message translates to:
  /// **'Close'**
  String get integratedHelplineClose;

  /// No description provided for @helplineDescPolice.
  ///
  /// In en, this message translates to:
  /// **'Police SOS provides instant help in police services.'**
  String get helplineDescPolice;

  /// No description provided for @helplineDescFire.
  ///
  /// In en, this message translates to:
  /// **'Fire SOS provides instant help for fire and rescue.'**
  String get helplineDescFire;

  /// No description provided for @helplineDescMedical.
  ///
  /// In en, this message translates to:
  /// **'Medical SOS connects you for ambulance and medical aid.'**
  String get helplineDescMedical;

  /// No description provided for @helplineDescDisaster.
  ///
  /// In en, this message translates to:
  /// **'Disaster SOS alerts response teams for natural disasters.'**
  String get helplineDescDisaster;

  /// No description provided for @helplineDescWomen.
  ///
  /// In en, this message translates to:
  /// **'Woman SOS provides dedicated safety and helpline support.'**
  String get helplineDescWomen;

  /// No description provided for @helplineDescChild.
  ///
  /// In en, this message translates to:
  /// **'Child SOS connects to child protection and rescue.'**
  String get helplineDescChild;

  /// No description provided for @helplineDescElderly.
  ///
  /// In en, this message translates to:
  /// **'Elderly SOS provides dedicated assistance for senior citizens.'**
  String get helplineDescElderly;

  /// No description provided for @helplineDescRailway.
  ///
  /// In en, this message translates to:
  /// **'Railway SOS connects to railway security and assistance.'**
  String get helplineDescRailway;

  /// No description provided for @helplineDescEmergency.
  ///
  /// In en, this message translates to:
  /// **'Emergency SOS for any urgent situation.'**
  String get helplineDescEmergency;

  /// No description provided for @sendServiceSosTitle.
  ///
  /// In en, this message translates to:
  /// **'Send {service} SOS'**
  String sendServiceSosTitle(String service);

  /// No description provided for @holdToSendSos.
  ///
  /// In en, this message translates to:
  /// **'Hold 2s to Send SOS'**
  String get holdToSendSos;

  /// No description provided for @callNumberBtn.
  ///
  /// In en, this message translates to:
  /// **'Call {number}'**
  String callNumberBtn(String number);

  /// No description provided for @cancelBtn.
  ///
  /// In en, this message translates to:
  /// **'Cancel'**
  String get cancelBtn;

  /// No description provided for @sendingInSeconds.
  ///
  /// In en, this message translates to:
  /// **'Sending in {seconds}s... Tap to Cancel'**
  String sendingInSeconds(int seconds);

  /// No description provided for @sosSentConfirmed.
  ///
  /// In en, this message translates to:
  /// **'SOS received by server'**
  String get sosSentConfirmed;

  /// No description provided for @sosQueuedOffline.
  ///
  /// In en, this message translates to:
  /// **'Queued offline — will retry automatically'**
  String get sosQueuedOffline;

  /// No description provided for @dial112Title.
  ///
  /// In en, this message translates to:
  /// **'Call 112?'**
  String get dial112Title;

  /// No description provided for @dial112Message.
  ///
  /// In en, this message translates to:
  /// **'This will open your phone dialer to call 112. EmergencyIQ does not auto-call.'**
  String get dial112Message;

  /// No description provided for @dialNowBtn.
  ///
  /// In en, this message translates to:
  /// **'Open Dialer'**
  String get dialNowBtn;

  /// No description provided for @drawerHome.
  ///
  /// In en, this message translates to:
  /// **'Home'**
  String get drawerHome;

  /// No description provided for @drawerProfile.
  ///
  /// In en, this message translates to:
  /// **'Profile'**
  String get drawerProfile;

  /// No description provided for @drawerEContact.
  ///
  /// In en, this message translates to:
  /// **'E-Contact'**
  String get drawerEContact;

  /// No description provided for @drawerSosHistory.
  ///
  /// In en, this message translates to:
  /// **'SOS History'**
  String get drawerSosHistory;

  /// No description provided for @drawerSettings.
  ///
  /// In en, this message translates to:
  /// **'Settings'**
  String get drawerSettings;

  /// No description provided for @drawerAppInfo.
  ///
  /// In en, this message translates to:
  /// **'App Info'**
  String get drawerAppInfo;

  /// No description provided for @drawerTopQuestions.
  ///
  /// In en, this message translates to:
  /// **'Top Questions'**
  String get drawerTopQuestions;

  /// No description provided for @drawerLogout.
  ///
  /// In en, this message translates to:
  /// **'Logout'**
  String get drawerLogout;

  /// No description provided for @versionLabel.
  ///
  /// In en, this message translates to:
  /// **'Version {version}'**
  String versionLabel(String version);

  /// No description provided for @logoutConfirmTitle.
  ///
  /// In en, this message translates to:
  /// **'Logout'**
  String get logoutConfirmTitle;

  /// No description provided for @logoutConfirmMessage.
  ///
  /// In en, this message translates to:
  /// **'Are you sure you want to log out? Clear local offline SOS queue too?'**
  String get logoutConfirmMessage;

  /// No description provided for @logoutKeepQueue.
  ///
  /// In en, this message translates to:
  /// **'Logout (Keep Queue)'**
  String get logoutKeepQueue;

  /// No description provided for @logoutClearQueue.
  ///
  /// In en, this message translates to:
  /// **'Logout & Clear Queue'**
  String get logoutClearQueue;

  /// No description provided for @eContactTitle.
  ///
  /// In en, this message translates to:
  /// **'Emergency Contacts'**
  String get eContactTitle;

  /// No description provided for @eContactEmpty.
  ///
  /// In en, this message translates to:
  /// **'No emergency contacts added yet (max 5).'**
  String get eContactEmpty;

  /// No description provided for @eContactAddBtn.
  ///
  /// In en, this message translates to:
  /// **'Add Contact'**
  String get eContactAddBtn;

  /// No description provided for @eContactLimitReached.
  ///
  /// In en, this message translates to:
  /// **'Maximum 5 emergency contacts allowed.'**
  String get eContactLimitReached;

  /// No description provided for @eContactSuggestionTitle.
  ///
  /// In en, this message translates to:
  /// **'Quick Add from Profile'**
  String get eContactSuggestionTitle;

  /// No description provided for @eContactAddSuggested.
  ///
  /// In en, this message translates to:
  /// **'Add as emergency contact'**
  String get eContactAddSuggested;

  /// No description provided for @sosHistoryTitle.
  ///
  /// In en, this message translates to:
  /// **'SOS History'**
  String get sosHistoryTitle;

  /// No description provided for @sosHistoryEmpty.
  ///
  /// In en, this message translates to:
  /// **'No SOS alerts sent yet.'**
  String get sosHistoryEmpty;

  /// No description provided for @notificationsTitle.
  ///
  /// In en, this message translates to:
  /// **'Notifications'**
  String get notificationsTitle;

  /// No description provided for @notificationsEmpty.
  ///
  /// In en, this message translates to:
  /// **'No notifications yet.'**
  String get notificationsEmpty;

  /// No description provided for @markAllRead.
  ///
  /// In en, this message translates to:
  /// **'Mark all read'**
  String get markAllRead;

  /// No description provided for @trackMeTitle.
  ///
  /// In en, this message translates to:
  /// **'TrackMe Live Sharing'**
  String get trackMeTitle;

  /// No description provided for @trackMeStart.
  ///
  /// In en, this message translates to:
  /// **'Start TrackMe'**
  String get trackMeStart;

  /// No description provided for @trackMeStop.
  ///
  /// In en, this message translates to:
  /// **'Stop Session'**
  String get trackMeStop;

  /// No description provided for @trackMeShareLink.
  ///
  /// In en, this message translates to:
  /// **'Share Link'**
  String get trackMeShareLink;

  /// No description provided for @settingsTitle.
  ///
  /// In en, this message translates to:
  /// **'Settings'**
  String get settingsTitle;

  /// No description provided for @appInfoTitle.
  ///
  /// In en, this message translates to:
  /// **'App Info'**
  String get appInfoTitle;

  /// No description provided for @appInfoDisclaimer.
  ///
  /// In en, this message translates to:
  /// **'A successful send means our server received it. It is not confirmation that an official emergency service has been dispatched.'**
  String get appInfoDisclaimer;

  /// No description provided for @topQuestionsTitle.
  ///
  /// In en, this message translates to:
  /// **'Top Questions'**
  String get topQuestionsTitle;

  /// No description provided for @aboutUsTitle.
  ///
  /// In en, this message translates to:
  /// **'About Us'**
  String get aboutUsTitle;
}

class _AppLocalizationsDelegate
    extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  Future<AppLocalizations> load(Locale locale) {
    return SynchronousFuture<AppLocalizations>(lookupAppLocalizations(locale));
  }

  @override
  bool isSupported(Locale locale) =>
      <String>['en', 'gu', 'hi', 'mr'].contains(locale.languageCode);

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}

AppLocalizations lookupAppLocalizations(Locale locale) {
  // Lookup logic when only language code is specified.
  switch (locale.languageCode) {
    case 'en':
      return AppLocalizationsEn();
    case 'gu':
      return AppLocalizationsGu();
    case 'hi':
      return AppLocalizationsHi();
    case 'mr':
      return AppLocalizationsMr();
  }

  throw FlutterError(
      'AppLocalizations.delegate failed to load unsupported locale "$locale". This is likely '
      'an issue with the localizations generation tool. Please file an issue '
      'on GitHub with a reproducible sample app and the gen-l10n configuration '
      'that was used.');
}
