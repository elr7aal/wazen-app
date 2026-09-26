import 'package:flutter/material.dart';
import '../core/theme.dart';
import '../services/api_client.dart';
import 'auth_screen.dart';
import 'startup_gate.dart';

class VerificationRequiredScreen extends StatefulWidget{
  const VerificationRequiredScreen({super.key});

  @override
  State<VerificationRequiredScreen> createState()=>_VerificationRequiredScreenState();
}

class _VerificationRequiredScreenState extends State<VerificationRequiredScreen>{
  bool loading=true;
  bool sending=false;
  String? email;
  String? error;

  @override
  void initState(){
    super.initState();
    _load();
  }

  Future<void> _load()async{
    setState((){loading=true;error=null;});
    try{
      final me=await WazenApi.instance.me();
      email=(me['email']??'').toString();
      if(me['email_verified']==true&&mounted){
        Navigator.pushAndRemoveUntil(
          context,
          MaterialPageRoute(builder:(_)=>const StartupGate()),
          (_)=>false,
        );
        return;
      }
    }catch(e){
      error=e.toString();
    }finally{
      if(mounted)setState(()=>loading=false);
    }
  }

  Future<void> _resend()async{
    setState((){sending=true;error=null;});
    try{
      final data=await WazenApi.instance.resendEmailVerification();
      if(!mounted)return;
      final delivery=(data['delivery']??'').toString();
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content:Text(
          delivery=='SENT'
            ?'تم إرسال رابط التحقق إلى بريدك.'
            :'تم تسجيل طلب التحقق. إذا كانت خدمة البريد مفعلة سيصلك الرابط.',
        ),
      ));
    }catch(e){
      if(mounted)setState(()=>error=e.toString());
    }finally{
      if(mounted)setState(()=>sending=false);
    }
  }

  Future<void> _logout()async{
    await WazenApi.instance.logout();
    if(!mounted)return;
    Navigator.pushAndRemoveUntil(
      context,
      MaterialPageRoute(builder:(_)=>const AuthScreen()),
      (_)=>false,
    );
  }

  @override
  Widget build(BuildContext context)=>Scaffold(
    appBar:AppBar(
      title:const Text('تأكيد البريد الإلكتروني'),
      actions:[
        TextButton(onPressed:_logout,child:const Text('خروج')),
      ],
    ),
    body:SafeArea(child:Center(child:SingleChildScrollView(
      padding:const EdgeInsets.all(24),
      child:ConstrainedBox(
        constraints:const BoxConstraints(maxWidth:440),
        child:Column(crossAxisAlignment:CrossAxisAlignment.stretch,children:[
          Container(
            width:88,height:88,
            alignment:Alignment.center,
            decoration:BoxDecoration(color:WazenTheme.beige,borderRadius:BorderRadius.circular(28)),
            child:const Icon(Icons.mark_email_unread_outlined,size:48,color:WazenTheme.greenDark),
          ),
          const SizedBox(height:24),
          const Text(
            'أكد بريدك قبل المتابعة',
            textAlign:TextAlign.center,
            style:TextStyle(fontSize:28,fontWeight:FontWeight.w900),
          ),
          const SizedBox(height:10),
          Text(
            email==null||email!.isEmpty
              ?'أرسلنا رابط تحقق إلى بريد حسابك.'
              :'أرسلنا رابط تحقق إلى:\n$email',
            textAlign:TextAlign.center,
            style:const TextStyle(color:Colors.black54,height:1.5),
          ),
          const SizedBox(height:12),
          const Text(
            'تقدر تسجل الدخول وتدير حسابك، لكن وظائف WAZEN الأساسية تتطلب بريدًا موثّقًا في بيئة الإنتاج.',
            textAlign:TextAlign.center,
            style:TextStyle(fontSize:13,color:Colors.black54,height:1.5),
          ),
          if(loading)...[
            const SizedBox(height:18),
            const LinearProgressIndicator(minHeight:2),
          ],
          if(error!=null)...[
            const SizedBox(height:12),
            Text(error!,textAlign:TextAlign.center,style:const TextStyle(color:Colors.red)),
          ],
          const SizedBox(height:24),
          FilledButton.icon(
            onPressed:loading?null:_load,
            icon:const Icon(Icons.refresh_rounded),
            label:const Text('تم التحقق — تحديث الحالة'),
          ),
          const SizedBox(height:10),
          OutlinedButton.icon(
            onPressed:sending?null:_resend,
            icon:const Icon(Icons.forward_to_inbox_outlined),
            label:Text(sending?'جاري الإرسال...':'إعادة إرسال رابط التحقق'),
          ),
          const SizedBox(height:10),
          TextButton(
            onPressed:_logout,
            child:const Text('استخدام حساب آخر'),
          ),
        ]),
      ),
    ))),
  );
}
