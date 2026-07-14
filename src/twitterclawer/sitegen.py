"""產生單檔 index.html 漫畫閱讀器（file:// 雙擊可用、離線可用）。"""

import json
from pathlib import Path

from . import paths

_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__ARTIST__ 作品集</title>
<style>
  :root { --bg:#16161a; --panel:#1f1f27; --ink:#e8e6e3; --dim:#9a97a3; --accent:#7aa2f7; }
  * { box-sizing:border-box; margin:0; padding:0; }
  body { background:var(--bg); color:var(--ink);
         font-family:"Segoe UI","Microsoft JhengHei",sans-serif; line-height:1.6; }
  a { color:var(--accent); text-decoration:none; cursor:pointer; }
  header { position:sticky; top:0; z-index:9; background:var(--panel);
           padding:.7rem 1rem; display:flex; gap:1rem; align-items:baseline;
           border-bottom:1px solid #333; flex-wrap:wrap; }
  header h1 { font-size:1.05rem; }
  header .sub { color:var(--dim); font-size:.85rem; }
  main { max-width:860px; margin:0 auto; padding:1rem; }
  .ep-list { list-style:none; display:flex; flex-direction:column; gap:.5rem; }
  .ep-list a { display:flex; justify-content:space-between; gap:1rem;
               background:var(--panel); padding:.8rem 1rem; border-radius:8px; }
  .ep-list a:hover { outline:1px solid var(--accent); }
  .ep-list .meta { color:var(--dim); font-size:.85rem; white-space:nowrap; }
  .page { margin:0 0 1.2rem; }
  .page img, .page video { display:block; width:100%; height:auto;
                           border-radius:4px; background:#000; }
  .caption { color:var(--dim); font-size:.9rem; padding:.4rem .2rem;
             white-space:pre-wrap; }
  nav.epnav { display:flex; justify-content:space-between; gap:1rem;
              padding:1rem 0; }
  nav.epnav span { color:#555; }
  .hint { color:var(--dim); font-size:.8rem; text-align:center; padding:1rem 0 2rem; }
</style>
</head>
<body>
<header>
  <h1><a onclick="go('')">__ARTIST__ 作品集</a></h1>
  <span class="sub" id="headSub"></span>
</header>
<main id="main"></main>
<script>
const DATA = __MANIFEST_JSON__;
const EPS = DATA.episodes; // 新到舊
// 本頁位於 sites/<handle>.html，圖檔在 ../data/<handle>/raw/
const RAW = "../data/" + encodeURIComponent(DATA.artist) + "/raw/";

function esc(s){ return String(s).replace(/[&<>"]/g,
  c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c])); }
function day(d){ return d.split(" ")[0]; }
function go(hash){ location.hash = hash; }

function renderIndex(){
  document.getElementById("headSub").textContent =
    EPS.length + " 話 · 資料更新於 " + (EPS[0] ? day(EPS[0].date) : "-");
  const items = EPS.map((ep,i) =>
    '<li><a onclick="go(\\'ep-'+ep.id+'\\')">' +
    '<span>'+esc(ep.title)+'</span>' +
    '<span class="meta">'+day(ep.date)+' · '+ep.pages.length+' 頁</span></a></li>'
  ).join("");
  document.getElementById("main").innerHTML =
    '<ul class="ep-list">'+items+'</ul>' +
    '<p class="hint">點一話開始閱讀 · 閱讀中 ← 上一話（較舊）｜→ 下一話（較新）｜Esc 回目錄</p>';
  window.scrollTo(0,0);
}

function navHtml(i){
  const older = EPS[i+1], newer = EPS[i-1];
  return '<nav class="epnav">' +
    (older ? '<a onclick="go(\\'ep-'+older.id+'\\')">← 上一話</a>' : '<span>← 沒有更舊</span>') +
    '<a onclick="go(\\'\\')">目錄</a>' +
    (newer ? '<a onclick="go(\\'ep-'+newer.id+'\\')">下一話 →</a>' : '<span>沒有更新 →</span>') +
    '</nav>';
}

function renderEpisode(i){
  const ep = EPS[i];
  document.getElementById("headSub").textContent =
    esc(ep.title) + " · " + day(ep.date);
  let prevText = null;
  const EAGER_COUNT = 3; // 前幾張立即載入，其餘 lazy
  const pages = ep.pages.map((p, idx) => {
    const src = RAW + encodeURIComponent(p.file);
    const lazy = idx < EAGER_COUNT ? '' : ' loading="lazy"';
    const media = /\\.(mp4|webm)$/i.test(p.file)
      ? '<video controls src="'+src+'"></video>'
      : '<img'+lazy+' src="'+src+'" alt="">';
    const cap = (p.text && p.text !== prevText)
      ? '<div class="caption">'+esc(p.text)+'</div>' : '';
    prevText = p.text;
    return '<figure class="page">'+media+cap+'</figure>';
  }).join("");
  document.getElementById("main").innerHTML =
    navHtml(i) + '<h2 style="padding:.2rem 0 1rem">'+esc(ep.title)+'</h2>' +
    pages + navHtml(i);
  window.scrollTo(0,0);
}

function route(){
  const h = location.hash.replace(/^#/,"");
  if (h.startsWith("ep-")){
    const i = EPS.findIndex(e => e.id === h.slice(3));
    if (i >= 0){ renderEpisode(i); return; }
  }
  renderIndex();
}

document.addEventListener("keydown", e => {
  const h = location.hash.replace(/^#/,"");
  if (!h.startsWith("ep-")) return;
  const i = EPS.findIndex(x => x.id === h.slice(3));
  if (e.key === "Escape") go("");
  else if (e.key === "ArrowLeft" && EPS[i+1]) go("ep-"+EPS[i+1].id);
  else if (e.key === "ArrowRight" && EPS[i-1]) go("ep-"+EPS[i-1].id);
});
window.addEventListener("hashchange", route);
route();
</script>
</body>
</html>
"""


def render_site(manifest: dict) -> str:
    # "</" 轉義：避免推文文字含 "</script>" 時提早關閉 script 標籤
    data = json.dumps(manifest, ensure_ascii=False).replace("</", "<\\/")
    return _TEMPLATE.replace("__ARTIST__", _esc(manifest["artist"])).replace(
        "__MANIFEST_JSON__", data
    )


def write_site(manifest: dict, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_site(manifest), encoding="utf-8")


_OVERVIEW_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>圖文作家追蹤總覽</title>
<style>
  :root { --bg:#16161a; --panel:#1f1f27; --ink:#e8e6e3; --dim:#9a97a3; --accent:#7aa2f7; }
  * { box-sizing:border-box; margin:0; padding:0; }
  body { background:var(--bg); color:var(--ink);
         font-family:"Segoe UI","Microsoft JhengHei",sans-serif; line-height:1.6; }
  header { background:var(--panel); padding:.9rem 1.2rem; border-bottom:1px solid #333; }
  header h1 { font-size:1.1rem; }
  main { max-width:860px; margin:0 auto; padding:1.2rem 1rem; }
  .cards { list-style:none; display:grid; gap:.8rem;
           grid-template-columns:repeat(auto-fill, minmax(240px, 1fr)); }
  .cards a { display:block; background:var(--panel); border-radius:10px;
             padding:1rem 1.1rem; color:var(--ink); text-decoration:none; }
  .cards a:hover { outline:1px solid var(--accent); }
  .cards .name { color:var(--accent); font-weight:600; font-size:1.05rem;
                 word-break:break-all; }
  .cards .stats { color:var(--dim); font-size:.85rem; margin-top:.3rem; }
  .empty { color:var(--dim); padding:2rem 0; text-align:center; }
</style>
</head>
<body>
<header><h1>圖文作家追蹤總覽</h1></header>
<main>__CARDS__</main>
</body>
</html>
"""


def _esc(s: str) -> str:
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render_overview(entries: list[dict]) -> str:
    if entries:
        cards = "".join(
            f'<li><a href="sites/{_esc(e["artist"])}.html">'
            f'<div class="name">{_esc(e["artist"])}</div>'
            f'<div class="stats">{e["episodes"]} 話 · {e["pages"]} 頁 · '
            f'更新 {_esc(e["updated"])}</div></a></li>'
            for e in entries
        )
        body = f'<ul class="cards">{cards}</ul>'
    else:
        body = '<p class="empty">還沒有追蹤任何作家——雙擊 add-artist.bat 開始。</p>'
    return _OVERVIEW_TEMPLATE.replace("__CARDS__", body)


def write_overview(entries: list[dict], target: Path = paths.INDEX_HTML) -> None:
    target.write_text(render_overview(entries), encoding="utf-8")
