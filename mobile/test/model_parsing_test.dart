import 'package:flutter_test/flutter_test.dart';
import 'package:wazen_mobile/models/api_models.dart';

void main() {
  test('RecommendationItem parses API payload', () {
    final item = RecommendationItem.fromJson({
      'food_id': 'KFC-AE-014',
      'vendor': 'KFC UAE',
      'name': 'Zinger Sandwich',
      'name_ar': 'زنجر ساندويتش',
      'nutrition': {'calories': 613, 'protein_g': 31.5},
      'scores': {'wazen': 89.4},
      'decision': 'ELIGIBLE',
      'reasons': ['Fits the requested calorie context'],
      'warnings': [],
      'can_modify': false,
    });
    expect(item.foodId, 'KFC-AE-014');
    expect(item.nutrition.calories, 613);
    expect(item.wazenScore, 89.4);
  });
}
