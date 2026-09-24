import 'dart:async';
import 'package:flutter/material.dart';
import '../core/theme.dart';
import '../services/app_preferences.dart';
import 'auth_screen.dart';

class IntroFlowScreen extends StatefulWidget {
  const IntroFlowScreen({super.key});
  @override
  State<IntroFlowScreen> createState()=>_IntroFlowScreenState();
}

class _IntroFlowScreenState extends State<IntroFlowScreen> {
  int step=0;
  Timer? timer;

  bool get arabic=>AppPreferences.instance.language.value=='ar';

  @override
  void initState(){
    super.initState();
    timer=Timer(const Duration(milliseconds:1200),(){
      if(mounted&&step==0)setState(()=>step=1);
    });
  }

  @override
  void dispose(){
    timer?.cancel();
    super.dispose();
  }

  Future<void> chooseLanguage(String code) async {
    await AppPreferences.instance.setLanguage(code);
    if(mounted)setState(()=>step=2);
  }

  Future<void> finishToEmail() async {
    await AppPreferences.instance.markIntroSeen();
    if(!mounted)return;
    Navigator.pushReplacement(context,MaterialPageRoute(builder:(_)=>const AuthScreen()));
  }

  void unavailable(String label){
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content:Text(arabic?'$label يحتاج ربط مزود دخول آمن قبل التفعيل.':'$label requires a secure sign-in provider before activation.'),
    ));
  }

  @override
  Widget build(BuildContext context){
    if(step==0)return _splash();
    if(step==1)return _language();
    if(step==2)return _welcome();
    return _accountOptions();
  }

  Widget _splash()=>Scaffold(
    body:Container(
      width:double.infinity,
      decoration:const BoxDecoration(
        gradient:LinearGradient(
          begin:Alignment.topCenter,
          end:Alignment.bottomCenter,
          colors:[Color(0xFFF7F4E8),Color(0xFFFFFFFF)],
        ),
      ),
      child:SafeArea(child:Column(
        mainAxisAlignment:MainAxisAlignment.center,
        children:[
          Container(
            width:92,height:92,
            decoration:BoxDecoration(color:WazenTheme.greenDark,borderRadius:BorderRadius.circular(28)),
            child:const Icon(Icons.eco_rounded,color:Colors.white,size:52),
          ),
          const SizedBox(height:24),
          const Text('WAZEN',style:TextStyle(fontSize:34,fontWeight:FontWeight.w900,letterSpacing:7,color:WazenTheme.greenDark)),
          const SizedBox(height:4),
          const Text('وازن',style:TextStyle(fontSize:30,fontWeight:FontWeight.w900)),
          const SizedBox(height:12),
          const Text('المناسب لك، الآن.',style:TextStyle(fontSize:18,color:Colors.black54)),
        ],
      )),
    ),
  );

  Widget _language()=>Scaffold(
    body:SafeArea(child:Padding(
      padding:const EdgeInsets.all(24),
      child:Column(crossAxisAlignment:CrossAxisAlignment.stretch,children:[
        const Spacer(),
        const Icon(Icons.language_rounded,size:60,color:WazenTheme.greenDark),
        const SizedBox(height:24),
        const Text('اختر لغتك',textAlign:TextAlign.center,style:TextStyle(fontSize:30,fontWeight:FontWeight.w900)),
        const SizedBox(height:6),
        const Text('You can change this later',textAlign:TextAlign.center,style:TextStyle(color:Colors.black54)),
        const SizedBox(height:28),
        _languageTile('العربية','ar'),
        const SizedBox(height:12),
        _languageTile('English','en'),
        const Spacer(flex:2),
      ]),
    )),
  );

  Widget _languageTile(String label,String code){
    final selected=AppPreferences.instance.language.value==code;
    return InkWell(
      borderRadius:BorderRadius.circular(18),
      onTap:()=>chooseLanguage(code),
      child:Container(
        padding:const EdgeInsets.symmetric(horizontal:18,vertical:18),
        decoration:BoxDecoration(
          color:selected?WazenTheme.beige:Colors.white,
          border:Border.all(color:selected?WazenTheme.green:const Color(0xFFDADFDA),width:selected?2:1),
          borderRadius:BorderRadius.circular(18),
        ),
        child:Row(children:[
          Expanded(child:Text(label,style:const TextStyle(fontSize:18,fontWeight:FontWeight.w800))),
          Icon(selected?Icons.radio_button_checked:Icons.radio_button_off,color:selected?WazenTheme.green:Colors.black38),
        ]),
      ),
    );
  }

  Widget _welcome()=>Scaffold(
    body:SafeArea(child:Padding(
      padding:const EdgeInsets.all(24),
      child:Column(crossAxisAlignment:CrossAxisAlignment.stretch,children:[
        const Spacer(),
        Container(
          height:220,
          decoration:BoxDecoration(color:WazenTheme.beige,borderRadius:BorderRadius.circular(32)),
          child:const Icon(Icons.ramen_dining_rounded,size:110,color:WazenTheme.greenDark),
        ),
        const SizedBox(height:28),
        Text(
          arabic?'أكلك يناسب حياتك\nمو العكس.':'Your food should fit your life.\nNot the other way around.',
          style:const TextStyle(fontSize:31,fontWeight:FontWeight.w900,height:1.2),
        ),
        const SizedBox(height:14),
        Text(
          arabic
            ?'وازن يساعدك تعرف ماذا تأكل وتشتري بناءً على هدفك، ذوقك، نشاطك وما هو متوفر حولك.'
            :'WAZEN helps you decide what to eat and buy based on your goal, taste, activity and what is available around you.',
          style:const TextStyle(fontSize:16,color:Colors.black54,height:1.55),
        ),
        const Spacer(),
        FilledButton(
          onPressed:()=>setState(()=>step=3),
          child:Text(arabic?'ابدأ':'Get started'),
        ),
        const SizedBox(height:10),
        OutlinedButton(
          onPressed:finishToEmail,
          child:Text(arabic?'تسجيل الدخول':'Sign in'),
        ),
      ]),
    )),
  );

  Widget _accountOptions()=>Scaffold(
    appBar:AppBar(
      leading:IconButton(icon:const Icon(Icons.arrow_back),onPressed:()=>setState(()=>step=2)),
    ),
    body:SafeArea(child:SingleChildScrollView(
      padding:const EdgeInsets.all(24),
      child:Column(crossAxisAlignment:CrossAxisAlignment.stretch,children:[
        Text(arabic?'أنشئ حسابك':'Create your account',style:const TextStyle(fontSize:30,fontWeight:FontWeight.w900)),
        const SizedBox(height:8),
        Text(arabic?'اختر الطريقة المناسبة لك.':'Choose the method that works for you.',style:const TextStyle(color:Colors.black54)),
        const SizedBox(height:28),
        _provider(Icons.apple,'Apple',()=>unavailable('Apple Sign in')),
        const SizedBox(height:10),
        _provider(Icons.g_mobiledata_rounded,'Google',()=>unavailable('Google Sign in')),
        const SizedBox(height:10),
        _provider(Icons.email_outlined,arabic?'البريد الإلكتروني':'Email',finishToEmail),
        const SizedBox(height:10),
        _provider(Icons.phone_iphone_rounded,arabic?'رقم الجوال':'Mobile number',()=>unavailable('Mobile Sign in')),
        const SizedBox(height:24),
        Text(
          arabic?'بالاستمرار، فإنك توافق على الشروط وسياسة الخصوصية.':'By continuing, you agree to the Terms and Privacy Policy.',
          textAlign:TextAlign.center,
          style:const TextStyle(fontSize:12,color:Colors.black45,height:1.4),
        ),
      ]),
    )),
  );

  Widget _provider(IconData icon,String label,VoidCallback onTap)=>OutlinedButton.icon(
    onPressed:onTap,
    icon:Icon(icon),
    label:Padding(
      padding:const EdgeInsets.symmetric(vertical:14),
      child:Text(label,style:const TextStyle(fontSize:17,fontWeight:FontWeight.w700)),
    ),
  );
}
