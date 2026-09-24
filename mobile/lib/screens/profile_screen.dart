
import 'package:flutter/material.dart';
import '../core/theme.dart';
import '../services/api_client.dart';
import 'home_screen.dart';
import 'food_log_screen.dart';
import 'craving_screen.dart';
import 'auth_screen.dart';
import 'plan_screen.dart';

class ProfileScreen extends StatefulWidget{
  const ProfileScreen({super.key});
  @override State<ProfileScreen> createState()=>_ProfileScreenState();
}
class _ProfileScreenState extends State<ProfileScreen>{
  Map<String,dynamic>? user;
  Map<String,dynamic>? insights;
  List<Map<String,dynamic>> goalHistory=[];
  Map<String,String> explicitPreferences={};
  bool loading=true,saving=false;
  String? error;

  final weight=TextEditingController();
  final targetWeight=TextEditingController();
  final budget=TextEditingController();
  final calories=TextEditingController();
  final protein=TextEditingController();
  final carbs=TextEditingController();
  final fat=TextEditingController();
  String goal='MAINTAIN';
  String activity='LIGHT';
  Set<String> allergies={};
  Set<String> prefs={};
  Set<String> dislikes={};

  static const foodOptions={
    'CHICKEN':'دجاج','BEEF':'لحم','FISH':'سمك','RICE':'رز','BURGERS':'برغر',
    'SALADS':'سلطات','YOGURT':'زبادي','OATS':'شوفان','TUNA':'تونة','EGGS':'بيض',
    'MUSHROOM':'مشروم','SPICY':'حار',
  };
  static const allergenOptions={
    'PEANUT':'الفول السوداني','MILK':'الحليب','EGG':'البيض','FISH':'السمك',
    'GLUTEN':'الغلوتين','SOY':'الصويا','SESAME':'السمسم','NUTS':'المكسرات',
  };

  @override void initState(){super.initState();load();}
  @override void dispose(){
    weight.dispose();targetWeight.dispose();budget.dispose();calories.dispose();protein.dispose();carbs.dispose();fat.dispose();
    super.dispose();
  }

  Future<void> load()async{
    setState(()=>loading=true);
    try{
      final results=await Future.wait([WazenApi.instance.me(),WazenApi.instance.profileInsights(),WazenApi.instance.goalHistory(limit:8),WazenApi.instance.preferenceSettings()]);
      final u=Map<String,dynamic>.from(results[0] as Map);
      final p=Map<String,dynamic>.from(u['profile'] as Map);
      if(!mounted)return;
      setState((){
        user=u;
        insights=Map<String,dynamic>.from(results[1] as Map);
        goalHistory=List<Map<String,dynamic>>.from(results[2] as List);
        explicitPreferences={
          for(final row in List<Map<String,dynamic>>.from(results[3] as List))
            if((row['target_type']??'').toString()=='TERM')
              (row['target_value']??'').toString():(row['level']??'NEUTRAL').toString(),
        };
        weight.text='${p['weight_kg']??''}';
        targetWeight.text='${p['target_weight_kg']??''}';
        budget.text='${p['daily_budget']??''}';
        calories.text='${p['target_calories']??''}';
        protein.text='${p['target_protein_g']??''}';
        carbs.text='${p['target_carbs_g']??''}';
        fat.text='${p['target_fat_g']??''}';
        goal=(p['goal_type']??'MAINTAIN').toString();
        activity=(p['activity_level']??'LIGHT').toString();
        allergies=Set<String>.from((p['severe_allergens'] as List? ?? const []).map((x)=>x.toString()));
        prefs=Set<String>.from((p['food_preferences'] as List? ?? const []).map((x)=>x.toString()));
        dislikes=Set<String>.from((p['disliked_foods'] as List? ?? const []).map((x)=>x.toString()));
      });
    }catch(e){if(mounted)setState(()=>error=e.toString());}
    finally{if(mounted)setState(()=>loading=false);}
  }

  double? _n(TextEditingController c)=>double.tryParse(c.text.trim());

  Future<void> saveProfile()async{
    setState(()=>saving=true);
    try{
      await WazenApi.instance.updateProfile({
        'weight_kg':_n(weight),'target_weight_kg':_n(targetWeight),'daily_budget':_n(budget),
        'target_calories':_n(calories),'target_protein_g':_n(protein),
        'target_carbs_g':_n(carbs),'target_fat_g':_n(fat),
        'goal_type':goal,'activity_level':activity,
        'severe_allergens':allergies.toList(),'food_preferences':prefs.toList(),'disliked_foods':dislikes.toList(),
      });
      if(mounted){ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content:Text('تم حفظ التغييرات.')));await load();}
    }catch(e){if(mounted)setState(()=>error=e.toString());}
    finally{if(mounted)setState(()=>saving=false);}
  }

  Future<void> recalc()async{
    setState(()=>saving=true);
    try{
      final r=await WazenApi.instance.recalculatePlan({
        'weight_kg':_n(weight),'target_weight_kg':_n(targetWeight),'goal_type':goal,'activity_level':activity,
      });
      if(!mounted)return;
      final t=Map<String,dynamic>.from(r['targets'] as Map);
      await showDialog<void>(context:context,builder:(_)=>AlertDialog(
        title:const Text('تم تحديث الخطة'),
        content:Text('السعرات ${t['target_calories']} • البروتين ${t['target_protein_g']}g • الكربوهيدرات ${t['target_carbs_g']}g • الدهون ${t['target_fat_g']}g'),
        actions:[TextButton(onPressed:()=>Navigator.pop(context),child:const Text('تمام'))],
      ));
      await load();
    }catch(e){if(mounted)setState(()=>error=e.toString());}
    finally{if(mounted)setState(()=>saving=false);}
  }

  @override Widget build(BuildContext context)=>Scaffold(
    appBar:AppBar(
      title:const Text('حسابي وخطتي'),
      actions:[IconButton(onPressed:load,icon:const Icon(Icons.refresh_rounded))]
    ),
    bottomNavigationBar:NavigationBar(
      selectedIndex:4,
      onDestinationSelected:(i){
        if(i==0)Navigator.pushReplacement(context,MaterialPageRoute(builder:(_)=>const HomeScreen()));
        if(i==1)Navigator.pushReplacement(context,MaterialPageRoute(builder:(_)=>const FoodLogScreen()));
        if(i==2)Navigator.push(context,MaterialPageRoute(builder:(_)=>const CravingScreen()));
        if(i==3)Navigator.pushReplacement(context,MaterialPageRoute(builder:(_)=>const PlanScreen()));
      },
      destinations:const[
        NavigationDestination(icon:Icon(Icons.home_outlined),label:'الرئيسية'),
        NavigationDestination(icon:Icon(Icons.today_outlined),label:'يومي'),
        NavigationDestination(icon:Icon(Icons.restaurant_menu_outlined),label:'اكتشف'),
        NavigationDestination(icon:Icon(Icons.calendar_month_outlined),label:'خطتي'),
        NavigationDestination(icon:Icon(Icons.person_outline),selectedIcon:Icon(Icons.person),label:'حسابي'),
      ],
    ),
    body:RefreshIndicator(
      onRefresh:load,
      child:ListView(padding:const EdgeInsets.all(20),children:[
        if(loading)const LinearProgressIndicator(minHeight:2),
        if(error!=null)Text(error!,style:const TextStyle(color:Colors.red)),
        Text(user?['first_name']?.toString().isNotEmpty==true?'هلا ${user!['first_name']}':'حسابي',style:const TextStyle(fontSize:28,fontWeight:FontWeight.w900)),
        const SizedBox(height:18),
        _section('جسمي وهدفي',[
          Row(children:[
            Expanded(child:_field(weight,'الوزن kg')),const SizedBox(width:10),
            Expanded(child:_field(targetWeight,'الهدف kg')),
          ]),
          const SizedBox(height:12),
          DropdownButtonFormField(value:goal,decoration:const InputDecoration(labelText:'الهدف'),items:const[
            DropdownMenuItem(value:'LOSE',child:Text('نزول وزن')),
            DropdownMenuItem(value:'MAINTAIN',child:Text('المحافظة')),
            DropdownMenuItem(value:'GAIN',child:Text('زيادة وزن')),
          ],onChanged:(v)=>setState(()=>goal=v!)),
          const SizedBox(height:12),
          DropdownButtonFormField(value:activity,decoration:const InputDecoration(labelText:'النشاط'),items:const[
            DropdownMenuItem(value:'SEDENTARY',child:Text('قليل الحركة')),
            DropdownMenuItem(value:'LIGHT',child:Text('خفيف')),
            DropdownMenuItem(value:'MODERATE',child:Text('متوسط')),
            DropdownMenuItem(value:'ACTIVE',child:Text('نشيط')),
            DropdownMenuItem(value:'VERY_ACTIVE',child:Text('نشيط جدًا')),
          ],onChanged:(v)=>setState(()=>activity=v!)),
          const SizedBox(height:12),
          _field(budget,'ميزانية الوجبة AED'),
          const SizedBox(height:12),
          OutlinedButton.icon(onPressed:saving?null:recalc,icon:const Icon(Icons.calculate_outlined),label:const Text('أعد حساب خطتي من بياناتي')),
        ]),
        const SizedBox(height:16),
        _section('أهدافي اليومية',[
          Row(children:[Expanded(child:_field(calories,'السعرات')),const SizedBox(width:10),Expanded(child:_field(protein,'البروتين g'))]),
          const SizedBox(height:10),
          Row(children:[Expanded(child:_field(carbs,'الكربوهيدرات g')),const SizedBox(width:10),Expanded(child:_field(fat,'الدهون g'))]),
          const SizedBox(height:8),
          const Text('تقدر تعدل الأهداف يدويًا. وإذا استخدمت إعادة الحساب، وازن يبني نقطة بداية جديدة من بيانات جسمك ونشاطك.',style:TextStyle(color:Colors.black54,height:1.4)),
        ]),
        const SizedBox(height:16),
        _section('سلامتي',[
          const Text('الحساسية الشديدة',style:TextStyle(fontWeight:FontWeight.w900)),
          const SizedBox(height:8),
          Wrap(spacing:8,runSpacing:8,children:allergenOptions.entries.map((e)=>FilterChip(
            label:Text(e.value),selected:allergies.contains(e.key),
            onSelected:(v)=>setState(()=>v?allergies.add(e.key):allergies.remove(e.key)),
          )).toList()),
          const SizedBox(height:8),
          const Text('هذه فقط هي التي تعمل كاستبعاد تلقائي. لا نستخدم التفضيلات بدل قواعد السلامة.',style:TextStyle(color:Colors.black54)),
        ]),
        const SizedBox(height:16),
        _section('ذوقي',[
          const Text('حدد درجة تفضيلك. «لا تعرضه» يخفي هذا النوع من توصياتك، بينما باقي الدرجات تؤثر على الترتيب فقط.',style:TextStyle(color:Colors.black54,height:1.4)),
          const SizedBox(height:12),
          ...foodOptions.entries.map((e)=>_preferenceRow(e.key,e.value)),
        ]),
        const SizedBox(height:16),
        _goalHistorySection(),
        const SizedBox(height:16),
        _why(),
        const SizedBox(height:18),
        FilledButton(onPressed:saving?null:saveProfile,child:Text(saving?'جاري الحفظ...':'حفظ التغييرات')),
        const SizedBox(height:10),
        TextButton.icon(
          onPressed:()async{
            await WazenApi.instance.logout();
            if(context.mounted)Navigator.pushAndRemoveUntil(context,MaterialPageRoute(builder:(_)=>const AuthScreen()),(_)=>false);
          },
          icon:const Icon(Icons.logout),label:const Text('تسجيل الخروج')
        ),
        const SizedBox(height:40),
      ]),
    ),
  );


  Future<void> setPreferenceLevel(String term,String level) async {
    final previous=explicitPreferences[term]??(prefs.contains(term)?'LIKE':dislikes.contains(term)?'DISLIKE':'NEUTRAL');
    setState(()=>explicitPreferences[term]=level);
    if(level=='LOVE'||level=='LIKE'){
      prefs.add(term);dislikes.remove(term);
    }else if(level=='DISLIKE'){
      dislikes.add(term);prefs.remove(term);
    }else{
      prefs.remove(term);dislikes.remove(term);
    }
    try{
      await WazenApi.instance.setPreference(targetType:'TERM',targetValue:term,level:level);
      await WazenApi.instance.updateProfile({
        'food_preferences':prefs.toList(),
        'disliked_foods':dislikes.toList(),
      });
    }catch(e){
      if(mounted){
        setState(()=>explicitPreferences[term]=previous);
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content:Text(e.toString())));
      }
    }
  }

  Widget _preferenceRow(String key,String label){
    final level=explicitPreferences[key]??(prefs.contains(key)?'LIKE':dislikes.contains(key)?'DISLIKE':'NEUTRAL');
    const labels={
      'LOVE':'أحبه جدًا',
      'LIKE':'أحبه',
      'NEUTRAL':'عادي',
      'DISLIKE':'ما أفضل',
      'NEVER_SHOW':'لا تعرضه',
    };
    IconData icon;
    switch(level){
      case 'LOVE':icon=Icons.favorite;break;
      case 'LIKE':icon=Icons.thumb_up_alt_outlined;break;
      case 'DISLIKE':icon=Icons.thumb_down_alt_outlined;break;
      case 'NEVER_SHOW':icon=Icons.visibility_off_outlined;break;
      default:icon=Icons.remove_circle_outline;
    }
    return Container(
      margin:const EdgeInsets.only(bottom:8),
      padding:const EdgeInsets.symmetric(horizontal:12,vertical:6),
      decoration:BoxDecoration(color:Colors.white,borderRadius:BorderRadius.circular(14),border:Border.all(color:const Color(0xFFE7EAE7))),
      child:Row(children:[
        Icon(icon,color:level=='NEVER_SHOW'?Colors.redAccent:WazenTheme.greenDark),
        const SizedBox(width:10),
        Expanded(child:Text(label,style:const TextStyle(fontWeight:FontWeight.w700))),
        PopupMenuButton<String>(
          initialValue:level,
          onSelected:(v)=>setPreferenceLevel(key,v),
          itemBuilder:(_)=>labels.entries.map((x)=>PopupMenuItem(value:x.key,child:Text(x.value))).toList(),
          child:Container(
            padding:const EdgeInsets.symmetric(horizontal:10,vertical:7),
            decoration:BoxDecoration(color:const Color(0xFFF4F6F2),borderRadius:BorderRadius.circular(10)),
            child:Row(mainAxisSize:MainAxisSize.min,children:[
              Text(labels[level]??level,style:const TextStyle(fontSize:12,fontWeight:FontWeight.w700)),
              const SizedBox(width:4),
              const Icon(Icons.expand_more,size:16),
            ]),
          ),
        ),
      ]),
    );
  }

  Widget _field(TextEditingController c,String label)=>TextField(controller:c,keyboardType:TextInputType.number,decoration:InputDecoration(labelText:label));

  Widget _section(String title,List<Widget> children)=>Container(
    padding:const EdgeInsets.all(18),
    decoration:BoxDecoration(color:const Color(0xFFF7F8F5),borderRadius:BorderRadius.circular(20)),
    child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
      Text(title,style:const TextStyle(fontSize:19,fontWeight:FontWeight.w900)),
      const SizedBox(height:14),...children,
    ]),
  );


  Widget _goalHistorySection(){
    String goalLabel(String value){
      switch(value){
        case 'LOSE':return 'نزول وزن';
        case 'GAIN':return 'زيادة وزن';
        default:return 'المحافظة';
      }
    }
    if(goalHistory.isEmpty){
      return _section('سجل خطتي',[
        const Text('أول تعديل جوهري على هدفك أو خطتك بيظهر هنا.',style:TextStyle(color:Colors.black54,height:1.4)),
      ]);
    }
    return _section('سجل خطتي',[
      ...goalHistory.take(6).map((row){
        final snap=Map<String,dynamic>.from((row['snapshot'] as Map?)??const{});
        final created=(row['created_at']??'').toString();
        final date=created.length>=10?created.substring(0,10):created;
        final reason=(row['reason']??'').toString();
        return Container(
          margin:const EdgeInsets.only(bottom:10),
          padding:const EdgeInsets.all(12),
          decoration:BoxDecoration(color:Colors.white,borderRadius:BorderRadius.circular(14),border:Border.all(color:const Color(0xFFE7EAE7))),
          child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
            Row(children:[
              Expanded(child:Text(goalLabel((snap['goal_type']??'MAINTAIN').toString()),style:const TextStyle(fontWeight:FontWeight.w900))),
              Text(date,style:const TextStyle(fontSize:11,color:Colors.black45)),
            ]),
            const SizedBox(height:6),
            Text(
              'الوزن ${snap['weight_kg']??'—'} kg • الهدف ${snap['target_weight_kg']??'—'} kg • ${snap['target_calories']??'—'} سعرة',
              style:const TextStyle(fontSize:12,color:Colors.black54,height:1.4),
            ),
            const SizedBox(height:4),
            Text(
              reason=='ONBOARDING'?'بداية الخطة':reason=='RECALCULATE'?'إعادة حساب الخطة':'تحديث الخطة',
              style:const TextStyle(fontSize:11,color:WazenTheme.greenDark,fontWeight:FontWeight.w700),
            ),
          ]),
        );
      }),
    ]);
  }

  Widget _why(){
    final i=insights;
    final positive=(i?['learned_positive'] as List?)??const[];
    final negative=(i?['learned_negative'] as List?)??const[];
    return Container(
      padding:const EdgeInsets.all(18),
      decoration:BoxDecoration(color:WazenTheme.beige,borderRadius:BorderRadius.circular(20)),
      child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
        const Row(children:[Icon(Icons.psychology_alt_outlined,color:WazenTheme.greenDark),SizedBox(width:8),Expanded(child:Text('ليش وازن يقترح لي هالأشياء؟',style:TextStyle(fontSize:18,fontWeight:FontWeight.w900)))]),
        const SizedBox(height:12),
        const Text('وازن يرتب الخيارات من أكثر من إشارة، مو من ذوقك بس:',style:TextStyle(height:1.4)),
        const SizedBox(height:8),
        ...(((i?['explanation_ar'] as List?)??const []).map((x)=>Padding(
          padding:const EdgeInsets.only(bottom:6),child:Text('• $x',style:const TextStyle(height:1.4)),
        ))),
        if(positive.isNotEmpty)...[
          const SizedBox(height:10),
          Text('تعلمنا إيجابيًا من ${positive.length} اختيار/نمط متكرر.',style:const TextStyle(fontWeight:FontWeight.w700)),
        ],
        if(negative.isNotEmpty)...[
          const SizedBox(height:6),
          Text('وفي ${negative.length} اختيار قلت لنا إنه مو مناسب لك.',style:const TextStyle(fontWeight:FontWeight.w700)),
        ],
      ]),
    );
  }
}
