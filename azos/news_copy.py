"""AZ-OS local standalone copy of the AZNews store (AZOS-NEWS-COPY-1.0, CLI side).

The AZ-OS tracker keeps a verified copy of the aziel-runtime AZNews store in its own
Durable Object: the runtime sends signed rows (AZRT-AZOS-NEWS-1.0) and the tracker
checks the Ed25519 signature against the pinned runtime key and every hash before it
keeps them. ``sync()`` pulls that copy to this machine (``GET /v1/aznews/copy``) and
checks it again here, row by row from genesis: each document hash (when the document
is still present), each primary = H(document, primary_prev), each secondary, and the
links. ``serve()`` then works offline: it re-checks the served window up to the stored
tip and reports ``standalone: True`` only when that check passes. It is a copy, so
``live`` stays False. Nothing here is minted, posted, or installed.

Author: Aziel Eliab.
"""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from azos.httpget import get_bytes

AUTHOR = "Aziel Eliab"
COPY_SPEC = "AZOS-NEWS-COPY-1.0"
TRACKER = "https://azos-download-tracker.vibelock.workers.dev"
GENESIS = "0" * 64
PAGE = 500
READ_WINDOW = 3000


def _js_number(x: Any) -> str:
    if isinstance(x, bool):
        return "true" if x else "false"
    if isinstance(x, int):
        return str(x)
    if x != x or x in (float("inf"), float("-inf")):
        raise ValueError("non-finite number")
    if x == 0:
        return "0"
    sign = "-" if x < 0 else ""
    d = Decimal(repr(abs(x)))
    t = d.as_tuple()
    digits = "".join(str(v) for v in t.digits).rstrip("0") or "0"
    k = len(digits)
    n = t.exponent + len(t.digits)
    if k <= n <= 21:
        return sign + digits + "0" * (n - k)
    if 0 < n <= 21:
        return sign + digits[:n] + "." + digits[n:]
    if -6 < n <= 0:
        return sign + "0." + "0" * (-n) + digits
    e = n - 1
    mant = digits[0] + ("." + digits[1:] if k > 1 else "")
    return sign + mant + "e" + ("+" if e > 0 else "-") + str(abs(e))


def canonicalize(value: Any) -> str:
    """Same bytes as the runtime's canonicalize (sorted keys, JS number and string forms)."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return _js_number(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, list):
        return "[" + ",".join(canonicalize(v) for v in value) + "]"
    if isinstance(value, dict):
        keys = sorted(value.keys(), key=lambda s: s.encode("utf-16-be"))
        return "{" + ",".join(json.dumps(k, ensure_ascii=False) + ":" + canonicalize(value[k]) for k in keys) + "}"
    raise ValueError("cannot canonicalize " + type(value).__name__)


def _h(obj: Any) -> str:
    return hashlib.sha256(canonicalize(obj).encode("utf-8")).hexdigest()


def check_row(row: dict[str, Any], expected: dict[str, str]) -> str | None:
    """None when the row's hashes recompute and it links to ``expected``; else a reason."""
    lat = row.get("lattice") or {}
    if lat.get("primary_prev") != expected["primary"] or lat.get("secondary_prev") != expected["secondary"]:
        return "does not link to the previous tip"
    if row.get("doc") is not None and _h(row["doc"]) != lat.get("document_hash"):
        return "document hash does not recompute"
    if _h({"document": lat.get("document_hash"), "prev": lat.get("primary_prev") or GENESIS}) != lat.get("primary"):
        return "primary hash does not recompute"
    if lat.get("offline") is True:
        want = _h({"primary": lat.get("document_hash"), "username": str(lat.get("username"))})
    else:
        want = _h({"offline": False, "prev": lat.get("secondary_prev") or GENESIS, "primary": lat.get("primary")})
    if want != lat.get("secondary"):
        return "secondary hash does not recompute"
    return None


def copy_dir(root: Path | str | None = None) -> Path:
    base = Path(root) if root is not None else Path.cwd()
    return base / ".azos" / "aznews-copy"


def _load(root: Path | str | None) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    d = copy_dir(root)
    meta_p, rows_p = d / "meta.json", d / "rows.jsonl"
    if not meta_p.exists() or not rows_p.exists():
        return None, []
    meta = json.loads(meta_p.read_text("utf-8"))
    rows = [json.loads(line) for line in rows_p.read_text("utf-8").splitlines() if line.strip()]
    return meta, rows


def sync(root: Path | str | None = None, *, tracker: str = TRACKER, pages: int = 20, fetch=get_bytes) -> dict[str, Any]:
    """Pull new rows from the tracker's verified copy and check them here before keeping them."""
    d = copy_dir(root)
    d.mkdir(parents=True, exist_ok=True)
    meta, _rows = _load(root)
    tip_seq = int(meta["tip_seq"]) if meta else 0
    expected = dict(meta["tips"]) if meta else {"primary": GENESIS, "secondary": GENESIS}
    added = 0
    remote_tip = None
    for _ in range(max(1, pages)):
        status, body = fetch(f"{tracker}/v1/aznews/copy?after={tip_seq}&limit={PAGE}", limit=40_000_000, timeout=30.0)
        if status != 200 or not body:
            return {"ok": False, "code": "NEWS-COPY-SYNC-UNREACHABLE", "rows_added": added, "tip_seq": tip_seq, "author": AUTHOR}
        page = json.loads(body.decode("utf-8"))
        remote_tip = page.get("tip_seq")
        if page.get("from_genesis") is not True:
            return {"ok": False, "code": "NEWS-COPY-SYNC-NOT-GENESIS", "rows_added": added, "author": AUTHOR}
        rows = page.get("rows") or []
        if not rows:
            break
        good = []
        for row in rows:
            if int(row.get("seq", -1)) != tip_seq + len(good) + 1:
                return {"ok": False, "code": "NEWS-COPY-SYNC-SEQ", "at_seq": row.get("seq"), "rows_added": added, "author": AUTHOR}
            why = check_row(row, expected)
            if why:
                return {"ok": False, "code": "NEWS-COPY-SYNC-HASH", "at_seq": row.get("seq"), "reason": why, "rows_added": added, "author": AUTHOR}
            good.append(row)
            expected = {"primary": row["lattice"]["primary"], "secondary": row["lattice"]["secondary"]}
        with (d / "rows.jsonl").open("a", encoding="utf-8") as fh:
            for row in good:
                fh.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
        tip_seq += len(good)
        added += len(good)
        meta = {"spec": COPY_SPEC, "from_genesis": True, "tip_seq": tip_seq, "tips": expected, "tracker": tracker}
        (d / "meta.json").write_text(json.dumps(meta), "utf-8")
        if remote_tip is not None and tip_seq >= int(remote_tip):
            break
    tips_match = remote_tip is not None and tip_seq == int(remote_tip) and (page.get("tips") or {}).get("primary") == expected["primary"]
    return {"ok": True, "code": "NEWS-COPY-SYNCED", "rows_added": added, "tip_seq": tip_seq, "tracker_tip_seq": remote_tip, "tips_match_tracker": tips_match, "author": AUTHOR}


def _news(r: dict[str, Any]) -> dict[str, Any]:
    d = r.get("doc") or {}
    return {"seq": r["seq"], "item_id": d.get("item_id"), "title": d.get("title"), "outlet": (d.get("outlet") or {}).get("name"), "link": d.get("canonical_url") or d.get("link"), "published": d.get("published")}


def _pin(r: dict[str, Any]) -> dict[str, Any]:
    d = r.get("doc") or {}
    return {"pin_id": f"pin-{r['seq']}", "pin_type": d.get("pin_type"), "color": d.get("color"), "event": d.get("event"), "geo": d.get("geo"), "date": d.get("date")}


def serve(op: str = "feed", root: Path | str | None = None, *, limit: int = 20) -> dict[str, Any]:
    """Answer offline from the local copy. standalone is True only when the window re-verifies."""
    base = {"source": "azos-local-copy (cli)", "spec": COPY_SPEC, "live": False, "merged": False, "installed": False, "mints_receipts": False, "author": AUTHOR}
    meta, rows = _load(root)
    if not meta or not rows:
        return {**base, "ok": False, "standalone": False, "code": "NEWS-COPY-EMPTY", "plain": "There is no local copy yet. Run azos.news_copy.sync() while the tracker is reachable."}
    window = rows[-READ_WINDOW:]
    first = window[0]
    if first["seq"] == 1:
        expected = {"primary": GENESIS, "secondary": GENESIS}
    else:
        prev = rows[-len(window) - 1]["lattice"]
        expected = {"primary": prev["primary"], "secondary": prev["secondary"]}
    reason = None
    for r in window:
        why = check_row(r, expected)
        if why:
            reason = f"row {r['seq']}: {why}"
            break
        expected = {"primary": r["lattice"]["primary"], "secondary": r["lattice"]["secondary"]}
    if reason is None and (expected != meta["tips"] or window[-1]["seq"] != meta["tip_seq"]):
        reason = "the last row is not the stored tip"
    ok = reason is None and meta.get("from_genesis") is True
    n = max(1, min(50, int(limit)))
    news = [r for r in reversed(window) if r["kind"] == "news" and r.get("doc")][:n]
    pins = [r for r in reversed(window) if r["kind"] == "pin" and r.get("doc")][: max(n, 10)]
    sky = next((r for r in reversed(window) if r["kind"] == "sky" and r.get("doc")), None)
    body: dict[str, Any] = {"op": op}
    if op in ("feed", "status"):
        body["items"] = [_news(r) for r in news]
    if op in ("pins", "status"):
        body["pins"] = [_pin(r) for r in pins]
        body["last10"] = body["pins"][:10]
    if op in ("sky", "status"):
        body["sky"] = sky["doc"] if sky else None
    return {
        **base,
        **body,
        "ok": ok,
        "standalone": ok,
        "code": "NEWS-COPY-SERVED" if ok else "NEWS-COPY-UNVERIFIED",
        "copy": {"tip_seq": meta["tip_seq"], "tips": meta["tips"], "rows": len(rows), "from_genesis": meta.get("from_genesis") is True},
        "copy_verify": {"ok": reason is None, "from": first["seq"], "to": window[-1]["seq"], "reason": reason},
        "plain": (
            "Served offline from AZ-OS's own copy of the AZNews store, re-checked just now up to tip "
            f"{meta['tip_seq']}. It is a copy, so live is false."
            if ok
            else f"The local copy did not verify ({reason}), so standalone is false."
        ),
    }
