import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import '../models/api_models.dart';

class ApiException implements Exception {
  final String message;
  final int? statusCode;
  const ApiException(this.message, [this.statusCode]);
  @override
  String toString() => message;
}

class WazenApi {
  WazenApi._();
  static final WazenApi instance = WazenApi._();

  String baseUrl = const String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://127.0.0.1:8000/api/v1',
  );
  String? token;
  String? refreshToken;

  Future<void> restore() async {
    final prefs = await SharedPreferences.getInstance();
    baseUrl = prefs.getString('api_base_url') ?? baseUrl;
    token = prefs.getString('access_token');
    refreshToken = prefs.getString('refresh_token');
  }

  Future<void> configureBaseUrl(String value) async {
    final normalized = value.trim().replaceAll(RegExp(r'/$'), '');
    baseUrl = normalized.endsWith('/api/v1') ? normalized : '$normalized/api/v1';
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('api_base_url', baseUrl);
  }

  Map<String, String> get _headers => {
        'Content-Type': 'application/json',
        if (token != null) 'Authorization': 'Bearer $token',
      };

  dynamic _unwrap(http.Response response) {
    final body = response.body.isEmpty ? <String, dynamic>{} : jsonDecode(response.body);
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw ApiException(body is Map ? (body['detail'] ?? 'تعذر تنفيذ الطلب').toString() : 'تعذر تنفيذ الطلب', response.statusCode);
    }
    if (body is Map && body['success'] == false) {
      throw ApiException((body['error'] ?? 'تعذر تنفيذ الطلب').toString(), response.statusCode);
    }
    return body is Map ? body['data'] : body;
  }

  Future<void> register({required String email, required String password, String? firstName}) async {
    final r = await http.post(Uri.parse('$baseUrl/auth/register'), headers: _headers, body: jsonEncode({
      'email': email, 'password': password, 'first_name': firstName, 'language': 'ar',
    }));
    final data = _unwrap(r) as Map<String, dynamic>;
    await _saveSession(data);
  }

  Future<void> login(String email, String password) async {
    final r = await http.post(Uri.parse('$baseUrl/auth/login'), headers: _headers, body: jsonEncode({'email': email, 'password': password}));
    final data = _unwrap(r) as Map<String, dynamic>;
    await _saveSession(data);
  }

  Future<void> _saveSession(Map<String,dynamic> data) async {
    token = data['access_token']?.toString();
    refreshToken = data['refresh_token']?.toString();
    final prefs = await SharedPreferences.getInstance();
    if(token!=null)await prefs.setString('access_token',token!);
    if(refreshToken!=null)await prefs.setString('refresh_token',refreshToken!);
  }

  Future<bool> refreshSession() async {
    final value=refreshToken;
    if(value==null||value.isEmpty)return false;
    try{
      final r=await http.post(
        Uri.parse('$baseUrl/auth/refresh'),
        headers:{'Content-Type':'application/json'},
        body:jsonEncode({'refresh_token':value}),
      );
      final data=Map<String,dynamic>.from(_unwrap(r));
      await _saveSession(data);
      return true;
    }catch(_){
      await clearSession();
      return false;
    }
  }

  Future<void> clearSession() async {
    token=null;
    refreshToken=null;
    final prefs=await SharedPreferences.getInstance();
    await prefs.remove('access_token');
    await prefs.remove('refresh_token');
  }

  Future<void> logout({bool allSessions=false}) async {
    final access=token;
    final refresh=refreshToken;
    if(access!=null&&refresh!=null){
      try{
        await http.post(
          Uri.parse('$baseUrl/auth/logout'),
          headers:_headers,
          body:jsonEncode({'refresh_token':refresh,'all_sessions':allSessions}),
        );
      }catch(_){}
    }
    await clearSession();
  }

  Future<Map<String, dynamic>> me() async {
    final r = await http.get(Uri.parse('$baseUrl/users/me'), headers: _headers);
    return Map<String, dynamic>.from(_unwrap(r));
  }

  Future<DailyState> todayState() async {
    final r = await http.get(Uri.parse('$baseUrl/nutrition/today'), headers: _headers);
    final data = Map<String, dynamic>.from(_unwrap(r));
    return DailyState.fromJson(Map<String, dynamic>.from(data['daily_state']));
  }

  Future<List<RecommendationItem>> goldenFlow(String craving) async {
    final r = await http.post(Uri.parse('$baseUrl/golden-flow'), headers: _headers, body: jsonEncode({
      'craving_text': craving,
      'meal_type': 'DINNER',
      'allow_modifications': true,
    }));
    final data = Map<String, dynamic>.from(_unwrap(r));
    final recommendation = Map<String, dynamic>.from(data['recommendations']);
    return ((recommendation['results'] as List?) ?? const [])
        .map((e) => RecommendationItem.fromJson(Map<String, dynamic>.from(e as Map)))
        .toList();
  }

  Future<FoodDetail> foodDetail(String foodId) async {
    final r = await http.get(Uri.parse('$baseUrl/foods/$foodId'), headers: _headers);
    return FoodDetail.fromJson(Map<String, dynamic>.from(_unwrap(r)));
  }

  Future<DailyState> logFromCatalog(String foodId, {String mealType = 'DINNER', double quantity = 1}) async {
    final r = await http.post(Uri.parse('$baseUrl/food-log/from-catalog'), headers: _headers, body: jsonEncode({
      'food_id': foodId,
      'meal_type': mealType,
      'quantity': quantity,
      'entry_method': 'RECOMMENDATION',
    }));
    final data = Map<String, dynamic>.from(_unwrap(r));
    return DailyState.fromJson(Map<String, dynamic>.from(data['daily_state']));
  }


  Future<List<ModifierOption>> makeItFitOptions(String foodId) async {
    final r=await http.get(Uri.parse('$baseUrl/foods/$foodId/make-it-fit-options'),headers:_headers);
    final data=Map<String,dynamic>.from(_unwrap(r));
    return ((data['options'] as List?)??const []).map((e)=>ModifierOption.fromJson(Map<String,dynamic>.from(e as Map))).toList();
  }

  Future<MakeItFitPreview> makeItFitPreview(String foodId,List<String> components) async {
    final sr=await http.get(Uri.parse('$baseUrl/nutrition/today'),headers:_headers);
    final sd=Map<String,dynamic>.from(_unwrap(sr));
    final r=await http.post(Uri.parse('$baseUrl/recommendations/make-it-fit'),headers:_headers,body:jsonEncode({
      'food_id':foodId,
      'daily_state':Map<String,dynamic>.from(sd['daily_request'] as Map),
      'included_components':components,
    }));
    return MakeItFitPreview.fromJson(Map<String,dynamic>.from(_unwrap(r)));
  }

  Future<DailyState> logModifiedFromCatalog(String foodId,List<String> components,{String mealType='DINNER',double quantity=1}) async {
    final r=await http.post(Uri.parse('$baseUrl/food-log/from-modified-catalog'),headers:_headers,body:jsonEncode({
      'food_id':foodId,'meal_type':mealType,'quantity':quantity,'included_components':components,
    }));
    final data=Map<String,dynamic>.from(_unwrap(r));
    return DailyState.fromJson(Map<String,dynamic>.from(data['daily_state']));
  }



  Future<RebalanceData> rebalanceForMe() async {
    final r = await http.get(Uri.parse('$baseUrl/rebalance/for-me'), headers: _headers);
    return RebalanceData.fromJson(Map<String, dynamic>.from(_unwrap(r)));
  }



  Future<FoodLogDay> foodLogToday() async {
    final r=await http.get(Uri.parse('$baseUrl/food-log/today'),headers:_headers);
    return FoodLogDay.fromJson(Map<String,dynamic>.from(_unwrap(r)));
  }

  Future<FoodLogDay> deleteFoodLog(String logId) async {
    final r=await http.delete(Uri.parse('$baseUrl/food-log/$logId'),headers:_headers);
    _unwrap(r);
    return foodLogToday();
  }

  Future<FoodLogDay> updateFoodLog(
    String logId, {
    String? mealType,
    double? calories,
    double? proteinG,
    double? carbsG,
    double? fatG,
    double? sodiumMg,
  }) async {
    final body=<String,dynamic>{
      if(mealType!=null)'meal_type':mealType,
      if(calories!=null)'calories':calories,
      if(proteinG!=null)'protein_g':proteinG,
      if(carbsG!=null)'carbs_g':carbsG,
      if(fatG!=null)'fat_g':fatG,
      if(sodiumMg!=null)'sodium_mg':sodiumMg,
    };
    final r=await http.patch(Uri.parse('$baseUrl/food-log/$logId'),headers:_headers,body:jsonEncode(body));
    _unwrap(r);
    return foodLogToday();
  }



  Future<List<FoodDetail>> searchFoods(String query) async {
    final uri=Uri.parse('$baseUrl/foods/search').replace(queryParameters:{'q':query,'limit':'25'});
    final r=await http.get(uri,headers:_headers);
    final data=Map<String,dynamic>.from(_unwrap(r));
    return ((data['items'] as List?)??const []).map((e)=>FoodDetail.fromJson(Map<String,dynamic>.from(e as Map))).toList();
  }

  Future<FoodDetail?> barcodeLookup(String barcode) async {
    final r=await http.get(Uri.parse('$baseUrl/foods/barcode/$barcode'),headers:_headers);
    final data=Map<String,dynamic>.from(_unwrap(r));
    if(data['found']!=true || data['item']==null)return null;
    return FoodDetail.fromJson(Map<String,dynamic>.from(data['item'] as Map));
  }

  Future<List<FoodDetail>> parseFoodText(String text,{String mealType='SNACK'}) async {
    final r=await http.post(Uri.parse('$baseUrl/food-log/parse-text'),headers:_headers,body:jsonEncode({'text':text,'meal_type':mealType}));
    final data=Map<String,dynamic>.from(_unwrap(r));
    return ((data['candidates'] as List?)??const []).map((e)=>FoodDetail.fromJson(Map<String,dynamic>.from(e as Map))).toList();
  }

  Future<Map<String,dynamic>> analyzeFoodImage(String imageBase64,{String? caption,String mealType='SNACK'}) async {
    final r=await http.post(Uri.parse('$baseUrl/food-log/analyze-image'),headers:_headers,body:jsonEncode({
      'image_base64':imageBase64,'user_caption':caption,'meal_type':mealType,
    }));
    return Map<String,dynamic>.from(_unwrap(r));
  }



  Future<bool> onboardingStatus() async {
    final r=await http.get(Uri.parse('$baseUrl/onboarding/status'),headers:_headers);
    final data=Map<String,dynamic>.from(_unwrap(r));
    return data['complete']==true;
  }

  Future<Map<String,dynamic>> completeOnboarding(Map<String,dynamic> payload) async {
    final r=await http.post(Uri.parse('$baseUrl/onboarding/complete'),headers:_headers,body:jsonEncode(payload));
    return Map<String,dynamic>.from(_unwrap(r));
  }



  Future<void> sendRecommendationFeedback(String foodId,String action) async {
    final r=await http.post(Uri.parse('$baseUrl/recommendations/feedback'),headers:_headers,body:jsonEncode({
      'food_id':foodId,'action':action,
    }));
    _unwrap(r);
  }



  Future<Map<String,dynamic>> updateProfile(Map<String,dynamic> payload) async {
    final r=await http.patch(Uri.parse('$baseUrl/users/me'),headers:_headers,body:jsonEncode(payload));
    return Map<String,dynamic>.from(_unwrap(r));
  }

  Future<Map<String,dynamic>> recalculatePlan(Map<String,dynamic> payload) async {
    final r=await http.post(Uri.parse('$baseUrl/profile/recalculate-plan'),headers:_headers,body:jsonEncode(payload));
    return Map<String,dynamic>.from(_unwrap(r));
  }

  Future<Map<String,dynamic>> profileInsights() async {
    final r=await http.get(Uri.parse('$baseUrl/profile/insights'),headers:_headers);
    return Map<String,dynamic>.from(_unwrap(r));
  }


  Future<WeeklyPlan> weeklyPlan() async {
    final r=await http.get(Uri.parse('$baseUrl/plan/week'),headers:_headers);
    return WeeklyPlan.fromJson(Map<String,dynamic>.from(_unwrap(r)));
  }

  Future<WeeklyPlan> regenerateWeeklyPlan() async {
    final r=await http.post(Uri.parse('$baseUrl/plan/week/generate'),headers:_headers);
    return WeeklyPlan.fromJson(Map<String,dynamic>.from(_unwrap(r)));
  }

  Future<WeeklyPlan> rebalancePlanDay(DateTime date) async {
    final d='${date.year.toString().padLeft(4,'0')}-${date.month.toString().padLeft(2,'0')}-${date.day.toString().padLeft(2,'0')}';
    final r=await http.post(Uri.parse('$baseUrl/plan/day/$d/rebalance'),headers:_headers);
    return WeeklyPlan.fromJson(Map<String,dynamic>.from(_unwrap(r)));
  }

  Future<ProgressSummary> progress(String range) async {
    final uri=Uri.parse('$baseUrl/progress').replace(queryParameters:{'range':range});
    final r=await http.get(uri,headers:_headers);
    return ProgressSummary.fromJson(Map<String,dynamic>.from(_unwrap(r)));
  }


  Future<Map<String,dynamic>> forgotPassword(String email) async {
    final r=await http.post(
      Uri.parse('$baseUrl/auth/forgot-password'),
      headers:{'Content-Type':'application/json'},
      body:jsonEncode({'email':email.trim()}),
    );
    return Map<String,dynamic>.from(_unwrap(r));
  }

  Future<void> resetPassword(String resetToken,String newPassword) async {
    final r=await http.post(
      Uri.parse('$baseUrl/auth/reset-password'),
      headers:{'Content-Type':'application/json'},
      body:jsonEncode({'token':resetToken,'new_password':newPassword}),
    );
    _unwrap(r);
  }


  Future<List<Map<String,dynamic>>> goalHistory({int limit=20}) async {
    final uri=Uri.parse('$baseUrl/profile/history').replace(queryParameters:{'limit':'$limit'});
    final r=await http.get(uri,headers:_headers);
    final data=Map<String,dynamic>.from(_unwrap(r));
    return ((data['items'] as List?)??const [])
      .map((e)=>Map<String,dynamic>.from(e as Map)).toList();
  }

}
