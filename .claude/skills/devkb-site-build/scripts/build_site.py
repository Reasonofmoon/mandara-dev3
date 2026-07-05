#!/usr/bin/env python3
"""DevKB 정적 사이트 빌더.
사용법: python3 build_site.py <devkb_dir> <dist_dir>
- 01~05 디렉토리의 md를 ID 기준으로 파싱해 dist/data/content.json 생성
- site/index.html에 본문 렌더링 통합 코드를 주입해 dist/index.html 생성
- 빌드 후 항목 수 assertion 수행 (실패 시 exit 1 — 깨진 사이트 배포 방지)
"""
import json, re, sys, shutil
from pathlib import Path

EXPECTED = {"patterns": 30, "errors": 80, "flows": 25, "prompts": 45, "references": 6}
# 주의: README는 프롬프트 48개로 기재했으나 실제 파일은 45개 (2026-07-05 인벤토리 기준)
ID_RE = re.compile(r"^((?:P|E)-[A-Za-z]+-\d+|F-\d+|PB-[A-Za-z]+-\d+)", re.IGNORECASE)

def first_heading(text, fallback):
    for line in text.splitlines():
        m = re.match(r"^#{1,2}\s+(.+)", line.strip())
        if m:
            return m.group(1).strip()
    return fallback

def collect(devkb: Path):
    content, prompts, skipped = {}, [], []
    buckets = {"patterns": ("01-patterns", "P-"), "errors": ("02-errors", "E-"),
               "flows": ("03-flows", "F-"), "prompts": ("04-prompts", "PB-")}
    counts = {}
    for key, (sub, prefix) in buckets.items():
        n = 0
        for f in sorted((devkb / sub).rglob("*.md")):
            m = ID_RE.match(f.name)
            if not m or not f.name.upper().startswith(prefix):
                skipped.append(str(f.relative_to(devkb)))
                continue
            fid = m.group(1).upper()  # 파일명이 소문자여도 메타데이터 ID(대문자)로 정규화
            text = f.read_text(encoding="utf-8")
            if fid in content:
                skipped.append(f"DUPLICATE {fid}: {f.name}")
                continue
            content[fid] = text
            n += 1
            if key == "prompts":
                prompts.append({"id": fid, "title": first_heading(text, fid),
                                "cat": f.parent.name})
        counts[key] = n
    # references: index.html의 REFERENCES 배열에서 file→id 매핑을 얻는다
    html = (devkb / "site" / "index.html").read_text(encoding="utf-8")
    ref_map = dict(re.findall(r'\{id:"(REF-\d+)"[^}]*?file:"([^"]+)"', html))
    n = 0
    for rid, fname in ref_map.items():
        p = devkb / "05-references" / fname
        if p.exists():
            content[rid] = p.read_text(encoding="utf-8"); n += 1
        else:
            skipped.append(f"MISSING reference file: {fname}")
    counts["references"] = n
    return content, prompts, counts, skipped, html

INJECT_CSS = """
/* injected: full-document rendering */
.md-body { font-size:14px; }
.md-body h1,.md-body h2 { margin:20px 0 10px; font-size:18px; border-bottom:1px solid var(--border); padding-bottom:6px; }
.md-body h3 { margin:16px 0 8px; font-size:15px; color:var(--accent); }
.md-body h4 { margin:12px 0 6px; font-size:14px; }
.md-body p { margin:8px 0; }
.md-body ul,.md-body ol { margin:8px 0 8px 22px; }
.md-body li { margin:3px 0; }
.md-body pre { background:#0a0c12; border:1px solid var(--border); border-radius:8px; padding:12px; overflow-x:auto; margin:10px 0; }
.md-body code { font-family:ui-monospace,Menlo,monospace; font-size:12.5px; color:var(--cyan); }
.md-body pre code { color:var(--text); }
.md-body table { border-collapse:collapse; margin:10px 0; width:100%; font-size:13px; }
.md-body th,.md-body td { border:1px solid var(--border); padding:6px 10px; text-align:left; }
.md-body th { background:var(--bg-hover); }
.md-body blockquote { border-left:3px solid var(--accent); padding:4px 12px; margin:10px 0; color:var(--text-dim); }
.md-body hr { border:0; border-top:1px solid var(--border); margin:16px 0; }
"""

INJECT_JS = r"""
// === injected by build_site.py: full-document content ===
let CONTENT = {}; let PROMPTS = [];
fetch('data/content.json').then(r=>r.json()).then(d=>{ CONTENT=d.content||{}; PROMPTS=d.prompts||[]; render(); }).catch(e=>console.warn('content.json load failed:', e));

function escHtml(s){ return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
function mdInline(s){
  return s.replace(/`([^`]+)`/g,(m,c)=>'<code>'+c+'</code>')
    .replace(/\*\*([^*]+)\*\*/g,'<strong>$1</strong>')
    .replace(/(^|[^*])\*([^*\n]+)\*/g,'$1<em>$2</em>')
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g,'<a href="$2" target="_blank" rel="noopener">$1</a>');
}
function mdRender(src){
  // frontmatter 제거
  src = src.replace(/^---\n[\s\S]*?\n---\n/,'');
  const lines = src.split('\n'); let out=[], i=0, list=null;
  const closeList=()=>{ if(list){ out.push('</'+list+'>'); list=null; } };
  while(i<lines.length){
    let line=lines[i];
    if(/^```/.test(line)){ closeList(); let buf=[]; i++;
      while(i<lines.length && !/^```/.test(lines[i])){ buf.push(lines[i]); i++; }
      out.push('<pre><code>'+escHtml(buf.join('\n'))+'</code></pre>'); i++; continue; }
    if(/^\|/.test(line)){ closeList(); let rows=[];
      while(i<lines.length && /^\|/.test(lines[i])){ rows.push(lines[i]); i++; }
      let html='<table>'; rows.forEach((r,ri)=>{
        if(/^\|[\s:|-]+\|?$/.test(r)) return;
        const cells=r.split('|').slice(1,-1).map(c=>mdInline(escHtml(c.trim())));
        const tag = ri===0?'th':'td';
        html+='<tr>'+cells.map(c=>'<'+tag+'>'+c+'</'+tag+'>').join('')+'</tr>';
      }); out.push(html+'</table>'); continue; }
    let m;
    if(m=line.match(/^(#{1,4})\s+(.*)/)){ closeList(); const l=m[1].length;
      out.push('<h'+l+'>'+mdInline(escHtml(m[2]))+'</h'+l+'>'); }
    else if(/^(-{3,}|\*{3,})\s*$/.test(line)){ closeList(); out.push('<hr>'); }
    else if(m=line.match(/^>\s?(.*)/)){ closeList(); out.push('<blockquote>'+mdInline(escHtml(m[1]))+'</blockquote>'); }
    else if(m=line.match(/^\s*[-*]\s+(.*)/)){ if(list!=='ul'){ closeList(); out.push('<ul>'); list='ul'; } out.push('<li>'+mdInline(escHtml(m[1]))+'</li>'); }
    else if(m=line.match(/^\s*\d+\.\s+(.*)/)){ if(list!=='ol'){ closeList(); out.push('<ol>'); list='ol'; } out.push('<li>'+mdInline(escHtml(m[1]))+'</li>'); }
    else if(line.trim()===''){ closeList(); }
    else { closeList(); out.push('<p>'+mdInline(escHtml(line))+'</p>'); }
    i++;
  }
  closeList(); return out.join('\n');
}
function contentKey(item){ return item ? item.id : null; }

const _openItem = openItem;
openItem = function(type, id){
  if(type==='prompt'){
    const p = PROMPTS.find(x=>x.id===id);
    if(p){ currentItem={...p,_type:'prompt'}; currentView='detail'; render(); document.getElementById('main').scrollTop=0; }
    return;
  }
  _openItem(type, id);
};

const _renderDetail = renderDetail;
renderDetail = function(main){
  if(currentItem && currentItem._type==='prompt'){
    const body = CONTENT[currentItem.id];
    main.innerHTML = '<div class="detail-view">'
      +'<button class="back-btn" onclick="goHome()">← 목록으로</button>'
      +'<div class="detail-header"><div class="card-type prompt" style="font-size:13px">PROMPT · '+currentItem.id+'</div>'
      +'<h2>'+escHtml(currentItem.title)+'</h2>'
      +'<div class="detail-meta"><span class="tag">'+currentItem.cat+'</span></div></div>'
      +'<div class="detail-body"><div class="md-body">'+(body?mdRender(body):'<p>본문 없음</p>')+'</div></div></div>';
    return;
  }
  _renderDetail(main);
  const key = contentKey(currentItem);
  const body = key && CONTENT[key];
  if(body){
    const el = main.querySelector('.detail-body');
    if(el) el.insertAdjacentHTML('beforeend',
      '<h3 style="margin-top:28px;border-top:1px solid var(--border);padding-top:16px">📄 전체 문서</h3><div class="md-body">'+mdRender(body)+'</div>');
  }
};

const _renderSidebar = renderSidebar;
renderSidebar = function(){
  _renderSidebar();
  if(!PROMPTS.length) return;
  const sb = document.getElementById('sidebar');
  const cats = [...new Set(PROMPTS.map(p=>p.cat))];
  let h = '<div class="sidebar-section"><div class="sidebar-title">🧩 Prompt Blocks ('+PROMPTS.length+')</div>';
  cats.forEach(c=>{
    h += '<div class="sidebar-group-title">'+c+'</div>';
    PROMPTS.filter(p=>p.cat===c).forEach(p=>{
      h += '<div class="sidebar-item '+(currentItem&&currentItem.id===p.id?'active':'')+'" onclick="openItem(\'prompt\',\''+p.id+'\')"><span>'+escHtml(p.title)+'</span></div>';
    });
  });
  sb.insertAdjacentHTML('beforeend', h+'</div>');
};
"""

def main():
    devkb, dist = Path(sys.argv[1]), Path(sys.argv[2])
    content, prompts, counts, skipped, html = collect(devkb)

    # 원본 버그 수리: JS 객체 리터럴에 CSS 문법(color:var(--x))이 섞여 파싱 오류를 내는 문제.
    # <script> 구간에서만 따옴표로 감싼다 (<style> 구간의 정상 CSS는 건드리지 않음).
    head, sep, script = html.partition("<script>")
    # 객체 리터럴 문맥({ 또는 , 뒤)만 치환 — 템플릿 문자열 내 style="color:var(--x)"는 정상이므로 보존
    script = re.sub(r"([{,]\s*color):(var\(--[a-z]+\))", r'\1:"\2"', script)
    html = head + sep + script

    # HTML 주입
    assert "// Init\nrender();" in html, "주입 앵커(// Init) 미발견 — index.html 구조 변경됨"
    html = html.replace("</style>", INJECT_CSS + "\n</style>", 1)
    html = html.replace("// Init\nrender();", INJECT_JS + "\n// Init\nrender();", 1)

    # 삭제가 제한된 환경(Cowork 마운트)이 있으므로 rmtree 대신 고정 파일명 덮어쓰기
    try:
        if dist.exists(): shutil.rmtree(dist)
    except PermissionError:
        pass
    (dist / "data").mkdir(parents=True, exist_ok=True)
    (dist / "index.html").write_text(html, encoding="utf-8")
    (dist / "data" / "content.json").write_text(
        json.dumps({"content": content, "prompts": prompts}, ensure_ascii=False), encoding="utf-8")
    meta = {"counts": counts, "content_items": len(content), "skipped": skipped}
    (dist / "data" / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(meta, ensure_ascii=False, indent=2))
    fails = [f"{k}: expected {v}, got {counts.get(k)}" for k, v in EXPECTED.items() if counts.get(k) != v]
    if fails:
        print("ASSERTION FAILED:\n" + "\n".join(fails)); sys.exit(1)
    print("BUILD OK")

if __name__ == "__main__":
    main()
