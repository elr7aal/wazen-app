
import 'package:flutter/material.dart';
import '../services/api_client.dart';
import '../services/app_preferences.dart';
import 'auth_screen.dart';
import 'home_screen.dart';
import 'onboarding_screen.dart';
import 'intro_flow_screen.dart';
import 'verification_required_screen.dart';

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
      final enforced=await WazenApi.instance.emailVerificationEnforced();
      if(enforced){
        final account=await WazenApi.instance.me();
        if(account['email_verified']!=true){
          if(mounted)setState(()=>page=const VerificationRequiredScreen());
          return;
        }
      }
      final complete=await WazenApi.instance.onboardingStatus();
      if(mounted)setState(()=>page=complete?const HomeScreen():const OnboardingScreen());
    }catch(e){
      final refreshed=await WazenApi.instance.refreshSession();
      if(refreshed){
        try{
          final enforced=await WazenApi.instance.emailVerificationEnforced();
          if(enforced){
            final account=await WazenApi.instance.me();
            if(account['email_verified']!=true){
              if(mounted)setState(()=>page=const VerificationRequiredScreen());
              return;
            }
          }
          final complete=await WazenApi.instance.onboardingStatus();
          if(mounted)setState(()=>page=complete?const HomeScreen():const OnboardingScreen());
          return;
        }catch(_){}
      }
      if(mounted)setState(()=>page=const AuthScreen());
    }
  }
  @override Widget build(BuildContext context)=>page??const Scaffold(body:Center(child:CircularProgressIndicator()));
}
