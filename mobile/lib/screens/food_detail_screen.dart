import 'package:flutter/material.dart';
import '../core/theme.dart';
import '../models/api_models.dart';
import '../services/api_client.dart';
import 'make_it_fit_screen.dart';
import 'rebalance_screen.dart';

class FoodDetailScreen extends StatefulWidget {
  final RecommendationItem item;
  const FoodDetailScreen({super.key, required this.item});
  @override
  State<FoodDetailScreen> createState() => _FoodDetailScreenState();
}

class _FoodDetailScreenState extends State<FoodDetailScreen> {
  FoodDetail? detail;
  bool loading = true;
  bool saving = false;
  String? error;

  @override
  void initState() { super.initState(); load(); }

  Future<void> load() async {
    try {
      final d = await WazenApi.instance.foodDetail(widget.item.foodId);
      if (mounted) setState(() => detail = d);
    } catch (e) {
      if (mounted) setState(() => error = e.toString());
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  Future<void> addToDay() async {
    setState(() { saving = true; error = null; });
    try {
      final newState = await WazenApi.instance.logFromCatalog(widget.item.foodId);
      if (!mounted) return;
      await showDialog<void>(context: context, builder: (_) => AlertDialog(
        title: const Text('تم تسجيل الوجبة'),
        content: Text('باقي لك اليوم ${newState.remainingCalories.toStringAsFixed(0)} سعرة، و${newState.proteinGapG.toStringAsFixed(0)}g بروتين.'),
        actions: [TextButton(onPressed: () => Navigator.pop(context), child: const Text('تمام'))],
      ));
      if (!mounted) return;
      await Navigator.pushReplacement(
        context,
        MaterialPageRoute(builder: (_) => const RebalanceScreen()),
      );
    } catch (e) {
      if (mounted) setState(() => error = e.toString());
    } finally {
      if (mounted) setState(() => saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final n = detail?.nutrition ?? widget.item.nutrition;
    final name = detail?.nameAr?.isNotEmpty == true ? detail!.nameAr! : (widget.item.nameAr?.isNotEmpty == true ? widget.item.nameAr! : widget.item.name);
    return Scaffold(
      appBar: AppBar(title: const Text('تفاصيل الوجبة')),
      bottomNavigationBar: SafeArea(child: Padding(padding: const EdgeInsets.all(16), child: FilledButton(onPressed: saving ? null : addToDay, child: Text(saving ? 'جاري التسجيل...' : 'أضف ليومي')))),
      body: ListView(padding: const EdgeInsets.all(20), children: [
        if (loading) const LinearProgressIndicator(minHeight: 2),
        Text(name, style: const TextStyle(fontSize: 28, fontWeight: FontWeight.w900)),
        const SizedBox(height: 4),
        Text(detail?.vendor ?? widget.item.vendor, style: const TextStyle(fontSize: 16, color: Colors.black54)),
        const SizedBox(height: 20),
        Container(
          padding: const EdgeInsets.all(18),
          decoration: BoxDecoration(color: WazenTheme.beige, borderRadius: BorderRadius.circular(20)),
          child: Row(children: [
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [const Text('مناسب لك', style: TextStyle(color: Colors.black54)), Text('${widget.item.wazenScore.toStringAsFixed(0)}%', style: const TextStyle(fontSize: 34, fontWeight: FontWeight.w900, color: WazenTheme.greenDark))])),
            Text(_decision(widget.item.decision), style: const TextStyle(fontWeight: FontWeight.w800)),
          ]),
        ),
        const SizedBox(height: 18),
        const Text('القيم الغذائية', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
        const SizedBox(height: 10),
        GridView.count(
          crossAxisCount: 2,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          childAspectRatio: 2.5,
          mainAxisSpacing: 8,
          crossAxisSpacing: 8,
          children: [
            _stat('السعرات', '${n.calories?.toStringAsFixed(0) ?? '—'} kcal'),
            _stat('البروتين', '${n.proteinG?.toStringAsFixed(1) ?? '—'} g'),
            _stat('الكربوهيدرات', '${n.carbsG?.toStringAsFixed(1) ?? '—'} g'),
            _stat('الدهون', '${n.fatG?.toStringAsFixed(1) ?? '—'} g'),
            _stat('الصوديوم', '${n.sodiumMg?.toStringAsFixed(0) ?? '—'} mg'),
            _stat('المصدر', detail?.sourceConfidence ?? widget.item.sourceConfidence ?? '—'),
          ],
        ),
        if(detail!=null)...[
          const SizedBox(height:18),
          const Text('مصدر البيانات',style:TextStyle(fontSize:18,fontWeight:FontWeight.w800)),
          const SizedBox(height:8),
          Container(
            padding:const EdgeInsets.all(14),
            decoration:BoxDecoration(
              color:const Color(0xFFF6F7F3),
              borderRadius:BorderRadius.circular(14),
            ),
            child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
              Text(detail!.sourceName??'المصدر غير محدد',style:const TextStyle(fontWeight:FontWeight.w800)),
              const SizedBox(height:4),
              Text('الثقة: ${detail!.sourceConfidence??'غير محددة'}',style:const TextStyle(color:Colors.black54)),
              const SizedBox(height:4),
              Text(
                detail!.sourceVerifiedAt==null
                  ?'آخر تحقق: غير متوفر'
                  :'آخر تحقق: ${detail!.sourceVerifiedAt!.year}-${detail!.sourceVerifiedAt!.month.toString().padLeft(2,'0')}-${detail!.sourceVerifiedAt!.day.toString().padLeft(2,'0')}',
                style:const TextStyle(color:Colors.black54),
              ),
              if((detail!.sourceReference??'').isNotEmpty)...[
                const SizedBox(height:4),
                Text(
                  detail!.sourceReference!,
                  maxLines:2,
                  overflow:TextOverflow.ellipsis,
                  textDirection:TextDirection.ltr,
                  style:const TextStyle(fontSize:11,color:Colors.black45),
                ),
              ],
              const SizedBox(height:8),
              const Text(
                'أي قيمة غير متوفرة تظهر بعلامة — ولا يعاملها وازن كأنها صفر أو منخفضة.',
                style:TextStyle(fontSize:11,color:Colors.black45,height:1.4),
              ),
            ]),
          ),
        ],
        if ((detail?.allergens ?? const []).isNotEmpty) ...[
          const SizedBox(height: 18),
          const Text('مسببات الحساسية المسجلة', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
          const SizedBox(height: 8),
          Wrap(spacing: 8, runSpacing: 8, children: detail!.allergens.map((a) => Chip(label: Text(a))).toList()),
        ],
        if (widget.item.canModify && detail != null) ...[
          const SizedBox(height: 18),
          OutlinedButton.icon(
            icon: const Icon(Icons.tune_rounded),
            label: const Text('وازن الوجبة قبل ما تعتمدها'),
            onPressed: () async {
              final logged = await Navigator.push<bool>(context, MaterialPageRoute(builder: (_) => MakeItFitScreen(detail: detail!)));
              if (logged == true && context.mounted) Navigator.pop(context, true);
            },
          ),
        ],
        if (error != null) Padding(padding: const EdgeInsets.only(top: 14), child: Text(error!, style: const TextStyle(color: Colors.red))),
        const SizedBox(height: 90),
      ]),
    );
  }

  Widget _stat(String label, String value) => Container(padding: const EdgeInsets.all(12), decoration: BoxDecoration(color: const Color(0xFFF6F7F3), borderRadius: BorderRadius.circular(14)), child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [Text(label, style: const TextStyle(fontSize: 12, color: Colors.black54)), const SizedBox(height: 2), Text(value, style: const TextStyle(fontWeight: FontWeight.w800))]));

  String _decision(String d) => switch (d) {'ELIGIBLE' => 'مناسب الآن', 'NEAR_MATCH' => 'قريب من الخطة', 'MAKE_IT_FIT' => 'نقدر نوازنه', _ => d};
}
