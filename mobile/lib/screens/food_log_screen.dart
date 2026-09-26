
import 'package:flutter/material.dart';
import '../core/theme.dart';
import '../models/api_models.dart';
import '../services/api_client.dart';
import 'home_screen.dart';
import 'craving_screen.dart';
import 'add_food_screen.dart';
import 'profile_screen.dart';
import 'plan_screen.dart';

class FoodLogScreen extends StatefulWidget {
  const FoodLogScreen({super.key});
  @override State<FoodLogScreen> createState()=>_FoodLogScreenState();
}

class _FoodLogScreenState extends State<FoodLogScreen>{
  FoodLogDay? day;
  List<Map<String,dynamic>> favorites=[];
  bool loading=true;
  String? error;

  static const mealOrder=['BREAKFAST','LUNCH','DINNER','SNACK'];
  static const mealNames={
    'BREAKFAST':'الفطور','LUNCH':'الغداء','DINNER':'العشاء','SNACK':'السناك',
  };

  @override void initState(){super.initState();load();}

  Future<void> load() async{
    setState((){loading=true;error=null;});
    try{
      final results=await Future.wait([
        WazenApi.instance.foodLogToday(),
        WazenApi.instance.favoriteMeals(),
      ]);
      if(mounted)setState((){
        day=results[0] as FoodLogDay;
        favorites=List<Map<String,dynamic>>.from(results[1] as List);
      });
    }catch(e){if(mounted)setState(()=>error=e.toString());}
    finally{if(mounted)setState(()=>loading=false);}
  }

  Future<void> remove(FoodLogItem item) async{
    final ok=await showDialog<bool>(context:context,builder:(_)=>AlertDialog(
      title:const Text('حذف الوجبة؟'),
      content:Text('بنحذف "${item.foodName}" من يومك ونعيد حساب المتبقي.'),
      actions:[
        TextButton(onPressed:()=>Navigator.pop(context,false),child:const Text('إلغاء')),
        FilledButton(onPressed:()=>Navigator.pop(context,true),child:const Text('حذف')),
      ],
    ));
    if(ok!=true)return;
    try{final d=await WazenApi.instance.deleteFoodLog(item.id);if(mounted)setState(()=>day=d);}
    catch(e){if(mounted)setState(()=>error=e.toString());}
  }

  Future<void> edit(FoodLogItem item) async{
    final cal=TextEditingController(text:item.calories.toStringAsFixed(0));
    final protein=TextEditingController(text:item.proteinG.toStringAsFixed(1));
    String meal=item.mealType;
    final result=await showDialog<Map<String,dynamic>>(context:context,builder:(ctx)=>StatefulBuilder(
      builder:(ctx,setLocal)=>AlertDialog(
        title:const Text('تعديل السجل'),
        content:SingleChildScrollView(child:Column(mainAxisSize:MainAxisSize.min,children:[
          DropdownButtonFormField<String>(
            value:meal,
            items:mealOrder.map((x)=>DropdownMenuItem(value:x,child:Text(mealNames[x]!))).toList(),
            onChanged:(v){if(v!=null)setLocal(()=>meal=v);},
            decoration:const InputDecoration(labelText:'الوجبة'),
          ),
          const SizedBox(height:12),
          TextField(controller:cal,keyboardType:TextInputType.number,decoration:const InputDecoration(labelText:'السعرات')),
          const SizedBox(height:12),
          TextField(controller:protein,keyboardType:TextInputType.number,decoration:const InputDecoration(labelText:'البروتين g')),
        ])),
        actions:[
          TextButton(onPressed:()=>Navigator.pop(ctx),child:const Text('إلغاء')),
          FilledButton(onPressed:()=>Navigator.pop(ctx,{
            'meal':meal,
            'calories':double.tryParse(cal.text),
            'protein':double.tryParse(protein.text),
          }),child:const Text('حفظ')),
        ],
      ),
    ));
    if(result==null)return;
    try{
      final d=await WazenApi.instance.updateFoodLog(item.id,mealType:result['meal'],calories:result['calories'],proteinG:result['protein']);
      if(mounted)setState(()=>day=d);
    }catch(e){if(mounted)setState(()=>error=e.toString());}
  }


  Future<void> duplicate(FoodLogItem item) async{
    try{
      final d=await WazenApi.instance.duplicateFoodLog(item.id);
      if(mounted){
        setState(()=>day=d);
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content:Text('تم نسخ الوجبة.')));
      }
    }catch(e){if(mounted)setState(()=>error=e.toString());}
  }

  Future<void> favorite(FoodLogItem item) async{
    try{
      final result=await WazenApi.instance.favoriteFoodLog(item.id);
      if(!mounted)return;
      final created=result['created']==true;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content:Text(created?'تم حفظ الوجبة في المفضلة.':'هذه الوجبة موجودة في المفضلة بالفعل.'),
      ));
      await load();
    }catch(e){if(mounted)setState(()=>error=e.toString());}
  }

  Future<void> logFavorite(Map<String,dynamic> fav) async{
    try{
      final d=await WazenApi.instance.logFavoriteMeal(
        fav['id'].toString(),
        mealType:(fav['default_meal_type']??'SNACK').toString(),
      );
      if(mounted){
        setState(()=>day=d);
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content:Text('تمت إضافة الوجبة المفضلة ليومك.')));
      }
    }catch(e){if(mounted)setState(()=>error=e.toString());}
  }

  @override Widget build(BuildContext context){
    final d=day;
    return Scaffold(
      appBar:AppBar(title:const Text('يومي')),
      bottomNavigationBar:NavigationBar(
        selectedIndex:1,
        onDestinationSelected:(i)async{
          if(i==0){
            Navigator.pushReplacement(context,MaterialPageRoute(builder:(_)=>const HomeScreen()));
          }else if(i==2){
            final changed=await Navigator.push<bool>(context,MaterialPageRoute(builder:(_)=>const CravingScreen()));
            if(changed==true&&mounted)load();
          }else if(i==3){
            Navigator.pushReplacement(context,MaterialPageRoute(builder:(_)=>const PlanScreen()));
          }else if(i==4){
            Navigator.pushReplacement(context,MaterialPageRoute(builder:(_)=>const ProfileScreen()));
          }
        },
        destinations:const[
          NavigationDestination(icon:Icon(Icons.home_outlined),selectedIcon:Icon(Icons.home_rounded),label:'الرئيسية'),
          NavigationDestination(icon:Icon(Icons.today_outlined),selectedIcon:Icon(Icons.today_rounded),label:'يومي'),
          NavigationDestination(icon:Icon(Icons.restaurant_menu_outlined),selectedIcon:Icon(Icons.restaurant_menu_rounded),label:'اكتشف'),
          NavigationDestination(icon:Icon(Icons.calendar_month_outlined),selectedIcon:Icon(Icons.calendar_month_rounded),label:'خطتي'),
          NavigationDestination(icon:Icon(Icons.person_outline),selectedIcon:Icon(Icons.person),label:'حسابي'),
        ],
      ),
      body:RefreshIndicator(
        onRefresh:load,
        child:ListView(
          physics:const AlwaysScrollableScrollPhysics(),
          padding:const EdgeInsets.fromLTRB(20,8,20,32),
          children:[
            if(loading)const LinearProgressIndicator(minHeight:2),
            if(error!=null)Padding(padding:const EdgeInsets.only(bottom:12),child:Text(error!,style:const TextStyle(color:Colors.red))),
            if(d!=null)...[
              _summary(d),
              if(favorites.isNotEmpty)...[
                const SizedBox(height:16),
                _favoritesSection(),
              ],
              const SizedBox(height:20),
              ...mealOrder.map((meal)=>_section(meal,d.items.where((x)=>x.mealType==meal).toList())),
            ],
          ],
        ),
      ),
      floatingActionButton:FloatingActionButton.extended(
        onPressed:()async{
          final changed=await Navigator.push<bool>(context,MaterialPageRoute(builder:(_)=>const AddFoodScreen()));
          if(changed==true&&mounted)load();
        },
        icon:const Icon(Icons.add),
        label:const Text('أضف أكل'),
      ),
    );
  }

  Widget _summary(FoodLogDay d){
    final consumed=(d.totals['calories'] as num? ?? 0).toDouble();
    final protein=(d.totals['protein_g'] as num? ?? 0).toDouble();
    return Container(
      padding:const EdgeInsets.all(18),
      decoration:BoxDecoration(color:WazenTheme.beige,borderRadius:BorderRadius.circular(22)),
      child:Column(children:[
        Row(children:[
          Expanded(child:_metric('أكلت',consumed,'kcal')),
          Expanded(child:_metric('باقي',d.dailyState.remainingCalories,'kcal')),
          Expanded(child:_metric('بروتين',protein,'g')),
        ]),
        const SizedBox(height:10),
        Text('باقي لك ${d.dailyState.proteinGapG.toStringAsFixed(0)}g بروتين اليوم',style:const TextStyle(color:Colors.black54)),
      ]),
    );
  }

  Widget _section(String meal,List<FoodLogItem> items){
    final total=items.fold<double>(0,(s,x)=>s+x.calories);
    return Padding(
      padding:const EdgeInsets.only(bottom:18),
      child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
        Row(children:[
          Expanded(child:Text(mealNames[meal]!,style:const TextStyle(fontSize:18,fontWeight:FontWeight.w900))),
          Text('${total.toStringAsFixed(0)} kcal',style:const TextStyle(color:Colors.black54)),
        ]),
        const SizedBox(height:8),
        if(items.isEmpty)
          Container(
            width:double.infinity,padding:const EdgeInsets.all(14),
            decoration:BoxDecoration(color:const Color(0xFFF6F7F3),borderRadius:BorderRadius.circular(14)),
            child:const Text('ما سجلت شيء هنا بعد.',style:TextStyle(color:Colors.black45)),
          ),
        ...items.map((x)=>Card(
          margin:const EdgeInsets.only(bottom:8),
          child:ListTile(
            title:Text(x.foodName,style:const TextStyle(fontWeight:FontWeight.w700)),
            subtitle:Text('${x.calories.toStringAsFixed(0)} kcal • ${x.proteinG.toStringAsFixed(1)}g بروتين'),
            trailing:PopupMenuButton<String>(
              onSelected:(v){
                if(v=='edit')edit(x);
                if(v=='duplicate')duplicate(x);
                if(v=='favorite')favorite(x);
                if(v=='delete')remove(x);
              },
              itemBuilder:(_)=>const[
                PopupMenuItem(value:'edit',child:Text('تعديل')),
                PopupMenuItem(value:'duplicate',child:Text('نسخ الوجبة')),
                PopupMenuItem(value:'favorite',child:Text('حفظ كمفضلة')),
                PopupMenuItem(value:'delete',child:Text('حذف')),
              ],
            ),
          ),
        )),
      ]),
    );
  }


  Widget _favoritesSection()=>Container(
    padding:const EdgeInsets.all(14),
    decoration:BoxDecoration(
      color:const Color(0xFFF7F8F5),
      borderRadius:BorderRadius.circular(18),
    ),
    child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
      const Row(children:[
        Icon(Icons.star_rounded,color:WazenTheme.greenDark),
        SizedBox(width:6),
        Text('المفضلة',style:TextStyle(fontSize:17,fontWeight:FontWeight.w900)),
      ]),
      const SizedBox(height:10),
      SizedBox(
        height:84,
        child:ListView.separated(
          scrollDirection:Axis.horizontal,
          itemCount:favorites.length,
          separatorBuilder:(_,__)=>const SizedBox(width:8),
          itemBuilder:(_,i){
            final f=favorites[i];
            return InkWell(
              borderRadius:BorderRadius.circular(14),
              onTap:()=>logFavorite(f),
              child:Container(
                width:165,
                padding:const EdgeInsets.all(12),
                decoration:BoxDecoration(
                  color:Colors.white,
                  borderRadius:BorderRadius.circular(14),
                  border:Border.all(color:const Color(0xFFE3E7E3)),
                ),
                child:Column(
                  crossAxisAlignment:CrossAxisAlignment.start,
                  mainAxisAlignment:MainAxisAlignment.center,
                  children:[
                    Text(
                      (f['food_name']??'وجبة').toString(),
                      maxLines:1,
                      overflow:TextOverflow.ellipsis,
                      style:const TextStyle(fontWeight:FontWeight.w800),
                    ),
                    const SizedBox(height:5),
                    Text(
                      '0 kcal • اضغط للإضافة',
                      style:const TextStyle(fontSize:11,color:Colors.black54),
                    ),
                  ],
                ),
              ),
            );
          },
        ),
      ),
    ]),
  );

  Widget _metric(String label,double value,String unit)=>Column(children:[
    Text(label,style:const TextStyle(fontSize:12,color:Colors.black54)),
    const SizedBox(height:4),
    Text('${value.toStringAsFixed(0)} $unit',style:const TextStyle(fontSize:18,fontWeight:FontWeight.w900,color:WazenTheme.greenDark)),
  ]);
}
