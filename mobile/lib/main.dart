import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'core/theme.dart';
import 'services/api_client.dart';
import 'screens/auth_screen.dart';
import 'screens/home_screen.dart';
import 'screens/startup_gate.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await WazenApi.instance.restore();
  runApp(const WazenApp());
}

class WazenApp extends StatelessWidget {
  const WazenApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'WAZEN | وازن',
      theme: WazenTheme.light(),
      locale: const Locale('ar'),
      supportedLocales: const [Locale('ar'), Locale('en')],
      localizationsDelegates: const [
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      builder: (context, child) => Directionality(textDirection: TextDirection.rtl, child: child ?? const SizedBox.shrink()),
      home: const StartupGate(),
    );
  }
}
