import 'dart:math' as math;
import 'package:flutter/material.dart';
import '../core/theme.dart';

class WazenRing extends StatelessWidget {
  final double remaining;
  final double target;
  const WazenRing({super.key, required this.remaining, required this.target});

  @override
  Widget build(BuildContext context) {
    final consumed = math.max(0, target - remaining);
    final progress = target <= 0 ? 0.0 : (consumed / target).clamp(0.0, 1.0);
    return SizedBox(
      width: 204,
      height: 204,
      child: Stack(
        alignment: Alignment.center,
        children: [
          SizedBox(
            width: 194,
            height: 194,
            child: CircularProgressIndicator(
              value: progress,
              strokeWidth: 14,
              color: WazenTheme.green,
              backgroundColor: WazenTheme.mint,
              strokeCap: StrokeCap.round,
            ),
          ),
          Column(mainAxisSize: MainAxisSize.min, children: [
            const Text('متبقي اليوم', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: WazenTheme.muted)),
            const SizedBox(height: 2),
            Text(remaining.toStringAsFixed(0), style: const TextStyle(fontSize: 41, fontWeight: FontWeight.w900, color: WazenTheme.greenDark, height: 1.05)),
            const Text('سعرة', style: TextStyle(fontSize: 14, color: WazenTheme.muted)),
          ]),
        ],
      ),
    );
  }
}
