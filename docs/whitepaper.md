# AZ-OS and AZ Interface

**A minimal ethical overlay framework and its control surface**

Aziel Eliab — July 2026 (combined)

This document merges three July 2026 papers:

1. *AZ-OS — a minimal ethical self-propagating framework*
2. *AZOS & AZ Interface — ARC, Lumen, and the control surface*
3. *Malware comparison — structural constraints only*

This tree is the software overlay described by those papers. It is **not**
a kernel, bootloader, hypervisor, worm, or malware implementation.

---

## 1. AZ-OS is an overlay

AZ-OS is a **portable folder**. You place it next to work you already do.
It does not replace the host operating system. It does not boot hardware.
It does not schedule processes below user space. It does not virtualize
a machine.

The unit of installation is a directory you chose to run. The unit of
removal is that directory plus, if you ask, the session folder `.azos/`.
Purge never touches `$HOME` as a whole and never touches OS paths.

“Self-propagating” in the paper means **ethical circulation**: a person
who encounters AZ-OS is invited to download and run it. It does not mean
copying bytes onto machines that did not ask. `azos invite` prints
principles and a download URL. That is the entire propagation mechanism.

---

## 2. AZ Interface is the control surface

AZ-OS without the Interface is a library. **AZ Interface is the product.**

The Interface (`azos ui`, `127.0.0.1:8800`) is where:

- a human proposes an action
- five gates return PASS or FAIL in the open
- ARC issues a token, or the request is blocked
- blocked requests show an **invite**, not a silent error
- action buttons exist, and they are disabled until a live token exists
- Halt stops execution authority
- Lumen continues to display as running after Halt
- Purge requires the operator to type `CONFIRM`

The Interface is not cosmetic. If a control is not on this surface, it is
not part of the product. There is no hidden channel that bypasses the
gates. A root or user *string* is a name on a form, not a privilege.

Self-contained CSS. No CDN. Loopback only.

---

## 3. ARC — execution authority

ARC (authority, revocation, custody) issues execution tokens.

- Tokens are 32 random bytes.
- Only a sha256 of the raw bytes is stored at rest (`.azos/tokens.json`).
- The issued token is shown once (Interface) or returned once (API).
- Revocation is final for that token.
- A string such as `root` or `user` does **not** auto-grant a token.

No module and no action runs without a token from ARC. Default is deny.
`run()` of an unsigned or unauthorized name raises `AuthorizationError`.

---

## 4. Lumen — the gatekeeper that outlives halt

Lumen is an in-process watch loop. Halt does not kill Lumen.

After halt:

- builtins will not run
- new tokens will not issue
- Lumen can still **revoke** tokens
- Lumen can still **purge** the session directory `.azos/` only

This is architectural self-protection: stopping execution is not the same
as abandoning custody of keys and session state.

---

## 5. Five gates (DecisionGATE-shaped)

A proposed action is authorized only if all five pass:

| Gate | Question |
|------|----------|
| Definition | What exactly is proposed? |
| Evidence | What justifies doing it? |
| Impact | What will change? |
| Integrity | Is this a registered safe builtin (unsigned code cannot run)? |
| Responsibility | Who owns the outcome? |

Any FAIL → no token. The Interface renders each gate. Understanding
precedes modification: extending or loading a new module additionally
requires an explicit comprehension checkbox and a short restatement of
intent. Comprehension is not a bypass. Unsigned modules still fail
integrity.

This tree reimplements a tiny five-gate check inline. It does not vend
DecisionGATE as a product.

---

## 6. Time-bound actions are final

Authorized executions append to an immutable log: a sha256 hash chain
written JSONL, file opened only in append mode. The in-memory object
refuses `pop`, `insert`, `remove`, `clear`, `reverse`, item assignment,
and item deletion.

There is no rewrite. A correction is a new execution, which requires a
new (or still-live) token, which requires the gates.

---

## 7. Safe builtins

`azos.exec` dispatches a closed allow-list:

- `list_modules`
- `echo`
- `status`
- `purge_session`

There is no `eval()`, no `exec()` of user strings, no `subprocess`, and
no shell. Echo never leaves the process. Purge as a builtin still
requires a live token; CLI `azos purge --confirm` is a Lumen operation
so it remains available after halt.

---

## 8. Invite, not a silent block

An unauthorized environment — no token, failed gates, revoked token —
does not fail closed and mute. It receives the invite text: the five
principles and a counted download URL.

```
https://azos-download-tracker.vibelock.workers.dev/
```

That is voluntary adoption. AZ-OS does not copy itself onto other
machines. That is the ethical meaning of “self-propagating” in the
July 2026 paper.

---

## 9. Malware comparison (structural constraints only)

This section compares **structure**. It does not implement malware,
ransomware “defenses” that wipe a host disk, or self-replication.

| Constraint | Typical malware | AZ-OS |
|------------|-----------------|-------|
| Execution | Silent, unsolicited | Token from ARC after five gates |
| Default | Permit until detected | Deny |
| Propagation | Copy / infect | Print an invite + URL |
| Persistence | Hide, survive wipe | Portable folder; purge deletes `.azos/` only |
| Privilege | Steal root | `root` is a name, not a grant |
| Host disk | Encrypt / destroy | Refuses OS paths; never `$HOME` |
| Mutation | Pack, obfuscate | Append-only log; no rewrite |
| Control surface | None, or C2 | AZ Interface on loopback |
| Halt | Kill-switch for the operator | Halt stops *our* execution; Lumen keeps custody |
| New code | Drop unsigned payloads | Integrity gate; comprehension required even to *ask* |

The comparison exists so a reader can see why AZ-OS is not in that
category. The software in this repository follows the right-hand column
only.

---

## 10. What this repository will not contain

- A real kernel, bootloader, or hypervisor
- A worm, self-replicator, or installer that writes outside the session
- Host-disk wipe, format, or ransomware logic
- `eval` / subprocess / shell dispatch of user strings
- A UI bound to `0.0.0.0`
- A CDN for the Interface

---

## 11. Motto

Integrity precedes execution.
