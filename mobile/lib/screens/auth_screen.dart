import 'package:flutter/material.dart';
import '../core/theme.dart';
import '../services/api_client.dart';
import 'home_screen.dart';
import 'onboarding_screen.dart';

class AuthScreen extends StatefulWidget {
  const AuthScreen({super.key});
  @override
  State<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends State<AuthScreen> {
  final email = TextEditingController(text: 'alpha@wazen.local');
  final password = TextEditingController(text: 'Password123!');
  final apiUrl = TextEditingController(text: WazenApi.instance.baseUrl.replaceAll('/api/v1', ''));
  bool loading = false;
  String? error;

  Future<void> submit({required bool register}) async {
    setState(() { loading = true; error = null; });
    try {
      await WazenApi.instance.configureBaseUrl(apiUrl.text);
      if (register) {
        await WazenApi.instance.register(email: email.text, password: password.text, firstName: 'عبدالله');
      } else {
        await WazenApi.instance.login(email.text, password.text);
      }
      if (!mounted) return;
      if (register) {
        Navigator.of(context).pushReplacement(MaterialPageRoute(builder: (_) => const OnboardingScreen()));
      } else {
        final complete = await WazenApi.instance.onboardingStatus();
        if (!mounted) return;
        Navigator.of(context).pushReplacement(MaterialPageRoute(builder: (_) => complete ? const HomeScreen() : const OnboardingScreen()));
      }
    } catch (e) {
      setState(() => error = e.toString());
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 440),
              child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                const Text('وازن', textAlign: TextAlign.center, style: TextStyle(fontSize: 48, fontWeight: FontWeight.w900, color: WazenTheme.greenDark)),
                const Text('WAZEN', textAlign: TextAlign.center, style: TextStyle(letterSpacing: 7, color: Colors.black45)),
                const SizedBox(height: 8),
                const Text('المناسب لك، الآن.', textAlign: TextAlign.center, style: TextStyle(fontSize: 18)),
                const SizedBox(height: 36),
                TextField(controller: apiUrl, textDirection: TextDirection.ltr, decoration: const InputDecoration(labelText: 'عنوان الـ API', helperText: 'Android emulator: http://10.0.2.2:8000')),
                const SizedBox(height: 12),
                TextField(controller: email, textDirection: TextDirection.ltr, keyboardType: TextInputType.emailAddress, decoration: const InputDecoration(labelText: 'البريد الإلكتروني')),
                const SizedBox(height: 12),
                TextField(controller: password, obscureText: true, textDirection: TextDirection.ltr, decoration: const InputDecoration(labelText: 'كلمة المرور')),
                if (error != null) Padding(padding: const EdgeInsets.only(top: 12), child: Text(error!, style: const TextStyle(color: Colors.red))),
                const SizedBox(height: 20),
                FilledButton(onPressed: loading ? null : () => submit(register: false), child: Text(loading ? '...' : 'دخول')),
                const SizedBox(height: 10),
                OutlinedButton(onPressed: loading ? null : () => submit(register: true), child: const Text('إنشاء حساب Alpha')),
              ]),
            ),
          ),
        ),
      ),
    );
  }
}
