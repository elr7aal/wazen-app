import 'package:flutter/material.dart';
import '../models/api_models.dart';
import '../services/api_client.dart';

class TextParsePreviewScreen extends StatefulWidget {
  final Map<String,dynamic> parsed;
  final String mealType;
  final String title;
  final String intro;
  const TextParsePreviewScreen({
    super.key,
    required this.parsed,
    required this.mealType,
    this.title='راجع اللي فهمناه',
    this.intro='ولا عنصر ينحفظ تلقائيًا. راجع المطابقة والكمية لكل جزء قبل الإضافة.',
  });

  @override
  State<TextParsePreviewScreen> createState()=>_TextParsePreviewScreenState();
}

class _ParsedItemState {
  final String rawText;
  final String queryText;
  final String confidence;
  final String unit;
  final List<FoodDetail> candidates;
  int selectedIndex;
  double quantity;
  bool include;
  final bool requiresConfirmation;

  _ParsedItemState({
    required this.rawText,
    required this.queryText,
    required this.confidence,
    required this.unit,
    required this.candidates,
    required this.selectedIndex,
    required this.quantity,
    required this.include,
    required this.requiresConfirmation,
  });
}

class _TextParsePreviewScreenState extends State<TextParsePreviewScreen>{
  late final List<_ParsedItemState> items;
  bool saving=false;
  String? error;

  @override
  void initState(){
    super.initState();
    final rows=((widget.parsed['items'] as List?)??const []);
    items=rows.map((raw){
      final m=Map<String,dynamic>.from(raw as Map);
      final candidates=((m['candidates'] as List?)??const [])
        .map((e)=>FoodDetail.fromJson(Map<String,dynamic>.from(e as Map))).toList();
      final requiresConfirmation=m['requires_confirmation']==true;
      return _ParsedItemState(
        rawText:(m['raw_text']??'').toString(),
        queryText:(m['query_text']??'').toString(),
        confidence:(m['confidence']??'UNKNOWN').toString(),
        unit:(m['estimated_unit']??'SERVING').toString(),
        candidates:candidates,
        selectedIndex:0,
        quantity:(m['estimated_quantity'] as num? ?? 1).toDouble().clamp(.25,20),
        include:candidates.isNotEmpty&&!requiresConfirmation,
        requiresConfirmation:requiresConfirmation,
      );
    }).toList();
  }

  Future<void> save()async{
    final selected=items.where((x)=>x.include&&x.candidates.isNotEmpty).toList();
    if(selected.isEmpty){
      setState(()=>error='اختر عنصرًا واحدًا على الأقل له مطابقة في الكتالوج.');
      return;
    }
    setState((){saving=true;error=null;});
    try{
      for(final item in selected){
        final food=item.candidates[item.selectedIndex];
        await WazenApi.instance.logFromCatalog(
          food.foodId,
          mealType:widget.mealType,
          quantity:item.quantity,
        );
      }
      if(!mounted)return;
      Navigator.pop(context,true);
    }catch(e){
      if(mounted)setState(()=>error=e.toString());
    }finally{
      if(mounted)setState(()=>saving=false);
    }
  }

  String confidenceLabel(String value){
    switch(value){
      case 'HIGH':return 'ثقة عالية';
      case 'MEDIUM':return 'ثقة متوسطة';
      default:return 'تحتاج مراجعة';
    }
  }

  @override
  Widget build(BuildContext context)=>Scaffold(
    appBar:AppBar(title:Text(widget.title)),
    bottomNavigationBar:SafeArea(
      child:Padding(
        padding:const EdgeInsets.all(16),
        child:FilledButton.icon(
          onPressed:saving?null:save,
          icon:const Icon(Icons.check_circle_outline),
          label:Text(saving?'جاري الإضافة...':'أضف العناصر المختارة'),
        ),
      ),
    ),
    body:ListView(
      padding:const EdgeInsets.fromLTRB(18,12,18,28),
      children:[
        Text(
          widget.intro,
          style:const TextStyle(color:Colors.black54,height:1.5),
        ),
        if(error!=null)Padding(
          padding:const EdgeInsets.only(top:10),
          child:Text(error!,style:const TextStyle(color:Colors.red)),
        ),
        const SizedBox(height:14),
        ...List.generate(items.length,(i)=>_card(i,items[i])),
      ],
    ),
  );

  Widget _card(int index,_ParsedItemState item){
    final hasCandidates=item.candidates.isNotEmpty;
    final selected=hasCandidates?item.candidates[item.selectedIndex]:null;
    return Card(
      margin:const EdgeInsets.only(bottom:12),
      child:Padding(
        padding:const EdgeInsets.all(14),
        child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
          Row(crossAxisAlignment:CrossAxisAlignment.start,children:[
            Checkbox(
              value:item.include,
              onChanged:hasCandidates?(v)=>setState(()=>item.include=v??false):null,
            ),
            Expanded(child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
              Text(item.rawText,style:const TextStyle(fontSize:17,fontWeight:FontWeight.w900)),
              const SizedBox(height:3),
              Text(
                '${confidenceLabel(item.confidence)} • ${item.unit}',
                style:const TextStyle(fontSize:12,color:Colors.black54),
              ),
            ])),
          ]),
          if(item.requiresConfirmation&&hasCandidates)...[
            const SizedBox(height:8),
            Container(
              width:double.infinity,
              padding:const EdgeInsets.all(10),
              decoration:BoxDecoration(
                color:const Color(0xFFFFF1E8),
                borderRadius:BorderRadius.circular(10),
              ),
              child:const Text(
                'الثقة منخفضة: هذا العنصر غير محدد للحفظ تلقائيًا. فعّل المربع فقط إذا راجعت المطابقة والكمية.',
                style:TextStyle(fontSize:12,height:1.4),
              ),
            ),
          ],
          const SizedBox(height:10),
          if(!hasCandidates)
            Container(
              width:double.infinity,
              padding:const EdgeInsets.all(12),
              decoration:BoxDecoration(
                color:const Color(0xFFFFF4DD),
                borderRadius:BorderRadius.circular(12),
              ),
              child:const Text(
                'ما حصلنا مطابقة مؤكدة في الكتالوج لهذا العنصر. ما راح ينحفظ.',
                style:TextStyle(height:1.4),
              ),
            )
          else ...[
            DropdownButtonFormField<int>(
              value:item.selectedIndex,
              decoration:const InputDecoration(labelText:'المطابقة من الكتالوج'),
              items:List.generate(item.candidates.length,(j){
                final f=item.candidates[j];
                final name=f.nameAr?.isNotEmpty==true?f.nameAr!:f.name;
                return DropdownMenuItem(
                  value:j,
                  child:Text(
                    '$name • ${f.nutrition.calories?.toStringAsFixed(0)??'—'} kcal',
                    overflow:TextOverflow.ellipsis,
                  ),
                );
              }),
              onChanged:(v){
                if(v!=null)setState(()=>item.selectedIndex=v);
              },
            ),
            const SizedBox(height:12),
            Row(children:[
              const Text('الكمية',style:TextStyle(fontWeight:FontWeight.w800)),
              const Spacer(),
              IconButton(
                onPressed:item.quantity>.25?()=>setState(()=>item.quantity=(item.quantity-.25).clamp(.25,20)):null,
                icon:const Icon(Icons.remove_circle_outline),
              ),
              Text(
                item.quantity.toStringAsFixed(item.quantity%1==0?0:2),
                style:const TextStyle(fontWeight:FontWeight.w900),
              ),
              IconButton(
                onPressed:()=>setState(()=>item.quantity=(item.quantity+.25).clamp(.25,20)),
                icon:const Icon(Icons.add_circle_outline),
              ),
            ]),
            if(selected!=null)Padding(
              padding:const EdgeInsets.only(top:6),
              child:Text(
                'التقدير بعد الكمية: ${((selected.nutrition.calories??0)*item.quantity).toStringAsFixed(0)} kcal • ${((selected.nutrition.proteinG??0)*item.quantity).toStringAsFixed(1)}g بروتين',
                style:const TextStyle(fontSize:12,color:Colors.black54),
              ),
            ),
          ],
        ]),
      ),
    );
  }
}
