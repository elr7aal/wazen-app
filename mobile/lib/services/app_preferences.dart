import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

class AppPreferences {
  AppPreferences._();
  static final AppPreferences instance=AppPreferences._();

  final ValueNotifier<String> language=ValueNotifier<String>('ar');
  bool introSeen=false;

  Future<void> restore() async {
    final prefs=await SharedPreferences.getInstance();
    language.value=prefs.getString('app_language')??'ar';
    introSeen=prefs.getBool('intro_seen')??false;
  }

  Future<void> setLanguage(String code) async {
    final normalized=code=='en'?'en':'ar';
    language.value=normalized;
    final prefs=await SharedPreferences.getInstance();
    await prefs.setString('app_language',normalized);
  }

  Future<void> markIntroSeen() async {
    introSeen=true;
    final prefs=await SharedPreferences.getInstance();
    await prefs.setBool('intro_seen',true);
  }

  Future<void> resetIntro() async {
    introSeen=false;
    final prefs=await SharedPreferences.getInstance();
    await prefs.remove('intro_seen');
  }
}
