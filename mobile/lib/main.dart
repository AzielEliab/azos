import 'dart:math';

import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'facts.dart';
import 'hints.dart';
import 'theme.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final prefs = await SharedPreferences.getInstance();
  runApp(AzosApp(hints: PrefsHintStore(prefs)));
}

class AzosApp extends StatelessWidget {
  const AzosApp({required this.hints, super.key});

  final HintStore hints;

  @override
  Widget build(BuildContext context) {
    return HintScope(
      store: hints,
      child: MaterialApp(
        title: 'AZ-OS',
        debugShowCheckedModeBanner: false,
        theme: buildAppTheme(),
        home: const HomePage(),
      ),
    );
  }
}

class _Nav {
  const _Nav(this.id, this.name, this.icon);
  final String id;
  final String name;
  final IconData icon;
}

const List<_Nav> _nav = <_Nav>[
  _Nav('sentences', 'Sentences', Icons.article_outlined),
  _Nav('invite', 'Invite', Icons.mail_outline),
  _Nav('controls', 'Controls', Icons.tune),
];

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  int _section = 0;
  int _page = 0;
  String? _token;
  bool _halted = false;
  String _status = kNoToken;

  Future<void> _select(int index) async {
    final item = _nav[index];
    await meetControl(context, item.id, item.name, kHints[item.id]!);
    if (!mounted) return;
    setState(() => _section = index);
  }

  void _issue() {
    if (_halted) {
      setState(() => _status = kIssueRefused);
      return;
    }
    final random = Random.secure();
    final bytes = List<int>.generate(32, (_) => random.nextInt(256));
    setState(() {
      _token = bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join();
      _status = kIssued;
    });
  }

  void _revoke() {
    setState(() {
      _token = null;
      _status = kRevoked;
    });
  }

  void _halt() {
    setState(() {
      _halted = true;
      _token = null;
      _status = kHalted;
    });
  }

  @override
  Widget build(BuildContext context) {
    final wide = MediaQuery.sizeOf(context).width >= 900;
    return Scaffold(
      appBar: AppBar(title: const Text('AZ-OS')),
      body: SafeArea(
        child: Row(
          children: [
            if (wide) _rail(),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Padding(
                    padding: EdgeInsets.fromLTRB(16, 12, 16, 0),
                    child: Text(kOpeningLine),
                  ),
                  Expanded(child: _body()),
                ],
              ),
            ),
          ],
        ),
      ),
      bottomNavigationBar: wide ? null : _bar(),
    );
  }

  Widget _rail() {
    return NavigationRail(
      selectedIndex: _section,
      onDestinationSelected: (index) => _select(index),
      labelType: NavigationRailLabelType.all,
      destinations: [
        for (final item in _nav)
          NavigationRailDestination(
            icon: Icon(item.icon),
            label: Text(item.name),
          ),
      ],
    );
  }

  Widget _bar() {
    return NavigationBar(
      selectedIndex: _section,
      onDestinationSelected: (index) => _select(index),
      destinations: [
        for (final item in _nav)
          NavigationDestination(icon: Icon(item.icon), label: item.name),
      ],
    );
  }

  Widget _body() {
    switch (_section) {
      case 1:
        return _invite();
      case 2:
        return _controls();
      default:
        return _sentences();
    }
  }

  Widget _sentences() {
    final page = kSentencePages[_page];
    final last = _page >= kSentencePages.length - 1;
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Text(
            'Integrity precedes execution.',
            style: TextStyle(
                color: kGold, fontStyle: FontStyle.italic, fontSize: 16),
          ),
          const SizedBox(height: 12),
          Expanded(
            child: Card(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(16),
                child: Text(page,
                    style: const TextStyle(fontSize: 22, height: 1.4)),
              ),
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Sentence ${_page + 1} of ${kSentencePages.length}',
            style: const TextStyle(color: kGoldDim),
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              HintButton(
                id: 'previous',
                name: 'Previous',
                hint: kHints['previous']!,
                onPressed: _page == 0 ? null : () => setState(() => _page -= 1),
              ),
              HintButton(
                id: 'next',
                name: 'Next',
                hint: kHints['next']!,
                filled: true,
                onPressed: last ? null : () => setState(() => _page += 1),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _invite() {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: const [
        Text(
          'Propagation is invitation, not infection. This text writes no files.',
        ),
        SizedBox(height: 12),
        Card(
          child: Padding(
            padding: EdgeInsets.all(12),
            child: SelectableText(
              kInvite,
              style:
                  TextStyle(fontFamily: 'monospace', fontSize: 13, height: 1.4),
            ),
          ),
        ),
      ],
    );
  }

  Widget _controls() {
    final preview = _token?.substring(0, 16);
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text(_status),
        const SizedBox(height: 8),
        Text(preview == null ? kTokenHidden : kTokenShown),
        if (preview != null) Text(preview),
        const SizedBox(height: 12),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            HintButton(
              id: 'issue',
              name: 'Issue token',
              hint: kHints['issue']!,
              filled: true,
              onPressed: _issue,
            ),
            HintButton(
              id: 'revoke',
              name: 'Revoke',
              hint: kHints['revoke']!,
              onPressed: _revoke,
            ),
            HintButton(
              id: 'halt',
              name: 'Halt',
              hint: kHints['halt']!,
              onPressed: _halt,
            ),
          ],
        ),
        const SizedBox(height: 16),
        const Text(kWatchLine),
        const SizedBox(height: 8),
        const Text(kAppNotInstalled),
        const SizedBox(height: 8),
        const Text(kSecondDevicePage),
        const SizedBox(height: 8),
        const Text(kLimitsPlain),
        const SizedBox(height: 12),
        const Text(kControlNote,
            style: TextStyle(color: kGoldDim, fontSize: 12)),
      ],
    );
  }
}

class HintButton extends StatelessWidget {
  const HintButton({
    required this.id,
    required this.name,
    required this.hint,
    required this.onPressed,
    this.filled = false,
    super.key,
  });

  final String id;
  final String name;
  final String hint;
  final VoidCallback? onPressed;
  final bool filled;

  @override
  Widget build(BuildContext context) {
    final child = Text(name);
    final VoidCallback? handler = onPressed == null
        ? null
        : () async {
            await meetControl(context, id, name, hint);
            if (!context.mounted) return;
            onPressed!();
          };
    if (filled) {
      return FilledButton(
          key: Key('control-$id'), onPressed: handler, child: child);
    }
    return OutlinedButton(
        key: Key('control-$id'), onPressed: handler, child: child);
  }
}
