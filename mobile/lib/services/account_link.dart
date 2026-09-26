/// Account email links support canonical paths and Flutter hash routes.
class AccountLink {
  final String action;
  final String token;
  const AccountLink(this.action, this.token);

  static AccountLink? parse(Uri uri) {
    final candidates = <Uri>[uri];
    if (uri.fragment.startsWith('/')) {
      final fragment = Uri.tryParse(uri.fragment);
      if (fragment != null) candidates.add(fragment);
    }
    for (final candidate in candidates) {
      final path = candidate.path.replaceFirst(RegExp(r'/$'), '');
      if (path != '/verify-email' && path != '/reset-password') continue;
      final tokens = candidate.queryParametersAll['token'];
      if (tokens == null || tokens.length != 1 || tokens.single.trim().isEmpty) continue;
      return AccountLink(path.substring(1), tokens.single.trim());
    }
    return null;
  }
}
