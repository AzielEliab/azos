"""Request a builtin through the five gates, then run it.

Not a kernel. Not malware. Overlay session lives under ./_out/.azos.
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
        action="echo",
        definition="Print a bounded status string from a registered builtin.",
        evidence="echo is on the closed SAFE_ACTIONS list in azos.exec.",
        impact="Returns a JSON string. Writes nothing outside .azos.",
        actor="example-operator",
    )
    result = rt.request(proposal)
    print("passed:", result.passed)
    if not result.passed:
        print(result.invite)
        return
    out = rt.run("echo", token=result.token, args={"message": "integrity precedes execution"})
    print(out)
    print("log length:", len(rt.log))
    rt.lumen.stop()


if __name__ == "__main__":
    main()
