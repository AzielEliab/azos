/// Sentences a person reads. They match the public worker and stay
/// the same not-live facts as aziel-runtime and AZ Interface.
///
/// userspace_base may stay a base. It is not a boot.
library;

const Map<String, bool> kFlags = <String, bool>{
  'kernel': false,
  'booted': false,
  'installed': false,
  'internet_base_live': false,
  'alt_internet_live': false,
  'packet_path_live': false,
  'mail_send': false,
  'mesh_node_live': false,
  'second_device': false,
  'userspace_base': true,
  'userspace_is_boot': false,
};

const String kLimitsPlain =
    'There is no kernel. The kernel base is absent. This has not booted. '
    'This is not installed as an operating system. This is not an operating system yet. '
    'The userspace base is present. That is a base, not a boot. '
    'An alternative internet is not live (alt_internet_live is false). '
    'A packet path is not live (packet_path_live is false). '
    'This isolate cannot see host hardware (worker_hardware is false). '
    'Still missing: a packet that leaves this machine and arrives on a different machine id. '
    'A same-machine mesh frame does not count. '
    'Cap-7 and .aziel stay names, not a public registrar and not ICANN or BGP. '
    'WireGuard, OpenVPN, an L3 exit pool, kernel UDP, and TUN/TAP stay SLOT. '
    'Public mail send, the kernel, and boot stay not live. '
    'The public door stays FG-STUB. '
    'Isolation is single-node security-awareness. '
    'Phoenix is a local wait and re-seal. '
    'That is not a loopback fence. '
    'Mail is not sent from here. One-click install is not live. This is not a live mesh node. '
    'Existing doors stay in place. App shells are not started.';

const List<String> kLimitPages = <String>[
  'There is no kernel.',
  'The kernel base is absent.',
  'This has not booted.',
  'This is not installed as an operating system.',
  'This is not an operating system yet.',
  'The userspace base is present. That is a base, not a boot.',
  'An alternative internet is not live (alt_internet_live is false).',
  'A packet path is not live (packet_path_live is false).',
  'This isolate cannot see host hardware (worker_hardware is false).',
  'Still missing: a packet that leaves this machine and arrives on a different machine id.',
  'A same-machine mesh frame does not count.',
  'Cap-7 and .aziel stay names, not a public registrar and not ICANN or BGP.',
  'WireGuard, OpenVPN, an L3 exit pool, kernel UDP, and TUN/TAP stay SLOT.',
  'Public mail send, the kernel, and boot stay not live.',
  'The public door stays FG-STUB.',
  'Isolation is single-node security-awareness.',
  'Phoenix is a local wait and re-seal.',
  'That is not a loopback fence.',
  'Mail is not sent from here.',
  'One-click install is not live.',
  'This is not a live mesh node.',
  'Existing doors stay in place.',
  'App shells are not started.',
];

const String kThisIs =
    'THIS IS: prefab AZ-OS — ethics-coded remote shell with catalog software hooked in. '
    'Windows-style desktop locally; the sigil / brand mark (rose-star, no words) replaces a vendor logo. '
    'TemporalLock × StaticClock integrity lattice. Author Aziel Eliab only.';

const String kThisIsNot =
    'THIS IS NOT: a kernel, bootloader, hypervisor, replacement OS, VPN, worm, malware, '
    'unrestricted host bash, or SSH. Halt stops overlay authority. It does not kill the caller OS.';

const String kThisWorker =
    'THIS WORKER is the public homepage + counted download + read-only hosted ops '
    '(status, invite, health, skill, prefab, lattice snapshot). Session, exec, and lattice bind '
    'persist in product-Worker KV and need full AZ-OS (azos ui / azos shell). The HTTP proxy is not the full OS.';

const String kNewsPage =
    'AZNews and 4DMap are listed. They are not joined and not live. '
    'No fetched news item has landed as a map pin. AZNews can stand alone. 4DMap can stand alone. '
    'A news item could become a map pin (date, event, and place), or a pin could open the matching news, '
    'only after a real item is fetched. This page does not install 4DMap and does not serve articles. '
    'This page does not claim the aziel-runtime side is done. The news source is absent. Nothing here is live or merged.';

const String kMeshPage =
    'The suite mesh is off. This page is not a live mesh node. '
    'The cite is QNM-BUILD-1.0 and QNS-CD-1.0. Not an anonymity network.';

const String kMeshStay = 'This page does not start a mesh node.';

const String kSecondDevicePage = 'There is no second device.';

const String kInterfacePage =
    'AZ Interface is a separate shell. It is not this kernel and not this boot.';

const String kPublicWorkerKernel = 'The public worker does not run a kernel.';

const String kPublicWorkerBoot = 'Boot does not run on the public worker.';

const String kHostOsPage =
    'The host operating system stays the host operating system.';

const List<String> kSentencePages = <String>[
  kThisIs,
  kThisIsNot,
  kThisWorker,
  ...kLimitPages,
  kNewsPage,
  kMeshPage,
  kMeshStay,
  kSecondDevicePage,
  kInterfacePage,
  kPublicWorkerKernel,
  kPublicWorkerBoot,
  kHostOsPage,
];

const String kOpeningLine = 'Opening this app is not a boot.';

const String kWatchLine =
    'The watch label is on. There is no kernel. This has not booted. '
    'The userspace base is present. That is a base, not a boot.';

const String kAppNotInstalled =
    'This app is not installed as an operating system.';

const String kNoToken = 'No token yet. This has not booted.';

const String kIssued =
    'A token was issued in memory. Integrity precedes execution. This is not a boot.';

const String kRevoked =
    'The token was revoked. The next command is refused until a new token is issued.';

const String kHalted = 'Halted. The watch label stays on. Tokens were revoked. '
    'The operating system on this computer keeps running.';

const String kIssueRefused =
    'Halted. A new token is refused. The operating system on this computer keeps running.';

const String kTokenHidden = 'No token is showing.';

const String kTokenShown =
    'A token was issued. Only the first 16 characters are shown here.';

const String kControlNote =
    'Invite writes no files. Halt and revoke are labels on in-memory state. '
    'This app does not execute host modules, does not copy itself, and does not wipe a disk.';

const String kInvite =
    '''AZ-OS — ethics-coded remote shell (voluntary; not an infection)

AZ-OS is a true remote shell gated by coded ethics. You run it because
you choose to. It is not a kernel, bootloader, hypervisor, or malware.
It is not unrestricted host bash and not SSH.

Integrity precedes execution.

Principles
  1. Integrity precedes execution.
     No module, session, or command runs without a token from ARC.
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

Scope (honest)
  Protocols: HTTPS JSON (hosted Worker), HTTP loopback 127.0.0.1:8800,
             CLI stdin (`azos shell`).
  Auth:      ARC 32-byte token after the five ethics gates. Hashed at rest.
  Sandbox:   session vfs under .azos/workspace (local) or KV vfs (hosted).
             No host subprocess. Halt stops the overlay session, not the
             caller OS.

You are invited to run AZ-OS yourself. This is not a silent block.
Adoption is voluntary.

Counted download:
  https://azos-download-tracker.vibelock.workers.dev/

Source:
  https://github.com/AzielEliab/azos
''';

const Map<String, String> kHints = <String, String>{
  'next': 'Next shows the following sentence. It does not change a fact.',
  'previous': 'Previous shows the sentence you just read.',
  'sentences':
      'Sentences opens the pages a person reads. It does not boot anything.',
  'invite':
      'Invite shows the invitation. It writes no files and does not copy this app.',
  'controls':
      'Controls opens the token buttons. They stay in memory and do not install an operating system.',
  'issue':
      'Issue token makes a token in this app\'s memory. It does not boot the computer.',
  'revoke':
      'Revoke forgets that token. Nothing new runs until a token is issued again.',
  'halt':
      'Halt stops new tokens. The operating system on this computer keeps running.',
};
