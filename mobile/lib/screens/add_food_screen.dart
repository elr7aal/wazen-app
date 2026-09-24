
import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:speech_to_text/speech_to_text.dart' as stt;
import '../models/api_models.dart';
import '../services/api_client.dart';
import 'add_food_review_screen.dart';
import 'text_parse_preview_screen.dart';

class AddFoodScreen extends StatefulWidget{
  const AddFoodScreen({super.key});
  @override State<AddFoodScreen> createState()=>_AddFoodScreenState();
}
class _AddFoodScreenState extends State<AddFoodScreen> with SingleTickerProviderStateMixin{
  late final TabController tabs;
  final search=TextEditingController();
  final natural=TextEditingController();
  final caption=TextEditingController();
  final maxCalories=TextEditingController();
  final minProtein=TextEditingController();
  final maxSodium=TextEditingController();
  final maxPrice=TextEditingController();
  final stt.SpeechToText speech=stt.SpeechToText();
  bool listening=false;
  Map<String,dynamic>? visionResult;
  String meal='SNACK';
  bool loading=false;
  bool showFilters=false;
  String searchType='ALL';
  String? message;
  List<FoodDetail> results=const[];

  static const meals={'BREAKFAST':'فطور','LUNCH':'غداء','DINNER':'عشاء','SNACK':'سناك'};

  @override void initState(){super.initState();tabs=TabController(length:4,vsync:this);}
  @override void dispose(){tabs.dispose();search.dispose();natural.dispose();caption.dispose();maxCalories.dispose();minProtein.dispose();maxSodium.dispose();maxPrice.dispose();super.dispose();}

  Future<void> showResults(List<FoodDetail> x,String msg)async{
    setState(()=>results=x);
    if(x.isEmpty){setState(()=>message=msg);return;}
    setState(()=>message=null);
  }

  double? _num(TextEditingController c)=>double.tryParse(c.text.trim());

  Future<void> doSearch()async{
    if(search.text.trim().isEmpty&&
       maxCalories.text.trim().isEmpty&&
       minProtein.text.trim().isEmpty&&
       maxSodium.text.trim().isEmpty&&
       maxPrice.text.trim().isEmpty&&
       searchType=='ALL')return;
    setState(()=>loading=true);
    try{
      await showResults(
        await WazenApi.instance.searchFoods(
          search.text.trim(),
          foodType:searchType=='ALL'?null:searchType,
          maxCalories:_num(maxCalories),
          minProteinG:_num(minProtein),
          maxSodiumMg:_num(maxSodium),
          maxPrice:_num(maxPrice),
          limit:50,
        ),
        'ما حصلت نتيجة مطابقة للفلاتر الحالية.'
      );
    }finally{if(mounted)setState(()=>loading=false);}
  }

  void clearFilters(){
    maxCalories.clear();minProtein.clear();maxSodium.clear();maxPrice.clear();
    setState(()=>searchType='ALL');
  }

  Future<void> doText()async{
    if(natural.text.trim().isEmpty)return;
    setState(()=>loading=true);
    try{
      final parsed=await WazenApi.instance.parseFoodTextDetailed(natural.text.trim(),mealType:meal);
      if(!mounted)return;
      final rows=((parsed['items'] as List?)??const []);
      if(rows.isEmpty){
        setState(()=>message='ما قدرت أحدد أي عنصر من النص. جرّب صياغة أبسط أو استخدم البحث.');
        return;
      }
      final saved=await Navigator.push<bool>(
        context,
        MaterialPageRoute(
          builder:(_)=>TextParsePreviewScreen(parsed:parsed,mealType:meal),
        ),
      );
      if(saved==true&&mounted)Navigator.pop(context,true);
    }catch(e){
      if(mounted)setState(()=>message=e.toString());
    }finally{
      if(mounted)setState(()=>loading=false);
    }
  }

  Future<void> pickImage()async{
    final file=await ImagePicker().pickImage(source:ImageSource.camera,imageQuality:70,maxWidth:1600);
    if(file==null)return;
    setState(()=>loading=true);
    try{
      final bytes=await File(file.path).readAsBytes();
      final data=await WazenApi.instance.analyzeFoodImage(
        base64Encode(bytes),
        caption:caption.text.trim().isEmpty?null:caption.text.trim(),
        mealType:meal,
      );
      final vr=data['vision_result'];
      if(mounted)setState(()=>visionResult=vr is Map?Map<String,dynamic>.from(vr):null);

      final rows=((data['items'] as List?)??const []);
      if(rows.isNotEmpty&&mounted){
        final provider=(data['analysis_provider']??'UNKNOWN').toString();
        final saved=await Navigator.push<bool>(
          context,
          MaterialPageRoute(
            builder:(_)=>TextParsePreviewScreen(
              parsed:data,
              mealType:meal,
              title:'راجع تحليل الصورة',
              intro:provider=='NOT_CONFIGURED'
                ?'الصورة نفسها لم تُحلل لأن مزود Vision غير مفعّل. المعروض أدناه مبني فقط على الوصف الذي كتبته، وولا عنصر ينحفظ تلقائيًا.'
                :'تحليل الصورة تقديري. راجع كل صنف والمطابقة والكمية؛ العناصر منخفضة الثقة تحتاج منك تأكيدًا صريحًا.',
            ),
          ),
        );
        if(saved==true&&mounted)Navigator.pop(context,true);
      }else if(mounted){
        setState(()=>message=data['analysis_provider']=='NOT_CONFIGURED'
          ?'تحليل الصورة غير مفعّل حاليًا، وما عندنا وصف نصي قابل للمطابقة. ما تم حفظ أي شيء.'
          :data['analysis_provider']=='ERROR'
            ?'تعذر تحليل الصورة الآن. ما تم حفظ أي شيء.'
            :'ما قدرنا نحدد عناصر قابلة للمراجعة من الصورة. ما تم حفظ أي شيء.');
      }
    }finally{if(mounted)setState(()=>loading=false);}
  }

  Future<void> toggleVoice() async{
    if(listening){
      await speech.stop();
      if(mounted)setState(()=>listening=false);
      if(natural.text.trim().isNotEmpty)await doText();
      return;
    }
    final available=await speech.initialize(
      onStatus:(s){if((s=='done'||s=='notListening')&&mounted)setState(()=>listening=false);},
      onError:(_){if(mounted)setState(()=>listening=false);},
    );
    if(!available){
      if(mounted)setState(()=>message='ما قدرت أفعّل المايك. تأكد من صلاحية الميكروفون.');
      return;
    }
    setState(()=>listening=true);
    await speech.listen(
      localeId:'ar_AE',
      listenOptions:stt.SpeechListenOptions(partialResults:true),
      onResult:(r){if(mounted)setState(()=>natural.text=r.recognizedWords);},
    );
  }

  Future<void> openReview(FoodDetail f,String source)async{
    final saved=await Navigator.push<bool>(context,MaterialPageRoute(builder:(_)=>AddFoodReviewScreen(food:f,mealType:meal,sourceLabel:source)));
    if(saved==true&&mounted)Navigator.pop(context,true);
  }

  Future<void> scanBarcode()async{
    final code=await Navigator.push<String>(context,MaterialPageRoute(builder:(_)=>const _BarcodeScannerScreen()));
    if(code==null)return;
    setState(()=>loading=true);
    try{
      final food=await WazenApi.instance.barcodeLookup(code);
      if(food==null){setState(()=>message='الباركود غير موجود في قاعدة WAZEN حالياً. نسمح بإرساله للمراجعة في مرحلة Partner/Admin القادمة.');}
      else{await openReview(food,'Barcode • بيانات الكتالوج');}
    }finally{if(mounted)setState(()=>loading=false);}
  }

  @override Widget build(BuildContext context)=>Scaffold(
    appBar:AppBar(title:const Text('أضف أكل'),bottom:TabBar(controller:tabs,isScrollable:true,tabs:const[
      Tab(icon:Icon(Icons.search),text:'بحث'),
      Tab(icon:Icon(Icons.text_fields),text:'اكتب'),
      Tab(icon:Icon(Icons.camera_alt_outlined),text:'صورة'),
      Tab(icon:Icon(Icons.qr_code_scanner),text:'باركود'),
    ])),
    body:Column(children:[
      Padding(padding:const EdgeInsets.fromLTRB(16,12,16,4),child:DropdownButtonFormField<String>(
        value:meal,decoration:const InputDecoration(labelText:'أضيفها تحت'),
        items:meals.entries.map((e)=>DropdownMenuItem(value:e.key,child:Text(e.value))).toList(),
        onChanged:(v){if(v!=null)setState(()=>meal=v);},
      )),
      if(loading)const LinearProgressIndicator(minHeight:2),
      Expanded(child:TabBarView(controller:tabs,children:[
        _searchTab(),
        ListView(padding:const EdgeInsets.all(18),children:[
          TextField(controller:natural,minLines:2,maxLines:4,decoration:const InputDecoration(hintText:'مثال: أكلت نص دجاجة مع رز ولبن')),
          const SizedBox(height:12),
          Row(children:[
            Expanded(child:FilledButton(onPressed:doText,child:const Text('حلل النص'))),
            const SizedBox(width:10),
            IconButton.filledTonal(
              tooltip:listening?'إيقاف':'تكلم',
              onPressed:toggleVoice,
              icon:Icon(listening?Icons.stop_circle_outlined:Icons.mic_none_rounded),
            ),
          ]),
          if(listening)const Padding(padding:EdgeInsets.only(top:10),child:Text('أسمعك... تكلم بطريقتك.',style:TextStyle(color:Colors.black54))),
        ]),
        ListView(padding:const EdgeInsets.all(18),children:[
          const Text('صوّر وجبتك ثم راجع النتيجة قبل تسجيلها.',style:TextStyle(fontSize:17,fontWeight:FontWeight.w800)),
          const SizedBox(height:12),
          TextField(controller:caption,decoration:const InputDecoration(labelText:'وصف اختياري يساعد التحليل',hintText:'مثال: زنجر من KFC')),
          const SizedBox(height:12),
          FilledButton.icon(onPressed:pickImage,icon:const Icon(Icons.camera_alt),label:const Text('التقط صورة')),
          const SizedBox(height:10),
          const Text('في نسخة Alpha الحالية لا يتم اختلاق تقدير للصورة إذا لم يكن مزوّد Vision مفعّلًا.',style:TextStyle(color:Colors.black54)),
        ]),
        ListView(padding:const EdgeInsets.all(18),children:[
          const Text('امسح باركود المنتج لمطابقته مع قاعدة السوبرماركت.',style:TextStyle(fontSize:17,fontWeight:FontWeight.w800)),
          const SizedBox(height:14),
          FilledButton.icon(onPressed:scanBarcode,icon:const Icon(Icons.qr_code_scanner),label:const Text('افتح الماسح')),
        ]),
      ])),
      if(message!=null)Padding(padding:const EdgeInsets.all(14),child:Text(message!,style:const TextStyle(color:Colors.black54))),
      if(visionResult!=null)Container(
        margin:const EdgeInsets.fromLTRB(14,6,14,10),
        padding:const EdgeInsets.all(14),
        decoration:BoxDecoration(color:const Color(0xFFFFF7D6),borderRadius:BorderRadius.circular(14)),
        child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
          const Text('AI Estimate — يحتاج مراجعتك',style:TextStyle(fontWeight:FontWeight.w900)),
          const SizedBox(height:6),
          Text((visionResult!['description_ar']??'تم تحليل الصورة').toString()),
          const SizedBox(height:6),
          ...(((visionResult!['items'] as List?)??const []).take(4).map((x){
            final m=Map<String,dynamic>.from(x as Map);
            return Padding(
              padding:const EdgeInsets.only(top:4),
              child:Text('• ${m['name_ar']??m['name']??'صنف'} — ${m['estimated_calories']??'—'} kcal'),
            );
          })),
          const SizedBox(height:6),
          const Text('ما راح ينحفظ أي تقدير إلا بعد ما تختار أو تعدّل وتأكد.',style:TextStyle(fontSize:12,color:Colors.black54)),
        ]),
      ),
      if(results.isNotEmpty)SizedBox(height:220,child:ListView.builder(
        itemCount:results.length,padding:const EdgeInsets.fromLTRB(12,0,12,12),
        itemBuilder:(context,i){final f=results[i];return Card(child:ListTile(
          title:Text(f.nameAr?.isNotEmpty==true?f.nameAr!:f.name),
          subtitle:Text('${f.vendor} • ${f.nutrition.calories?.toStringAsFixed(0)??'—'} kcal'),
          trailing:const Icon(Icons.chevron_left),
          onTap:()=>openReview(f,tabs.index==1?'Text match • راجع قبل الحفظ':'Catalog • ${f.sourceConfidence??'—'}'),
        ));},
      )),
    ]),
  );


  Widget _searchTab()=>ListView(
    padding:const EdgeInsets.all(18),
    children:[
      TextField(
        controller:search,
        textInputAction:TextInputAction.search,
        onSubmitted:(_)=>doSearch(),
        decoration:const InputDecoration(
          hintText:'ابحث عن أكلة، منتج أو مطعم',
          prefixIcon:Icon(Icons.search),
        ),
      ),
      const SizedBox(height:12),
      SegmentedButton<String>(
        segments:const[
          ButtonSegment(value:'ALL',label:Text('الكل')),
          ButtonSegment(value:'RESTAURANT',label:Text('مطاعم')),
          ButtonSegment(value:'GROCERY',label:Text('منتجات')),
        ],
        selected:{searchType},
        onSelectionChanged:(s)=>setState(()=>searchType=s.first),
      ),
      const SizedBox(height:10),
      TextButton.icon(
        onPressed:()=>setState(()=>showFilters=!showFilters),
        icon:Icon(showFilters?Icons.tune:Icons.tune_outlined),
        label:Text(showFilters?'إخفاء الفلاتر':'فلاتر إضافية'),
      ),
      if(showFilters)...[
        const SizedBox(height:4),
        Row(children:[
          Expanded(child:TextField(
            controller:maxCalories,
            keyboardType:TextInputType.number,
            decoration:const InputDecoration(labelText:'أقصى سعرات'),
          )),
          const SizedBox(width:10),
          Expanded(child:TextField(
            controller:minProtein,
            keyboardType:TextInputType.number,
            decoration:const InputDecoration(labelText:'أقل بروتين g'),
          )),
        ]),
        const SizedBox(height:10),
        Row(children:[
          Expanded(child:TextField(
            controller:maxSodium,
            keyboardType:TextInputType.number,
            decoration:const InputDecoration(labelText:'أقصى صوديوم mg'),
          )),
          const SizedBox(width:10),
          Expanded(child:TextField(
            controller:maxPrice,
            keyboardType:TextInputType.number,
            decoration:const InputDecoration(labelText:'أقصى سعر AED'),
          )),
        ]),
        Align(
          alignment:AlignmentDirectional.centerEnd,
          child:TextButton(onPressed:clearFilters,child:const Text('مسح الفلاتر')),
        ),
      ],
      const SizedBox(height:12),
      FilledButton.icon(
        onPressed:loading?null:doSearch,
        icon:const Icon(Icons.search),
        label:const Text('ابحث'),
      ),
      const SizedBox(height:8),
      const Text(
        'يدعم البحث صيغًا متقاربة مثل برغر / برجر / burger.',
        style:TextStyle(fontSize:12,color:Colors.black54),
      ),
    ],
  );

  Widget _input(TextEditingController c,String hint,String label,Future<void> Function() action)=>ListView(
    padding:const EdgeInsets.all(18),children:[
      TextField(controller:c,minLines:2,maxLines:4,decoration:InputDecoration(hintText:hint)),
      const SizedBox(height:12),
      FilledButton(onPressed:action,child:Text(label)),
    ]);
}

class _BarcodeScannerScreen extends StatefulWidget{
  const _BarcodeScannerScreen();
  @override State<_BarcodeScannerScreen> createState()=>_BarcodeScannerScreenState();
}
class _BarcodeScannerScreenState extends State<_BarcodeScannerScreen>{
  bool done=false;
  @override Widget build(BuildContext context)=>Scaffold(
    appBar:AppBar(title:const Text('امسح الباركود')),
    body:MobileScanner(onDetect:(capture){
      if(done)return;
      final raw=capture.barcodes.isEmpty?null:capture.barcodes.first.rawValue;
      if(raw!=null&&raw.isNotEmpty){done=true;Navigator.pop(context,raw);}
    }),
  );
}
