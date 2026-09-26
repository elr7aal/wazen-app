import 'package:flutter_test/flutter_test.dart';
import 'package:wazen_mobile/services/account_link.dart';
import 'package:wazen_mobile/models/api_models.dart';

void main() {
  test('canonical and hash account links preserve tokens', () {
    for (final action in ['verify-email', 'reset-password']) {
      for (final prefix in ['', '/#']) {
        final link = AccountLink.parse(Uri.parse('https://wazen.example$prefix/$action?token=abc%2B123'));
        expect(link?.action, action);
        expect(link?.token, 'abc+123');
      }
    }
  });
  test('rejects missing, ambiguous and unrelated account links', () {
    for (final suffix in ['/verify-email', '/verify-email?token=',
      '/verify-email?token=a&token=b', '/fake-reset-password?token=a']) {
      expect(AccountLink.parse(Uri.parse('https://wazen.example$suffix')), isNull);
    }
  });
  test('food log distinguishes unknown nutrients from measured zero', () {
    final unknown = FoodLogItem.fromJson({'id': '1'});
    expect(unknown.fiberG, isNull);
    expect(unknown.sodiumMg, isNull);
    final zero = FoodLogItem.fromJson({'id': '2', 'fiber_g': 0, 'sodium_mg': 0});
    expect(zero.fiberG, 0);
    expect(zero.sodiumMg, 0);
  });
}
