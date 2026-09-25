import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
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
  static const FlutterSecureStorage _secureStorage=FlutterSecureStorage();
  static const String _accessTokenKey='wazen_access_token';
  static const String _refreshTokenKey='wazen_refresh_token';

  String? token;
  String? refreshToken;
  int _idempotencyCounter=0;

  Future<void> restore() async {
    final prefs = await SharedPreferences.getInstance();
    baseUrl = prefs.getString('api_base_url') ?? baseUrl;

    try{
      token=await _secureStorage.read(key:_accessTokenKey);
      refreshToken=await _secureStorage.read(key:_refreshTokenKey);

      // One-time migration from the pre-v42 SharedPreferences session.
      final legacyAccess=prefs.getString('access_token');
      final legacyRefresh=prefs.getString('refresh_token');
      if(token==null&&legacyAccess!=null){
        token=legacyAccess;
        await _secureStorage.write(key:_accessTokenKey,value:legacyAccess);
      }
      if(refreshToken==null&&legacyRefresh!=null){
        refreshToken=legacyRefresh;
        await _secureStorage.write(key:_refreshTokenKey,value:legacyRefresh);
      }
      if(legacyAccess!=null)await prefs.remove('access_token');
      if(legacyRefresh!=null)await prefs.remove('refresh_token');
    }catch(_){
      // Never fall back to persisting authentication tokens in plain preferences.
      token=null;
      refreshToken=null;
    }
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

  String _newIdempotencyKey(String action){
    _idempotencyCounter++;
    return 'mobile-$action-${DateTime.now().microsecondsSinceEpoch}-$_idempotencyCounter';
  }

  Map<String,String> _writeHeaders(String key)=>{
    ..._headers,
    'Idempotency-Key':key,
  };


  Future<bool>? _refreshInFlight;

  Future<bool> _refreshOnce() {
    final current=_refreshInFlight;
    if(current!=null)return current;

    final future=refreshSession();
    _refreshInFlight=future;
    future.whenComplete((){
      if(identical(_refreshInFlight,future))_refreshInFlight=null;
    });
    return future;
  }

  Future<http.Response> _withAuthRetry(
    Future<http.Response> Function() request,
  ) async {
    var response=await request();
    if(response.statusCode!=401 || refreshToken==null || refreshToken!.isEmpty){
      return response;
    }

    final refreshed=await _refreshOnce();
    if(!refreshed)return response;

    response=await request();
    return response;
  }

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
    token=data['access_token']?.toString();
    refreshToken=data['refresh_token']?.toString();
    if(token!=null)await _secureStorage.write(key:_accessTokenKey,value:token!);
    if(refreshToken!=null)await _secureStorage.write(key:_refreshTokenKey,value:refreshToken!);

    final prefs=await SharedPreferences.getInstance();
    await prefs.remove('access_token');
    await prefs.remove('refresh_token');
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
      if(r.statusCode==401){
        await clearSession();
        return false;
      }
      final data=Map<String,dynamic>.from(_unwrap(r));
      await _saveSession(data);
      return true;
    }catch(_){
      // Network/server errors are not proof that the refresh token is invalid.
      // Keep the local session so it can be retried when connectivity returns.
      return false;
    }
  }

  Future<void> clearSession() async {
    token=null;
    refreshToken=null;
    await _secureStorage.delete(key:_accessTokenKey);
    await _secureStorage.delete(key:_refreshTokenKey);

    // Clean up any pre-v42 values as a defense-in-depth migration step.
    final prefs=await SharedPreferences.getInstance();
    await prefs.remove('access_token');
    await prefs.remove('refresh_token');
  }

  Future<void> logout({bool allSessions=false}) async {
    final access=token;
    final refresh=refreshToken;
    if(access!=null&&refresh!=null){
      try{
        await _withAuthRetry(()=>http.post(
          Uri.parse('$baseUrl/auth/logout'),
          headers:_headers,
          body:jsonEncode({'refresh_token':refreshToken,'all_sessions':allSessions}),
        ));
      }catch(_){}
    }
    await clearSession();
  }

  Future<Map<String, dynamic>> me() async {
    final r = await _withAuthRetry(()=>http.get(Uri.parse('$baseUrl/users/me'), headers: _headers));
    return Map<String, dynamic>.from(_unwrap(r));
  }

  Future<DailyState> todayState() async {
    final r = await _withAuthRetry(()=>http.get(Uri.parse('$baseUrl/nutrition/today'), headers: _headers));
    final data = Map<String, dynamic>.from(_unwrap(r));
    return DailyState.fromJson(Map<String, dynamic>.from(data['daily_state']));
  }



  Future<Map<String,dynamic>> parseCraving(String text) async {
    final r=await _withAuthRetry(()=>http.post(
      Uri.parse('$baseUrl/cravings/parse'),
      headers:_headers,
      body:jsonEncode({'text':text}),
    ));
    return Map<String,dynamic>.from(_unwrap(r));
  }
  Future<List<RecommendationItem>> goldenFlow(String craving) async {
    final key=_newIdempotencyKey('golden');
    final r = await _withAuthRetry(()=>http.post(Uri.parse('$baseUrl/golden-flow'), headers: _writeHeaders(key), body: jsonEncode({
      'craving_text': craving,
      'meal_type': 'DINNER',
      'allow_modifications': true,
    })));
    final data = Map<String, dynamic>.from(_unwrap(r));
    final recommendation = Map<String, dynamic>.from(data['recommendations']);
    return ((recommendation['results'] as List?) ?? const [])
        .map((e) => RecommendationItem.fromJson(Map<String, dynamic>.from(e as Map)))
        .toList();
  }

  Future<FoodDetail> foodDetail(String foodId) async {
    final r = await _withAuthRetry(()=>http.get(Uri.parse('$baseUrl/foods/$foodId'), headers: _headers));
    return FoodDetail.fromJson(Map<String, dynamic>.from(_unwrap(r)));
  }

  Future<DailyState> logFromCatalog(String foodId, {String mealType = 'DINNER', double quantity = 1}) async {
    final key=_newIdempotencyKey('catalog');
    final r = await _withAuthRetry(()=>http.post(Uri.parse('$baseUrl/food-log/from-catalog'), headers: _writeHeaders(key), body: jsonEncode({
      'food_id': foodId,
      'meal_type': mealType,
      'quantity': quantity,
      'entry_method': 'RECOMMENDATION',
    })));
    final data = Map<String, dynamic>.from(_unwrap(r));
    return DailyState.fromJson(Map<String, dynamic>.from(data['daily_state']));
  }


  Future<List<ModifierOption>> makeItFitOptions(String foodId) async {
    final r=await _withAuthRetry(()=>http.get(Uri.parse('$baseUrl/foods/$foodId/make-it-fit-options'),headers:_headers));
    final data=Map<String,dynamic>.from(_unwrap(r));
    return ((data['options'] as List?)??const []).map((e)=>ModifierOption.fromJson(Map<String,dynamic>.from(e as Map))).toList();
  }

  Future<MakeItFitPreview> makeItFitPreview(String foodId,List<String> components) async {
    final sr=await _withAuthRetry(()=>http.get(Uri.parse('$baseUrl/nutrition/today'),headers:_headers));
    final sd=Map<String,dynamic>.from(_unwrap(sr));
    final r=await _withAuthRetry(()=>http.post(Uri.parse('$baseUrl/recommendations/make-it-fit'),headers:_headers,body:jsonEncode({
      'food_id':foodId,
      'daily_state':Map<String,dynamic>.from(sd['daily_request'] as Map),
      'included_components':components,
    })));
    return MakeItFitPreview.fromJson(Map<String,dynamic>.from(_unwrap(r)));
  }

  Future<DailyState> logModifiedFromCatalog(String foodId,List<String> components,{String mealType='DINNER',double quantity=1}) async {
    final key=_newIdempotencyKey('modified');
    final r=await _withAuthRetry(()=>http.post(Uri.parse('$baseUrl/food-log/from-modified-catalog'),headers:_writeHeaders(key),body:jsonEncode({
      'food_id':foodId,'meal_type':mealType,'quantity':quantity,'included_components':components,
    })));
    final data=Map<String,dynamic>.from(_unwrap(r));
    return DailyState.fromJson(Map<String,dynamic>.from(data['daily_state']));
  }



  Future<RebalanceData> rebalanceForMe() async {
    final r = await _withAuthRetry(()=>http.get(Uri.parse('$baseUrl/rebalance/for-me'), headers: _headers));
    return RebalanceData.fromJson(Map<String, dynamic>.from(_unwrap(r)));
  }



  Future<FoodLogDay> foodLogToday() async {
    final r=await _withAuthRetry(()=>http.get(Uri.parse('$baseUrl/food-log/today'),headers:_headers));
    return FoodLogDay.fromJson(Map<String,dynamic>.from(_unwrap(r)));
  }

  Future<FoodLogDay> deleteFoodLog(String logId) async {
    final r=await _withAuthRetry(()=>http.delete(Uri.parse('$baseUrl/food-log/$logId'),headers:_headers));
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
    final r=await _withAuthRetry(()=>http.patch(Uri.parse('$baseUrl/food-log/$logId'),headers:_headers,body:jsonEncode(body)));
    _unwrap(r);
    return foodLogToday();
  }



  Future<List<FoodDetail>> searchFoods(
    String query, {
    String? vendor,
    String? brand,
    String? category,
    String? foodType,
    double? maxCalories,
    double? minProteinG,
    double? maxSodiumMg,
    double? maxPrice,
    int limit=25,
  }) async {
    final params=<String,String>{
      if(query.trim().isNotEmpty)'q':query.trim(),
      if(vendor!=null&&vendor.isNotEmpty)'vendor':vendor,
      if(brand!=null&&brand.isNotEmpty)'brand':brand,
      if(category!=null&&category.isNotEmpty)'category':category,
      if(foodType!=null&&foodType.isNotEmpty)'food_type':foodType,
      if(maxCalories!=null)'max_calories':'$maxCalories',
      if(minProteinG!=null)'min_protein_g':'$minProteinG',
      if(maxSodiumMg!=null)'max_sodium_mg':'$maxSodiumMg',
      if(maxPrice!=null)'max_price':'$maxPrice',
      'limit':'$limit',
    };
    final uri=Uri.parse('$baseUrl/foods/search').replace(queryParameters:params);
    final r=await _withAuthRetry(()=>http.get(uri,headers:_headers));
    final data=Map<String,dynamic>.from(_unwrap(r));
    return ((data['items'] as List?)??const [])
      .map((e)=>FoodDetail.fromJson(Map<String,dynamic>.from(e as Map))).toList();
  }

  Future<FoodDetail?> barcodeLookup(String barcode) async {
    final r=await _withAuthRetry(()=>http.get(Uri.parse('$baseUrl/foods/barcode/$barcode'),headers:_headers));
    final data=Map<String,dynamic>.from(_unwrap(r));
    if(data['found']!=true || data['item']==null)return null;
    return FoodDetail.fromJson(Map<String,dynamic>.from(data['item'] as Map));
  }

  Future<Map<String,dynamic>> parseFoodTextDetailed(String text,{String mealType='SNACK'}) async {
    final r=await _withAuthRetry(()=>http.post(
      Uri.parse('$baseUrl/food-log/parse-text'),
      headers:_headers,
      body:jsonEncode({'text':text,'meal_type':mealType}),
    ));
    return Map<String,dynamic>.from(_unwrap(r));
  }

  Future<List<FoodDetail>> parseFoodText(String text,{String mealType='SNACK'}) async {
    final data=await parseFoodTextDetailed(text,mealType:mealType);
    return ((data['candidates'] as List?)??const [])
      .map((e)=>FoodDetail.fromJson(Map<String,dynamic>.from(e as Map))).toList();
  }

  Future<Map<String,dynamic>> analyzeFoodImage(String imageBase64,{String? caption,String mealType='SNACK'}) async {
    final r=await _withAuthRetry(()=>http.post(Uri.parse('$baseUrl/food-log/analyze-image'),headers:_headers,body:jsonEncode({
      'image_base64':imageBase64,'user_caption':caption,'meal_type':mealType,
    })));
    return Map<String,dynamic>.from(_unwrap(r));
  }



  Future<bool> onboardingStatus() async {
    final r=await _withAuthRetry(()=>http.get(Uri.parse('$baseUrl/onboarding/status'),headers:_headers));
    final data=Map<String,dynamic>.from(_unwrap(r));
    return data['complete']==true;
  }

  Future<Map<String,dynamic>> completeOnboarding(Map<String,dynamic> payload) async {
    final r=await _withAuthRetry(()=>http.post(Uri.parse('$baseUrl/onboarding/complete'),headers:_headers,body:jsonEncode(payload)));
    return Map<String,dynamic>.from(_unwrap(r));
  }



  Future<void> sendRecommendationFeedback(String foodId,String action) async {
    final r=await _withAuthRetry(()=>http.post(Uri.parse('$baseUrl/recommendations/feedback'),headers:_headers,body:jsonEncode({
      'food_id':foodId,'action':action,
    })));
    _unwrap(r);
  }



  Future<Map<String,dynamic>> updateProfile(Map<String,dynamic> payload) async {
    final r=await _withAuthRetry(()=>http.patch(Uri.parse('$baseUrl/users/me'),headers:_headers,body:jsonEncode(payload)));
    return Map<String,dynamic>.from(_unwrap(r));
  }

  Future<Map<String,dynamic>> recalculatePlan(Map<String,dynamic> payload) async {
    final r=await _withAuthRetry(()=>http.post(Uri.parse('$baseUrl/profile/recalculate-plan'),headers:_headers,body:jsonEncode(payload)));
    return Map<String,dynamic>.from(_unwrap(r));
  }

  Future<Map<String,dynamic>> profileInsights() async {
    final r=await _withAuthRetry(()=>http.get(Uri.parse('$baseUrl/profile/insights'),headers:_headers));
    return Map<String,dynamic>.from(_unwrap(r));
  }


  Future<WeeklyPlan> weeklyPlan() async {
    final r=await _withAuthRetry(()=>http.get(Uri.parse('$baseUrl/plan/week'),headers:_headers));
    return WeeklyPlan.fromJson(Map<String,dynamic>.from(_unwrap(r)));
  }

  Future<WeeklyPlan> regenerateWeeklyPlan() async {
    final r=await _withAuthRetry(()=>http.post(Uri.parse('$baseUrl/plan/week/generate'),headers:_headers));
    return WeeklyPlan.fromJson(Map<String,dynamic>.from(_unwrap(r)));
  }

  Future<WeeklyPlan> rebalancePlanDay(DateTime date) async {
    final d='${date.year.toString().padLeft(4,'0')}-${date.month.toString().padLeft(2,'0')}-${date.day.toString().padLeft(2,'0')}';
    final r=await _withAuthRetry(()=>http.post(Uri.parse('$baseUrl/plan/day/$d/rebalance'),headers:_headers));
    return WeeklyPlan.fromJson(Map<String,dynamic>.from(_unwrap(r)));
  }

  Future<ProgressSummary> progress(String range) async {
    final uri=Uri.parse('$baseUrl/progress').replace(queryParameters:{'range':range});
    final r=await _withAuthRetry(()=>http.get(uri,headers:_headers));
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
    final r=await _withAuthRetry(()=>http.get(uri,headers:_headers));
    final data=Map<String,dynamic>.from(_unwrap(r));
    return ((data['items'] as List?)??const [])
      .map((e)=>Map<String,dynamic>.from(e as Map)).toList();
  }


  Future<List<Map<String,dynamic>>> preferenceSettings() async {
    final r=await _withAuthRetry(()=>http.get(Uri.parse('$baseUrl/preferences'),headers:_headers));
    final data=Map<String,dynamic>.from(_unwrap(r));
    return ((data['items'] as List?)??const [])
      .map((e)=>Map<String,dynamic>.from(e as Map)).toList();
  }

  Future<Map<String,dynamic>> setPreference({
    required String targetType,
    required String targetValue,
    required String level,
  }) async {
    final r=await _withAuthRetry(()=>http.put(
      Uri.parse('$baseUrl/preferences'),
      headers:_headers,
      body:jsonEncode({
        'target_type':targetType,
        'target_value':targetValue,
        'level':level,
      }),
    ));
    return Map<String,dynamic>.from(_unwrap(r));
  }


  Future<List<Map<String,dynamic>>> healthLimits() async {
    final r=await _withAuthRetry(()=>http.get(Uri.parse('$baseUrl/health-limits'),headers:_headers));
    final data=Map<String,dynamic>.from(_unwrap(r));
    return ((data['items'] as List?)??const [])
      .map((e)=>Map<String,dynamic>.from(e as Map)).toList();
  }

  Future<Map<String,dynamic>> setHealthLimit({
    required String nutrientCode,
    required String limitType,
    required double value,
    required String unit,
    required String severity,
    required String sourceType,
    String? note,
    bool active=true,
  }) async {
    final r=await _withAuthRetry(()=>http.put(
      Uri.parse('$baseUrl/health-limits'),
      headers:_headers,
      body:jsonEncode({
        'nutrient_code':nutrientCode,
        'limit_type':limitType,
        'value':value,
        'unit':unit,
        'severity':severity,
        'source_type':sourceType,
        'note':note,
        'active':active,
      }),
    ));
    return Map<String,dynamic>.from(_unwrap(r));
  }


  Future<FoodLogDay> duplicateFoodLog(String logId) async {
    final key=_newIdempotencyKey('duplicate');
    final r=await _withAuthRetry(()=>http.post(Uri.parse('$baseUrl/food-log/$logId/duplicate'),headers:_writeHeaders(key)));
    _unwrap(r);
    return foodLogToday();
  }

  Future<Map<String,dynamic>> favoriteFoodLog(String logId) async {
    final r=await _withAuthRetry(()=>http.post(Uri.parse('$baseUrl/food-log/$logId/favorite'),headers:_headers));
    return Map<String,dynamic>.from(_unwrap(r));
  }

  Future<List<Map<String,dynamic>>> favoriteMeals() async {
    final r=await _withAuthRetry(()=>http.get(Uri.parse('$baseUrl/food-log/favorites'),headers:_headers));
    final data=Map<String,dynamic>.from(_unwrap(r));
    return ((data['items'] as List?)??const [])
      .map((e)=>Map<String,dynamic>.from(e as Map)).toList();
  }

  Future<FoodLogDay> logFavoriteMeal(String favoriteId,{String? mealType}) async {
    final key=_newIdempotencyKey('favorite');
    final r=await _withAuthRetry(()=>http.post(
      Uri.parse('$baseUrl/food-log/favorites/$favoriteId/log'),
      headers:_writeHeaders(key),
      body:jsonEncode({'meal_type':mealType}),
    ));
    _unwrap(r);
    return foodLogToday();
  }


  Future<Map<String,dynamic>> activityToday() async {
    final r=await _withAuthRetry(()=>http.get(Uri.parse('$baseUrl/activity-log/today'),headers:_headers));
    return Map<String,dynamic>.from(_unwrap(r));
  }

  Future<DailyState> addActivityCredit(double caloriesCredit,{String source='MANUAL',String? note}) async {
    final key=_newIdempotencyKey('activity');
    final r=await _withAuthRetry(()=>http.post(
      Uri.parse('$baseUrl/activity-log'),
      headers:_writeHeaders(key),
      body:jsonEncode({'calories_credit':caloriesCredit,'source':source,'note':note}),
    ));
    final data=Map<String,dynamic>.from(_unwrap(r));
    return DailyState.fromJson(Map<String,dynamic>.from(data['daily_state'] as Map));
  }

  Future<DailyState> deleteActivityCredit(String activityId) async {
    final r=await _withAuthRetry(()=>http.delete(Uri.parse('$baseUrl/activity-log/$activityId'),headers:_headers));
    final data=Map<String,dynamic>.from(_unwrap(r));
    return DailyState.fromJson(Map<String,dynamic>.from(data['daily_state'] as Map));
  }


  Future<List<Map<String,dynamic>>> activeSessions() async {
    final r=await _withAuthRetry(()=>http.get(Uri.parse('$baseUrl/auth/sessions'),headers:_headers));
    final data=Map<String,dynamic>.from(_unwrap(r));
    return ((data['items'] as List?)??const [])
      .map((e)=>Map<String,dynamic>.from(e as Map)).toList();
  }

}
