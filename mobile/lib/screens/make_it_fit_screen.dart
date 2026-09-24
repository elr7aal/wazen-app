
import 'package:flutter/material.dart';
import '../core/theme.dart';
import '../models/api_models.dart';
import '../services/api_client.dart';
import 'rebalance_screen.dart';

class MakeItFitScreen extends StatefulWidget {
  final FoodDetail detail;
  const MakeItFitScreen({super.key,required this.detail});
  @override State<MakeItFitScreen> createState()=>_MakeItFitScreenState();
}

class _MakeItFitScreenState extends State<MakeItFitScreen>{
  bool loading=true,saving=false;
  String? error;
  List<ModifierOption> options=const[];
  final Set<String> selected={};
  MakeItFitPreview? preview;

  @override void initState(){super.initState();load();}

  Future<void> load() async{
    try{final x=await WazenApi.instance.makeItFitOptions(widget.detail.foodId);if(mounted)setState(()=>options=x);}
    catch(e){if(mounted)setState(()=>error=e.toString());}
    finally{if(mounted)setState(()=>loading=false);}
  }

  Future<void> updatePreview() async{
    setState(()=>loading=true);
    try{final x=await WazenApi.instance.makeItFitPreview(widget.detail.foodId,selected.toList());if(mounted)setState(()=>preview=x);}
    catch(e){if(mounted)setState(()=>error=e.toString());}
    finally{if(mounted)setState(()=>loading=false);}
  }

  Future<void> confirm() async{
    setState(()=>saving=true);
    try{
      final state=await WazenApi.instance.logModifiedFromCatalog(widget.detail.foodId,selected.toList());
      if(!mounted)return;
      await showDialog<void>(context:context,builder:(_)=>AlertDialog(
        title:const Text('تم اعتماد الوجبة'),
        content:Text('باقي لك اليوم ${state.remainingCalories.toStringAsFixed(0)} سعرة و${state.proteinGapG.toStringAsFixed(0)}g بروتين.'),
        actions:[TextButton(onPressed:()=>Navigator.pop(context),child:const Text('تمام'))],
      ));
      if(!mounted)return;
      await Navigator.pushReplacement(
        context,
        MaterialPageRoute(builder:(_)=>const RebalanceScreen()),
      );
    }catch(e){if(mounted)setState(()=>error=e.toString());}
    finally{if(mounted)setState(()=>saving=false);}
  }

  @override Widget build(BuildContext context){
    final base=widget.detail.nutrition.calories??0;
    final local=(base+options.where((o)=>selected.contains(o.component)).fold<double>(0,(s,o)=>s+o.calorieDelta)).clamp(0,double.infinity);
    final after=preview?.modifiedNutrition.calories??local;
    final saved=preview?.caloriesSaved??(base-local);
    return Scaffold(
      appBar:AppBar(title:const Text('وازن الوجبة')),
      bottomNavigationBar:SafeArea(child:Padding(padding:const EdgeInsets.all(16),child:FilledButton(
        onPressed:saving?null:confirm,
        child:Text(saving?'جاري الاعتماد...':selected.isEmpty?'اعتمدها كما هي':'اعتمد النسخة المعدلة'),
      ))),
      body:ListView(padding:const EdgeInsets.all(20),children:[
        Text(widget.detail.nameAr?.isNotEmpty==true?widget.detail.nameAr!:widget.detail.name,style:const TextStyle(fontSize:26,fontWeight:FontWeight.w900)),
        const SizedBox(height:6),
        const Text('اختر فقط الأشياء الموجودة فعلًا في طلبك. وازن ما يفترض وجود بطاطس أو مشروب أو صوص.',style:TextStyle(color:Colors.black54)),
        const SizedBox(height:18),
        Container(padding:const EdgeInsets.all(18),decoration:BoxDecoration(color:WazenTheme.beige,borderRadius:BorderRadius.circular(20)),child:Row(children:[
          Expanded(child:_n('قبل','${base.toStringAsFixed(0)} kcal')),
          const Icon(Icons.arrow_back_rounded),
          Expanded(child:_n('بعد','${after.toStringAsFixed(0)} kcal')),
        ])),
        if(saved>0)Padding(padding:const EdgeInsets.only(top:10),child:Text('وفّرت تقريبًا ${saved.toStringAsFixed(0)} سعرة',style:const TextStyle(fontWeight:FontWeight.w800,color:WazenTheme.greenDark))),
        const SizedBox(height:22),
        const Text('شو موجود في طلبك؟',style:TextStyle(fontSize:18,fontWeight:FontWeight.w900)),
        if(loading&&options.isEmpty)const LinearProgressIndicator(minHeight:2),
        if(!loading&&options.isEmpty)Container(padding:const EdgeInsets.all(16),decoration:BoxDecoration(color:const Color(0xFFF6F7F3),borderRadius:BorderRadius.circular(16)),child:const Text('حالياً ما عندنا تعديلات غذائية موثقة لهذا المطعم. تقدر تعتمد الوجبة كما هي.')),
        ...options.map((o)=>CheckboxListTile(
          contentPadding:EdgeInsets.zero,
          value:selected.contains(o.component),
          title:Text(o.labelAr,style:const TextStyle(fontWeight:FontWeight.w700)),
          subtitle:Text(o.calorieDelta<0?'${o.calorieDelta.abs().toStringAsFixed(0)} سعرة أقل • ${o.confidence??''}':'${o.calorieDelta.toStringAsFixed(0)} سعرة • ${o.confidence??''}'),
          onChanged:(v)async{setState((){if(v==true){selected.add(o.component);}else{selected.remove(o.component);}});await updatePreview();},
        )),
        if(preview!=null)...[
          const SizedBox(height:18),
          const Text('بعد التعديل',style:TextStyle(fontSize:18,fontWeight:FontWeight.w900)),
          const SizedBox(height:8),
          Wrap(spacing:8,runSpacing:8,children:[
            _c('السعرات',preview!.modifiedNutrition.calories,'kcal'),
            _c('البروتين',preview!.modifiedNutrition.proteinG,'g'),
            _c('الكربوهيدرات',preview!.modifiedNutrition.carbsG,'g'),
            _c('الدهون',preview!.modifiedNutrition.fatG,'g'),
            _c('الصوديوم',preview!.modifiedNutrition.sodiumMg,'mg'),
          ]),
          const SizedBox(height:12),
          Row(children:[
            Icon(preview!.fitsRemainingCalories?Icons.check_circle:Icons.info_outline,color:preview!.fitsRemainingCalories?WazenTheme.greenDark:Colors.orange),
            const SizedBox(width:8),
            Expanded(child:Text(preview!.fitsRemainingCalories?'هالنسخة تدخل ضمن السعرات المتبقية حالياً.':'ما زالت أعلى من المتبقي، وتقدر تختارها ووازن يعيد ترتيب باقي يومك.')),
          ]),
        ],
        if(error!=null)Padding(padding:const EdgeInsets.only(top:14),child:Text(error!,style:const TextStyle(color:Colors.red))),
        const SizedBox(height:100),
      ]),
    );
  }

  Widget _n(String l,String v)=>Column(children:[Text(l,style:const TextStyle(color:Colors.black54)),const SizedBox(height:4),Text(v,style:const TextStyle(fontSize:22,fontWeight:FontWeight.w900))]);
  Widget _c(String l,double? v,String u)=>Chip(label:Text('$l: ${v?.toStringAsFixed(1)??'—'} $u'));
}
