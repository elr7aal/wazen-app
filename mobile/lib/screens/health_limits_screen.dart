import 'package:flutter/material.dart';
import '../core/theme.dart';
import '../services/api_client.dart';

class HealthLimitsScreen extends StatefulWidget{
  const HealthLimitsScreen({super.key});
  @override
  State<HealthLimitsScreen> createState()=>_HealthLimitsScreenState();
}

class _HealthLimitsScreenState extends State<HealthLimitsScreen>{
  bool loading=true;
  bool saving=false;
  String? error;
  List<Map<String,dynamic>> items=[];

  static const nutrients={
    'SODIUM_MG':('الصوديوم','mg'),
    'SUGAR_G':('السكر','g'),
    'SATURATED_FAT_G':('الدهون المشبعة','g'),
    'FAT_G':('الدهون','g'),
    'CARBS_G':('الكربوهيدرات','g'),
    'PROTEIN_G':('البروتين','g'),
    'CALORIES':('السعرات','kcal'),
  };

  @override
  void initState(){super.initState();load();}

  Future<void> load()async{
    setState((){loading=true;error=null;});
    try{
      final data=await WazenApi.instance.healthLimits();
      if(mounted)setState(()=>items=data);
    }catch(e){
      if(mounted)setState(()=>error=e.toString());
    }finally{
      if(mounted)setState(()=>loading=false);
    }
  }

  Future<void> edit([Map<String,dynamic>? current])async{
    String nutrient=current?['nutrient_code']?.toString()??'SODIUM_MG';
    String limitType=current?['limit_type']?.toString()??'MAX';
    String severity=current?['severity']?.toString()??'SOFT';
    String source=current?['source_type']?.toString()??'USER';
    bool active=current?['active']!=false;
    final value=TextEditingController(text:current?['value']?.toString()??'');
    final note=TextEditingController(text:current?['note']?.toString()??'');

    final saved=await showDialog<bool>(
      context:context,
      builder:(ctx)=>StatefulBuilder(
        builder:(ctx,setLocal)=>AlertDialog(
          title:Text(current==null?'إضافة حد صحي':'تعديل الحد الصحي'),
          content:SizedBox(
            width:420,
            child:SingleChildScrollView(child:Column(mainAxisSize:MainAxisSize.min,children:[
              const Text(
                'أدخل فقط حدًا تعرفه أو أوصى به مختص. وازن لا يحدد لك قيمة طبية من نفسه.',
                style:TextStyle(color:Colors.black54,height:1.4,fontSize:12),
              ),
              const SizedBox(height:14),
              DropdownButtonFormField<String>(
                value:nutrient,
                decoration:const InputDecoration(labelText:'العنصر الغذائي'),
                items:nutrients.entries.map((e)=>DropdownMenuItem(value:e.key,child:Text(e.value.$1))).toList(),
                onChanged:(v)=>setLocal(()=>nutrient=v!),
              ),
              const SizedBox(height:10),
              Row(children:[
                Expanded(child:DropdownButtonFormField<String>(
                  value:limitType,
                  decoration:const InputDecoration(labelText:'نوع الحد'),
                  items:const[
                    DropdownMenuItem(value:'MAX',child:Text('حد أقصى')),
                    DropdownMenuItem(value:'MIN',child:Text('حد أدنى')),
                  ],
                  onChanged:(v)=>setLocal(()=>limitType=v!),
                )),
                const SizedBox(width:10),
                Expanded(child:TextField(
                  controller:value,
                  keyboardType:const TextInputType.numberWithOptions(decimal:true),
                  decoration:InputDecoration(labelText:'القيمة (${nutrients[nutrient]!.$2})'),
                )),
              ]),
              const SizedBox(height:10),
              DropdownButtonFormField<String>(
                value:severity,
                decoration:const InputDecoration(labelText:'طريقة التطبيق'),
                items:const[
                  DropdownMenuItem(value:'SOFT',child:Text('تنبيه فقط')),
                  DropdownMenuItem(value:'HARD',child:Text('استبعاد صارم')),
                ],
                onChanged:(v)=>setLocal(()=>severity=v!),
              ),
              const SizedBox(height:10),
              DropdownButtonFormField<String>(
                value:source,
                decoration:const InputDecoration(labelText:'مصدر الحد'),
                items:const[
                  DropdownMenuItem(value:'USER',child:Text('أدخلته بنفسي')),
                  DropdownMenuItem(value:'CLINICIAN',child:Text('من مختص/خطة علاجية')),
                ],
                onChanged:(v)=>setLocal(()=>source=v!),
              ),
              const SizedBox(height:10),
              TextField(
                controller:note,
                maxLines:2,
                decoration:const InputDecoration(labelText:'ملاحظة اختيارية'),
              ),
              SwitchListTile(
                contentPadding:EdgeInsets.zero,
                title:const Text('مفعّل'),
                value:active,
                onChanged:(v)=>setLocal(()=>active=v),
              ),
            ])),
          ),
          actions:[
            TextButton(onPressed:()=>Navigator.pop(ctx,false),child:const Text('إلغاء')),
            FilledButton(
              onPressed:(){
                if(double.tryParse(value.text.trim())==null)return;
                Navigator.pop(ctx,true);
              },
              child:const Text('حفظ'),
            ),
          ],
        ),
      ),
    );

    if(saved!=true){
      value.dispose();note.dispose();return;
    }

    setState(()=>saving=true);
    try{
      await WazenApi.instance.setHealthLimit(
        nutrientCode:nutrient,
        limitType:limitType,
        value:double.parse(value.text.trim()),
        unit:nutrients[nutrient]!.$2,
        severity:severity,
        sourceType:source,
        note:note.text.trim().isEmpty?null:note.text.trim(),
        active:active,
      );
      await load();
    }catch(e){
      if(mounted)setState(()=>error=e.toString());
    }finally{
      value.dispose();note.dispose();
      if(mounted)setState(()=>saving=false);
    }
  }

  String _label(String code)=>nutrients[code]?.$1??code;

  @override
  Widget build(BuildContext context)=>Scaffold(
    appBar:AppBar(
      title:const Text('الحدود الصحية'),
      actions:[IconButton(onPressed:loading?null:load,icon:const Icon(Icons.refresh_rounded))],
    ),
    floatingActionButton:FloatingActionButton.extended(
      onPressed:saving?null:()=>edit(),
      icon:const Icon(Icons.add),
      label:const Text('إضافة حد'),
    ),
    body:RefreshIndicator(
      onRefresh:load,
      child:ListView(
        physics:const AlwaysScrollableScrollPhysics(),
        padding:const EdgeInsets.fromLTRB(18,18,18,100),
        children:[
          Container(
            padding:const EdgeInsets.all(16),
            decoration:BoxDecoration(color:WazenTheme.beige,borderRadius:BorderRadius.circular(18)),
            child:const Row(crossAxisAlignment:CrossAxisAlignment.start,children:[
              Icon(Icons.health_and_safety_outlined,color:WazenTheme.greenDark),
              SizedBox(width:10),
              Expanded(child:Text(
                'وازن يطبق الحدود التي تدخلها أنت أو المختص فقط. إذا كانت بيانات عنصر غذائي مطلوبة لحد صارم ومفقودة، فلن نفترض أنها صفر أو آمنة.',
                style:TextStyle(height:1.5),
              )),
            ]),
          ),
          if(loading)const Padding(padding:EdgeInsets.only(top:12),child:LinearProgressIndicator(minHeight:2)),
          if(error!=null)Padding(
            padding:const EdgeInsets.only(top:12),
            child:Text(error!,style:const TextStyle(color:Colors.red)),
          ),
          const SizedBox(height:16),
          if(!loading&&items.isEmpty)
            const Padding(
              padding:EdgeInsets.symmetric(vertical:30),
              child:Center(child:Text('ما عندك حدود صحية مضافة حاليًا.',style:TextStyle(color:Colors.black54))),
            ),
          ...items.map((x)=>Card(
            margin:const EdgeInsets.only(bottom:10),
            child:ListTile(
              onTap:()=>edit(x),
              leading:CircleAvatar(
                backgroundColor:x['severity']=='HARD'?const Color(0xFFFFEAEA):WazenTheme.beige,
                child:Icon(
                  x['severity']=='HARD'?Icons.block_outlined:Icons.warning_amber_rounded,
                  color:x['severity']=='HARD'?Colors.redAccent:WazenTheme.greenDark,
                ),
              ),
              title:Text(
                '${_label(x['nutrient_code'].toString())} • ${x['limit_type']=='MAX'?'حد أقصى':'حد أدنى'}',
                style:const TextStyle(fontWeight:FontWeight.w800),
              ),
              subtitle:Text(
                '${x['value']} ${x['unit']} • ${x['severity']=='HARD'?'استبعاد صارم':'تنبيه'} • ${x['source_type']=='CLINICIAN'?'من مختص':'بواسطة المستخدم'}'
                '${x['active']==false?' • غير مفعّل':''}',
              ),
              trailing:const Icon(Icons.edit_outlined),
            ),
          )),
        ],
      ),
    ),
  );
}
