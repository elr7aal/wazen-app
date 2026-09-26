import 'package:flutter/material.dart';
import '../services/api_client.dart';
import 'startup_gate.dart';

class VerifyEmailScreen extends StatefulWidget{
  final String token;
  const VerifyEmailScreen({super.key,required this.token});

  @override
  State<VerifyEmailScreen> createState()=>_VerifyEmailScreenState();
}

class _VerifyEmailScreenState extends State<VerifyEmailScreen>{
  bool loading=true;
  bool verified=false;
  String? error;

  @override
  void initState(){
    super.initState();
    _verify();
  }

  Future<void> _verify()async{
    setState((){loading=true;error=null;});
    try{
      await WazenApi.instance.verifyEmail(widget.token);
      if(mounted)setState(()=>verified=true);
    }catch(e){
      if(mounted)setState(()=>error=e.toString());
    }finally{
      if(mounted)setState(()=>loading=false);
    }
  }

  @override
  Widget build(BuildContext context)=>Scaffold(
    appBar:AppBar(title:const Text('تأكيد البريد الإلكتروني')),
    body:SafeArea(child:Center(child:SingleChildScrollView(
      padding:const EdgeInsets.all(24),
      child:ConstrainedBox(
        constraints:const BoxConstraints(maxWidth:440),
        child:Column(
          crossAxisAlignment:CrossAxisAlignment.stretch,
          children:[
            Icon(
              verified?Icons.mark_email_read_rounded:Icons.mark_email_unread_outlined,
              size:76,
              color:verified?Colors.green:null,
            ),
            const SizedBox(height:20),
            if(loading)...[
              const LinearProgressIndicator(),
              const SizedBox(height:18),
              const Text('جاري تأكيد بريدك الإلكتروني...',textAlign:TextAlign.center),
            ]else if(verified)...[
              const Text(
                'تم تأكيد بريدك الإلكتروني',
                textAlign:TextAlign.center,
                style:TextStyle(fontSize:26,fontWeight:FontWeight.w900),
              ),
              const SizedBox(height:8),
              const Text(
                'صار بريد حساب WAZEN موثّقًا.',
                textAlign:TextAlign.center,
                style:TextStyle(color:Colors.black54),
              ),
              const SizedBox(height:24),
              FilledButton(
                onPressed:()=>Navigator.pushAndRemoveUntil(
                  context,
                  MaterialPageRoute(builder:(_)=>const StartupGate()),
                  (_)=>false,
                ),
                child:const Text('متابعة'),
              ),
            ]else...[
              const Text(
                'تعذر تأكيد البريد',
                textAlign:TextAlign.center,
                style:TextStyle(fontSize:26,fontWeight:FontWeight.w900),
              ),
              const SizedBox(height:8),
              Text(
                error??'الرابط غير صالح أو انتهت صلاحيته.',
                textAlign:TextAlign.center,
                style:const TextStyle(color:Colors.red,height:1.5),
              ),
              const SizedBox(height:24),
              OutlinedButton(
                onPressed:_verify,
                child:const Text('حاول مرة ثانية'),
              ),
            ],
          ],
        ),
      ),
    ))),
  );
}
