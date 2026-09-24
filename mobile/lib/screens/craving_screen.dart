import 'package:flutter/material.dart';
import '../models/api_models.dart';
import '../services/api_client.dart';
import '../widgets/recommendation_card.dart';
import 'food_detail_screen.dart';

class CravingScreen extends StatefulWidget {
  const CravingScreen({super.key});
  @override
  State<CravingScreen> createState() => _CravingScreenState();
}

class _CravingScreenState extends State<CravingScreen> {
  final controller = TextEditingController(text: 'أبي برغر من KFC تحت 600 سعرة');
  bool loading = false;
  String? error;
  List<RecommendationItem> results = const [];

  Future<void> search() async {
    if (controller.text.trim().isEmpty) return;
    setState(() { loading = true; error = null; results = const []; });
    try {
      final r = await WazenApi.instance.goldenFlow(controller.text);
      if (mounted) setState(() => results = r);
    } catch (e) {
      if (mounted) setState(() => error = e.toString());
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('شو آكل الحين؟')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          const Text('خاطرك بشي؟', style: TextStyle(fontSize: 26, fontWeight: FontWeight.w900)),
          const SizedBox(height: 6),
          const Text('قلها بطريقتك. مطعم، نوع أكل، سعرات أو بروتين.', style: TextStyle(color: Colors.black54)),
          const SizedBox(height: 18),
          TextField(
            controller: controller,
            minLines: 2,
            maxLines: 4,
            decoration: const InputDecoration(hintText: 'مثال: أبي برغر من هارديز تحت 600 سعرة'),
          ),
          const SizedBox(height: 12),
          FilledButton.icon(onPressed: loading ? null : search, icon: const Icon(Icons.auto_awesome_rounded), label: Text(loading ? 'أدور لك...' : 'دور لي')),
          if (error != null) Padding(padding: const EdgeInsets.only(top: 14), child: Text(error!, style: const TextStyle(color: Colors.red))),
          if (results.isNotEmpty) ...[
            const SizedBox(height: 28),
            Text('لقيت لك ${results.length} خيارات', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
            const SizedBox(height: 12),
            ...results.map((item) => Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: RecommendationCard(item: item, onFeedback: (action) async {
                await WazenApi.instance.sendRecommendationFeedback(item.foodId, action);
                if (mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(action == 'REJECT' ? 'بنقلل ظهور هالنوع لك.' : 'حفظنا تفضيلك.')));
                }
              }, onTap: () async {
                final logged = await Navigator.push<bool>(context, MaterialPageRoute(builder: (_) => FoodDetailScreen(item: item)));
                if (logged == true && context.mounted) Navigator.pop(context, true);
              }),
            )),
          ],
        ],
      ),
    );
  }
}
