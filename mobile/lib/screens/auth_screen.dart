import 'package:flutter/material.dart';
import '../core/theme.dart';
import '../services/api_client.dart';
import '../services/app_preferences.dart';
import 'home_screen.dart';
import 'onboarding_screen.dart';
import 'verification_required_screen.dart';

class AuthScreen extends StatefulWidget {
  const AuthScreen({super.key});
  @override
  State<AuthScreen> createState()=>_AuthScreenState();
}

class _AuthScreenState extends State<AuthScreen> {
  final email=TextEditingController();
  final password=TextEditingController();
  final firstName=TextEditingController();
  final apiUrl=TextEditingController(text:WazenApi.instance.baseUrl.replaceAll('/api/v1',''));
  bool loading=false;
  bool registerMode=false;
  bool showAdvanced=false;
  String? error;

  bool get arabic=>AppPreferences.instance.language.value=='ar';

  @override
  void dispose(){
    email.dispose();password.dispose();firstName.dispose();apiUrl.dispose();
    super.dispose();
  }


  String? passwordPolicyError(String value){
    if(value.length<8)return arabic?'كلمة المرور لازم تكون 8 أحرف على الأقل.':'Password must be at least 8 characters.';
    if(!RegExp(r'[A-Z]').hasMatch(value))return arabic?'أضف حرف إنجليزي كبير واحد على الأقل.':'Add at least one uppercase letter.';
    if(!RegExp(r'[a-z]').hasMatch(value))return arabic?'أضف حرف إنجليزي صغير واحد على الأقل.':'Add at least one lowercase letter.';
    if(!RegExp(r'[0-9]').hasMatch(value))return arabic?'أضف رقمًا واحدًا على الأقل.':'Add at least one number.';
    return null;
  }

  Future<void> submit() async {
    if(registerMode){
      final policy=passwordPolicyError(password.text);
      if(policy!=null){
        setState(()=>error=policy);
        return;
      }
    }
    setState((){loading=true;error=null;});
    try{
      if(showAdvanced&&apiUrl.text.trim().isNotEmpty){
        await WazenApi.instance.configureBaseUrl(apiUrl.text);
      }
      if(registerMode){
        await WazenApi.instance.register(
          email:email.text.trim(),
          password:password.text,
          firstName:firstName.text.trim().isEmpty?null:firstName.text.trim(),
        );
      }else{
        await WazenApi.instance.login(email.text.trim(),password.text);
      }
      if(!mounted)return;
      final enforced=await WazenApi.instance.emailVerificationEnforced();
      if(enforced){
        final account=await WazenApi.instance.me();
        if(account['email_verified']!=true){
          if(!mounted)return;
          Navigator.pushReplacement(context,MaterialPageRoute(builder:(_)=>const VerificationRequiredScreen()));
          return;
        }
      }
      final complete=await WazenApi.instance.onboardingStatus();
      if(!mounted)return;
      Navigator.pushReplacement(context,MaterialPageRoute(
        builder:(_)=>complete?const HomeScreen():const OnboardingScreen(),
      ));
    }catch(e){
      if(mounted)setState(()=>error=e.toString());
    }finally{
      if(mounted)setState(()=>loading=false);
    }
  }


  Future<void> forgotPassword() async {
    final controller=TextEditingController(text:email.text.trim());
    final value=await showDialog<String>(
      context:context,
      builder:(ctx)=>AlertDialog(
        title:Text(arabic?'استعادة كلمة المرور':'Reset password'),
        content:TextField(
          controller:controller,
          keyboardType:TextInputType.emailAddress,
          textDirection:TextDirection.ltr,
          decoration:InputDecoration(labelText:arabic?'البريد الإلكتروني':'Email'),
        ),
        actions:[
          TextButton(onPressed:()=>Navigator.pop(ctx),child:Text(arabic?'إلغاء':'Cancel')),
          FilledButton(onPressed:()=>Navigator.pop(ctx,controller.text.trim()),child:Text(arabic?'متابعة':'Continue')),
        ],
      ),
    );
    controller.dispose();
    if(value==null||value.isEmpty)return;
    setState(()=>loading=true);
    try{
      final result=await WazenApi.instance.forgotPassword(value);
      if(!mounted)return;
      final deliveryAvailable=result['delivery_available']==true;
      final msg=!deliveryAvailable
        ?(arabic?'خدمة استعادة كلمة المرور جاهزة، لكن إرسال البريد غير مفعّل في هذه البيئة حاليًا.':'Password recovery is ready, but email delivery is not enabled in this environment.')
        :(arabic?'إذا كان الحساب موجودًا، ستصلك تعليمات الاستعادة على البريد.':'If the account exists, password reset instructions will be sent by email.');
      await showDialog<void>(context:context,builder:(ctx)=>AlertDialog(
        title:Text(arabic?'استعادة كلمة المرور':'Reset password'),
        content:Text(msg),
        actions:[TextButton(onPressed:()=>Navigator.pop(ctx),child:Text(arabic?'تمام':'OK'))],
      ));
    }catch(e){
      if(mounted)setState(()=>error=e.toString());
    }finally{
      if(mounted)setState(()=>loading=false);
    }
  }

  @override
  Widget build(BuildContext context)=>Scaffold(
    appBar:AppBar(
      actions:[
        TextButton(
          onPressed:()async{
            final code=arabic?'en':'ar';
            await AppPreferences.instance.setLanguage(code);
            if(mounted)setState((){});
          },
          child:Text(arabic?'EN':'العربية'),
        ),
      ],
    ),
    body:SafeArea(child:Center(child:SingleChildScrollView(
      padding:const EdgeInsets.all(24),
      child:ConstrainedBox(
        constraints:const BoxConstraints(maxWidth:440),
        child:Column(crossAxisAlignment:CrossAxisAlignment.stretch,children:[
          Container(
            width:70,height:70,
            alignment:Alignment.center,
            decoration:BoxDecoration(color:WazenTheme.greenDark,borderRadius:BorderRadius.circular(22)),
            child:const Icon(Icons.eco_rounded,color:Colors.white,size:40),
          ),
          const SizedBox(height:18),
          Text(
            registerMode
              ?(arabic?'أنشئ حسابك':'Create your account')
              :(arabic?'أهلًا بعودتك':'Welcome back'),
            style:const TextStyle(fontSize:30,fontWeight:FontWeight.w900),
          ),
          const SizedBox(height:6),
          Text(
            registerMode
              ?(arabic?'ابدأ رحلتك مع وازن.':'Start your WAZEN journey.')
              :(arabic?'سجل دخولك وكمل يومك.':'Sign in and continue your day.'),
            style:const TextStyle(color:Colors.black54),
          ),
          const SizedBox(height:26),
          if(registerMode)...[
            TextField(
              controller:firstName,
              textInputAction:TextInputAction.next,
              decoration:InputDecoration(labelText:arabic?'الاسم الأول':'First name'),
            ),
            const SizedBox(height:12),
          ],
          TextField(
            controller:email,
            textDirection:TextDirection.ltr,
            keyboardType:TextInputType.emailAddress,
            textInputAction:TextInputAction.next,
            autocorrect:false,
            decoration:InputDecoration(labelText:arabic?'البريد الإلكتروني':'Email'),
          ),
          const SizedBox(height:12),
          TextField(
            controller:password,
            obscureText:true,
            textDirection:TextDirection.ltr,
            onSubmitted:(_)=>loading?null:submit(),
            decoration:InputDecoration(
              labelText:arabic?'كلمة المرور':'Password',
              helperText:registerMode
                ?(arabic?'8+ أحرف مع حرف كبير وصغير ورقم':'8+ chars with uppercase, lowercase and a number')
                :null,
            ),
          ),
          if(!registerMode)
            Align(
              alignment:AlignmentDirectional.centerEnd,
              child:TextButton(
                onPressed:loading?null:forgotPassword,
                child:Text(arabic?'نسيت كلمة المرور؟':'Forgot password?'),
              ),
            ),
          if(error!=null)Padding(
            padding:const EdgeInsets.only(top:12),
            child:Text(error!,style:const TextStyle(color:Colors.red)),
          ),
          const SizedBox(height:20),
          FilledButton(
            onPressed:loading?null:submit,
            child:Text(loading?'...':registerMode?(arabic?'إنشاء الحساب':'Create account'):(arabic?'تسجيل الدخول':'Sign in')),
          ),
          const SizedBox(height:10),
          OutlinedButton(
            onPressed:loading?null:()=>setState(()=>registerMode=!registerMode),
            child:Text(
              registerMode
                ?(arabic?'عندي حساب بالفعل':'I already have an account')
                :(arabic?'إنشاء حساب جديد':'Create a new account'),
            ),
          ),
          const SizedBox(height:14),
          TextButton.icon(
            onPressed:()=>setState(()=>showAdvanced=!showAdvanced),
            icon:Icon(showAdvanced?Icons.expand_less:Icons.settings_outlined,size:18),
            label:Text(arabic?'إعدادات الاتصال المتقدمة':'Advanced connection settings'),
          ),
          if(showAdvanced)...[
            const SizedBox(height:8),
            TextField(
              controller:apiUrl,
              textDirection:TextDirection.ltr,
              decoration:const InputDecoration(
                labelText:'API URL',
                helperText:'Developer / test environment only',
              ),
            ),
          ],
          const SizedBox(height:18),
          Text(
            arabic?'WAZEN | وازن\nالمناسب لك، الآن.':'WAZEN\nRight for you, now.',
            textAlign:TextAlign.center,
            style:const TextStyle(color:Colors.black45,height:1.5),
          ),
        ]),
      ),
    ))),
  );
}
