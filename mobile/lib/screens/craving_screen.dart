import 'package:flutter/material.dart';
import '../models/api_models.dart';
import '../services/api_client.dart';
import '../widgets/recommendation_card.dart';
import 'food_detail_screen.dart';

class CravingScreen extends StatefulWidget {
  const CravingScreen({super.key});
  @override
  State<CravingScreen> createState() => _CravingScreenState();
}

class _CravingScreenState extends State<CravingScreen> {
  final controller = TextEditingController(text: 'أبي برغر من KFC تحت 600 سعرة');
  bool loading = false;
  String? error;
  Map<String,dynamic>? parsedIntent;
  List<RecommendationItem> results = const [];

  Future<void> search() async {
    if (controller.text.trim().isEmpty) return;
    setState(() { loading = true; error = null; results = const []; parsedIntent=null; });
    try {
      final intent=await WazenApi.instance.parseCraving(controller.text);
      final r = await WazenApi.instance.goldenFlow(controller.text);
      if (mounted) setState(() { parsedIntent=intent; results = r; });
    } catch (e) {
      if (mounted) setState(() => error = e.toString());
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('شو آكل الحين؟')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          const Text('خاطرك بشي؟', style: TextStyle(fontSize: 26, fontWeight: FontWeight.w900)),
          const SizedBox(height: 6),
          const Text('قلها بطريقتك. مطعم، نوع أكل، سعرات أو بروتين.', style: TextStyle(color: Colors.black54)),
          const SizedBox(height: 18),
          TextField(
            controller: controller,
            minLines: 2,
            maxLines: 4,
            decoration: const InputDecoration(hintText: 'مثال: أبي برغر من هارديز تحت 600 سعرة'),
          ),
          const SizedBox(height: 12),
          FilledButton.icon(onPressed: loading ? null : search, icon: const Icon(Icons.auto_awesome_rounded), label: Text(loading ? 'أدور لك...' : 'دور لي')),
          if (error != null) Padding(padding: const EdgeInsets.only(top: 14), child: Text(error!, style: const TextStyle(color: Colors.red))),

          if(parsedIntent!=null)...[
            const SizedBox(height:14),
            Container(
              padding:const EdgeInsets.all(14),
              decoration:BoxDecoration(
                color:const Color(0xFFF6F7F3),
                borderRadius:BorderRadius.circular(16),
              ),
              child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
                const Text('فهمت طلبك كالتالي',style:TextStyle(fontWeight:FontWeight.w900)),
                const SizedBox(height:10),
                Wrap(
                  spacing:8,
                  runSpacing:8,
                  children:[
                    if(parsedIntent!['restaurant']!=null)
                      _intentChip(Icons.storefront_outlined,parsedIntent!['restaurant'].toString()),
                    if(parsedIntent!['food_category']!=null)
                      _intentChip(Icons.restaurant_outlined,parsedIntent!['food_category'].toString()),
                    if(parsedIntent!['max_calories']!=null)
                      _intentChip(Icons.local_fire_department_outlined,'≤ ${(parsedIntent!['max_calories'] as num).toStringAsFixed(0)} kcal'),
                    if(parsedIntent!['budget_max']!=null)
                      _intentChip(Icons.payments_outlined,'≤ AED ${(parsedIntent!['budget_max'] as num).toStringAsFixed(0)}'),
                    if(parsedIntent!['min_protein_g']!=null)
                      _intentChip(Icons.fitness_center_outlined,'≥ ${(parsedIntent!['min_protein_g'] as num).toStringAsFixed(0)}g بروتين'),
                  ],
                ),
                if(parsedIntent!['preserve_restaurant']==true)...[
                  const SizedBox(height:8),
                  const Text('المطعم المذكور محفوظ كقيد صريح في البحث.',style:TextStyle(fontSize:12,color:Colors.black54)),
                ],
              ]),
            ),
          ],
          if (results.isNotEmpty) ...[
            const SizedBox(height: 28),
            Text('لقيت لك ${results.length} خيارات', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
            const SizedBox(height: 12),
            ...results.map((item) => Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: RecommendationCard(item: item, onFeedback: (action) async {
                await WazenApi.instance.sendRecommendationFeedback(item.foodId, action);
                if (mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(action == 'REJECT' ? 'بنقلل ظهور هالنوع لك.' : 'حفظنا تفضيلك.')));
                }
              }, onTap: () async {
                final logged = await Navigator.push<bool>(context, MaterialPageRoute(builder: (_) => FoodDetailScreen(item: item)));
                if (logged == true && context.mounted) Navigator.pop(context, true);
              }),
            )),
          ],
        ],
      ),
    );
  }

  Widget _intentChip(IconData icon,String text)=>Chip(
    avatar:Icon(icon,size:16),
    label:Text(text),
    visualDensity:VisualDensity.compact,
  );

}
