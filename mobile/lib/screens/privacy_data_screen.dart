import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../core/theme.dart';
import '../services/api_client.dart';
import 'auth_screen.dart';

class PrivacyDataScreen extends StatefulWidget{
  const PrivacyDataScreen({super.key});
  @override
  State<PrivacyDataScreen> createState()=>_PrivacyDataScreenState();
}

class _PrivacyDataScreenState extends State<PrivacyDataScreen>{
  bool busy=false;
  String? error;

  Future<void> exportData() async{
    setState(()=>busy=true);
    try{
      final data=await WazenApi.instance.exportMyData();
      final pretty=const JsonEncoder.withIndent('  ').convert(data);
      await Clipboard.setData(ClipboardData(text:pretty));
      if(!mounted)return;
      await showDialog<void>(
        context:context,
        builder:(ctx)=>AlertDialog(
          title:const Text('تم تجهيز بياناتك'),
          content:const Text(
            'تم نسخ نسخة JSON من بيانات حسابك إلى الحافظة. لا تتضمن كلمة المرور أو مفاتيح الجلسات أو رموز الاستعادة.',
          ),
          actions:[
            TextButton(onPressed:()=>Navigator.pop(ctx),child:const Text('تمام')),
          ],
        ),
      );
    }catch(e){
      if(mounted)setState(()=>error=e.toString());
    }finally{
      if(mounted)setState(()=>busy=false);
    }
  }

  Future<void> deleteAccount() async{
    final password=TextEditingController();
    final confirm=TextEditingController();
    final approved=await showDialog<bool>(
      context:context,
      barrierDismissible:false,
      builder:(ctx)=>StatefulBuilder(
        builder:(ctx,setLocal)=>AlertDialog(
          title:const Text('حذف الحساب نهائيًا؟'),
          content:SingleChildScrollView(child:Column(
            mainAxisSize:MainAxisSize.min,
            crossAxisAlignment:CrossAxisAlignment.start,
            children:[
              const Text(
                'سيتم حذف ملفك، سجل الطعام، الأهداف، التفضيلات، الحدود الصحية، الخطط، النشاط والجلسات المرتبطة بالحساب. لا يمكن التراجع عن هذه العملية.',
                style:TextStyle(height:1.5),
              ),
              const SizedBox(height:16),
              TextField(
                controller:password,
                obscureText:true,
                onChanged:(_)=>setLocal((){}),
                decoration:const InputDecoration(labelText:'كلمة المرور'),
              ),
              const SizedBox(height:12),
              const Text('للتأكيد اكتب: حذف حسابي',style:TextStyle(fontWeight:FontWeight.w700)),
              const SizedBox(height:6),
              TextField(
                controller:confirm,
                onChanged:(_)=>setLocal((){}),
                decoration:const InputDecoration(labelText:'تأكيد الحذف'),
              ),
            ],
          )),
          actions:[
            TextButton(onPressed:()=>Navigator.pop(ctx,false),child:const Text('إلغاء')),
            FilledButton(
              style:FilledButton.styleFrom(backgroundColor:Colors.redAccent),
              onPressed:confirm.text.trim()=='حذف حسابي'&&password.text.isNotEmpty
                ?()=>Navigator.pop(ctx,true)
                :null,
              child:const Text('حذف الحساب نهائيًا'),
            ),
          ],
        ),
      ),
    );

    final passwordValue=password.text;
    password.dispose();
    confirm.dispose();
    if(approved!=true)return;

    setState(()=>busy=true);
    try{
      await WazenApi.instance.deleteMyAccount(passwordValue);
      if(!mounted)return;
      Navigator.pushAndRemoveUntil(
        context,
        MaterialPageRoute(builder:(_)=>const AuthScreen()),
        (_)=>false,
      );
    }catch(e){
      if(mounted)setState(()=>error=e.toString());
    }finally{
      if(mounted)setState(()=>busy=false);
    }
  }

  @override
  Widget build(BuildContext context)=>Scaffold(
    appBar:AppBar(title:const Text('الخصوصية والبيانات')),
    body:ListView(
      padding:const EdgeInsets.all(18),
      children:[
        Container(
          padding:const EdgeInsets.all(16),
          decoration:BoxDecoration(color:WazenTheme.beige,borderRadius:BorderRadius.circular(18)),
          child:const Row(crossAxisAlignment:CrossAxisAlignment.start,children:[
            Icon(Icons.privacy_tip_outlined,color:WazenTheme.greenDark),
            SizedBox(width:10),
            Expanded(child:Text(
              'بياناتك ملكك. تقدر تأخذ نسخة منها أو تحذف حسابك نهائيًا من هنا.',
              style:TextStyle(height:1.5),
            )),
          ]),
        ),
        if(error!=null)...[
          const SizedBox(height:12),
          Text(error!,style:const TextStyle(color:Colors.red)),
        ],
        const SizedBox(height:18),
        _card(
          icon:Icons.download_outlined,
          title:'تصدير بياناتي',
          text:'ينشئ نسخة JSON من بيانات حسابك ويضعها في الحافظة. لا يتم تضمين كلمات المرور أو رموز الجلسات.',
          child:FilledButton.icon(
            onPressed:busy?null:exportData,
            icon:const Icon(Icons.content_copy_rounded),
            label:Text(busy?'جاري التجهيز...':'نسخ بياناتي'),
          ),
        ),
        const SizedBox(height:16),
        _card(
          icon:Icons.delete_forever_outlined,
          title:'حذف الحساب',
          text:'الحذف نهائي ويزيل بيانات الحساب المرتبطة من WAZEN. ستحتاج كلمة المرور وتأكيدًا صريحًا قبل التنفيذ.',
          danger:true,
          child:OutlinedButton.icon(
            onPressed:busy?null:deleteAccount,
            icon:const Icon(Icons.delete_forever_outlined),
            label:const Text('حذف حسابي'),
            style:OutlinedButton.styleFrom(foregroundColor:Colors.redAccent),
          ),
        ),
        const SizedBox(height:24),
        const Text(
          'ملاحظة: نسخة التصدير لا تتضمن بيانات اعتماد أمنية داخلية مثل password hashes أو refresh/reset token hashes أو مخزن idempotency.',
          style:TextStyle(fontSize:12,color:Colors.black54,height:1.5),
        ),
      ],
    ),
  );

  Widget _card({
    required IconData icon,
    required String title,
    required String text,
    required Widget child,
    bool danger=false,
  })=>Container(
    padding:const EdgeInsets.all(18),
    decoration:BoxDecoration(
      color:Colors.white,
      borderRadius:BorderRadius.circular(18),
      border:Border.all(color:danger?const Color(0xFFFFD7D7):const Color(0xFFE4E8E4)),
    ),
    child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
      Row(children:[
        Icon(icon,color:danger?Colors.redAccent:WazenTheme.greenDark),
        const SizedBox(width:10),
        Text(title,style:const TextStyle(fontSize:18,fontWeight:FontWeight.w900)),
      ]),
      const SizedBox(height:10),
      Text(text,style:const TextStyle(color:Colors.black54,height:1.45)),
      const SizedBox(height:14),
      child,
    ]),
  );
}
