import 'package:flutter/material.dart';
import '../core/theme.dart';
import '../models/api_models.dart';

class RecommendationCard extends StatelessWidget {
  final RecommendationItem item;
  final VoidCallback onTap;
  final void Function(String action)? onFeedback;
  const RecommendationCard({super.key, required this.item, required this.onTap, this.onFeedback});

  String get decisionLabel => switch (item.decision) {
        'ELIGIBLE' => 'مناسب الآن',
        'NEAR_MATCH' => 'قريب من خطتك',
        'MAKE_IT_FIT' => 'نقدر نوازنه',
        _ => item.decision,
      };

  @override
  Widget build(BuildContext context) {
    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(22),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(18),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(item.nameAr?.isNotEmpty == true ? item.nameAr! : item.name, style: const TextStyle(fontSize: 19, fontWeight: FontWeight.w800)),
                const SizedBox(height: 4),
                Text(item.vendor, style: const TextStyle(color: Colors.black54)),
              ])),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                decoration: BoxDecoration(color: WazenTheme.beige, borderRadius: BorderRadius.circular(14)),
                child: Text('${item.wazenScore.toStringAsFixed(0)}%', style: const TextStyle(fontWeight: FontWeight.w800, color: WazenTheme.greenDark)),
              ),
            ]),
            const SizedBox(height: 14),
            Wrap(spacing: 8, runSpacing: 8, children: [
              _chip('${item.nutrition.calories?.toStringAsFixed(0) ?? '—'} kcal'),
              _chip('${item.nutrition.proteinG?.toStringAsFixed(0) ?? '—'}g بروتين'),
              _chip(decisionLabel),
            ]),
            if (item.reasons.isNotEmpty) ...[
              const SizedBox(height: 14),
              Text(_translateReason(item.reasons.first), style: const TextStyle(color: Colors.black87, height: 1.4)),
            ],
            const SizedBox(height: 8),
            Row(children:[
              Expanded(child:Text('مصدر البيانات: ${item.sourceConfidence ?? 'غير محدد'}', style: const TextStyle(fontSize: 12, color: Colors.black45))),
              if(onFeedback!=null)...[
                IconButton(tooltip:'حفظ',onPressed:()=>onFeedback!('SAVE'),icon:const Icon(Icons.bookmark_add_outlined,size:20)),
                IconButton(tooltip:'مو مناسب لي',onPressed:()=>onFeedback!('REJECT'),icon:const Icon(Icons.thumb_down_alt_outlined,size:20)),
              ],
            ]),
          ]),
        ),
      ),
    );
  }

  Widget _chip(String text) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
        decoration: BoxDecoration(color: const Color(0xFFF2F4F0), borderRadius: BorderRadius.circular(12)),
        child: Text(text, style: const TextStyle(fontSize: 13)),
      );

  String _translateReason(String value) {
    if (value.contains('Fits the requested')) return 'يناسب سياق السعرات الذي طلبته.';
    if (value.contains('Close to the requested')) return 'قريب من حد السعرات الذي طلبته.';
    if (value.contains('modification may help')) return 'أعلى من المطلوب، لكن يمكن نوازنه بتعديل الوجبة.';
    return value;
  }
}
