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
                decoration: BoxDecoration(color: WazenTheme.mint, borderRadius: BorderRadius.circular(14)),
                child: Text('${item.wazenScore.toStringAsFixed(0)}%', style: const TextStyle(fontWeight: FontWeight.w800, color: WazenTheme.greenDark)),
              ),
            ]),
            const SizedBox(height: 14),
            Wrap(spacing: 8, runSpacing: 8, children: [
              _chip('${item.nutrition.calories?.toStringAsFixed(0) ?? '—'} kcal'),
              _chip('${item.nutrition.proteinG?.toStringAsFixed(0) ?? '—'}g بروتين'),
              if(item.price!=null)_chip('${item.currency??'AED'} ${item.price!.toStringAsFixed(0)}'),
              _chip(decisionLabel),
              if(item.sourceFreshness!=null)_chip(_freshnessLabel(item.sourceFreshness!,item.sourceAgeDays)),
            ]),
            if (item.reasons.isNotEmpty) ...[
              const SizedBox(height: 14),
              Text(_translateReason(item.reasons.first), style: const TextStyle(color: Colors.black87, height: 1.4)),
            ],
            if(item.warnings.isNotEmpty)...[
              const SizedBox(height:10),
              Wrap(
                spacing:6,
                runSpacing:6,
                children:item.warnings.map((w)=>Container(
                  padding:const EdgeInsets.symmetric(horizontal:9,vertical:6),
                  decoration:BoxDecoration(
                    color:const Color(0xFFFFECE8),
                    borderRadius:BorderRadius.circular(10),
                  ),
                  child:Row(mainAxisSize:MainAxisSize.min,children:[
                    const Icon(Icons.warning_amber_rounded,size:15,color:WazenTheme.coral),
                    const SizedBox(width:4),
                    Text(_translateWarning(w),style:const TextStyle(fontSize:11)),
                  ]),
                )).toList(),
              ),
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
        decoration: BoxDecoration(color: WazenTheme.mint, borderRadius: BorderRadius.circular(12)),
        child: Text(text, style: const TextStyle(fontSize: 13,color:WazenTheme.greenDark,fontWeight:FontWeight.w600)),
      );

  String _translateReason(String value) {
    if (value.contains('Fits the requested')) return 'يناسب سياق السعرات الذي طلبته.';
    if (value.contains('Close to the requested')) return 'قريب من حد السعرات الذي طلبته.';
    if (value.contains('modification may help')) return 'أعلى من المطلوب، لكن يمكن نوازنه بتعديل الوجبة.';
    if (value.contains('remaining protein')) return 'يساعدك على تغطية احتياج البروتين المتبقي.';
    if (value.contains('marked LOVE')) return 'يتوافق مع شيء حددته ضمن المفضلات.';
    if (value.contains('marked LIKE')) return 'يتوافق مع أحد تفضيلاتك.';
    return value;
  }

  String _freshnessLabel(String status,int? age){
    switch(status){
      case 'FRESH': return age==null?'مصدر حديث':'تحقق قبل $age يوم';
      case 'AGING': return age==null?'مصدر يحتاج تحديث':'تحقق قبل $age يوم';
      case 'STALE': return age==null?'مصدر قديم':'مصدر قديم • $age يوم';
      default: return 'تاريخ التحقق غير معروف';
    }
  }

  String _translateWarning(String value) {
    switch(value){
      case 'HIGH_SODIUM_FOR_REMAINING_DAY': return 'صوديوم مرتفع بالنسبة لباقي اليوم';
      case 'OVER_BUDGET': return 'أعلى من الميزانية المحددة';
      case 'ALLERGEN_CROSS_CONTACT_WARNING': return 'يوجد تنبيه احتمال تلامس مع مسبب حساسية';
      case 'SOURCE_STALE': return 'بيانات المصدر قديمة وتحتاج إعادة تحقق';
      case 'SOURCE_AGING': return 'مر وقت على آخر تحقق من المصدر';
      case 'SOURCE_VERIFICATION_UNKNOWN': return 'تاريخ التحقق من المصدر غير متوفر';
      case 'MISSING_HEALTH_DATA': return 'بعض البيانات الصحية غير متوفرة';
      default:
        if(value.startsWith('MISSING_')) return 'بيانات غذائية مطلوبة غير متوفرة';
        if(value.endsWith('_MAX_LIMIT')||value.endsWith('_MIN_LIMIT')) return 'يتجاوز حدًا صحيًا مرنًا';
        return value;
    }
  }
}
