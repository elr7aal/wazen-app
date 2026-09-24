class DailyState {
  final double remainingCalories;
  final double proteinGapG;
  final double? carbsRemainingG;
  final double? fatRemainingG;
  final double? fiberRemainingG;
  final double activityCredit;
  final double? sodiumRemainingMg;

  const DailyState({
    required this.remainingCalories,
    required this.proteinGapG,
    this.carbsRemainingG,
    this.fatRemainingG,
    this.fiberRemainingG,
    this.activityCredit=0,
    this.sodiumRemainingMg,
  });

  factory DailyState.fromJson(Map<String, dynamic> json) => DailyState(
        remainingCalories: (json['remaining_calories'] ?? 0).toDouble(),
        proteinGapG: (json['protein_gap_g'] ?? 0).toDouble(),
        carbsRemainingG: (json['carbs_remaining_g'] as num?)?.toDouble(),
        fatRemainingG: (json['fat_remaining_g'] as num?)?.toDouble(),
        fiberRemainingG: (json['fiber_remaining_g'] as num?)?.toDouble(),
        activityCredit: (json['activity_credit'] as num? ?? 0).toDouble(),
        sodiumRemainingMg: (json['sodium_remaining_mg'] as num?)?.toDouble(),
      );
}

class NutritionInfo {
  final double? calories;
  final double? proteinG;
  final double? carbsG;
  final double? fatG;
  final double? fiberG;
  final double? sodiumMg;

  const NutritionInfo({this.calories, this.proteinG, this.carbsG, this.fatG, this.fiberG, this.sodiumMg});

  factory NutritionInfo.fromJson(Map<String, dynamic> json) => NutritionInfo(
        calories: (json['calories'] as num?)?.toDouble(),
        proteinG: (json['protein_g'] as num?)?.toDouble(),
        carbsG: (json['carbs_g'] as num?)?.toDouble(),
        fatG: (json['fat_g'] as num?)?.toDouble(),
        fiberG: (json['fiber_g'] as num?)?.toDouble(),
        sodiumMg: (json['sodium_mg'] as num?)?.toDouble(),
      );
}

class RecommendationItem {
  final String foodId;
  final String vendor;
  final String name;
  final String? nameAr;
  final String? category;
  final NutritionInfo nutrition;
  final double? price;
  final String? currency;
  final double wazenScore;
  final String decision;
  final List<String> reasons;
  final List<String> warnings;
  final bool canModify;
  final String? sourceConfidence;

  const RecommendationItem({
    required this.foodId,
    required this.vendor,
    required this.name,
    required this.nutrition,
    required this.wazenScore,
    required this.decision,
    required this.reasons,
    required this.warnings,
    required this.canModify,
    this.nameAr,
    this.category,
    this.price,
    this.currency,
    this.sourceConfidence,
  });

  factory RecommendationItem.fromJson(Map<String, dynamic> json) {
    final scores = (json['scores'] as Map<String, dynamic>?) ?? const {};
    return RecommendationItem(
      foodId: json['food_id'] as String,
      vendor: (json['vendor'] ?? '') as String,
      name: (json['name'] ?? '') as String,
      nameAr: json['name_ar'] as String?,
      category: json['category'] as String?,
      nutrition: NutritionInfo.fromJson((json['nutrition'] as Map<String, dynamic>?) ?? const {}),
      price: (json['price'] as num?)?.toDouble(),
      currency: json['currency'] as String?,
      wazenScore: (scores['wazen'] ?? 0).toDouble(),
      decision: (json['decision'] ?? '') as String,
      reasons: ((json['reasons'] as List?) ?? const []).map((e) => e.toString()).toList(),
      warnings: ((json['warnings'] as List?) ?? const []).map((e) => e.toString()).toList(),
      canModify: json['can_modify'] == true,
      sourceConfidence: json['source_confidence'] as String?,
    );
  }
}

class FoodDetail {
  final String foodId;
  final String vendor;
  final String name;
  final String? nameAr;
  final NutritionInfo nutrition;
  final List<String> allergens;
  final String? sourceConfidence;
  final String? sourceReference;
  final double? price;
  final String? currency;

  const FoodDetail({
    required this.foodId,
    required this.vendor,
    required this.name,
    required this.nutrition,
    required this.allergens,
    this.nameAr,
    this.sourceConfidence,
    this.sourceReference,
    this.price,
    this.currency,
  });

  factory FoodDetail.fromJson(Map<String, dynamic> json) => FoodDetail(
        foodId: json['food_id'] as String,
        vendor: (json['vendor'] ?? '') as String,
        name: (json['name'] ?? '') as String,
        nameAr: json['name_ar'] as String?,
        nutrition: NutritionInfo.fromJson((json['nutrition'] as Map<String, dynamic>?) ?? const {}),
        allergens: ((json['allergens'] as List?) ?? const []).map((e) => e.toString()).toList(),
        sourceConfidence: json['source_confidence'] as String?,
        sourceReference: json['source_reference'] as String?,
        price: (json['price'] as num?)?.toDouble(),
        currency: json['currency'] as String?,
      );
}


class ModifierOption {
  final String component;
  final String labelAr;
  final String labelEn;
  final double calorieDelta;
  final double? proteinDeltaG;
  final double? carbsDeltaG;
  final double? fatDeltaG;
  final double? sodiumDeltaMg;
  final String? confidence;

  const ModifierOption({required this.component, required this.labelAr, required this.labelEn, required this.calorieDelta, this.proteinDeltaG, this.carbsDeltaG, this.fatDeltaG, this.sodiumDeltaMg, this.confidence});

  factory ModifierOption.fromJson(Map<String,dynamic> json)=>ModifierOption(
    component:json['component'] as String,
    labelAr:(json['label_ar']??'') as String,
    labelEn:(json['label_en']??'') as String,
    calorieDelta:(json['calorie_delta'] as num? ?? 0).toDouble(),
    proteinDeltaG:(json['protein_delta_g'] as num?)?.toDouble(),
    carbsDeltaG:(json['carbs_delta_g'] as num?)?.toDouble(),
    fatDeltaG:(json['fat_delta_g'] as num?)?.toDouble(),
    sodiumDeltaMg:(json['sodium_delta_mg'] as num?)?.toDouble(),
    confidence:json['confidence'] as String?,
  );
}

class MakeItFitPreview {
  final NutritionInfo baseNutrition;
  final NutritionInfo modifiedNutrition;
  final double caloriesSaved;
  final bool fitsRemainingCalories;
  const MakeItFitPreview({required this.baseNutrition,required this.modifiedNutrition,required this.caloriesSaved,required this.fitsRemainingCalories});
  factory MakeItFitPreview.fromJson(Map<String,dynamic> json)=>MakeItFitPreview(
    baseNutrition:NutritionInfo.fromJson(Map<String,dynamic>.from(json['base_nutrition'] as Map)),
    modifiedNutrition:NutritionInfo.fromJson(Map<String,dynamic>.from(json['modified_nutrition'] as Map)),
    caloriesSaved:(json['calories_saved'] as num? ?? 0).toDouble(),
    fitsRemainingCalories:json['fits_remaining_calories']==true,
  );
}


class RebalanceData {
  final DailyState dailyState;
  final String headline;
  final String message;
  final List<RecommendationItem> nextOptions;

  const RebalanceData({
    required this.dailyState,
    required this.headline,
    required this.message,
    required this.nextOptions,
  });

  factory RebalanceData.fromJson(Map<String, dynamic> json) => RebalanceData(
    dailyState: DailyState.fromJson(Map<String, dynamic>.from(json['daily_state'] as Map)),
    headline: (json['headline'] ?? '') as String,
    message: (json['message'] ?? '') as String,
    nextOptions: ((json['next_options'] as List?) ?? const [])
      .map((e) => RecommendationItem.fromJson(Map<String, dynamic>.from(e as Map)))
      .toList(),
  );
}


class FoodLogItem {
  final String id;
  final String? foodId;
  final String foodName;
  final String mealType;
  final String entryMethod;
  final double calories;
  final double proteinG;
  final double carbsG;
  final double fatG;
  final double fiberG;
  final double sodiumMg;
  final DateTime? loggedAt;

  const FoodLogItem({
    required this.id, required this.foodName, required this.mealType,
    required this.entryMethod, required this.calories, required this.proteinG,
    required this.carbsG, required this.fatG, required this.fiberG, required this.sodiumMg,
    this.foodId, this.loggedAt,
  });

  factory FoodLogItem.fromJson(Map<String,dynamic> json)=>FoodLogItem(
    id:json['id'] as String,
    foodId:json['food_id'] as String?,
    foodName:(json['food_name']??'') as String,
    mealType:(json['meal_type']??'SNACK') as String,
    entryMethod:(json['entry_method']??'') as String,
    calories:(json['calories'] as num? ?? 0).toDouble(),
    proteinG:(json['protein_g'] as num? ?? 0).toDouble(),
    carbsG:(json['carbs_g'] as num? ?? 0).toDouble(),
    fatG:(json['fat_g'] as num? ?? 0).toDouble(),
    fiberG:(json['fiber_g'] as num? ?? 0).toDouble(),
    sodiumMg:(json['sodium_mg'] as num? ?? 0).toDouble(),
    loggedAt:json['logged_at']==null?null:DateTime.tryParse(json['logged_at'].toString()),
  );
}

class FoodLogDay {
  final List<FoodLogItem> items;
  final Map<String,dynamic> totals;
  final DailyState dailyState;
  const FoodLogDay({required this.items,required this.totals,required this.dailyState});

  factory FoodLogDay.fromJson(Map<String,dynamic> json)=>FoodLogDay(
    items:((json['items'] as List?)??const []).map((e)=>FoodLogItem.fromJson(Map<String,dynamic>.from(e as Map))).toList(),
    totals:Map<String,dynamic>.from((json['totals'] as Map?)??const {}),
    dailyState:DailyState.fromJson(Map<String,dynamic>.from(json['daily_state'] as Map)),
  );
}


class WeeklyPlanItem {
  final String id;
  final String mealType;
  final String? foodId;
  final String foodName;
  final double calories;
  final double proteinG;
  final double? price;
  final String currency;
  final String status;

  const WeeklyPlanItem({
    required this.id,
    required this.mealType,
    required this.foodName,
    required this.calories,
    required this.proteinG,
    required this.currency,
    required this.status,
    this.foodId,
    this.price,
  });

  factory WeeklyPlanItem.fromJson(Map<String,dynamic> json)=>WeeklyPlanItem(
    id:json['id'] as String,
    mealType:(json['meal_type']??'SNACK').toString(),
    foodId:json['food_id'] as String?,
    foodName:(json['food_name']??'').toString(),
    calories:(json['calories'] as num? ?? 0).toDouble(),
    proteinG:(json['protein_g'] as num? ?? 0).toDouble(),
    price:(json['price'] as num?)?.toDouble(),
    currency:(json['currency']??'AED').toString(),
    status:(json['status']??'PLANNED').toString(),
  );
}

class WeeklyPlanDay {
  final DateTime date;
  final List<WeeklyPlanItem> items;
  final double totalCalories;
  final double totalProteinG;

  const WeeklyPlanDay({
    required this.date,
    required this.items,
    required this.totalCalories,
    required this.totalProteinG,
  });

  factory WeeklyPlanDay.fromJson(Map<String,dynamic> json)=>WeeklyPlanDay(
    date:DateTime.parse(json['date'].toString()),
    items:((json['items'] as List?)??const [])
      .map((e)=>WeeklyPlanItem.fromJson(Map<String,dynamic>.from(e as Map))).toList(),
    totalCalories:(json['total_calories'] as num? ?? 0).toDouble(),
    totalProteinG:(json['total_protein_g'] as num? ?? 0).toDouble(),
  );
}

class WeeklyPlan {
  final DateTime weekStart;
  final List<WeeklyPlanDay> days;
  const WeeklyPlan({required this.weekStart,required this.days});
  factory WeeklyPlan.fromJson(Map<String,dynamic> json)=>WeeklyPlan(
    weekStart:DateTime.parse(json['week_start'].toString()),
    days:((json['days'] as List?)??const [])
      .map((e)=>WeeklyPlanDay.fromJson(Map<String,dynamic>.from(e as Map))).toList(),
  );
}

class WeightPoint {
  final DateTime date;
  final double weightKg;
  const WeightPoint({required this.date,required this.weightKg});
  factory WeightPoint.fromJson(Map<String,dynamic> json)=>WeightPoint(
    date:DateTime.parse(json['date'].toString()),
    weightKg:(json['weight_kg'] as num).toDouble(),
  );
}

class ProgressSummary {
  final int rangeDays;
  final int trackedDays;
  final int goalDays;
  final double averageCalories;
  final double averageProteinG;
  final double restaurantSpendAed;
  final double targetCalories;
  final double targetProteinG;
  final List<WeightPoint> weightTrend;
  final List<Map<String,dynamic>> daily;

  const ProgressSummary({
    required this.rangeDays,
    required this.trackedDays,
    required this.goalDays,
    required this.averageCalories,
    required this.averageProteinG,
    required this.restaurantSpendAed,
    required this.targetCalories,
    required this.targetProteinG,
    required this.weightTrend,
    required this.daily,
  });

  factory ProgressSummary.fromJson(Map<String,dynamic> json)=>ProgressSummary(
    rangeDays:(json['range_days'] as num? ?? 7).toInt(),
    trackedDays:(json['tracked_days'] as num? ?? 0).toInt(),
    goalDays:(json['goal_days'] as num? ?? 0).toInt(),
    averageCalories:(json['average_calories'] as num? ?? 0).toDouble(),
    averageProteinG:(json['average_protein_g'] as num? ?? 0).toDouble(),
    restaurantSpendAed:(json['restaurant_spend_aed'] as num? ?? 0).toDouble(),
    targetCalories:(json['target_calories'] as num? ?? 0).toDouble(),
    targetProteinG:(json['target_protein_g'] as num? ?? 0).toDouble(),
    weightTrend:((json['weight_trend'] as List?)??const [])
      .map((e)=>WeightPoint.fromJson(Map<String,dynamic>.from(e as Map))).toList(),
    daily:((json['daily'] as List?)??const [])
      .map((e)=>Map<String,dynamic>.from(e as Map)).toList(),
  );
}
