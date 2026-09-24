
import 'package:flutter/material.dart';
import '../models/api_models.dart';
import '../services/api_client.dart';

class AddFoodReviewScreen extends StatefulWidget {
  final FoodDetail food;
  final String mealType;
  final String sourceLabel;
  const AddFoodReviewScreen({super.key,required this.food,required this.mealType,required this.sourceLabel});
  @override State<AddFoodReviewScreen> createState()=>_AddFoodReviewScreenState();
}
class _AddFoodReviewScreenState extends State<AddFoodReviewScreen>{
  bool saving=false;
  double quantity=1;
  @override Widget build(BuildContext context){
    final n=widget.food.nutrition;
    final kcal=(n.calories??0)*quantity;
    return Scaffold(
      appBar:AppBar(title:const Text('راجع قبل الإضافة')),
      bottomNavigationBar:SafeArea(child:Padding(padding:const EdgeInsets.all(16),child:FilledButton(
        onPressed:saving?null:()async{
          setState(()=>saving=true);
          try{
            final state=await WazenApi.instance.logFromCatalog(widget.food.foodId,mealType:widget.mealType,quantity:quantity);
            if(!mounted)return;
            Navigator.pop(context,true);
          }finally{if(mounted)setState(()=>saving=false);}
        },
        child:Text(saving?'جاري الإضافة...':'أضف ليومي'),
      ))),
      body:ListView(padding:const EdgeInsets.all(20),children:[
        Text(widget.food.nameAr?.isNotEmpty==true?widget.food.nameAr!:widget.food.name,style:const TextStyle(fontSize:26,fontWeight:FontWeight.w900)),
        const SizedBox(height:4),
        Text('${widget.food.vendor} • ${widget.sourceLabel}',style:const TextStyle(color:Colors.black54)),
        const SizedBox(height:20),
        ListTile(title:const Text('السعرات'),trailing:Text('${kcal.toStringAsFixed(0)} kcal')),
        ListTile(title:const Text('البروتين'),trailing:Text('${((n.proteinG??0)*quantity).toStringAsFixed(1)} g')),
        ListTile(title:const Text('الكربوهيدرات'),trailing:Text('${((n.carbsG??0)*quantity).toStringAsFixed(1)} g')),
        ListTile(title:const Text('الدهون'),trailing:Text('${((n.fatG??0)*quantity).toStringAsFixed(1)} g')),
        const SizedBox(height:12),
        Row(children:[
          const Text('الكمية',style:TextStyle(fontWeight:FontWeight.w800)),
          const Spacer(),
          IconButton(onPressed:quantity>0.5?()=>setState(()=>quantity-=0.5):null,icon:const Icon(Icons.remove_circle_outline)),
          Text(quantity.toStringAsFixed(1),style:const TextStyle(fontWeight:FontWeight.w900)),
          IconButton(onPressed:()=>setState(()=>quantity+=0.5),icon:const Icon(Icons.add_circle_outline)),
        ]),
        if((widget.food.sourceConfidence??'').isNotEmpty)
          Padding(padding:const EdgeInsets.only(top:12),child:Text('ثقة البيانات: ${widget.food.sourceConfidence}',style:const TextStyle(color:Colors.black54))),
      ]),
    );
  }
}
