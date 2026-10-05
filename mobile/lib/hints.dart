import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Remembers which controls a person has already met.
abstract class HintStore {
  bool seen(String id);
  Future<void> mark(String id);
}

class MemoryHintStore implements HintStore {
  final Set<String> _seen = <String>{};

  @override
  bool seen(String id) => _seen.contains(id);

  @override
  Future<void> mark(String id) async {
    _seen.add(id);
  }
}

class PrefsHintStore implements HintStore {
  PrefsHintStore(this._prefs) {
    _seen.addAll(_prefs.getStringList(_key) ?? const <String>[]);
  }

  static const String _key = 'azos.hints.seen';
  final SharedPreferences _prefs;
  final Set<String> _seen = <String>{};

  @override
  bool seen(String id) => _seen.contains(id);

  @override
  Future<void> mark(String id) async {
    if (!_seen.add(id)) return;
    await _prefs.setStringList(_key, _seen.toList());
  }
}

class HintScope extends InheritedWidget {
  const HintScope({required this.store, required super.child, super.key});

  final HintStore store;

  static HintStore of(BuildContext context) {
    final scope = context.dependOnInheritedWidgetOfExactType<HintScope>();
    assert(scope != null, 'HintScope is missing');
    return scope!.store;
  }

  @override
  bool updateShouldNotify(HintScope oldWidget) => oldWidget.store != store;
}

/// Short popup the first time this person meets [id].
Future<void> meetControl(
    BuildContext context, String id, String name, String hint) async {
  final store = HintScope.of(context);
  if (store.seen(id)) return;
  await showDialog<void>(
    context: context,
    builder: (ctx) => AlertDialog(
      title: Text(name),
      content: Text(hint),
      actions: [
        TextButton(
          key: const Key('hint-ok'),
          onPressed: () => Navigator.of(ctx).pop(),
          child: const Text('OK'),
        ),
      ],
    ),
  );
  await store.mark(id);
}
