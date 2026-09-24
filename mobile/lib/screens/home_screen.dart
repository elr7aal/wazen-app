import 'package:flutter/material.dart';
import '../core/theme.dart';
import '../models/api_models.dart';
import '../services/api_client.dart';
import '../widgets/wazen_ring.dart';
import 'craving_screen.dart';
import 'auth_screen.dart';
import 'food_log_screen.dart';
import 'add_food_screen.dart';
import 'profile_screen.dart';
import 'plan_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});
  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  DailyState? state;
  Map<String, dynamic>? user;
  bool loading = true;
  String? error;

  @override
  void initState() { super.initState(); refresh(); }

  Future<void> refresh() async {
    setState(() { loading = true; error = null; });
    try {
      final results = await Future.wait([WazenApi.instance.todayState(), WazenApi.instance.me()]);
      if (!mounted) return;
      setState(() { state = results[0] as DailyState; user = results[1] as Map<String, dynamic>; });
    } catch (e) {
      if (mounted) setState(() => error = e.toString());
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final profile = user?['profile'] as Map<String, dynamic>?;
    final target = (profile?['target_calories'] as num?)?.toDouble() ?? 2000;
    final firstName = user?['first_name']?.toString();
    return Scaffold(
      appBar: AppBar(
        title: Text(firstName?.isNotEmpty == true ? 'هلا $firstName' : 'هلا'),
        actions: [IconButton(onPressed: refresh, icon: const Icon(Icons.refresh_rounded)), IconButton(onPressed: () async {
          await WazenApi.instance.logout();
          if (context.mounted) Navigator.pushAndRemoveUntil(context, MaterialPageRoute(builder: (_) => const AuthScreen()), (_) => false);
        }, icon: const Icon(Icons.logout_rounded))],
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: 0,
        onDestinationSelected: (i) async {
          if (i == 1) {
            await Navigator.pushReplacement(context, MaterialPageRoute(builder: (_) => const FoodLogScreen()));
          } else if (i == 2) {
            final changed = await Navigator.push<bool>(context, MaterialPageRoute(builder: (_) => const CravingScreen()));
            if (changed == true && mounted) refresh();
          } else if (i == 3) {
            await Navigator.pushReplacement(context, MaterialPageRoute(builder: (_) => const PlanScreen()));
          } else if (i == 4) {
            await Navigator.pushReplacement(context, MaterialPageRoute(builder: (_) => const ProfileScreen()));
          }
        },
        destinations: const [
          NavigationDestination(icon: Icon(Icons.home_outlined), selectedIcon: Icon(Icons.home_rounded), label: 'الرئيسية'),
          NavigationDestination(icon: Icon(Icons.today_outlined), selectedIcon: Icon(Icons.today_rounded), label: 'يومي'),
          NavigationDestination(icon: Icon(Icons.restaurant_menu_outlined), selectedIcon: Icon(Icons.restaurant_menu_rounded), label: 'اكتشف'),
          NavigationDestination(icon: Icon(Icons.calendar_month_outlined), selectedIcon: Icon(Icons.calendar_month_rounded), label: 'خطتي'),
          NavigationDestination(icon: Icon(Icons.person_outline), selectedIcon: Icon(Icons.person), label: 'حسابي'),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: refresh,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(20, 8, 20, 32),
          children: [
            if (loading) const LinearProgressIndicator(minHeight: 2),
            if (error != null) _error(error!),
            const SizedBox(height: 8),
            Card(child: Padding(padding: const EdgeInsets.all(22), child: Column(children: [
              WazenRing(remaining: state?.remainingCalories ?? target, target: target),
              const SizedBox(height: 20),
              Row(children: [
                Expanded(child: _metric('البروتين', '${state?.proteinGapG.toStringAsFixed(0) ?? '—'}g', 'باقي')),
                const SizedBox(width: 10),
                Expanded(child: _metric('الكربوهيدرات', '${state?.carbsRemainingG?.toStringAsFixed(0) ?? '—'}g', 'باقي')),
                const SizedBox(width: 10),
                Expanded(child: _metric('الدهون', '${state?.fatRemainingG?.toStringAsFixed(0) ?? '—'}g', 'باقي')),
              ]),
            ]))),
            const SizedBox(height: 18),
            FilledButton.icon(
              icon: const Icon(Icons.restaurant_menu_rounded),
              label: const Text('شو آكل الحين؟', style: TextStyle(fontSize: 19, fontWeight: FontWeight.w800)),
              onPressed: () async {
                final changed = await Navigator.push<bool>(context, MaterialPageRoute(builder: (_) => const CravingScreen()));
                if (changed == true) refresh();
              },
            ),
            const SizedBox(height: 10),
            OutlinedButton.icon(
              icon: const Icon(Icons.add_circle_outline),
              label: const Text('أضف اللي أكلته'),
              onPressed: () async {
                final changed = await Navigator.push<bool>(context, MaterialPageRoute(builder: (_) => const AddFoodScreen()));
                if (changed == true && mounted) refresh();
              },
            ),
            const SizedBox(height: 18),
            const Text('الوصول السريع', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
            const SizedBox(height: 10),
            GridView.count(
              crossAxisCount: 2,
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              mainAxisSpacing: 10,
              crossAxisSpacing: 10,
              childAspectRatio: 2.0,
              children: [
                _quick(Icons.camera_alt_outlined, 'صور وجبتك', 'قريبًا'),
                _quick(Icons.edit_note_rounded, 'سجل ما أكلت', 'يدوي'),
                _quick(Icons.search_rounded, 'ابحث', 'الكتالوج'),
                _quick(Icons.shopping_basket_outlined, 'تسوق', 'السوبرماركت'),
              ],
            ),
            const SizedBox(height: 22),
            Container(
              padding: const EdgeInsets.all(18),
              decoration: BoxDecoration(color: WazenTheme.beige, borderRadius: BorderRadius.circular(20)),
              child: const Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Icon(Icons.auto_awesome_rounded, color: WazenTheme.greenDark),
                SizedBox(width: 12),
                Expanded(child: Text('أكلك يناسب حياتك، مو العكس. اختر اللي خاطرك فيه، ووازن يساعدك تدخله ضمن يومك بأفضل طريقة ممكنة.', style: TextStyle(height: 1.5))),
              ]),
            ),
          ],
        ),
      ),
    );
  }

  Widget _metric(String title, String value, String foot) => Container(
    padding: const EdgeInsets.all(12),
    decoration: BoxDecoration(color: const Color(0xFFF6F7F3), borderRadius: BorderRadius.circular(16)),
    child: Column(children: [Text(title, style: const TextStyle(fontSize: 12, color: Colors.black54)), const SizedBox(height: 4), Text(value, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800)), Text(foot, style: const TextStyle(fontSize: 11, color: Colors.black45))]),
  );

  Widget _quick(IconData icon, String title, String sub) => Card(child: Padding(padding: const EdgeInsets.all(14), child: Row(children: [Icon(icon, color: WazenTheme.green), const SizedBox(width: 10), Expanded(child: Column(mainAxisAlignment: MainAxisAlignment.center, crossAxisAlignment: CrossAxisAlignment.start, children: [Text(title, style: const TextStyle(fontWeight: FontWeight.w700)), Text(sub, style: const TextStyle(fontSize: 11, color: Colors.black45))]))])));

  Widget _error(String msg) => Container(padding: const EdgeInsets.all(14), decoration: BoxDecoration(color: const Color(0xFFFFEEEE), borderRadius: BorderRadius.circular(14)), child: Text(msg, style: const TextStyle(color: Colors.red)));
}
