import 'package:azos/facts.dart';
import 'package:azos/hints.dart';
import 'package:azos/main.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

const List<String> _liveClaims = <String>[
  'There is a kernel.',
  'The kernel is live',
  'The kernel base is present.',
  'kernel is true',
  'This has booted.',
  'The host has booted',
  'booted is true',
  'This is installed as an operating system.',
  'This app is installed',
  'The app is installed',
  'installed is true',
  'The internet base is live',
  'internet base is live',
  'An alternative internet is live.',
  'alternative internet is live',
  'alt_internet_live is true',
  'A packet path is live',
  'packet_path_live is true',
  'Mail can be sent from here.',
  'Mail is sent from here.',
  'mail send is live',
  'This is a live mesh node.',
  'mesh node is live',
  'A second device is marked present',
  'A second device is live',
  'There is a second device',
  'second device is true',
  'One-click install is live.',
];

void main() {
  test('flags and limit sentences stay the worker facts', () {
    expect(kFlags['kernel'], isFalse);
    expect(kFlags['booted'], isFalse);
    expect(kFlags['installed'], isFalse);
    expect(kFlags['internet_base_live'], isFalse);
    expect(kFlags['alt_internet_live'], isFalse);
    expect(kFlags['packet_path_live'], isFalse);
    expect(kFlags['mail_send'], isFalse);
    expect(kFlags['mesh_node_live'], isFalse);
    expect(kFlags['second_device'], isFalse);
    expect(kFlags['userspace_base'], isTrue);
    expect(kFlags['userspace_is_boot'], isFalse);
    expect(kLimitPages.join(' '), kLimitsPlain);
    expect(kLimitsPlain.contains('That is a base, not a boot.'), isTrue);
    expect(kLimitsPlain.contains('alt_internet_live is false'), isTrue);
    expect(kLimitsPlain.contains('packet_path_live is false'), isTrue);
    expect(kLimitsPlain.contains('The public door stays FG-STUB.'), isTrue);
    expect(
        kLimitsPlain.contains('Isolation is single-node security-awareness.'),
        isTrue);
    expect(
        kLimitsPlain.contains('Phoenix is a local wait and re-seal.'), isTrue);
    expect(kLimitsPlain.contains('One-click install is not live.'), isTrue);
    expect(kNewsPage.contains('AZNews and 4DMap are listed.'), isTrue);
    expect(kNewsPage.contains('They are not joined and not live.'), isTrue);
    expect(kSentencePages, contains(kSecondDevicePage));
    for (final claim in _liveClaims) {
      expect(kSentencePages.join('\n').contains(claim), isFalse, reason: claim);
      expect(kInvite.contains(claim), isFalse, reason: claim);
      expect(kHints.values.join('\n').contains(claim), isFalse, reason: claim);
    }
  });

  testWidgets('the app shows the not-live sentences', (tester) async {
    await tester.pumpWidget(AzosApp(hints: MemoryHintStore()));
    await tester.pumpAndSettle();

    expect(find.text(kOpeningLine), findsOneWidget);
    expect(find.text('There is no kernel.'), findsNothing);
    expect(find.text(kSentencePages.first), findsOneWidget);

    final spoken = <String>[kOpeningLine, kSentencePages.first];
    for (var i = 0; i < kSentencePages.length - 1; i++) {
      await tester.tap(find.byKey(const Key('control-next')));
      await tester.pumpAndSettle();
      if (find.byKey(const Key('hint-ok')).evaluate().isNotEmpty) {
        expect(find.text(kHints['next']!), findsOneWidget);
        await tester.tap(find.byKey(const Key('hint-ok')));
        await tester.pumpAndSettle();
      }
      expect(find.text(kSentencePages[i + 1]), findsOneWidget);
      spoken.add(kSentencePages[i + 1]);
    }

    await tester.tap(find.text('Invite'));
    await tester.pumpAndSettle();
    expect(find.text(kHints['invite']!), findsOneWidget);
    await tester.tap(find.byKey(const Key('hint-ok')));
    await tester.pumpAndSettle();
    expect(find.text(kInvite), findsOneWidget);
    spoken.add(kInvite);

    await tester.tap(find.text('Controls'));
    await tester.pumpAndSettle();
    expect(find.text(kHints['controls']!), findsOneWidget);
    await tester.tap(find.byKey(const Key('hint-ok')));
    await tester.pumpAndSettle();
    expect(find.text(kWatchLine), findsOneWidget);
    expect(find.text(kAppNotInstalled), findsOneWidget);
    expect(find.text(kSecondDevicePage), findsOneWidget);
    expect(find.text(kLimitsPlain), findsOneWidget);
    spoken.add(kWatchLine);
    spoken.add(kAppNotInstalled);
    spoken.add(kLimitsPlain);

    final all = spoken.join('\n');
    for (final claim in _liveClaims) {
      expect(all.contains(claim), isFalse, reason: claim);
    }
    expect(all.contains('There is no kernel.'), isTrue);
    expect(all.contains('This has not booted.'), isTrue);
    expect(
        all.contains('This is not installed as an operating system.'), isTrue);
    expect(all.contains('alt_internet_live is false'), isTrue);
    expect(all.contains('packet_path_live is false'), isTrue);
    expect(all.contains('The public door stays FG-STUB.'), isTrue);
    expect(
        all.contains('Isolation is single-node security-awareness.'), isTrue);
    expect(all.contains('Phoenix is a local wait and re-seal.'), isTrue);
    expect(all.contains('Mail is not sent from here.'), isTrue);
    expect(all.contains('One-click install is not live.'), isTrue);
    expect(all.contains('This is not a live mesh node.'), isTrue);
    expect(all.contains('There is no second device.'), isTrue);
    expect(all.contains('That is a base, not a boot.'), isTrue);
    expect(
        all.contains(
            'AZNews and 4DMap are listed. They are not joined and not live.'),
        isTrue);
  });

  testWidgets(
      'a new user gets one short hint the first time they meet a control',
      (tester) async {
    final hints = MemoryHintStore();
    await tester.pumpWidget(AzosApp(hints: hints));
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const Key('control-next')));
    await tester.pumpAndSettle();
    expect(find.text('Next'), findsWidgets);
    expect(find.text(kHints['next']!), findsOneWidget);
    expect(find.text(kSentencePages[1]), findsNothing);

    await tester.tap(find.byKey(const Key('hint-ok')));
    await tester.pumpAndSettle();
    expect(find.text(kHints['next']!), findsNothing);
    expect(find.text(kSentencePages[1]), findsOneWidget);
    expect(hints.seen('next'), isTrue);

    await tester.tap(find.byKey(const Key('control-next')));
    await tester.pumpAndSettle();
    expect(find.text(kHints['next']!), findsNothing);
    expect(find.text(kSentencePages[2]), findsOneWidget);
  });

  testWidgets('a returning user does not see a hint they already met',
      (tester) async {
    final hints = MemoryHintStore();
    await hints.mark('next');
    await tester.pumpWidget(AzosApp(hints: hints));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('control-next')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('hint-ok')), findsNothing);
    expect(find.text(kSentencePages[1]), findsOneWidget);
  });

  testWidgets('issue, revoke, and halt stay in memory', (tester) async {
    await tester.pumpWidget(AzosApp(hints: MemoryHintStore()));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Controls'));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('hint-ok')));
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const Key('control-issue')));
    await tester.pumpAndSettle();
    expect(find.text(kHints['issue']!), findsOneWidget);
    await tester.tap(find.byKey(const Key('hint-ok')));
    await tester.pumpAndSettle();
    expect(find.text(kIssued), findsOneWidget);
    expect(find.text(kTokenShown), findsOneWidget);

    await tester.tap(find.byKey(const Key('control-issue')));
    await tester.pumpAndSettle();
    expect(find.text(kHints['issue']!), findsNothing);

    await tester.tap(find.byKey(const Key('control-revoke')));
    await tester.pumpAndSettle();
    expect(find.text(kHints['revoke']!), findsOneWidget);
    await tester.tap(find.byKey(const Key('hint-ok')));
    await tester.pumpAndSettle();
    expect(find.text(kRevoked), findsOneWidget);
    expect(find.text(kTokenHidden), findsOneWidget);

    await tester.tap(find.byKey(const Key('control-halt')));
    await tester.pumpAndSettle();
    expect(find.text(kHints['halt']!), findsOneWidget);
    await tester.tap(find.byKey(const Key('hint-ok')));
    await tester.pumpAndSettle();
    expect(find.text(kHalted), findsOneWidget);

    await tester.tap(find.byKey(const Key('control-issue')));
    await tester.pumpAndSettle();
    expect(find.text(kIssueRefused), findsOneWidget);
    expect(find.textContaining('has booted'), findsNothing);
  });

  testWidgets('phone and desktop widths keep the first sentence',
      (tester) async {
    Future<void> at(Size size) async {
      tester.view.physicalSize = size;
      tester.view.devicePixelRatio = 1;
      await tester.pumpWidget(AzosApp(hints: MemoryHintStore()));
      await tester.pumpAndSettle();
      expect(find.text(kSentencePages.first), findsOneWidget);
      expect(find.text(kOpeningLine), findsOneWidget);
      expect(tester.takeException(), isNull);
    }

    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await at(const Size(390, 844));
    await at(const Size(1280, 800));
  });
}
