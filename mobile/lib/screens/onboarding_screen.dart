
import 'package:flutter/material.dart';
import '../core/theme.dart';
import '../services/api_client.dart';
import 'home_screen.dart';

class OnboardingScreen extends StatefulWidget{
  const OnboardingScreen({super.key});
  @override State<OnboardingScreen> createState()=>_OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen>{
  int step=0;
  bool saving=false;
  String? error;

  final firstName=TextEditingController();
  DateTime dob=DateTime(1990,1,1);
  String gender='MALE';
  final height=TextEditingController(text:'175');
  final weight=TextEditingController(text:'80');
  final targetWeight=TextEditingController(text:'75');
  String goal='MAINTAIN';
  String activity='LIGHT';
  final budget=TextEditingController(text:'45');
  final Set<String> allergens={};
  final Set<String> prefs={};
  final Set<String> dislikes={};

  static const allergenOptions={
    'PEANUT':'الفول السوداني','MILK':'الحليب','EGG':'البيض','FISH':'السمك',
    'GLUTEN':'الغلوتين','SOY':'الصويا','SESAME':'السمسم','NUTS':'المكسرات',
  };
  static const foodOptions={
    'CHICKEN':'دجاج','BEEF':'لحم','FISH':'سمك','RICE':'رز','BURGERS':'برغر',
    'SALADS':'سلطات','YOGURT':'زبادي','OATS':'شوفان','TUNA':'تونة','EGGS':'بيض',
    'MUSHROOM':'مشروم','SPICY':'حار',
  };

  @override void dispose(){
    firstName.dispose();height.dispose();weight.dispose();targetWeight.dispose();budget.dispose();
    super.dispose();
  }

  Future<void> save()async{
    setState(()=>saving=true);
    try{
      final result=await WazenApi.instance.completeOnboarding({
        'first_name':firstName.text.trim().isEmpty?null:firstName.text.trim(),
        'date_of_birth':'${dob.year.toString().padLeft(4,'0')}-${dob.month.toString().padLeft(2,'0')}-${dob.day.toString().padLeft(2,'0')}',
        'gender':gender,
        'height_cm':double.parse(height.text),
        'weight_kg':double.parse(weight.text),
        'target_weight_kg':targetWeight.text.trim().isEmpty?null:double.parse(targetWeight.text),
        'goal_type':goal,
        'activity_level':activity,
        'daily_budget':budget.text.trim().isEmpty?null:double.parse(budget.text),
        'severe_allergens':allergens.toList(),
        'food_preferences':prefs.toList(),
        'disliked_foods':dislikes.toList(),
      });
      if(!mounted)return;
      final t=Map<String,dynamic>.from(result['targets'] as Map);
      await showDialog<void>(context:context,builder:(_)=>AlertDialog(
        title:const Text('خطة البداية جاهزة'),
        content:Text('هدف البداية ${t['target_calories']} سعرة • ${t['target_protein_g']}g بروتين\n\nتقدر تعدل أهدافك لاحقًا.'),
        actions:[TextButton(onPressed:()=>Navigator.pop(context),child:const Text('ابدأ'))],
      ));
      if(mounted)Navigator.pushAndRemoveUntil(context,MaterialPageRoute(builder:(_)=>const HomeScreen()),(_)=>false);
    }catch(e){if(mounted)setState(()=>error=e.toString());}
    finally{if(mounted)setState(()=>saving=false);}
  }

  @override Widget build(BuildContext context)=>Scaffold(
    appBar:AppBar(title:const Text('خل وازن يعرفك'),automaticallyImplyLeading:false),
    body:SafeArea(child:Column(children:[
      LinearProgressIndicator(value:(step+1)/4),
      Expanded(child:ListView(padding:const EdgeInsets.all(22),children:[
        Text('الخطوة ${step+1} من 4',style:const TextStyle(color:Colors.black45)),
        const SizedBox(height:8),
        if(step==0)_body(),
        if(step==1)_goal(),
        if(step==2)_safety(),
        if(step==3)_taste(),
        if(error!=null)Padding(padding:const EdgeInsets.only(top:12),child:Text(error!,style:const TextStyle(color:Colors.red))),
      ])),
      Padding(padding:const EdgeInsets.all(16),child:Row(children:[
        if(step>0)Expanded(child:OutlinedButton(onPressed:()=>setState(()=>step--),child:const Text('السابق'))),
        if(step>0)const SizedBox(width:10),
        Expanded(child:FilledButton(
          onPressed:saving?null:step<3?()=>setState(()=>step++):save,
          child:Text(saving?'جاري الحفظ...':step<3?'التالي':'أنشئ خطتي'),
        )),
      ])),
    ])),
  );

  Widget _title(String a,String b)=>Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
    Text(a,style:const TextStyle(fontSize:27,fontWeight:FontWeight.w900)),
    const SizedBox(height:6),Text(b,style:const TextStyle(color:Colors.black54,height:1.5)),const SizedBox(height:20),
  ]);

  Widget _body()=>Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
    _title('خلنا نبدأ بالأساس','هالمعلومات تساعدنا نحسب نقطة بداية مناسبة لك.'),
    TextField(controller:firstName,decoration:const InputDecoration(labelText:'الاسم الأول')),
    const SizedBox(height:12),
    ListTile(
      contentPadding:EdgeInsets.zero,
      title:const Text('تاريخ الميلاد'),
      subtitle:Text('${dob.day}/${dob.month}/${dob.year}'),
      trailing:const Icon(Icons.calendar_month),
      onTap:()async{
        final d=await showDatePicker(context:context,initialDate:dob,firstDate:DateTime(1940),lastDate:DateTime.now());
        if(d!=null)setState(()=>dob=d);
      },
    ),
    DropdownButtonFormField(value:gender,decoration:const InputDecoration(labelText:'الجنس'),items:const[
      DropdownMenuItem(value:'MALE',child:Text('ذكر')),DropdownMenuItem(value:'FEMALE',child:Text('أنثى')),
    ],onChanged:(v)=>setState(()=>gender=v!)),
    const SizedBox(height:12),
    Row(children:[
      Expanded(child:TextField(controller:height,keyboardType:TextInputType.number,decoration:const InputDecoration(labelText:'الطول cm'))),
      const SizedBox(width:10),
      Expanded(child:TextField(controller:weight,keyboardType:TextInputType.number,decoration:const InputDecoration(labelText:'الوزن kg'))),
    ]),
  ]);

  Widget _goal()=>Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
    _title('وش هدفك؟','وازن يستخدم الهدف والنشاط لحساب خطة بداية، وتقدر تغيرها متى ما تبي.'),
    DropdownButtonFormField(value:goal,decoration:const InputDecoration(labelText:'الهدف'),items:const[
      DropdownMenuItem(value:'LOSE',child:Text('نزول وزن')),
      DropdownMenuItem(value:'MAINTAIN',child:Text('المحافظة')),
      DropdownMenuItem(value:'GAIN',child:Text('زيادة وزن')),
    ],onChanged:(v)=>setState(()=>goal=v!)),
    const SizedBox(height:12),
    TextField(controller:targetWeight,keyboardType:TextInputType.number,decoration:const InputDecoration(labelText:'الوزن المستهدف kg')),
    const SizedBox(height:12),
    DropdownButtonFormField(value:activity,decoration:const InputDecoration(labelText:'نشاطك اليومي'),items:const[
      DropdownMenuItem(value:'SEDENTARY',child:Text('قليل الحركة')),
      DropdownMenuItem(value:'LIGHT',child:Text('خفيف')),
      DropdownMenuItem(value:'MODERATE',child:Text('متوسط')),
      DropdownMenuItem(value:'ACTIVE',child:Text('نشيط')),
      DropdownMenuItem(value:'VERY_ACTIVE',child:Text('نشيط جدًا')),
    ],onChanged:(v)=>setState(()=>activity=v!)),
    const SizedBox(height:12),
    TextField(controller:budget,keyboardType:TextInputType.number,decoration:const InputDecoration(labelText:'ميزانية الوجبة المفضلة AED')),
  ]);

  Widget _safety()=>Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
    _title('سلامتك أولًا','حدد فقط الحساسية الشديدة المؤكدة. وازن يستبعد الأطعمة التي تحتوي عليها بدل ما يخفض ترتيبها فقط.'),
    ...allergenOptions.entries.map((e)=>CheckboxListTile(
      contentPadding:EdgeInsets.zero,value:allergens.contains(e.key),title:Text(e.value),
      onChanged:(v)=>setState(()=>v==true?allergens.add(e.key):allergens.remove(e.key)),
    )),
    Container(padding:const EdgeInsets.all(14),decoration:BoxDecoration(color:WazenTheme.beige,borderRadius:BorderRadius.circular(14)),
      child:const Text('إذا عندك حدود غذائية يحددها طبيب أو أخصائي، تكون هي المرجع بدل الأهداف العامة المحسوبة هنا.',style:TextStyle(height:1.5))),
  ]);

  Widget _taste()=>Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
    _title('وش تحب عادة؟','هذي ما تمنع أكل معين؛ تساعد Wazen يرتب الخيارات الأقرب لذوقك.'),
    const Text('أشياء أحبها',style:TextStyle(fontWeight:FontWeight.w900)),
    const SizedBox(height:8),
    Wrap(spacing:8,runSpacing:8,children:foodOptions.entries.map((e)=>FilterChip(
      label:Text(e.value),selected:prefs.contains(e.key),
      onSelected:(v)=>setState(()=>v?prefs.add(e.key):prefs.remove(e.key)),
    )).toList()),
    const SizedBox(height:22),
    const Text('أشياء ما أفضلها',style:TextStyle(fontWeight:FontWeight.w900)),
    const SizedBox(height:8),
    Wrap(spacing:8,runSpacing:8,children:foodOptions.entries.map((e)=>FilterChip(
      label:Text(e.value),selected:dislikes.contains(e.key),
      onSelected:(v)=>setState(()=>v?dislikes.add(e.key):dislikes.remove(e.key)),
    )).toList()),
  ]);
}
