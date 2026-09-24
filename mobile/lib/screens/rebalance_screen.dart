
import 'package:flutter/material.dart';
import '../core/theme.dart';
import '../models/api_models.dart';
import '../services/api_client.dart';
import '../widgets/recommendation_card.dart';
import 'food_detail_screen.dart';

class RebalanceScreen extends StatefulWidget {
  const RebalanceScreen({super.key});

  @override
  State<RebalanceScreen> createState() => _RebalanceScreenState();
}

class _RebalanceScreenState extends State<RebalanceScreen> {
  RebalanceData? data;
  bool loading = true;
  String? error;

  @override
  void initState() {
    super.initState();
    load();
  }

  Future<void> load() async {
    setState(() { loading = true; error = null; });
    try {
      final result = await WazenApi.instance.rebalanceForMe();
      if (mounted) setState(() => data = result);
    } catch (e) {
      if (mounted) setState(() => error = e.toString());
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final d = data;
    return Scaffold(
      appBar: AppBar(
        title: const Text('وازن باقي يومك'),
        automaticallyImplyLeading: false,
        actions: [
          IconButton(
            tooltip: 'الرئيسية',
            onPressed: () => Navigator.of(context).popUntil((route) => route.isFirst),
            icon: const Icon(Icons.home_outlined),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: load,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(20),
          children: [
            if (loading) const LinearProgressIndicator(minHeight: 2),
            if (error != null) ...[
              Text(error!, style: const TextStyle(color: Colors.red)),
              const SizedBox(height: 12),
              OutlinedButton(onPressed: load, child: const Text('حاول مرة ثانية')),
            ],
            if (d != null) ...[
              Text(d.headline, style: const TextStyle(fontSize: 28, fontWeight: FontWeight.w900)),
              const SizedBox(height: 8),
              Text(d.message, style: const TextStyle(fontSize: 16, color: Colors.black54, height: 1.5)),
              const SizedBox(height: 20),
              Container(
                padding: const EdgeInsets.all(18),
                decoration: BoxDecoration(
                  color: WazenTheme.beige,
                  borderRadius: BorderRadius.circular(22),
                ),
                child: Column(
                  children: [
                    Row(children: [
                      Expanded(child: _metric('السعرات المتبقية', d.dailyState.remainingCalories, 'kcal')),
                      Expanded(child: _metric('البروتين المتبقي', d.dailyState.proteinGapG, 'g')),
                    ]),
                    const Divider(height: 28),
                    Row(children: [
                      Expanded(child: _metric('الكربوهيدرات', d.dailyState.carbsRemainingG, 'g')),
                      Expanded(child: _metric('الدهون', d.dailyState.fatRemainingG, 'g')),
                    ]),
                  ],
                ),
              ),
              const SizedBox(height: 24),
              Row(
                children: [
                  const Expanded(child: Text('ممكن تكمل يومك بهالخيارات', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w900))),
                  TextButton.icon(onPressed: load, icon: const Icon(Icons.refresh_rounded), label: const Text('تحديث')),
                ],
              ),
              const SizedBox(height: 8),
              if (d.nextOptions.isEmpty)
                Container(
                  padding: const EdgeInsets.all(18),
                  decoration: BoxDecoration(color: const Color(0xFFF6F7F3), borderRadius: BorderRadius.circular(16)),
                  child: const Text('ما عندنا حالياً خيار موثّق يناسب المتبقي بدقة. تقدر تكمل يومك بشكل طبيعي ونسجل أكلك لما تختاره.'),
                ),
              ...d.nextOptions.map((item) => Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: RecommendationCard(
                  item: item,
                  onFeedback: (action) async {
                    await WazenApi.instance.sendRecommendationFeedback(item.foodId, action);
                    if (mounted) await load();
                  },
                  onTap: () async {
                    final logged = await Navigator.push<bool>(
                      context,
                      MaterialPageRoute(builder: (_) => FoodDetailScreen(item: item)),
                    );
                    if (logged == true && mounted) await load();
                  },
                ),
              )),
              const SizedBox(height: 12),
              OutlinedButton(
                onPressed: () => Navigator.of(context).popUntil((route) => route.isFirst),
                child: const Text('رجوع للرئيسية'),
              ),
              const SizedBox(height: 40),
            ],
          ],
        ),
      ),
    );
  }

  Widget _metric(String label, double? value, String unit) => Column(
    children: [
      Text(label, textAlign: TextAlign.center, style: const TextStyle(fontSize: 12, color: Colors.black54)),
      const SizedBox(height: 4),
      Text(value == null ? '—' : '${value.toStringAsFixed(0)} $unit',
          style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w900, color: WazenTheme.greenDark)),
    ],
  );
}
