import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:wazen_mobile/widgets/wazen_ring.dart';

void main() {
  testWidgets('daily ring displays remaining calories and consumed proportion', (tester) async {
    await tester.pumpWidget(const MaterialApp(
      home: Scaffold(body: Directionality(
        textDirection: TextDirection.rtl,
        child: WazenRing(remaining: 700, target: 2000),
      )),
    ));
    expect(find.text('700'), findsOneWidget);
    expect(find.text('متبقي اليوم'), findsOneWidget);
    expect(find.text('سعرة'), findsOneWidget);
    final ring = tester.widget<CircularProgressIndicator>(find.byType(CircularProgressIndicator));
    expect(ring.value, closeTo(0.65, 0.001));
    expect(tester.takeException(), isNull);
  });

  testWidgets('daily ring handles a zero target without invalid progress', (tester) async {
    await tester.pumpWidget(const MaterialApp(
      home: Scaffold(body: WazenRing(remaining: 0, target: 0)),
    ));
    final ring = tester.widget<CircularProgressIndicator>(find.byType(CircularProgressIndicator));
    expect(ring.value, 0);
    expect(tester.takeException(), isNull);
  });
}
