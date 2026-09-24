import 'package:flutter/material.dart';
import '../core/theme.dart';
import '../models/api_models.dart';
import '../services/api_client.dart';
import 'home_screen.dart';
import 'food_log_screen.dart';
import 'craving_screen.dart';
import 'profile_screen.dart';

class PlanScreen extends StatefulWidget {
  const PlanScreen({super.key});
  @override
  State<PlanScreen> createState()=>_PlanScreenState();
}

class _PlanScreenState extends State<PlanScreen> with SingleTickerProviderStateMixin {
  WeeklyPlan? plan;
  ProgressSummary? progress;
  bool loading=true;
  bool acting=false;
  String? error;
  int selectedDay=0;
  String range='week';
  late final TabController tabs;

  static const mealNames={
    'BREAKFAST':'الفطور',
    'LUNCH':'الغداء',
    'DINNER':'العشاء',
    'SNACK':'سناك',
  };
  static const dayNames=['الاثنين','الثلاثاء','الأربعاء','الخميس','الجمعة','السبت','الأحد'];

  @override
  void initState(){
    super.initState();
    tabs=TabController(length:2,vsync:this);
    load();
  }

  @override
  void dispose(){
    tabs.dispose();
    super.dispose();
  }

  Future<void> load() async {
    setState((){loading=true;error=null;});
    try{
      final results=await Future.wait([
        WazenApi.instance.weeklyPlan(),
        WazenApi.instance.progress(range),
      ]);
      if(!mounted)return;
      final p=results[0] as WeeklyPlan;
      final now=DateTime.now();
      var idx=p.days.indexWhere((d)=>d.date.year==now.year&&d.date.month==now.month&&d.date.day==now.day);
      if(idx<0)idx=0;
      setState((){
        plan=p;
        progress=results[1] as ProgressSummary;
        selectedDay=idx;
      });
    }catch(e){
      if(mounted)setState(()=>error=e.toString());
    }finally{
      if(mounted)setState(()=>loading=false);
    }
  }

  Future<void> changeRange(String value) async {
    setState((){range=value;loading=true;});
    try{
      final p=await WazenApi.instance.progress(value);
      if(mounted)setState(()=>progress=p);
    }catch(e){
      if(mounted)setState(()=>error=e.toString());
    }finally{
      if(mounted)setState(()=>loading=false);
    }
  }

  Future<void> rebalanceSelected() async {
    final p=plan;
    if(p==null||p.days.isEmpty)return;
    setState(()=>acting=true);
    try{
      final next=await WazenApi.instance.rebalancePlanDay(p.days[selectedDay].date);
      if(mounted){
        setState(()=>plan=next);
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content:Text('تمت إعادة موازنة هذا اليوم.')));
      }
    }catch(e){
      if(mounted)setState(()=>error=e.toString());
    }finally{
      if(mounted)setState(()=>acting=false);
    }
  }

  Future<void> regenerateWeek() async {
    setState(()=>acting=true);
    try{
      final next=await WazenApi.instance.regenerateWeeklyPlan();
      if(mounted){
        setState((){plan=next;selectedDay=0;});
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content:Text('تم إنشاء خطة أسبوعية جديدة.')));
      }
    }catch(e){
      if(mounted)setState(()=>error=e.toString());
    }finally{
      if(mounted)setState(()=>acting=false);
    }
  }

  @override
  Widget build(BuildContext context)=>Scaffold(
    appBar:AppBar(
      title:const Text('خطتي'),
      actions:[
        PopupMenuButton<String>(
          onSelected:(v){if(v=='new')regenerateWeek();},
          itemBuilder:(_)=>const[
            PopupMenuItem(value:'new',child:Text('إنشاء خطة أسبوعية جديدة')),
          ],
        ),
      ],
      bottom:TabBar(
        controller:tabs,
        tabs:const[
          Tab(text:'الخطة الأسبوعية'),
          Tab(text:'تقدمك'),
        ],
      ),
    ),
    bottomNavigationBar:NavigationBar(
      selectedIndex:3,
      onDestinationSelected:(i)async{
        if(i==0)Navigator.pushReplacement(context,MaterialPageRoute(builder:(_)=>const HomeScreen()));
        if(i==1)Navigator.pushReplacement(context,MaterialPageRoute(builder:(_)=>const FoodLogScreen()));
        if(i==2)await Navigator.push(context,MaterialPageRoute(builder:(_)=>const CravingScreen()));
        if(i==4)Navigator.pushReplacement(context,MaterialPageRoute(builder:(_)=>const ProfileScreen()));
      },
      destinations:const[
        NavigationDestination(icon:Icon(Icons.home_outlined),selectedIcon:Icon(Icons.home_rounded),label:'الرئيسية'),
        NavigationDestination(icon:Icon(Icons.today_outlined),selectedIcon:Icon(Icons.today_rounded),label:'يومي'),
        NavigationDestination(icon:Icon(Icons.restaurant_menu_outlined),selectedIcon:Icon(Icons.restaurant_menu_rounded),label:'اكتشف'),
        NavigationDestination(icon:Icon(Icons.calendar_month_outlined),selectedIcon:Icon(Icons.calendar_month_rounded),label:'خطتي'),
        NavigationDestination(icon:Icon(Icons.person_outline),selectedIcon:Icon(Icons.person),label:'حسابي'),
      ],
    ),
    body:Column(children:[
      if(loading)const LinearProgressIndicator(minHeight:2),
      if(error!=null)Container(
        width:double.infinity,
        margin:const EdgeInsets.fromLTRB(16,10,16,0),
        padding:const EdgeInsets.all(12),
        decoration:BoxDecoration(color:const Color(0xFFFFEEEE),borderRadius:BorderRadius.circular(12)),
        child:Text(error!,style:const TextStyle(color:Colors.red)),
      ),
      Expanded(child:TabBarView(
        controller:tabs,
        children:[
          _weekly(),
          _progress(),
        ],
      )),
    ]),
  );

  Widget _weekly(){
    final p=plan;
    if(p==null)return const Center(child:Text('جاري تجهيز خطتك...'));
    final day=p.days[selectedDay];
    return RefreshIndicator(
      onRefresh:load,
      child:ListView(
        physics:const AlwaysScrollableScrollPhysics(),
        padding:const EdgeInsets.fromLTRB(18,16,18,32),
        children:[
          SizedBox(
            height:70,
            child:ListView.separated(
              scrollDirection:Axis.horizontal,
              itemCount:p.days.length,
              separatorBuilder:(_,__)=>const SizedBox(width:8),
              itemBuilder:(_,i){
                final d=p.days[i];
                final selected=i==selectedDay;
                return ChoiceChip(
                  selected:selected,
                  onSelected:(_)=>setState(()=>selectedDay=i),
                  label:Column(mainAxisSize:MainAxisSize.min,children:[
                    Text(dayNames[d.date.weekday-1],style:TextStyle(fontWeight:selected?FontWeight.w900:FontWeight.w600)),
                    Text('${d.date.day}/${d.date.month}',style:const TextStyle(fontSize:11)),
                  ]),
                );
              },
            ),
          ),
          const SizedBox(height:12),
          Container(
            padding:const EdgeInsets.all(16),
            decoration:BoxDecoration(color:WazenTheme.beige,borderRadius:BorderRadius.circular(18)),
            child:Row(children:[
              Expanded(child:_summaryMetric('السعرات','${day.totalCalories.toStringAsFixed(0)} kcal')),
              Expanded(child:_summaryMetric('البروتين','${day.totalProteinG.toStringAsFixed(0)}g')),
            ]),
          ),
          const SizedBox(height:16),
          ...day.items.map(_mealCard),
          const SizedBox(height:8),
          FilledButton.icon(
            onPressed:acting?null:rebalanceSelected,
            icon:const Icon(Icons.balance_rounded),
            label:Text(acting?'جاري الموازنة...':'أعد موازنة اليوم'),
          ),
          const SizedBox(height:8),
          const Text(
            'الخطة اقتراح مرن مبني على أهدافك وسلامتك الغذائية. تقدر تغيّر اختياراتك في أي وقت، ووازن يعيد حساب اليوم.',
            textAlign:TextAlign.center,
            style:TextStyle(color:Colors.black54,height:1.4,fontSize:12),
          ),
        ],
      ),
    );
  }

  Widget _mealCard(WeeklyPlanItem item)=>Card(
    margin:const EdgeInsets.only(bottom:10),
    child:ListTile(
      contentPadding:const EdgeInsets.symmetric(horizontal:16,vertical:8),
      leading:CircleAvatar(
        backgroundColor:WazenTheme.beige,
        child:Icon(_mealIcon(item.mealType),color:WazenTheme.greenDark),
      ),
      title:Text(mealNames[item.mealType]??item.mealType,style:const TextStyle(fontWeight:FontWeight.w800)),
      subtitle:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
        const SizedBox(height:3),
        Text(item.foodName,style:const TextStyle(fontWeight:FontWeight.w600,color:Colors.black87)),
        const SizedBox(height:3),
        Text('${item.calories.toStringAsFixed(0)} سعرة • ${item.proteinG.toStringAsFixed(0)}g بروتين${item.price==null?'':' • AED ${item.price!.toStringAsFixed(0)}'}'),
      ]),
      trailing:item.status=='DONE'?const Icon(Icons.check_circle,color:WazenTheme.green):null,
    ),
  );

  Widget _progress(){
    final p=progress;
    return RefreshIndicator(
      onRefresh:load,
      child:ListView(
        physics:const AlwaysScrollableScrollPhysics(),
        padding:const EdgeInsets.fromLTRB(18,16,18,32),
        children:[
          SegmentedButton<String>(
            segments:const[
              ButtonSegment(value:'week',label:Text('الأسبوع')),
              ButtonSegment(value:'month',label:Text('الشهر')),
              ButtonSegment(value:'3months',label:Text('3 أشهر')),
            ],
            selected:{range},
            onSelectionChanged:(s)=>changeRange(s.first),
          ),
          const SizedBox(height:18),
          if(p==null)
            const Center(child:Padding(padding:EdgeInsets.all(30),child:Text('جاري حساب تقدمك...')))
          else ...[
            _weightCard(p),
            const SizedBox(height:12),
            GridView.count(
              crossAxisCount:2,
              shrinkWrap:true,
              physics:const NeverScrollableScrollPhysics(),
              childAspectRatio:1.45,
              mainAxisSpacing:10,
              crossAxisSpacing:10,
              children:[
                _statCard(Icons.track_changes_rounded,'تحقيق الهدف','${p.goalDays} من ${p.rangeDays} يوم'),
                _statCard(Icons.fitness_center_rounded,'متوسط البروتين','${p.averageProteinG.toStringAsFixed(0)}g'),
                _statCard(Icons.local_fire_department_outlined,'متوسط السعرات','${p.averageCalories.toStringAsFixed(0)}'),
                _statCard(Icons.restaurant_outlined,'المطاعم','AED ${p.restaurantSpendAed.toStringAsFixed(0)}'),
              ],
            ),
            const SizedBox(height:16),
            _goalHistory(p),
          ],
        ],
      ),
    );
  }

  Widget _weightCard(ProgressSummary p){
    final points=p.weightTrend;
    final current=points.isEmpty?null:points.last.weightKg;
    final first=points.isEmpty?null:points.first.weightKg;
    final delta=(current!=null&&first!=null)?current-first:null;
    return Container(
      padding:const EdgeInsets.all(18),
      decoration:BoxDecoration(color:const Color(0xFFF7F8F5),borderRadius:BorderRadius.circular(20)),
      child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
        const Text('الوزن',style:TextStyle(fontSize:18,fontWeight:FontWeight.w900)),
        const SizedBox(height:10),
        if(current==null)
          const Text('أضف وزنك من حسابي حتى يظهر اتجاه التقدم.',style:TextStyle(color:Colors.black54))
        else Row(children:[
          Text('${current.toStringAsFixed(1)} kg',style:const TextStyle(fontSize:28,fontWeight:FontWeight.w900,color:WazenTheme.greenDark)),
          const SizedBox(width:12),
          if(delta!=null)Text(
            '${delta>=0?'+':''}${delta.toStringAsFixed(1)} kg',
            style:const TextStyle(color:Colors.black54,fontWeight:FontWeight.w700),
          ),
        ]),
        if(points.length>1)...[
          const SizedBox(height:14),
          Row(
            crossAxisAlignment:CrossAxisAlignment.end,
            children:points.take(12).map((x){
              final min=points.map((e)=>e.weightKg).reduce((a,b)=>a<b?a:b);
              final max=points.map((e)=>e.weightKg).reduce((a,b)=>a>b?a:b);
              final span=(max-min).abs()<0.1?1.0:max-min;
              final h=18+42*((x.weightKg-min)/span);
              return Expanded(child:Padding(
                padding:const EdgeInsets.symmetric(horizontal:2),
                child:Container(height:h,decoration:BoxDecoration(color:WazenTheme.green.withValues(alpha:.25),borderRadius:BorderRadius.circular(6))),
              ));
            }).toList(),
          ),
        ],
      ]),
    );
  }

  Widget _goalHistory(ProgressSummary p){
    final recent=p.daily.length>14?p.daily.sublist(p.daily.length-14):p.daily;
    return Container(
      padding:const EdgeInsets.all(16),
      decoration:BoxDecoration(color:Colors.white,border:Border.all(color:const Color(0xFFE7EAE7)),borderRadius:BorderRadius.circular(18)),
      child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
        const Text('الأيام الأخيرة',style:TextStyle(fontSize:17,fontWeight:FontWeight.w900)),
        const SizedBox(height:12),
        ...recent.reversed.map((d){
          final date=DateTime.parse(d['date'].toString());
          final cal=(d['calories'] as num? ?? 0).toDouble();
          final met=d['goal_met']==true;
          return Padding(
            padding:const EdgeInsets.only(bottom:8),
            child:Row(children:[
              SizedBox(width:62,child:Text('${date.day}/${date.month}',style:const TextStyle(color:Colors.black54))),
              Expanded(child:LinearProgressIndicator(
                value:p.targetCalories<=0?0:(cal/p.targetCalories).clamp(0.0,1.0),
                minHeight:8,
                borderRadius:BorderRadius.circular(8),
              )),
              const SizedBox(width:10),
              SizedBox(width:70,child:Text('${cal.toStringAsFixed(0)} kcal',style:const TextStyle(fontSize:11))),
              Icon(met?Icons.check_circle:Icons.circle_outlined,size:18,color:met?WazenTheme.green:Colors.black26),
            ]),
          );
        }),
      ]),
    );
  }

  Widget _summaryMetric(String label,String value)=>Column(children:[
    Text(label,style:const TextStyle(fontSize:12,color:Colors.black54)),
    const SizedBox(height:4),
    Text(value,style:const TextStyle(fontSize:18,fontWeight:FontWeight.w900,color:WazenTheme.greenDark)),
  ]);

  Widget _statCard(IconData icon,String label,String value)=>Container(
    padding:const EdgeInsets.all(15),
    decoration:BoxDecoration(color:const Color(0xFFF7F8F5),borderRadius:BorderRadius.circular(18)),
    child:Column(crossAxisAlignment:CrossAxisAlignment.start,mainAxisAlignment:MainAxisAlignment.center,children:[
      Icon(icon,color:WazenTheme.greenDark),
      const SizedBox(height:8),
      Text(label,style:const TextStyle(fontSize:12,color:Colors.black54)),
      const SizedBox(height:4),
      Text(value,style:const TextStyle(fontSize:18,fontWeight:FontWeight.w900)),
    ]),
  );

  IconData _mealIcon(String meal){
    switch(meal){
      case 'BREAKFAST': return Icons.free_breakfast_outlined;
      case 'LUNCH': return Icons.lunch_dining_outlined;
      case 'DINNER': return Icons.dinner_dining_outlined;
      default: return Icons.cookie_outlined;
    }
  }
}
