import 'dart:math';

import 'package:flutter/material.dart';

import 'theme.dart';

const invite = '''AZ-OS — voluntary overlay (not an infection)

AZ-OS is a portable folder and control surface. It is not a kernel,
not a bootloader, not a hypervisor, and not malware. You run it because
you choose to.

Principles
  1. Integrity precedes execution.
     No module or action runs without a token from ARC.
  2. Time-bound actions are final.
     Authorized executions append to an immutable sha256 chain. No rewrite.
  3. Understanding precedes modification.
     Extending or loading a module requires an explicit comprehension
     checkbox and a short restatement of intent.
  4. The system protects itself architecturally.
     Unsigned or unauthorized run() raises AuthorizationError. Default deny.
  5. Propagation is not infection.
     This invite prints principles and a download URL. AZ-OS does not
     copy itself onto other machines.

You are invited to run AZ-OS yourself. This is not a silent block.
Adoption is voluntary.

Counted download:
  https://azos-download-tracker.vibelock.workers.dev/

Source:
  https://github.com/AzielEliab/azos
''';

void main() {
  runApp(const AzosApp());
}

class AzosApp extends StatelessWidget {
  const AzosApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'AZ-OS',
      debugShowCheckedModeBanner: false,
      theme: buildAppTheme(),
      home: const ControlPage(),
    );
  }
}

class ControlPage extends StatefulWidget {
  const ControlPage({super.key});

  @override
  State<ControlPage> createState() => _ControlPageState();
}

class _ControlPageState extends State<ControlPage> {
  String? _token;
  bool _halted = false;
  String _status = 'idle — no token';
  bool _showInvite = true;

  void _issue() {
    if (_halted) {
      setState(() => _status = 'halted: new tokens refused');
      return;
    }
    final r = Random.secure();
    final bytes = List<int>.generate(32, (_) => r.nextInt(256));
    setState(() {
      _token = bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join();
      _status = 'token issued (in-memory). Integrity precedes execution.';
    });
  }

  void _revoke() {
    setState(() {
      _token = null;
      _status = 'token revoked (label). Default deny.';
    });
  }

  void _halt() {
    setState(() {
      _halted = true;
      _token = null;
      _status = 'HALT. Lumen watch remains a label: running. Tokens revoked.';
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('AZ-OS')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            color: const Color(0xFF2A1515),
            child: const Padding(
              padding: EdgeInsets.all(12),
              child: Text(
                'NOT a kernel. NOT a worm. NOT malware. This is a control surface '
                'for a portable overlay. Propagation is invitation, not infection.',
                style: TextStyle(height: 1.4),
              ),
            ),
          ),
          const SizedBox(height: 8),
          const Text(
            'Integrity precedes execution.',
            style: TextStyle(color: kGold, fontStyle: FontStyle.italic, fontSize: 16),
          ),
          const SizedBox(height: 16),
          Text('Status: $_status'),
          Text(
            _token == null ? 'token: none' : 'token: ${_token!.substring(0, 16)}… (hashed-at-rest analogue: not shown full)',
            style: const TextStyle(fontFamily: 'monospace', fontSize: 12),
          ),
          Text('halted: $_halted   lumen: running (watch loop is a label on this phone)'),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              FilledButton(onPressed: _issue, child: const Text('Issue token')),
              OutlinedButton(onPressed: _revoke, child: const Text('Revoke')),
              OutlinedButton(onPressed: _halt, child: const Text('Halt')),
              OutlinedButton(
                onPressed: () => setState(() => _showInvite = !_showInvite),
                child: const Text('Invite'),
              ),
            ],
          ),
          const SizedBox(height: 8),
          const Text(
            'Invite writes no files. Halt/revoke are labels on in-memory state. '
            'This phone app does not execute host modules, does not copy itself, '
            'and does not wipe a disk.',
            style: TextStyle(color: kGoldDim, fontSize: 12),
          ),
          if (_showInvite) ...[
            const SizedBox(height: 16),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: SelectableText(
                  invite,
                  style: const TextStyle(fontFamily: 'monospace', fontSize: 12, height: 1.4),
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}
