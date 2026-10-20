/**
 * AZ-LOCKSTEP-1.0 host-data scan: generated contracts and design files must not carry anything specific to the
 * build host: no private, CGNAT, link-local, loopback, "this network" or ULA addresses and no network interface names.
 * Build refuses to write a contract that fails it; verify-lockstep fails on a committed one.
 * The legs' vendored verify-lockstep carries the same scanner. Author: Aziel Eliab.
 *
 * R5 (AZBot #323): a regex over dotted quads misses 0.0.0.0/8 and the inet_aton spellings (2130706433,
 * 0177.0.0.1, 0x7f.1, 127.1). Every IP-looking token is now parsed to a normalized IPv4 or IPv6 address
 * (IPv4-mapped IPv6 folds to IPv4) and the range check runs on the parsed value.
 */
export const PRIVATE_IP = /\b(?:10(?:\.\d{1,3}){3}|172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2}|192\.168(?:\.\d{1,3}){2}|169\.254(?:\.\d{1,3}){2}|127(?:\.\d{1,3}){3}|100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])(?:\.\d{1,3}){2})\b|\b(?:fe[89ab][0-9a-f]|fc[0-9a-f]{2}|fd[0-9a-f]{2}):[0-9a-f:]*|(?<![0-9a-z:])::1(?![0-9a-z:.])/i;
export const IFACE = /\b(?:enp\d+s\d+|enx[0-9a-f]{12}|ens\d+|eno\d+|eth\d+|wlan\d+|wlp\d+s\d+|docker\d+|veth[0-9a-f]{4,}|br-[0-9a-f]{12}|virbr\d+|wg\d+|tailscale\d+|utun\d+)\b/;

/** inet_aton-style part: 0x.. hex, leading-0 octal, else decimal. */
function partValue(p) {
  if (/^0x[0-9a-f]*$/i.test(p)) return p.length > 2 ? parseInt(p.slice(2), 16) : 0;
  if (/^0[0-7]*$/.test(p)) return parseInt(p, 8) || 0;
  if (/^[1-9]\d*$/.test(p)) return Number(p);
  return NaN;
}
/** Parse an IPv4 in any inet_aton form (1-4 parts) to a uint32, or null. */
export function parseIpv4(s) {
  const parts = String(s).split(".");
  if (parts.length < 1 || parts.length > 4 || parts.some((x) => x === "")) return null;
  const v = parts.map(partValue);
  if (v.some((x) => !Number.isFinite(x))) return null;
  const last = v[v.length - 1], head = v.slice(0, -1);
  if (head.some((x) => x > 255)) return null;
  const restBits = 8 * (4 - head.length);
  if (last >= 2 ** restBits) return null;
  let n = 0;
  for (const h of head) n = n * 256 + h;
  return n * 2 ** restBits + last;
}
/** Parse IPv6 (with optional embedded dotted IPv4) to 8 numbers, or null. */
export function parseIpv6(s) {
  let t = String(s).toLowerCase();
  let tail = [];
  const m = t.match(/^(.*:)(\d{1,3}(?:\.\d{1,3}){3})$/);
  if (m) {
    const o = m[2].split(".").map(Number);
    if (o.some((x) => x > 255)) return null;
    tail = [o[0] * 256 + o[1], o[2] * 256 + o[3]];
    t = m[1].endsWith("::") ? m[1] : m[1].slice(0, -1);
  }
  const halves = t.split("::");
  if (halves.length > 2) return null;
  const a = halves[0] ? halves[0].split(":") : [];
  const b = halves.length === 2 && halves[1] ? halves[1].split(":") : [];
  if ([...a, ...b].some((g) => !/^[0-9a-f]{1,4}$/.test(g))) return null;
  const fill = 8 - a.length - b.length - tail.length;
  if (halves.length === 1 ? fill !== 0 : fill < 1) return null;
  return [...a.map((g) => parseInt(g, 16)), ...Array(halves.length === 2 ? fill : 0).fill(0), ...b.map((g) => parseInt(g, 16)), ...tail];
}
const V4_RANGES = [[0, 8], [10, 8], [100 * 2 ** 24 + 64 * 2 ** 16, 10], [127 * 2 ** 24, 8], [169 * 2 ** 24 + 254 * 2 ** 16, 16], [172 * 2 ** 24 + 16 * 2 ** 16, 12], [192 * 2 ** 24 + 168 * 2 ** 16, 16]]
  .map(([base, bits]) => [base === 10 ? 10 * 2 ** 24 : base, bits]);
export function isHostIpv4(n) {
  return V4_RANGES.some(([base, bits]) => Math.floor(n / 2 ** (32 - bits)) === Math.floor(base / 2 ** (32 - bits)));
}
export function isHostIpv6(g) {
  if (g.slice(0, 5).every((x) => x === 0) && g[5] === 0xffff) return isHostIpv4(g[6] * 65536 + g[7]); // IPv4-mapped
  if (g.slice(0, 7).every((x) => x === 0) && g[7] <= 1) return true; // :: and ::1
  if ((g[0] & 0xffc0) === 0xfe80) return true; // fe80::/10
  if ((g[0] & 0xfe00) === 0xfc00) return true; // fc00::/7 ULA
  return false;
}
// IPv4-looking token: 1-4 dot parts of decimal/octal/hex, not glued to letters, colons or further dots.
const V4_TOKEN = /(?<![\w.:-])(?:0x[0-9a-f]+|\d+)(?:\.(?:0x[0-9a-f]+|\d+)){0,3}(?![\w:]|\.\w|-\d)/gi;
const V6_TOKEN = /(?<![\w:.])[0-9a-f]{0,4}(?::[0-9a-f]{0,4}){2,7}(?::\d{1,3}(?:\.\d{1,3}){3})?(?![\w:])/gi;

/** Returns the first host-specific finding in text, or null. */
export function hostDataFinding(text) {
  const s = String(text);
  const ip = s.match(PRIVATE_IP);
  if (ip) return ip[0];
  for (const m of s.matchAll(V6_TOKEN)) {
    const tok = m[0].replace(/\.$/, "");
    if (!tok.includes("::") && tok.split(":").length < 8 && !/\d+\.\d+\.\d+\.\d+$/.test(tok)) continue;
    const g = parseIpv6(tok);
    if (g && isHostIpv6(g)) return tok;
  }
  for (const m of s.matchAll(V4_TOKEN)) {
    const tok = m[0];
    const dots = (tok.match(/\./g) || []).length;
    // A bare integer (any base) is only read as an address past 0.255.255.255, so counts, "0", hashes of zeros
    // and short hex like 0x1234 never trip. 0.0.0.0/8 is only matched in full dotted-quad form, so a decimal
    // fraction such as 0.5 is not an address.
    const n0 = parseIpv4(tok);
    if (n0 == null) continue;
    if (dots === 0 && n0 < 2 ** 24) continue;
    if (n0 < 2 ** 24 && dots !== 3) continue;
    if (isHostIpv4(n0)) return tok;
  }
  const nic = s.match(IFACE);
  return nic ? nic[0] : null;
}
