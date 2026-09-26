import 'package:flutter/material.dart';
import '../services/api_client.dart';
import 'auth_screen.dart';

class ResetPasswordScreen extends StatefulWidget{
  final String token;
  const ResetPasswordScreen({super.key,required this.token});

  @override
  State<ResetPasswordScreen> createState()=>_ResetPasswordScreenState();
}

class _ResetPasswordScreenState extends State<ResetPasswordScreen>{
  final password=TextEditingController();
  final confirm=TextEditingController();
  bool loading=false;
  bool done=false;
  String? error;

  @override
  void dispose(){
    password.dispose();
    confirm.dispose();
    super.dispose();
  }

  String? _policy(String value){
    if(value.length<8)return 'كلمة المرور لازم تكون 8 أحرف على الأقل.';
    if(!RegExp(r'[A-Z]').hasMatch(value))return 'أضف حرف إنجليزي كبير واحد على الأقل.';
    if(!RegExp(r'[a-z]').hasMatch(value))return 'أضف حرف إنجليزي صغير واحد على الأقل.';
    if(!RegExp(r'[0-9]').hasMatch(value))return 'أضف رقمًا واحدًا على الأقل.';
    return null;
  }

  Future<void> submit()async{
    final policy=_policy(password.text);
    if(policy!=null){
      setState(()=>error=policy);
      return;
    }
    if(password.text!=confirm.text){
      setState(()=>error='كلمتا المرور غير متطابقتين.');
      return;
    }

    setState((){loading=true;error=null;});
    try{
      await WazenApi.instance.resetPassword(widget.token,password.text);
      await WazenApi.instance.clearSession();
      if(mounted)setState(()=>done=true);
    }catch(e){
      if(mounted)setState(()=>error=e.toString());
    }finally{
      if(mounted)setState(()=>loading=false);
    }
  }

  @override
  Widget build(BuildContext context)=>Scaffold(
    appBar:AppBar(title:const Text('إعادة تعيين كلمة المرور')),
    body:SafeArea(child:Center(child:SingleChildScrollView(
      padding:const EdgeInsets.all(24),
      child:ConstrainedBox(
        constraints:const BoxConstraints(maxWidth:440),
        child:done?_success():Column(
          crossAxisAlignment:CrossAxisAlignment.stretch,
          children:[
            const Icon(Icons.lock_reset_rounded,size:64),
            const SizedBox(height:18),
            const Text(
              'اختر كلمة مرور جديدة',
              style:TextStyle(fontSize:28,fontWeight:FontWeight.w900),
            ),
            const SizedBox(height:8),
            const Text(
              'الرابط صالح للاستخدام مرة واحدة. بعد التغيير يتم إلغاء الجلسات القديمة.',
              style:TextStyle(color:Colors.black54,height:1.5),
            ),
            const SizedBox(height:24),
            TextField(
              controller:password,
              obscureText:true,
              textDirection:TextDirection.ltr,
              decoration:const InputDecoration(
                labelText:'كلمة المرور الجديدة',
                helperText:'8+ أحرف مع حرف كبير وصغير ورقم',
              ),
            ),
            const SizedBox(height:12),
            TextField(
              controller:confirm,
              obscureText:true,
              textDirection:TextDirection.ltr,
              onSubmitted:(_)=>loading?null:submit(),
              decoration:const InputDecoration(labelText:'تأكيد كلمة المرور'),
            ),
            if(error!=null)...[
              const SizedBox(height:12),
              Text(error!,style:const TextStyle(color:Colors.red)),
            ],
            const SizedBox(height:20),
            FilledButton(
              onPressed:loading?null:submit,
              child:Text(loading?'جاري التغيير...':'تغيير كلمة المرور'),
            ),
          ],
        ),
      ),
    ))),
  );

  Widget _success()=>Column(
    crossAxisAlignment:CrossAxisAlignment.stretch,
    children:[
      const Icon(Icons.check_circle_rounded,size:72,color:Colors.green),
      const SizedBox(height:18),
      const Text(
        'تم تغيير كلمة المرور',
        textAlign:TextAlign.center,
        style:TextStyle(fontSize:26,fontWeight:FontWeight.w900),
      ),
      const SizedBox(height:8),
      const Text(
        'تقدر الآن تسجل الدخول بكلمة المرور الجديدة.',
        textAlign:TextAlign.center,
        style:TextStyle(color:Colors.black54),
      ),
      const SizedBox(height:24),
      FilledButton(
        onPressed:()=>Navigator.pushAndRemoveUntil(
          context,
          MaterialPageRoute(builder:(_)=>const AuthScreen()),
          (_)=>false,
        ),
        child:const Text('العودة لتسجيل الدخول'),
      ),
    ],
  );
}
