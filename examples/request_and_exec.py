"""Request a shell session through the five gates, then run a command.

Ethics-coded remote shell. Not a kernel. Not malware. Not host bash.
Session lives under ./_out/.azos.
"""

from __future__ import annotations

from pathlib import Path

from azos.gate import Proposal
from azos.runtime import Runtime

ROOT = Path(__file__).resolve().parent / "_out"
ROOT.mkdir(exist_ok=True)


def main() -> None:
    rt = Runtime(root=ROOT)
    proposal = Proposal(
        action="shell",
        definition="Open an ethics-gated AZ-OS shell session in the session vfs.",
        evidence="Example operator requested a principle-bound shell.",
        impact="Sandbox workspace under .azos only. No host subprocess.",
        actor="example-operator",
    )
    result = rt.request(proposal)
    print("passed:", result.passed)
    if not result.passed:
        print(result.invite)
        return
    opened = rt.open_session(token=result.token, actor="example-operator")
    out = rt.run_command("uname", session_id=opened["session"], token=result.token)
    print(out.get("stdout"))
    print("log length:", len(rt.log))
    rt.lumen.stop()


if __name__ == "__main__":
    main()
