import 'package:flutter/material.dart';
import '../core/theme.dart';

class WazenBrandMark extends StatelessWidget {
  final double size;
  final bool light;
  const WazenBrandMark({super.key, this.size = 64, this.light = false});

  @override
  Widget build(BuildContext context) {
    final background = light ? Colors.white : WazenTheme.greenDark;
    final foreground = light ? WazenTheme.greenDark : Colors.white;
    return Semantics(
      label: 'وازن', image: true,
      child: Container(
        width: size, height: size,
        decoration: BoxDecoration(
          color: background, shape: BoxShape.circle,
          border: light ? Border.all(color: WazenTheme.border) : null,
          boxShadow: const [BoxShadow(color: Color(0x1F123F3A), blurRadius: 22, offset: Offset(0, 8))],
        ),
        child: Stack(alignment: Alignment.center, children: [
          Text('و', style: TextStyle(color: foreground, fontSize: size * .52, fontWeight: FontWeight.w900, height: 1)),
          Positioned(top: size * .18, right: size * .17, child: Transform.rotate(
            angle: -.65,
            child: Container(width: size * .17, height: size * .09, decoration: BoxDecoration(color: WazenTheme.sand, borderRadius: BorderRadius.circular(size))),
          )),
          Positioned(bottom: size * .13, child: Container(
            width: size * .17, height: size * .045,
            decoration: BoxDecoration(color: WazenTheme.coral, borderRadius: BorderRadius.circular(size)),
          )),
        ]),
      ),
    );
  }
}

class WazenWordmark extends StatelessWidget {
  final bool compact;
  final MainAxisAlignment alignment;
  const WazenWordmark({super.key, this.compact = false, this.alignment = MainAxisAlignment.center});

  @override
  Widget build(BuildContext context) => Row(
    mainAxisSize: MainAxisSize.min, mainAxisAlignment: alignment,
    children: [
      WazenBrandMark(size: compact ? 36 : 56),
      SizedBox(width: compact ? 10 : 14),
      Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
        Text('وازن', style: TextStyle(fontSize: compact ? 19 : 27, fontWeight: FontWeight.w900, color: WazenTheme.greenDark, height: 1.05)),
        Text('WAZEN', style: TextStyle(fontSize: compact ? 9 : 11, fontWeight: FontWeight.w800, letterSpacing: compact ? 2.2 : 3.4, color: WazenTheme.green)),
      ]),
    ],
  );
}
