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
      width: 190,
      height: 190,
      child: Stack(
        alignment: Alignment.center,
        children: [
          SizedBox(
            width: 180,
            height: 180,
            child: CircularProgressIndicator(
              value: progress,
              strokeWidth: 15,
              backgroundColor: WazenTheme.beige,
              strokeCap: StrokeCap.round,
            ),
          ),
          Column(mainAxisSize: MainAxisSize.min, children: [
            Text(remaining.toStringAsFixed(0), style: const TextStyle(fontSize: 38, fontWeight: FontWeight.w800, color: WazenTheme.greenDark)),
            const Text('سعرة متبقية', style: TextStyle(fontSize: 15, color: Colors.black54)),
          ]),
        ],
      ),
    );
  }
}
