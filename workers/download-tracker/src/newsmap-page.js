import { DESIGN_CSS } from "./lockstep.js";
/**
 * AZ-OS human page for AZNews + 4DMap (GET /aznews, alias /newsmap).
 * Three views (?mode=combined|news|map). AZNews: one globe read marked as a look
 * (?view=1, mints the view receipts for the headlines it shows) and one status read
 * (dry_run). 4DMap: GET /v1/map (corpus + reference layers from AZ-OS's own
 * verified 4DMap copy; no AZNews). When the runtime is unreachable, AZNews answers from
 * AZ-OS's own verified copy (standalone:true). Map: equirectangular, Natural Earth
 * land, colored pins, color key, last 10, permalinks (?mode=..&pin=..). Nothing installed.
 * Author: Aziel Eliab.
 */
import { LAND_PATH, LAND_SOURCE } from "./land-110m.js";

export const NEWSMAP_PAGE_PATHS = Object.freeze(["/aznews", "/newsmap"]);
export const RUNTIME_GLOBE = "https://aziel-runtime.vibelock.workers.dev/aznews";

const PAGE = `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AZNews + 4DMap — AZ-OS — Aziel Eliab</title>
<meta name="description" content="AZNews headlines, Open-Meteo weather, the computed sky, and 4DMap colored pins, read through the AZ-OS newsmap door. Author Aziel Eliab.">
<style>${DESIGN_CSS}
body{font:var(--az-type-body);margin:0;background:var(--az-bg);color:var(--az-ink)}
.wrap{max-width:1180px;margin:0 auto;padding:16px}
a{color:var(--az-link)}h1{font-size:22px;margin:4px 0}h2{font-size:17px;margin:18px 0 6px}
.muted{color:var(--az-muted)}.flags span{display:inline-block;margin:2px 6px 2px 0;padding:2px 8px;border-radius:10px;background:var(--az-card)}
.flags .t{background:#1f6f3f}.flags .f{background:#6e2b2b}.tabs a{margin-right:4px}
.grid{display:grid;grid-template-columns:2fr 1fr;gap:16px}@media(max-width:860px){.grid{grid-template-columns:1fr}}
#map{width:100%;height:auto;background:#0b2239;border:1px solid var(--az-line);border-radius:8px}
#map .land{fill:#2d3b2d;stroke:#4b5b4b;stroke-width:.15}#map .grat{stroke:#1d3a57;stroke-width:.15;fill:none}
#map circle{stroke:#000;stroke-width:.25;cursor:pointer}#map circle.sel{stroke:#fff;stroke-width:.8}
.panel{background:var(--az-card);border:1px solid var(--az-line);border-radius:8px;padding:10px 12px}
ul{padding-left:18px;margin:6px 0}li{margin:3px 0}.dot{display:inline-block;width:10px;height:10px;border-radius:50%;border:1px solid #000;margin-right:6px;vertical-align:middle}
table{border-collapse:collapse;width:100%}td,th{border-bottom:1px solid var(--az-line);padding:3px 6px;text-align:left;font-size:13px}
</style></head><body><div class="wrap">
<p class="muted"><a href="/">AZ-OS</a> · <a href="__GLOBE__">runtime globe</a> · <a href="/v1/newsmap">/v1/newsmap</a> · <a href="/v1/map">/v1/map</a> · <a href="/openapi.json">openapi</a></p>
<h1 id="title">AZNews + 4DMap</h1>
<p class="tabs" id="tabs"><a data-mode="combined" href="?mode=combined">Combined</a> · <a data-mode="news" href="?mode=news">AZNews only</a> · <a data-mode="map" href="?mode=map">4DMap only</a></p>
<p class="muted" id="plain">Reading the newsmap door… Until it answers, nothing here reads live, joined, or merged.</p>
<div class="flags" id="flags"></div>
<div class="flags" id="mapflags"></div>
<div class="grid">
  <div>
    <svg id="map" viewBox="0 0 360 180" role="img" aria-label="World map with AZNews and 4DMap pins">
      <g class="grat" id="grat"></g><path class="land" d="__LAND__"></path><g id="refpins"></g><g id="pins"></g>
    </svg>
    <p class="muted" style="font-size:12px">Map: equirectangular. Land: __LANDSRC__. Pins with no resolved place are listed but not drawn. <label id="reflabel"><input type="checkbox" id="showref" checked> reference places (GeoNames)</label></p>
    <div class="panel" id="detail"><span class="muted">Select a pin to see it here. Each pin has a permalink.</span></div>
    <div data-news><h2>Headlines</h2><div id="news" class="panel muted">__NEWS_INIT__</div></div>
  </div>
  <div>
    <h2>Color key</h2><div id="key" class="panel"></div>
    <h2>Last 10 pins</h2><div id="last" class="panel muted">Loading…</div>
    <div data-news><h2>Sky</h2><div id="sky" class="panel muted">__SKY_INIT__</div>
    <h2>Weather</h2><div id="weather" class="panel muted">__WEATHER_INIT__</div></div>
  </div>
</div>
<h2>How this page reads</h2>
<p class="muted" id="how">Three views. <b>AZNews only</b>: <code>GET /v1/newsmap/globe?view=1</code> (one look; mints the view receipts for the headlines shown) and <code>GET /v1/newsmap</code> (dry_run, mints nothing). <b>4DMap only</b>: <code>GET /v1/map</code>, map pins from the corpus layer (Aziel Corpus map) and the reference layer (GeoNames places), with no AZNews; it mints nothing. <b>Combined</b>: both. AZ-OS keeps its own copies of the runtime AZNews store and the runtime 4DMap store in its own Durable Object (SQLite), sent by the runtime over the signed tether and checked from genesis (pinned Ed25519 key, every document hash, both lattice links) before anything is kept. 4DMap is always served from that copy; AZNews is read from the runtime and served from the copy when the runtime cannot be reached. standalone: true means the answer came from this host's own copy and re-verified against its signed tip just now. A copy is not a live feed, so live reads false whenever the copy answers. Flags are this door's own check, never a relayed claim.</p>
</div>
<script>
(function(){
  var RT = "__RTORIGIN__";
  var Q = new URLSearchParams(location.search);
  var MODE = ({combined:1,news:1,map:1})[Q.get("mode")] ? Q.get("mode") : "combined";
  var WANT_NEWS = MODE !== "map", WANT_MAP = MODE !== "news";
  function el(t, txt, cls){ var e=document.createElement(t); if(txt!=null) e.textContent=String(txt); if(cls) e.className=cls; return e; }
  function clear(id){ var e=document.getElementById(id); e.textContent=""; e.classList.remove("muted"); return e; }
  function safeHref(u){ u=String(u||""); return u.indexOf("https://")===0 ? u : null; }
  function hexOk(h){ return /^#[0-9a-fA-F]{3,8}$/.test(String(h||"")) ? h : "#999"; }
  function link(pid){ return "?mode=" + MODE + "&pin=" + encodeURIComponent(pid); }
  document.querySelectorAll("#tabs a").forEach(function(a){ if (a.getAttribute("data-mode")===MODE){ a.style.fontWeight="bold"; a.style.textDecoration="none"; a.style.color="#e6edf3"; } });
  document.getElementById("title").textContent = MODE==="news" ? "AZNews" : MODE==="map" ? "4DMap" : "AZNews + 4DMap";
  // Map-only view: the AZNews panels say so (also in the served HTML, without JS); nothing is loading.
  if (!WANT_NEWS) { document.getElementById("news").textContent="Headlines hidden in map-only view."; document.getElementById("sky").textContent="Sky hidden in map-only view."; document.getElementById("weather").textContent="Weather hidden in map-only view."; }
  if (!WANT_MAP) document.getElementById("reflabel").style.display="none";
  var grat=document.getElementById("grat"), ns="http://www.w3.org/2000/svg";
  for (var x=0;x<=360;x+=30){ var l=document.createElementNS(ns,"line"); l.setAttribute("x1",x);l.setAttribute("x2",x);l.setAttribute("y1",0);l.setAttribute("y2",180); grat.appendChild(l); }
  for (var y=0;y<=180;y+=30){ var m=document.createElementNS(ns,"line"); m.setAttribute("x1",0);m.setAttribute("x2",360);m.setAttribute("y1",y);m.setAttribute("y2",y); grat.appendChild(m); }
  var wanted = Q.get("pin");
  var COLORS = {}, byId = {}, LAST = [], pending = (WANT_NEWS?1:0) + (WANT_MAP?1:0);
  function colorOf(p){ return hexOk(p.color_hex || (COLORS[p.pin_type] && COLORS[p.pin_type].hex)); }
  function show(p){
    var box=clear("detail");
    box.appendChild(el("b", p.event || p.pin_id)); box.appendChild(el("br"));
    var c=COLORS[p.pin_type]||{}; box.appendChild(el("span", (p.layer ? "layer " + p.layer + " · " : "") + (c.color||p.color||"") + " · " + (c.label||p.pin_type||""), "muted")); box.appendChild(el("br"));
    box.appendChild(el("span", "Date: " + (p.date || "undated"))); box.appendChild(el("br"));
    var g=p.geo; box.appendChild(el("span", "Place: " + (g ? (g.name||"") + " (" + Number(g.lat).toFixed(3) + ", " + Number(g.lon).toFixed(3) + ")" : "none resolved" + (p.geo_reason ? " (" + p.geo_reason + ")" : ""))));
    if (p.report_location_source){ box.appendChild(el("br")); box.appendChild(el("span", "Report location source: " + p.report_location_source)); }
    var src=p.source||{};
    if (p.layer==="corpus"){ box.appendChild(el("br")); box.appendChild(el("span", "Corpus event " + (src.event_id||"") + (src.record_id ? " · record " + src.record_id : "") + (src.status ? " · " + src.status : "") + (src.confidence!=null ? " · confidence " + src.confidence : ""))); }
    if (p.layer==="reference"){ box.appendChild(el("br")); box.appendChild(el("span", "Reference place, not an event. " + (src.gazetteer||"GeoNames") + " (" + (src.license||"CC BY 4.0") + ")", "muted")); }
    box.appendChild(el("br"));
    var a=el("a","Permalink"); a.href=link(p.pin_id); box.appendChild(a);
    if (/^pin-/.test(p.pin_id)){ box.appendChild(document.createTextNode(" · ")); var r=el("a","runtime pin"); r.href=RT + "/aznews?pin=" + encodeURIComponent(p.pin_id); box.appendChild(r); }
    document.querySelectorAll("#map circle").forEach(function(cn){ cn.classList.toggle("sel", cn.getAttribute("data-pin")===p.pin_id); });
  }
  function draw(p){
    byId[p.pin_id]=p; var g2=p.geo; if(!g2||!isFinite(Number(g2.lat))||!isFinite(Number(g2.lon))) return;
    var ref = p.layer==="reference";
    var c=document.createElementNS(ns,"circle"); c.setAttribute("cx", Number(g2.lon)+180); c.setAttribute("cy", 90-Number(g2.lat)); c.setAttribute("r", ref ? 0.7 : 1.6); c.setAttribute("fill", colorOf(p)); c.setAttribute("data-pin", p.pin_id);
    var t=document.createElementNS(ns,"title"); t.textContent=(p.event||p.pin_id); c.appendChild(t);
    c.addEventListener("click", function(){ history.replaceState(null,"",link(p.pin_id)); show(p); });
    document.getElementById(ref ? "refpins" : "pins").appendChild(c);
  }
  document.getElementById("showref").addEventListener("change", function(e){ document.getElementById("refpins").style.display = e.target.checked ? "" : "none"; });
  function addKey(colors){ Object.keys(colors||{}).forEach(function(t){ COLORS[t]=colors[t]; }); var key=clear("key"); Object.keys(COLORS).forEach(function(t){ var c=COLORS[t]; var li=el("div"); var s=el("span","", "dot"); s.style.background=hexOk(c.hex); li.appendChild(s); li.appendChild(el("span", (c.color||"") + " — " + (c.label||t))); key.appendChild(li); }); }
  function done(){
    pending -= 1; if (pending > 0) return;
    LAST.sort(function(a,b){ return String(b.added_at||"").localeCompare(String(a.added_at||"")); });
    var last=clear("last"); var ol=el("ol");
    LAST.slice(0,10).forEach(function(p){ var li=el("li"); var s=el("span","","dot"); s.style.background=colorOf(p); li.appendChild(s); var a=el("a", p.event || p.pin_id); a.href=link(p.pin_id); a.addEventListener("click", function(ev){ ev.preventDefault(); history.replaceState(null,"",link(p.pin_id)); show(byId[p.pin_id]||p); }); li.appendChild(a); li.appendChild(el("span", " " + (p.layer||"news"), "muted")); ol.appendChild(li); });
    if (!LAST.length) last.appendChild(el("span","No pins answered.","muted")); else last.appendChild(ol);
    if (wanted && byId[wanted]) show(byId[wanted]);
    else if (wanted) document.getElementById("detail").textContent = "Pin " + wanted + " is not among the pins shown here. Open AZNews pins on the runtime globe: " + RT + "/aznews?pin=" + wanted;
  }
  function chip(box, name, v){ box.appendChild(el("span", name + ": " + (v===true), v===true ? "t" : "f")); }
  function flags(nm){
    var f=clear("flags"); f.appendChild(el("span","AZNews","")) ;
    [["live",nm.live],["joined",nm.joined],["merged",nm.merged],["lattice_live",nm.lattice_live],["standalone",nm.standalone],["installed",nm.installed]].forEach(function(k){ chip(f,k[0],k[1]); });
    var c=nm.door_join_check, copy=nm.copy||{};
    var p = document.getElementById("plain");
    if (nm.store_copy===true) p.textContent = nm.standalone===true
      ? "The runtime was not used (" + (nm.served_because||"") + "). AZNews is served from AZ-OS's own copy, re-verified just now against the signed tip " + copy.tip_seq + " (from genesis). standalone: true. It is a copy, so live reads false. Joined in the copy: " + (nm.joined===true) + "."
      : "The runtime was not used and AZ-OS's own AZNews copy did not verify (" + ((nm.copy_verify&&nm.copy_verify.reason)||nm.code||"no copy") + "), so standalone is false.";
    else p.textContent = nm.joined===true
      ? "This door checked the join itself just now: the newest stored item (" + (c&&c.item_id) + ") has " + (c&&c.pins_on_item) + " pin(s), and pin " + (c&&c.pin_id) + " opens that same item with a matching report hash. The runtime's own join check agrees."
      : "Not shown as joined here: " + (nm.join_reason || nm.code || "no join check on this read") + ". Live, joined and merged read false on this page.";
  }
  async function getJson(u){ var r=await fetch(u,{headers:{accept:"application/json"}}); return r.json(); }
  if (WANT_NEWS) getJson("/v1/newsmap").then(flags).catch(function(){ document.getElementById("plain").textContent="The newsmap door gave no JSON. Nothing here reads live."; });
  else document.getElementById("plain").textContent="4DMap on its own: no AZNews is read on this view.";
  if (WANT_MAP) getJson("/v1/map?layers=corpus,reference").then(function(m){
    if (m.retracted && m.retracted.count) document.getElementById("how").appendChild(el("span", " " + m.retracted.count + " retracted corpus pin(s) (GEO-PIN-QUALITY-1.0, e.g. geoparser_junk) stay on the lattice but are hidden: /v1/map?include_retracted=1."));
    var f=clear("mapflags"); f.appendChild(el("span","4DMap")); chip(f,"standalone",m.standalone); chip(f,"live",m.live);
    var mc=(m.map_copy&&m.map_copy.copy)||{};
    f.appendChild(el("span", m.ok===false ? "4DMap: " + (m.code||"no answer") : "source: " + (m.source||"") + (mc.tip_seq ? " · copy tip " + mc.tip_seq : "") + " · " + ((m.pins||[]).length) + " pins"));
    addKey(m.colors||{});
    (m.pins||[]).forEach(function(p){ draw(p); if (p.layer!=="reference") LAST.push(p); });
    done();
  }).catch(function(){ clear("mapflags").appendChild(el("span","4DMap: the door gave no JSON","f")); done(); });
  if (WANT_NEWS) getJson("/v1/newsmap/globe?view=1").then(function(g){
    var d = g.runtime || g; addKey(d.colors || {});
    (d.pins||[]).forEach(function(p){ draw(p); });
    (d.last10||[]).forEach(function(p){ LAST.push(p); });
    var news=clear("news"); var ul=el("ul"); (d.items||[]).forEach(function(i){ var li=el("li"); var href=safeHref(i.link); var a=el(href?"a":"span", i.title||i.item_id); if(href){a.href=href;a.rel="noopener";} li.appendChild(a); li.appendChild(el("span"," — " + (i.outlet||"") + " · " + (i.published||""), "muted")); ul.appendChild(li); }); news.appendChild(ul);
    if (g.store_copy===true) news.appendChild(el("div", "From AZ-OS's own verified copy (standalone: " + (g.standalone===true) + ").", "muted"));
    var sky=clear("sky"); var s=d.sky||{};
    if (s.sun) sky.appendChild(el("div","Sun: " + s.sun.tropical_sign + " (tropical), in " + s.sun.constellation + " (IAU)"));
    if (s.moon) sky.appendChild(el("div","Moon: " + (s.moon.phase_name||"") + " · " + (s.moon.illuminated_percent!=null ? s.moon.illuminated_percent + "% lit" : "") + (s.moon.trend ? " · " + s.moon.trend : "") + (s.moon.next_new_moon ? " · next new moon " + s.moon.next_new_moon : "")));
    if (s.seasons) sky.appendChild(el("div","Season: north " + s.seasons.northern_hemisphere + ", south " + s.seasons.southern_hemisphere));
    var vis=Array.isArray(s.visible_tonight)?s.visible_tonight:[];
    if (vis.length){ sky.appendChild(el("div","Visible tonight (at local solar midnight):")); var vul=el("ul"); vis.slice(0,6).forEach(function(a){ var names=(Array.isArray(a.visible)?a.visible:[]).map(function(v){return v&&v.name;}).filter(Boolean).slice(0,6); vul.appendChild(el("li",(a.anchor_name||a.anchor_id||"") + ": " + (names.join(", ")||"none listed"))); }); sky.appendChild(vul); }
    if (s.computed_at) sky.appendChild(el("div","Computed " + s.computed_at, "muted"));
    var w=clear("weather"); var tb=el("table"); var hr=el("tr"); ["Area","°C","Conditions"].forEach(function(h){hr.appendChild(el("th",h));}); tb.appendChild(hr);
    ((d.weather&&d.weather.regions)||[]).forEach(function(r){ var tr=el("tr"); tr.appendChild(el("td",(r.anchor&&r.anchor.name)||"")); var rd=r.reading||{}; tr.appendChild(el("td", rd.temperature_2m!=null ? rd.temperature_2m : rd.temperature_c!=null ? rd.temperature_c : "")); tr.appendChild(el("td",(r.conditions||"") + (r.severe&&r.severe.length ? " · severe: " + r.severe.join(", ") : ""))); tb.appendChild(tr); });
    w.appendChild(tb); if (d.weather && d.weather.source) w.appendChild(el("div", typeof d.weather.source === "string" ? d.weather.source : (d.weather.source.text || "Weather data by Open-Meteo.com"), "muted"));
    if (g.ok===false && !(d.pins||[]).length) document.getElementById("news").textContent = "AZNews did not answer: " + (g.code||"no answer") + (g.local_copy ? " (local copy: " + g.local_copy.code + ")" : "") + ".";
    done();
  }).catch(function(){ ["news","sky","weather"].forEach(function(id){ document.getElementById(id).textContent="The newsmap door gave no JSON."; }); done(); });
})();
</script></body></html>`;

export const PAGE_MODES = Object.freeze(["combined", "news", "map"]);
export function newsmapPageHtml(runtimeOrigin = "https://aziel-runtime.vibelock.workers.dev", mode = "combined") {
  const mapOnly = mode === "map";
  return PAGE.replace("__NEWS_INIT__", mapOnly ? "Headlines hidden in map-only view." : "Loading…").replace("__SKY_INIT__", mapOnly ? "Sky hidden in map-only view." : "Loading…").replace("__WEATHER_INIT__", mapOnly ? "Weather hidden in map-only view." : "Loading…").replace("__LAND__", LAND_PATH).replace("__LANDSRC__", LAND_SOURCE).replace(/__GLOBE__/g, runtimeOrigin + "/aznews").replace("__RTORIGIN__", runtimeOrigin);
}
