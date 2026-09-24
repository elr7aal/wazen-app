
import 'package:flutter/material.dart';
import '../services/api_client.dart';
import '../services/app_preferences.dart';
import 'auth_screen.dart';
import 'home_screen.dart';
import 'onboarding_screen.dart';
import 'intro_flow_screen.dart';

class StartupGate extends StatefulWidget{
  const StartupGate({super.key});
  @override State<StartupGate> createState()=>_StartupGateState();
}
class _StartupGateState extends State<StartupGate>{
  Widget? page;
  @override void initState(){super.initState();load();}
  Future<void> load()async{
    if(WazenApi.instance.token==null){
      setState(()=>page=AppPreferences.instance.introSeen?const AuthScreen():const IntroFlowScreen());
      return;
    }
    try{
      final complete=await WazenApi.instance.onboardingStatus();
      if(mounted)setState(()=>page=complete?const HomeScreen():const OnboardingScreen());
    }catch(_){
      if(mounted)setState(()=>page=const AuthScreen());
    }
  }
  @override Widget build(BuildContext context)=>page??const Scaffold(body:Center(child:CircularProgressIndicator()));
}
