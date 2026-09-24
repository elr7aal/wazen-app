
import 'package:flutter/material.dart';
import '../services/api_client.dart';
import 'auth_screen.dart';
import 'home_screen.dart';
import 'onboarding_screen.dart';

class StartupGate extends StatefulWidget{
  const StartupGate({super.key});
  @override State<StartupGate> createState()=>_StartupGateState();
}
class _StartupGateState extends State<StartupGate>{
  Widget? page;
  @override void initState(){super.initState();load();}
  Future<void> load()async{
    if(WazenApi.instance.token==null){setState(()=>page=const AuthScreen());return;}
    try{
      final complete=await WazenApi.instance.onboardingStatus();
      if(mounted)setState(()=>page=complete?const HomeScreen():const OnboardingScreen());
    }catch(_){
      if(mounted)setState(()=>page=const AuthScreen());
    }
  }
  @override Widget build(BuildContext context)=>page??const Scaffold(body:Center(child:CircularProgressIndicator()));
}
