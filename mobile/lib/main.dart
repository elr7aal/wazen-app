import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'core/theme.dart';
import 'services/api_client.dart';
import 'services/app_preferences.dart';
import 'services/account_link.dart';
import 'screens/startup_gate.dart';
import 'screens/reset_password_screen.dart';
import 'screens/verify_email_screen.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Future.wait([
    WazenApi.instance.restore(),
    AppPreferences.instance.restore(),
  ]);
  runApp(const WazenApp());
}

class WazenApp extends StatelessWidget {
  const WazenApp({super.key});

  @override
  Widget build(BuildContext context) {
    return ValueListenableBuilder<String>(
      valueListenable: AppPreferences.instance.language,
      builder: (context, language, _) {
        final locale=Locale(language);
        final rtl=language=='ar';
        return MaterialApp(
          debugShowCheckedModeBanner: false,
          title: 'WAZEN | وازن',
          theme: WazenTheme.light(),
          locale: locale,
          supportedLocales: const [Locale('ar'), Locale('en')],
          localizationsDelegates: const [
            GlobalMaterialLocalizations.delegate,
            GlobalWidgetsLocalizations.delegate,
            GlobalCupertinoLocalizations.delegate,
          ],
          builder: (context, child) => Directionality(
            textDirection: rtl ? TextDirection.rtl : TextDirection.ltr,
            child: child ?? const SizedBox.shrink(),
          ),
          initialRoute: '/',
          home: Builder(builder:(_){
            final link = AccountLink.parse(Uri.base);
            if (link?.action == 'verify-email') {
              return VerifyEmailScreen(token: link!.token);
            }
            if (link?.action == 'reset-password') {
              return ResetPasswordScreen(token: link!.token);
            }
            return const StartupGate();
          }),
        );
      },
    );
  }
}

