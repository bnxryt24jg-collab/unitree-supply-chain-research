"""可视化：把 data/{entities,relations}.json 渲染为可交互关系图谱。

产出：graph.html（自包含：内联 Cytoscape 库 + 内联图数据 + 交互逻辑）。
可直接双击打开，无需起服务、无需联网。

运行：python src/build_graph_html.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "graph.html"
CY = Path("/tmp/cytoscape.min.js")  # Backward-compatible optional override.

# 显示用短名（避免长中文名在图上重叠）；详情面板仍显示全名
SHORT = {
    "SH.688836": "宇树科技", "SH.688017": "绿的谐波", "SH.603728": "鸣志电器",
    "SH.688322": "奥比中光", "SH.603009": "北特科技", "SZ.300580": "贝斯特",
    "SH.603319": "美湖股份", "SZ.002245": "蔚蓝锂芯", "SH.603893": "瑞芯微",
    "SZ.002180": "纳思达", "HK.02498": "速腾聚创", "SZ.300718": "长盛轴承",
    "SH.600143": "金发科技", "SH.600580": "卧龙电驱", "SH.600941": "中国移动",
    "STATE.国家电网": "国家电网", "HK.00788": "中国铁塔", "STATE.华电": "中国华电",
    "EDU.同济大学": "同济大学", "SZ.300543": "朗科智能", "SZ.300454": "深信服",
    "SZ.300496": "中科创达", "SH.603980": "吉华集团", "SZ.300308": "中际旭创",
    "UNLISTED.红杉中国": "红杉中国", "HK.03690": "美团", "HK.09880": "优必选",
    "HK.02432": "越疆科技", "UNLISTED.云深处": "云深处", "UNLISTED.乐聚": "乐聚",
    "UNLISTED.智元": "智元", "US.TSLA": "Tesla", "UNLISTED.Figure": "Figure AI",
    "NVDA": "NVIDIA", "UNLISTED.DeepSeek": "DeepSeek",
    "UNLISTED.GoogleDeepMind": "DeepMind", "GOV.天津市": "天津/津开区",
    "GOV.成都市": "成都市", "GOV.长春净月高新区": "净月高新区",
}


def build_elements():
    ent_doc = json.loads((DATA / "entities.json").read_text(encoding="utf-8"))
    rel_doc = json.loads((DATA / "relations.json").read_text(encoding="utf-8"))
    ents = ent_doc["entities"]
    rels = rel_doc["relations"]

    nodes, edges = [], []
    for eid, e in ents.items():
        full = e.get("name", eid)
        nodes.append({
            "data": {
                "id": eid,
                "label": SHORT.get(eid, full),
                "fullname": full,
                "etype": e.get("entity_type", "company"),
                "ticker": e.get("ticker") or "",
                "role": e.get("role_in_graph", ""),
                "focal": eid == "SH.688836",
                "notes": e.get("notes", ""),
            }
        })
    for r in rels:
        edges.append({
            "data": {
                "id": r["relationship_id"],
                "source": r["subject_entity_id"],
                "target": r["object_entity_id"],
                "rtype": r["relation_type"],
                "tier": r.get("relevance_tier", "supplementary"),
                "status": r["status"],
                "confidence": r["confidence_score"],
                "claim_support": r["claim_support"],
                "statement": r["natural_statement"],
                "evidence": [
                    {"name": ev.get("source_name", ""), "loc": ev.get("evidence_locator", ""),
                     "type": ev.get("source_type", ""), "url": ev.get("url", ""),
                     "published": ev.get("published_date", ""),
                     "retrieved": ev.get("retrieved_date", "")}
                    for ev in r.get("evidence", [])
                ],
                "needs_validation": r.get("needs_human_validation", False),
            }
        })
    return {"nodes": nodes, "edges": edges, "as_of": ent_doc["as_of"],
            "stats": {"entities": len(nodes), "relations": len(edges)}}


TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>宇树科技 · 供应链与合作关系图谱</title>
<style>
  :root{
    --bg:#0f1420; --panel:#171e2e; --panel2:#1f293b; --line:#2c3950;
    --txt:#e6edf7; --muted:#9fb0c9; --accent:#4ea1ff;
    --supplier:#00b894; --customer:#6c5ce7; --partner:#e17055;
    --investor:#00cec9; --peer:#d63031; --focal:#ffd166;
  }
  *{box-sizing:border-box}
  html,body{margin:0;height:100%;font-family:-apple-system,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;background:var(--bg);color:var(--txt)}
  #app{display:flex;height:100vh;overflow:hidden}
  #left{width:280px;min-width:280px;background:var(--panel);border-right:1px solid var(--line);display:flex;flex-direction:column}
  #cy{flex:1;position:relative;background:radial-gradient(circle at 50% 40%,#16213a 0%,#0f1420 70%)}
  #right{width:340px;min-width:340px;background:var(--panel);border-left:1px solid var(--line);padding:16px;overflow:auto}
  h1{font-size:16px;margin:0;padding:16px;border-bottom:1px solid var(--line);line-height:1.4}
  .sub{font-size:11px;color:var(--muted);padding:8px 16px 0}
  .stats{display:flex;gap:8px;padding:12px 16px;flex-wrap:wrap}
  .stat{background:var(--panel2);border:1px solid var(--line);border-radius:8px;padding:8px 10px;font-size:12px;flex:1;text-align:center}
  .stat b{display:block;font-size:18px;color:var(--accent)}
  .sec{padding:12px 16px;border-top:1px solid var(--line)}
  .sec h2{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin:0 0 8px}
  label.chk{display:flex;align-items:center;gap:8px;font-size:13px;padding:3px 0;cursor:pointer}
  .dot{width:10px;height:10px;border-radius:50%;display:inline-block}
  .swatch{width:14px;height:4px;border-radius:2px;display:inline-block}
  input[type=text]{width:100%;padding:8px 10px;background:var(--panel2);border:1px solid var(--line);border-radius:8px;color:var(--txt);font-size:13px}
  .btns{display:flex;gap:6px;flex-wrap:wrap}
  button{background:var(--panel2);border:1px solid var(--line);color:var(--txt);border-radius:8px;padding:6px 10px;font-size:12px;cursor:pointer}
  button:hover{border-color:var(--accent)}
  .legend{font-size:12px;line-height:1.9}
  #right h3{margin:0 0 6px;font-size:15px}
  .tag{display:inline-block;font-size:11px;padding:2px 8px;border-radius:20px;margin:2px 4px 2px 0;background:var(--panel2);border:1px solid var(--line)}
  .relitem{background:var(--panel2);border:1px solid var(--line);border-radius:8px;padding:10px;margin:8px 0;font-size:12px;line-height:1.5}
  .relitem .rt{font-weight:600;color:var(--accent)}
  .ev{font-size:11px;color:var(--muted);margin-top:4px}
  .score{display:flex;gap:6px;flex-wrap:wrap;margin-top:6px}
  .score span{background:#0f1420;border:1px solid var(--line);border-radius:6px;padding:2px 6px;font-size:10px}
  .hint{color:var(--muted);font-size:12px;line-height:1.6}
  .node-label{color:var(--txt);font-size:11px;font-family:inherit}
  .tip{position:absolute;pointer-events:none;background:#000d;color:#fff;padding:4px 8px;border-radius:6px;font-size:12px;display:none;z-index:9}
</style>
</head>
<body>
<div id="app">
  <div id="left">
    <h1>宇树科技<br/><span style="font-size:11px;color:var(--muted)">供应链与合作关系图谱</span></h1>
    <div class="sub">研究对象：宇树科技股份有限公司（688836.SH）· 截点 __ASOF__</div>
    <div class="stats">
      <div class="stat"><b>__NENT__</b>实体</div>
      <div class="stat"><b>__NREL__</b>关系记录</div>
    </div>
    <div class="sec">
      <h2>关系类型</h2>
      <div id="typeFilters"></div>
    </div>
    <div class="sec">
      <h2>相关度分层</h2>
      <label class="chk"><input type="radio" name="tier" value="supported" checked/> 已支持关系</label>
      <label class="chk"><input type="radio" name="tier" value="core"/> 仅核心 core</label>
      <label class="chk"><input type="radio" name="tier" value="supplementary"/> 仅补充 supplementary</label>
      <label class="chk"><input type="radio" name="tier" value="candidate"/> 仅候选 candidate</label>
      <label class="chk"><input type="radio" name="tier" value="all"/> 全部（含候选）</label>
    </div>
    <div class="sec">
      <h2>搜索</h2>
      <input type="text" id="search" placeholder="输入实体名 / 代码…"/>
    </div>
    <div class="sec">
      <h2>布局</h2>
      <div class="btns">
        <button data-layout="cose">力导</button>
        <button data-layout="concentric">同心</button>
        <button data-layout="breadthfirst">树状</button>
        <button data-layout="circle">环形</button>
      </div>
    </div>
    <div class="sec">
      <h2>图例</h2>
      <div class="legend">
        <div><span class="dot" style="background:var(--focal)"></span> 研究对象（宇树）</div>
        <div><span class="dot" style="background:var(--accent)"></span> 核心关系实体</div>
        <div><span class="dot" style="background:#b2bec3"></span> 补充/候选实体</div>
        <div style="margin-top:6px"><span class="swatch" style="background:var(--supplier)"></span> supplier 供应商</div>
        <div><span class="swatch" style="background:var(--customer)"></span> customer 客户</div>
        <div><span class="swatch" style="background:var(--partner)"></span> partner 合作伙伴</div>
        <div><span class="swatch" style="background:var(--investor)"></span> investor 投资</div>
        <div><span class="swatch" style="background:var(--peer)"></span> peer 竞品</div>
        <div style="margin-top:6px;color:var(--muted)">虚线 = inference（推断）</div>
      </div>
    </div>
  </div>
  <div id="cy"><div class="tip" id="tip"></div></div>
  <div id="right">
    <div class="hint" id="defaultHint">点击任意<strong>节点</strong>或<strong>边</strong>查看详情：实体属性、关系结论、证据链与评分维度。<br/><br/>左侧可按要求筛选关系类型、相关度分层，或切换布局。</div>
    <div id="detail"></div>
  </div>
</div>

<script>__CYTOSCAPE__</script>
<script>
const GRAPH = __DATA__;
const REL_COLORS = {supplier:'#00b894',customer:'#6c5ce7',partner:'#e17055',investor_or_investee:'#00cec9',peer:'#d63031'};
const RT_LABEL = {supplier:'供应商',customer:'客户',partner:'合作伙伴',investor_or_investee:'投资/被投',peer:'竞品'};
const ET_SHAPE = {company:'ellipse',government:'round-rectangle',fund:'diamond',person:'hexagon'};
const focalId = 'SH.688836';

const cy = cytoscape({
  container: document.getElementById('cy'),
  elements: GRAPH.nodes.concat(GRAPH.edges),
  style: [
    {selector:'node', style:{
      'label':'data(label)','color':'#e6edf7','font-size':10,'text-valign':'bottom','text-margin-y':4,
      'text-wrap':'wrap','text-max-width':92,'width':32,'height':32,
      'text-outline-width':3,'text-outline-color':'#0b101c','text-outline-opacity':0.95,
      'background-color':'#0984e3','border-width':2,'border-color':'#0f1420'
    }},
    {selector:'node[focal="true"]', style:{
      'background-color':'#ffd166','width':52,'height':52,'font-size':13,'font-weight':'bold',
      'border-color':'#fff','border-width':3
    }},
    {selector:'node[etype="government"]', style:{'shape':'round-rectangle'}},
    {selector:'node[etype="fund"]', style:{'shape':'diamond'}},
    {selector:'node[etype="person"]', style:{'shape':'hexagon'}},
    {selector:'edge', style:{
      'width':2,'line-color':'#888','curve-style':'bezier','target-arrow-shape':'triangle',
      'target-arrow-color':'#888','opacity':0.85
    }},
    {selector:'edge[status="inference"]', style:{'line-style':'dashed'}},
    {selector:'.faded', style:{'opacity':0.12,'text-opacity':0.12}},
    {selector:'.sel', style:{'border-color':'#fff','border-width':3,'z-index':99}}
  ],
  layout:{name:'concentric',
    concentric:function(n){ return n.data('focal')?3:(nodeTier(n)==='core'?2:1); },
    levelWidth:function(){ return 1; }, minNodeSpacing:30, padding:70,
    animate:true, animationDuration:700}
});

// 给边/点着色
cy.edges().forEach(e=>{
  const c = REL_COLORS[e.data('rtype')]||'#888';
  e.style({'line-color':c,'target-arrow-color':c,'width':1.5+Math.max(0,(e.data('confidence')-60)/8)});
});
cy.nodes().forEach(n=>{
  if(!n.data('focal')){
    const t = nodeTier(n);
    n.style('background-color', t==='core'?'#0984e3':'#b2bec3');
  }
});

function nodeTier(n){
  // 节点 tier 取其参与关系中最高的：任一 core 即为 core
  let hasCore=false, hasSupp=false;
  n.connectedEdges().forEach(e=>{ if(e.data('tier')==='core')hasCore=true; else hasSupp=true; });
  if(n.data('focal')) return 'core';
  return hasCore?'core':(hasSupp?'supplementary':'supplementary');
}

// ---- 筛选 ----
const activeTypes = new Set(Object.keys(REL_COLORS));
function applyFilter(){
  const tier = document.querySelector('input[name=tier]:checked').value;
  cy.batch(()=>{
    cy.edges().forEach(e=>{
      const showType = activeTypes.has(e.data('rtype'));
      const showTier = tier==='all' || (tier==='supported' && e.data('tier')!=='candidate') || e.data('tier')===tier;
      const vis = showType && showTier;
      e.style('display', vis?'element':'none');
    });
    cy.nodes().forEach(n=>{
      const connectedVisible = n.connectedEdges().some(e=>e.style('display')!=='none');
      const vis = connectedVisible || n.data('focal');
      n.style('display', vis?'element':'none');
    });
  });
}

// 关系类型勾选
const tf = document.getElementById('typeFilters');
Object.keys(REL_COLORS).forEach(rt=>{
  const l=document.createElement('label'); l.className='chk';
  l.innerHTML=`<input type="checkbox" checked value="${rt}"><span class="swatch" style="background:${REL_COLORS[rt]}"></span>${RT_LABEL[rt]} <span style="color:var(--muted)">(${rt})</span>`;
  l.querySelector('input').addEventListener('change',ev=>{
    ev.target.checked?activeTypes.add(rt):activeTypes.delete(rt); applyFilter();
  });
  tf.appendChild(l);
});
document.querySelectorAll('input[name=tier]').forEach(r=>r.addEventListener('change',applyFilter));
applyFilter();

// 搜索
document.getElementById('search').addEventListener('input',ev=>{
  const q=ev.target.value.trim().toLowerCase();
  if(!q){ cy.elements().removeClass('faded'); return; }
  cy.nodes().forEach(n=>{
    const hit=(n.data('label')+n.data('id')+n.data('ticker')).toLowerCase().includes(q);
    n.style('display', hit||n.data('focal')?'element':'none');
  });
  cy.edges().forEach(e=>{
    const s=e.source(), t=e.target();
    const hit=(s.data('label')+t.data('label')).toLowerCase().includes(q);
    e.style('display',(hit && s.style('display')!=='none' && t.style('display')!=='none')?'element':'none');
  });
});

// 布局按钮
function runLayout(name){
  const opt = name==='concentric'
    ? {name:'concentric',concentric:function(n){return n.data('focal')?3:(nodeTier(n)==='core'?2:1);},levelWidth:function(){return 1;},minNodeSpacing:30,padding:70,animate:true,animationDuration:600}
    : name==='circle'
    ? {name:'circle',padding:60,animate:true,animationDuration:600}
    : name==='breadthfirst'
    ? {name:'breadthfirst',roots:focalId,directed:false,padding:60,spacingFactor:1.1,animate:true,animationDuration:600}
    : {name:'cose',padding:50,nodeRepulsion:14000,idealEdgeLength:130,animate:true,animationDuration:600};
  cy.layout(opt).run();
}
document.querySelectorAll('button[data-layout]').forEach(b=>b.addEventListener('click',()=>runLayout(b.dataset.layout)));

// ---- 详情面板 ----
const detail=document.getElementById('detail');
const hint=document.getElementById('defaultHint');
function showNode(n){
  hint.style.display='none';
  const d=n.data();
  let relsHtml='';
  n.connectedEdges().forEach(e=>{
    const o=e.source().id()===focalId?e.target():e.source();
    relsHtml+=relCard(e,o);
  });
  detail.innerHTML=`<h3>${d.fullname||d.label} ${d.focal?'<span class="tag" style="background:#ffd166;color:#222">研究对象</span>':''}</h3>
    <div class="tag">${d.etype}</div>${d.ticker?`<div class="tag">${d.ticker}</div>`:''}${d.notes?`<div class="hint" style="margin:6px 0">${d.notes}</div>`:''}
    <h2 style="font-size:12px;color:var(--muted);margin:12px 0 4px">参与关系（${n.connectedEdges().length}）</h2>${relsHtml}`;
}
function relCard(e,other){
  const d=e.data();
  const t=d.tier;
  const evHtml=d.evidence.map(x=>`<div class="ev">· ${x.name} <span style="opacity:.7">[${x.type}]</span><br>&nbsp;&nbsp;↳ ${x.loc}<br>&nbsp;&nbsp;↳ ${x.url||'URL 未登记'}<br>&nbsp;&nbsp;↳ 发布 ${x.published||'未知'} · 获取 ${x.retrieved||'未知'}</div>`).join('');
  return `<div class="relitem">
    <div class="rt">${RT_LABEL[d.rtype]||d.rtype} → ${other.data('label')}</div>
    <div>${d.statement}</div>
    <div><span class="tag">${t}</span><span class="tag">${d.status}</span><span class="tag">${d.claim_support}</span><span class="tag">置信度 ${d.confidence}</span></div>
    <div class="score"><span>直接支持 ${scoreOf(d,'direct_support')}</span><span>来源 ${scoreOf(d,'source_authority')}</span><span>交叉验证 ${scoreOf(d,'independent_corroboration')}</span><span>实体/方向 ${scoreOf(d,'entity_direction_certainty')}</span><span>时效 ${scoreOf(d,'timeliness')}</span></div>
    ${evHtml}
  </div>`;
}
function scoreOf(d,key){ return GRAPH._scoreIndex && GRAPH._scoreIndex[d.id] ? GRAPH._scoreIndex[d.id][key] : '–'; }
function showEdge(e){
  hint.style.display='none';
  const o=e.source().id()===focalId?e.target():e.source();
  detail.innerHTML=`<h3>关系详情</h3>`+relCard(e,o);
}
cy.on('tap','node',e=>showNode(e.target()));
cy.on('tap','edge',e=>showEdge(e.target()));
cy.on('tap',ev=>{ if(ev.target===cy){ detail.innerHTML=''; hint.style.display='block'; }});

// hover tooltip
const tip=document.getElementById('tip');
cy.on('mouseover','node',e=>{ tip.textContent=e.target().data('label'); tip.style.display='block'; });
cy.on('mousemove',e=>{ tip.style.left=(e.renderedPosition.x+12)+'px'; tip.style.top=(e.renderedPosition.y+12)+'px'; });
cy.on('mouseout','node',()=>{ tip.style.display='none'; });
</script>
</body>
</html>
"""


def main():
    elements = build_elements()
    # 构建置信度索引，便于详情面板展示 5 个证据维度。
    rel_doc = json.loads((DATA / "relations.json").read_text(encoding="utf-8"))
    score_index = {}
    for r in rel_doc["relations"]:
        s = r["confidence_breakdown"]
        score_index[r["relationship_id"]] = {
            "direct_support": s["direct_support"],
            "source_authority": s["source_authority"],
            "independent_corroboration": s["independent_corroboration"],
            "entity_direction_certainty": s["entity_direction_certainty"],
            "timeliness": s["timeliness"],
        }
    payload = dict(elements)
    payload["_scoreIndex"] = score_index

    if CY.exists():
        cy = CY.read_text(encoding="utf-8")
    elif OUT.exists():
        # The committed graph is the offline dependency fallback. This keeps
        # regeneration reproducible without relying on /tmp or a network.
        previous = OUT.read_text(encoding="utf-8")
        script_start = previous.find("<script>")
        script_end = previous.find("</script>", script_start)
        cy = previous[script_start + len("<script>"):script_end]
        if "cytoscape=" not in cy:
            raise RuntimeError("graph.html does not contain a usable Cytoscape bundle")
    else:
        raise FileNotFoundError(
            "No Cytoscape bundle found. Keep the committed graph.html or provide /tmp/cytoscape.min.js."
        )
    html = (TEMPLATE
            .replace("__CYTOSCAPE__", cy)
            .replace("__DATA__", json.dumps(payload, ensure_ascii=False))
            .replace("__ASOF__", elements["as_of"])
            .replace("__NENT__", str(elements["stats"]["entities"]))
            .replace("__NREL__", str(elements["stats"]["relations"])))
    OUT.write_text(html, encoding="utf-8")
    print(f"已生成 {OUT}（自包含，{OUT.stat().st_size//1024} KB）")
    print(f"  实体 {elements['stats']['entities']} · 关系 {elements['stats']['relations']}")


if __name__ == "__main__":
    main()
