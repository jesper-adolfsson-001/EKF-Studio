import {createLinkController} from './links.js';
const $ = (s, root = document) => root.querySelector(s);
if(location.search.includes('access='))history.replaceState(null,'',location.pathname+location.hash);
const $$ = (s, root = document) => [...root.querySelectorAll(s)];
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const paths = {
  home:'M3 10 12 3l9 7v10H3Z M9 20v-7h6v7', grid:'M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z',
  graph:'M7 6h10 M6 8v8 M18 8v8 M8 18h8 M8 8l8 8 M8 16l8-8 M3 3h5v5H3z M16 3h5v5h-5z M3 16h5v5H3z M16 16h5v5h-5z',
  check:'m5 12 4 4L19 6', checkCircle:'M22 11v1a10 10 0 1 1-6-9 M22 4 12 14l-3-3', file:'M14 2H5v20h14V7z M14 2v6h5 M8 12h8 M8 16h6',
  code:'m8 6-6 6 6 6 M16 6l6 6-6 6 M14 3l-4 18', clock:'M12 8v5l3 2 M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0',
  settings:'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8 M9 3h6l1 3 3 1 2 5-2 5-3 1-1 3H9l-1-3-3-1-2-5 2-5 3-1Z',
  search:'M16 16l5 5 M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0', plus:'M12 5v14 M5 12h14', down:'m6 9 6 6 6-6',
  right:'M5 12h14 m-5-5 5 5-5 5', chevron:'m9 5 7 7-7 7', close:'m6 6 12 12 M6 18 18 6', branch:'M6 3v12 M18 3v3c0 6-12 3-12 9 M3 18a3 3 0 1 0 6 0 3 3 0 0 0-6 0 M3 3a3 3 0 1 0 6 0 M15 3a3 3 0 1 0 6 0',
  layers:'m12 3 10 5-10 5L2 8z M2 12l10 5 10-5 M2 16l10 5 10-5', arrowUp:'m6 14 6-6 6 6 M12 8v12',
  warning:'m12 3 10 18H2Z M12 9v5 M12 17v1', link:'m9 15 6-6 M8 16l-2 2a4 4 0 0 1-6-6l5-5a4 4 0 0 1 6 0 M16 8l2-2a4 4 0 0 1 6 6l-5 5a4 4 0 0 1-6 0',
  box:'m12 2 10 5v10l-10 5-10-5V7Z M2 7l10 5 10-5 M12 12v10', target:'M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0 M17 12a5 5 0 1 1-10 0 5 5 0 0 1 10 0 M12 10v4',
  shield:'m12 2 9 4v6c0 5-9 10-9 10S3 17 3 12V6Z m-4 10 3 3 5-6', play:'m7 4 14 8-14 8Z', terminal:'m4 6 6 6-6 6 M12 18h8',
  list:'M9 5h12 M9 12h12 M9 19h12 M3 5h1 M3 12h1 M3 19h1', download:'M12 3v12 m-5-5 5 5 5-5 M3 16v5h18v-5',
  edit:'m16 3 5 5L8 21H3v-5Z M13 6l5 5', tag:'M3 3h8l10 10-8 8L3 11Z M7 7h.01', spark:'m12 2 3 7 7 3-7 3-3 7-3-7-7-3 7-3Z',
  menu:'M3 6h18 M3 12h18 M3 18h18', refresh:'M20 7V2l-3 3a9 9 0 1 0 4 11 M20 2h-5', globe:'M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0 M2 12h20 M12 2c6 6 6 14 0 20-6-6-6-14 0-20',
  lock:'M5 10h14v12H5z M8 10V6a4 4 0 0 1 8 0v4', question:'M9 8a3 3 0 1 1 5 2c-2 1-2 2-2 4 M12 17v1 M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0',
};
const icon = (name, size=16) => `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${paths[name] || paths.file}"/></svg>`;
const typeConfig = {
  intent:['target','#659c88','#edf5ef'], requirement:['file','#6b8caf','#eef3f9'], constraint:['lock','#a38a63','#f7f1e9'],
  architecture:['layers','#9279ad','#f3eff8'], component:['box','#9580ad','#f3eff8'], interface:['link','#a38a63','#f7f2e9'],
  decision:['branch','#8b91b0','#f1f2f8'], assumption:['question','#b49758','#fbf5e9'], hazard:['warning','#b97c70','#fbf0ec'],
  risk:['shield','#b3895a','#fbf4e9'], verification:['checkCircle','#729c86','#eef6f0'], evidence:['check','#7f9b6c','#f1f6ec'], tool:['code','#7c9c98','#eef5f3']
};
const tc = type => typeConfig[type] || ['file','#849991','#f0f4f2'];
const typeIcon = type => `<span class="type-icon" style="--type-color:${tc(type)[1]};--type-bg:${tc(type)[2]}">${icon(tc(type)[0])}</span>`;
const badge = status => `<span class="badge ${esc(String(status).replace(/[^a-z-]/g,''))}">${esc(String(status).replaceAll('-',' '))}</span>`;
const btn = (label, action, ico='', cls='', attrs='') => readonly()&&writeActions.has(action)?'':`<button class="btn ${cls}" data-action="${action}" ${attrs}>${ico ? icon(ico,14) : ''}${label}</button>`;
const empty = (title, text, action='') => `<div class="empty">${icon('layers',30)}<h3>${esc(title)}</h3><p>${esc(text)}</p>${action}</div>`;
const date = value => new Date(value).toLocaleString(undefined,{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'});
const state = {page:location.hash.slice(1)||'overview', tab:'all', layout:'table', query:'', type:'', discipline:'', status:'', graphMode:'graph', verificationTab:'coverage', agentTab:'execute', detailTab:'content', focus:'', graphViews:new Map(), data:null, proposals:[], runs:[], history:[], baselines:[], tools:null};
Object.assign(state,{revision:null,historyTab:'timeline',compareBefore:'',compareAfter:'',comparison:null,comparisonLoading:false});
try{state.revision=JSON.parse(sessionStorage.getItem('ekf-revision')||'null');}catch{}
state.overviewRoots={};
try{state.overviewRoots=JSON.parse(sessionStorage.getItem('ekf-overview-roots')||'{}')||{};}catch{}
state.overviewTypes={};
try{state.overviewTypes=JSON.parse(sessionStorage.getItem('ekf-overview-types')||'{}')||{};}catch{}
let editorArtifact = null, editorMode = 'guided', toastTimer, pollTimer, currentRun, currentDetail;
let viewRequest=0, comparisonRequest=0, detailRequest=0;
const readonly = () => Boolean(state.revision);
const revisionPath = (path,ref=state.revision?.commit) => ref ? path+(path.includes('?')?'&':'?')+'ref='+encodeURIComponent(ref) : path;
const writeActions = new Set(['new','import','edit','save-artifact','review','proposal-new','proposal-create','proposal-decide','baseline','baseline-create','run','evidence','probe','manifest','manifest-save','links-open','editor-links','graph-child','editor-suggest-id']);

async function api(path, body) {
  if(body!==undefined&&readonly())throw new Error('This baseline is read only. Return to the current workspace to make changes.');
  const response = await fetch('/api/'+path,{...(body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})});
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Request failed');
  return data;
}
function toast(message,error=false) { clearTimeout(toastTimer); $('#notifications').innerHTML=`<div class="toast ${error?'error':''}">${esc(message)}</div>`;toastTimer=setTimeout(()=>$('#notifications').innerHTML='',5000); }
async function refresh(render=true) {
  const request=++viewRequest;
  const [data,proposals,runs,history,tools] = await Promise.all([api(revisionPath('snapshot')),api('proposals'),api('runs'),api('history'),api('tools')]);
  if(request!==viewRequest)return;
  Object.assign(state,{data,proposals,runs,history:history.history,baselines:history.baselines,tools});
  if(render) renderShell();
}
async function selectVersion(ref='',name=ref){
  const request=++viewRequest;
  closeOverlay(true);
  const data=await api(revisionPath('snapshot',ref));
  if(request!==viewRequest)return;
  state.revision=ref?{commit:data.head,name}:null;
  sessionStorage.setItem('ekf-revision',JSON.stringify(state.revision));
  state.data=data;state.query='';state.type='';state.discipline='';state.status='';state.focus='';state.graphViews.clear();
  renderShell();
}
function navigate(page) {state.page=page;state.query='';state.type='';state.discipline='';state.status='';state.focus='';location.hash=page;closeOverlay(true);renderShell();window.scrollTo(0,0);}
const pages = {overview:['Overview','home'],knowledge:['Knowledge library','layers'],traceability:['Traceability','graph'],verification:['Verification','checkCircle'],reports:['Generated views','file'],agent:['Agent workbench','spark'],changes:['Change proposals','branch'],activity:['History & baselines','clock'],settings:['Workspace settings','settings']};
function renderShell() {
  closeGraphMenu();
  if(!pages[state.page])state.page='overview';
  if(readonly()&&['agent','changes','settings'].includes(state.page))state.page='overview';
  const d=state.data, system=d.manifest.system||{}, pending=state.proposals.filter(p=>p.status==='pending').length;
  const nav = key => `<button class="nav-item ${state.page===key?'active':''}" data-action="nav" data-page="${key}" ${state.page===key?'aria-current="page"':''}>${icon(pages[key][1],16)}${pages[key][0]}${key==='knowledge'?`<span class="count">${d.artifacts.length}</span>`:key==='changes'&&pending?`<span class="count">${pending}</span>`:''}</button>`;
  $('#app').innerHTML=`<div class="shell"><aside class="sidebar"><div class="brand"><img src="/favicon.svg" alt=""><div class="brand-name">EKF <span>Studio</span></div></div>
    <button class="workspace-switch" data-action="nav" data-page="settings"><span class="avatar">${esc((system.id||'EK').slice(0,2))}</span><span><strong>${esc(system.title||'Engineering workspace')}</strong><small>${d.manifest.studio?.demo?'Example workspace':'Local workspace'}</small></span>${icon('down',12)}</button>
    <div class="nav-label">WORKSPACE</div>${['overview','knowledge','traceability','verification','reports'].map(nav).join('')}
    <div class="sidebar-sep"></div><div class="nav-label">ENGINEERING OPERATIONS</div>${(readonly()?['activity']:['agent','changes','activity']).map(nav).join('')}
    <div class="sidebar-bottom">${readonly()?'':nav('settings')}<div class="local-state"><span class="dot"></span>Local repository · EKF v0.1</div><div class="user"><span class="user-icon">LE</span><span><strong>Local engineer</strong><small>${readonly()?'Reading a baseline':'Human reviewer'}</small></span></div></div></aside>
    <main class="main"><header class="topbar"><div class="breadcrumb"><button class="icon-btn mobile-menu" aria-label="Toggle navigation" data-action="menu">${icon('menu')}</button><span>Workspace</span>${icon('chevron',10)}<span class="current">${pages[state.page][0]}</span></div><div class="top-actions"><button class="search-trigger" data-action="search" aria-label="Search knowledge">${icon('search',15)}<span>Search anything…</span><kbd>⌘ K</kbd></button><select class="revision-select" id="workspace-revision" aria-label="Workspace version"><option value="">Current workspace${!readonly()?' · '+esc(d.branch||'detached'):''}</option>${state.baselines.map(b=>`<option value="${esc(b.name)}" ${readonly()&&state.revision.name===b.name?'selected':''}>${esc(b.name)}</option>`).join('')}${readonly()&&!state.baselines.some(b=>b.name===state.revision.name)?`<option selected value="${esc(state.revision.commit)}">${esc(state.revision.name)}</option>`:''}</select><button class="icon-btn" data-action="refresh" aria-label="Refresh repository">${icon('refresh',14)}</button></div></header>${readonly()?`<div class="baseline-banner" role="status"><span>${icon('lock',15)} Viewing baseline <strong>${esc(state.revision.name)}</strong> · <code>${esc(d.head.slice(0,7))}</code> · Read only</span>${btn('Return to current workspace','current-workspace','right','small')}</div>`:''}<div class="content reveal" id="content">${renderPage()}</div></main></div>`;
  if(readonly())$$('[data-action]').filter(el=>writeActions.has(el.dataset.action)).forEach(el=>el.hidden=true);
}
function heading(title,subtitle,actions=''){return `<div class="page-heading"><div><h1>${title}</h1><p>${subtitle}</p></div><div class="heading-actions">${actions}</div></div>`;}
function footer(){return `<div class="footer-note"><span>${icon('branch',12)}Source of truth: Markdown + YAML. History: Git.</span><span>EKF v0.1 · ${esc(state.data.head.slice(0,7))}${state.data.manifest.studio?.demo?' · Synthetic example data':''}</span></div>`;}
function renderPage(){const renderers={overview,knowledge,traceability,verification,reports,agent,changes,activity,settings};return renderers[state.page]()+footer();}
function overview(){
  const d=state.data,v=d.validation,req=v.coverage,covered=req.filter(r=>r.verification.length).length,pct=req.length?Math.round(covered/req.length*100):0;
  const assumption=d.artifacts.filter(a=>a.type==='assumption'&&(a.meta.status||'draft')==='draft');
  const stat=(label,value,sub,ico,page,extra='')=>`<button class="stat stat-link" data-action="nav" data-page="${page}"><div class="stat-label">${icon(ico,13)}${label}</div><div class="stat-number" style="text-align:left">${value}${extra}</div><div class="stat-foot" style="text-align:left">${sub}</div></button>`;
  return heading('Engineering, connected.','One workspace for intent, design, verification, and the evidence behind it.',btn('New artifact','new','plus','primary'))+
    `<section class="welcome"><div><div class="eyebrow" style="margin-bottom:7px;color:#819680">${esc(d.manifest.system?.id||'WORKSPACE')} / ENGINEERING KNOWLEDGE</div><h2>${esc(d.manifest.system?.title||'Your engineering workspace')}</h2><p>${esc(d.manifest.studio?.description||'A living graph of engineering knowledge, across every discipline.')}</p></div><svg class="welcome-mark" viewBox="0 0 200 70" fill="none" stroke="currentColor"><path d="M10 35h40l35-23 40 23 35-23h30 M50 35l35 23 40-23 35 23h30 M85 12v46 M125 35h65"/><g fill="#edf2ee">${[[10,35],[50,35],[85,12],[85,58],[125,35],[160,12],[160,58],[190,35]].map(([x,y])=>`<circle cx="${x}" cy="${y}" r="4"/>`).join('')}</g></svg></section>
    <div class="stats">${stat('Knowledge artifacts',d.artifacts.length,`${new Set(d.artifacts.map(a=>a.type)).size} artifact types · all connected`,'layers','knowledge')}${stat('Trace relationships',d.edges.length,'Engineering meaning, made visible','graph','traceability')}${stat('Verification planned',pct+'<small>%</small>',`${covered} of ${req.length} requirements have a method`,'checkCircle','verification')}${stat('Open assumptions',assumption.length,'Uncertainty to resolve together','question','verification')}</div>
    <div class="dashboard-grid"><div>${overviewGraphPanel()}
    <section class="panel recent-panel"><div class="panel-head"><h2>Explore the knowledge</h2><button class="text-link" data-action="nav" data-page="knowledge">View all artifacts ${icon('right',12)}</button></div>${artifactTable(d.artifacts.filter(a=>['requirement','architecture','interface','decision'].includes(a.type)).slice(0,5),true)}</section></div>
    <div class="aside-stack"><section class="panel"><div class="panel-head"><h2>Engineering health</h2>${icon('shield',15)}</div><div class="health-top"><div class="health-ring"><svg viewBox="0 0 70 70"><circle cx="35" cy="35" r="29" fill="none" stroke="#edf1ed" stroke-width="5"/><circle cx="35" cy="35" r="29" fill="none" stroke="#87aa8d" stroke-width="5" stroke-dasharray="${pct*1.822} 182.2" stroke-linecap="round"/></svg><strong>${pct}<small style="font-size:10px">%</small></strong></div><div><h3>Verification coverage</h3><p>Linked methods across<br>active requirements</p></div></div><div class="health-list"><div class="health-row"><span>Syntax conformance</span><b>${v.syntactic?'Passing':'Needs attention'}</b></div><div class="health-row"><span>Graph integrity</span><b>${v.graph?'All targets resolved':v.errors+' errors'}</b></div><div class="health-row"><span>Engineering advisories</span><b class="amber">${v.warnings} to review</b></div></div></section>
    <section class="panel"><div class="panel-head"><h2>Needs your attention</h2><span class="badge warning">${v.warnings+v.errors}</span></div><div class="attention-list">${v.findings.slice(0,4).map(f=>`<button class="attention-item" data-action="${f.id?'artifact':'nav'}" data-id="${esc(f.id)}" data-page="verification"><span class="attention-icon">${icon(f.rule==='assumption'?'question':'warning',14)}</span><span><h3>${esc(f.message)}</h3><p>${esc(f.id||f.path||'Repository')}</p></span></button>`).join('')||'<p class="small muted">No current findings.</p>'}</div><div class="card-note">Deterministic checks · engineering judgement remains yours</div></section>
    </div></div>`;
}
function graphLegend(){return `<div class="graph-footer">${['intent','requirement','component','verification','evidence'].map(t=>`<span class="legend" style="--type-color:${tc(t)[1]}"><i></i>${t[0].toUpperCase()+t.slice(1)}</span>`).join('')}<span class="graph-direction-key"><span class="legend"><i class="incoming-line"></i>Incoming</span><span class="legend"><i class="outgoing-line"></i>Outgoing</span></span></div>`;}
function overviewRootType(){
  const type=state.overviewTypes[state.data.root]||'';
  return state.data.artifacts.some(a=>a.type===type)?type:'';
}
function overviewRootChoices(){
  const type=overviewRootType();
  return state.data.artifacts.filter(a=>!type||a.type===type).sort((a,b)=>a.id.localeCompare(b.id));
}
function overviewRoot(){
  const artifacts=overviewRootChoices(),preferred=state.overviewRoots[state.data.root];
  return artifacts.find(a=>a.id===preferred)||artifacts.find(a=>a.type==='intent')||artifacts[0]||null;
}
function graphNeighborhood(root,depth=3){
  const lookup=new Map(state.data.artifacts.map(a=>[a.id,a])),adjacent=new Map([...lookup.keys()].map(id=>[id,new Set()]));
  for(const e of state.data.edges){
    if(lookup.has(e.source)&&lookup.has(e.target)&&e.source!==e.target){adjacent.get(e.source).add(e.target);adjacent.get(e.target).add(e.source);}
  }
  const distances=new Map();
  if(lookup.has(root)){
    distances.set(root,0);let frontier=[root];
    for(let step=1;step<=depth&&frontier.length;step++){
      const next=[];
      for(const id of frontier)for(const target of adjacent.get(id))if(!distances.has(target)){distances.set(target,step);next.push(target);}
      frontier=next;
    }
  }
  return {lookup,adjacent,distances};
}
function overviewGraphLayout(){
  const root=overviewRoot(),{lookup,adjacent,distances}=graphNeighborhood(root?.id),cols=[root?[root]:[]];
  // Keep every displayed artifact connected to a displayed predecessor.
  for(let step=1;step<=3;step++){
    const previous=new Set(cols[step-1].map(a=>a.id));
    const ids=[...distances.keys()].filter(id=>distances.get(id)===step&&[...adjacent.get(id)].some(other=>previous.has(other)));
    ids.sort((a,b)=>adjacent.get(b).size-adjacent.get(a).size||a.localeCompare(b));
    cols.push(ids.slice(0,3).map(id=>lookup.get(id)));
  }
  return {root,cols,total:distances.size,shown:cols.flat().length,labels:['ROOT','1 LINK AWAY','2 LINKS AWAY','3 LINKS AWAY']};
}
function overviewGraphPanel(){
  const layout=overviewGraphLayout(),choices=overviewRootChoices(),types=[...new Set(state.data.artifacts.map(a=>a.type))].sort();
  const note=layout.total===1?'No linked artifacts in this version.':layout.total?`Showing ${layout.shown} of ${layout.total} artifacts within 3 links.`:'Create an artifact to choose a root.';
  return `<section class="panel graph-panel overview-graph-panel"><div class="panel-head"><div><h2>Knowledge graph</h2><p>Follow incoming and outgoing artifact links</p></div><button class="text-link" data-action="explore-overview" ${layout.root?'':'disabled'}>Explore graph ${icon('right',12)}</button></div><div class="overview-graph-toolbar"><label for="overview-root-type">Type</label><select id="overview-root-type" aria-label="Overview root type" ${types.length?'':'disabled'}>${options(types,overviewRootType(),'All types')}</select><label for="overview-root">Root</label><select id="overview-root" aria-label="Overview graph root" ${layout.root?'':'disabled'}>${choices.length?choices.map(a=>`<option value="${esc(a.id)}" ${a.id===layout.root.id?'selected':''}>${esc(a.id+' · '+a.title)}</option>`).join(''):'<option>No artifacts</option>'}</select></div>${graphView(true,layout)}<div class="graph-footer overview-graph-footer"><span class="overview-graph-count">${note}</span><span class="graph-direction-key"><span class="legend"><i class="incoming-line"></i>Incoming</span><span class="legend"><i class="outgoing-line"></i>Outgoing</span></span></div></section>`;
}
const graphKey = compact => compact ? 'overview:'+(overviewRoot()?.id||'') : 'traceability:' + state.focus;
const graphZoomSteps = [0.5, 0.75, 1, 1.25, 1.5, 2, 3, 4];
function graphView(compact=false,layout=null){
  const content=graphSvg(compact,layout),camera=content.startsWith('<svg')?state.graphViews.get(graphKey(compact)):null;
  const zoom=camera?.zoom||1,disabled=camera?'':'disabled';
  return `<div class="graph-viewport"><div class="graph-area">${content}</div><div class="graph-controls" role="group" aria-label="Graph zoom controls"><button class="icon-btn" data-graph-zoom="out" aria-label="Zoom out" title="Zoom out" ${disabled||zoom<=0.5?'disabled':''}>−</button><output class="graph-zoom-level" aria-label="Graph zoom" aria-live="polite">${Math.round(zoom*100)}%</output><button class="icon-btn" data-graph-zoom="in" aria-label="Zoom in" title="Zoom in" ${disabled||zoom>=4?'disabled':''}>${icon('plus',14)}</button><button class="btn small" data-graph-zoom="reset" title="Reset zoom and center the graph" ${disabled}>Fit</button></div><span class="graph-navigation-hint">Drag background to pan · Ctrl/⌘ + scroll to zoom</span></div>`;
}
function graphViewBox(camera,width,height){return `${camera.x-width/(2*camera.zoom)} ${camera.y-height/(2*camera.zoom)} ${width/camera.zoom} ${height/camera.zoom}`;}
function graphSvg(compact=false,layout=null){
  let artifacts=state.data.artifacts;
  if(!compact&&state.focus){const {distances}=graphNeighborhood(state.focus);artifacts=artifacts.filter(a=>distances.has(a.id));}
  const groups=[['intent'],['requirement','constraint'],['architecture','component','interface','decision','assumption','risk','hazard'],['verification','tool'],['evidence']];
  let cols=groups.map(types=>artifacts.filter(a=>types.includes(a.type))),labels=['INTENT','REQUIREMENTS','DESIGN','VERIFICATION','EVIDENCE'],root=state.focus;
  for(const a of artifacts)if(!groups.flat().includes(a.type))cols[2].push(a);
  if(compact){
    layout=layout||overviewGraphLayout();cols=layout.cols;labels=layout.labels;root=layout.root?.id;artifacts=cols.flat();
  }
  if(!artifacts.length)return empty('Your graph starts here','Create an artifact and connect it to the knowledge it depends on.');
  const width=compact?790:1060,height=compact?Math.max(230,Math.max(...cols.map(c=>c.length))*64+55):Math.max(440,Math.max(...cols.map(c=>c.length))*82+55),nodeWidth=compact?160:172,nodeHeight=compact?48:55;
  const gap=(width-nodeWidth*cols.length-40)/(cols.length-1), positions=new Map();
  cols.forEach((col,x)=>col.forEach((a,y)=>positions.set(a.id,{x:20+x*(nodeWidth+gap),y:34+(height-48-col.length*(nodeHeight+16))/2+y*(nodeHeight+16),a})));
  const key=graphKey(compact),arrow=compact?'arrow-overview':'arrow-traceability';
  let camera=state.graphViews.get(key);
  if(!camera||camera.width!==width||camera.height!==height){camera={zoom:1,x:width/2,y:height/2,width,height};state.graphViews.set(key,camera);}
  let svg=`<svg class="engineering-graph" data-graph-key="${esc(key)}" data-arrow="${arrow}" viewBox="${graphViewBox(camera,width,height)}" role="group" tabindex="0" aria-label="Engineering knowledge graph. Hover or focus an artifact to highlight its links. Use plus, minus or zero to zoom."><defs>${[['','#a2b6a9'],['-incoming','#477db7'],['-outgoing','#238366']].map(([suffix,color])=>`<marker id="${arrow+suffix}" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M0 0 8 4 0 8" fill="${color}"/></marker>`).join('')}</defs>`;
  cols.forEach((c,i)=>svg+=`<text class="flow-label" x="${20+i*(nodeWidth+gap)}" y="19">${labels[i]}</text>`);
  svg+='<g class="graph-edges">';
  for(const e of state.data.edges){const a=positions.get(e.source),b=positions.get(e.target);if(!a||!b||a===b)continue;
    const forward=a.x<b.x;const x1=a.x+(forward?nodeWidth:0),x2=b.x+(forward?0:nodeWidth),y1=a.y+nodeHeight/2,y2=b.y+nodeHeight/2;
    svg+=`<path class="graph-edge" data-source="${esc(e.source)}" data-target="${esc(e.target)}" d="M${x1} ${y1} C${(x1+x2)/2} ${y1},${(x1+x2)/2} ${y2},${x2} ${y2}" fill="none" stroke="#b9cbbf" stroke-width="1" opacity=".65" marker-end="url(#${arrow})" vector-effect="non-scaling-stroke"><title>${esc(e.source+' → '+e.type+' → '+e.target)}</title></path>`;
  }
  svg+='</g><g class="graph-nodes">';
  for(const {x,y,a} of positions.values()){const c=tc(a.type),max=compact?22:23;svg+=`<g class="graph-node ${a.id===root?'is-root':''}" data-artifact="${esc(a.id)}" tabindex="0" role="button" aria-haspopup="menu" aria-keyshortcuts="Shift+F10" aria-label="${esc(a.title)}${a.id===root?' (selected root)':''}"><rect x="${x}" y="${y}" width="${nodeWidth}" height="${nodeHeight}" rx="6" fill="white" stroke="#dce6df"/><rect x="${x+9}" y="${y+10}" width="4" height="${nodeHeight-20}" rx="2" fill="${c[1]}"/><text class="graph-sub" x="${x+20}" y="${y+17}">${esc(a.id)}</text><text class="graph-label" x="${x+20}" y="${y+33}">${esc(a.title.length>max?a.title.slice(0,max-1)+'…':a.title)}</text><title>${esc(a.id+' · '+a.title+' · '+a.type)}</title></g>`;}
  return svg+'</g></svg>';
}
function filtered(){return state.data.artifacts.filter(a=>(!state.query||(a.title+' '+a.id+' '+a.body).toLowerCase().includes(state.query.toLowerCase()))&&(!state.type||a.type===state.type)&&(!state.discipline||a.meta.discipline===state.discipline)&&(!state.status||a.meta.status===state.status));}
function options(values,selected,all){return `<option value="">${all}</option>`+values.map(v=>`<option value="${esc(v)}" ${v===selected?'selected':''}>${esc(v)}</option>`).join('');}
let relationLookup=null;
function relationIndex(){
  if(relationLookup?.snapshot!==state.data){
    const artifacts=new Map(state.data.artifacts.map(a=>[a.id,a])),incoming=new Map();
    for(const edge of state.data.edges)if(edge.target){if(!incoming.has(edge.target))incoming.set(edge.target,[]);incoming.get(edge.target).push(edge);}
    relationLookup={snapshot:state.data,artifacts,incoming};
  }
  return relationLookup;
}
function compactRelations(artifact,detail=false){
  const {artifacts,incoming}=relationIndex(),limit=detail?3:2;
  const row=(direction,links)=>{
    const label=direction==='incoming'?'Incoming':'Outgoing',short=direction==='incoming'?'In':'Out';
    const chip=r=>{
      const id=direction==='incoming'?r.source:r.target,resource=r.resource,target=artifacts.get(id);
      const text=id||resource.split('/').at(-1),description=resource?'Resource: '+resource:target?target.title:'Artifact unavailable in this version';
      const title=`${label} · ${r.type} · ${id||resource} · ${description}`;
      const attrs=resource?`data-action="resource" data-path="${esc(resource)}"`:target?`data-artifact="${esc(id)}"`:'aria-disabled="true"';
      const tag=target||resource?'button':'span';
      return `<${tag} class="relation-chip ${resource?'is-resource':''}" ${attrs} title="${esc(title)}" aria-label="${esc(title)}">${resource?icon('file',10):''}${detail?`<small>${esc(r.type)}</small>`:''}<span>${esc(text)}</span></${tag}>`;
    };
    return `<div class="relation-group ${direction}" data-direction="${direction}" role="group" aria-label="${label} links"><span class="relation-direction" title="${label} links">${direction==='incoming'?'←':'→'} ${detail?label:short}<b>${links.length}</b></span><div class="relation-chips">${links.length?links.slice(0,limit).map(chip).join(''):'<span class="relation-none">—</span>'}${links.length>limit?`<details class="relation-more"><summary aria-label="More ${direction} links (${links.length-limit})"><span class="more-count">+${links.length-limit}</span><span class="less-label">Less</span></summary><div class="relation-chips">${links.slice(limit).map(chip).join('')}</div></details>`:''}${detail?btn('+','links-open','','relation-add',`data-id="${esc(artifact.id)}" data-direction="${direction}" aria-label="Add ${direction} links"`):''}</div></div>`;
  };
  return `<div class="relations-compact ${detail?'detail-relations':''}" data-relations>${row('incoming',incoming.get(artifact.id)||[])}${row('outgoing',artifact.meta.relations||[])}${detail?btn('Manage links','links-open','link','relation-manage',`data-id="${esc(artifact.id)}" data-manage="true"`):''}</div>`;
}
function artifactTable(items,compact=false){return items.length?`<div class="table-wrap"><table><thead><tr><th>ARTIFACT</th>${!compact?'<th>TYPE</th>':''}<th>DISCIPLINE</th><th>STATUS</th>${!compact?'<th>RELATIONS</th>':''}</tr></thead><tbody>${items.map(a=>`<tr data-artifact="${esc(a.id)}" tabindex="0"><td><div class="artifact-title">${typeIcon(a.type)}<div>${esc(a.title)}<span class="artifact-id">${esc(a.id)}</span></div></div></td>${!compact?`<td>${esc(a.type)}</td>`:''}<td><span class="discipline">${esc(a.meta.discipline||'Unspecified')}</span></td><td>${badge(a.meta.status||'unspecified')}</td>${!compact?`<td class="relations-cell">${compactRelations(a)}</td>`:''}</tr>`).join('')}</tbody></table></div>`:empty('No artifacts found','Try another filter or create the first artifact.',btn('New artifact','new','plus','primary'));}
function knowledge(){const items=filtered();return heading('Knowledge library','Engineering knowledge, across every discipline.',btn('Import Markdown','import','download')+btn('New artifact','new','plus','primary'))+
  `<div class="tabs"><button class="tab active">All knowledge <span class="count">${state.data.artifacts.length}</span></button><span class="tab muted">Files are the database</span></div><div class="toolbar"><input class="input" id="library-search" data-filter="query" value="${esc(state.query)}" placeholder="Search artifacts…" aria-label="Filter artifacts"><select data-filter="type" aria-label="Artifact type">${options(state.data.types,state.type,'All types')}</select><select data-filter="discipline" aria-label="Discipline">${options([...new Set(state.data.artifacts.map(a=>a.meta.discipline).filter(Boolean))],state.discipline,'All disciplines')}</select><select data-filter="status" aria-label="Status">${options([...new Set(['draft','stable','deprecated',...state.data.artifacts.map(a=>a.meta.status).filter(Boolean)])],state.status,'All statuses')}</select><span class="spacer"></span><div class="segmented"><button data-action="layout" data-value="table" class="${state.layout==='table'?'active':''}" aria-label="Table view">${icon('list',14)}</button><button data-action="layout" data-value="cards" class="${state.layout==='cards'?'active':''}" aria-label="Card view">${icon('grid',14)}</button></div></div>
  ${state.layout==='table'?`<section class="panel">${artifactTable(items)}</section>`:`<div class="artifact-cards">${items.map(a=>`<article class="artifact-card"><button class="artifact-card-main" data-artifact="${esc(a.id)}"><div class="artifact-card-top">${typeIcon(a.type)}${badge(a.meta.status||'unspecified')}</div><h3>${esc(a.title)}</h3><span class="artifact-id">${esc(a.id)}</span><p>${esc(a.body.replace(/[#*`]/g,'').replace(/\n/g,' ').slice(0,160))}</p><div class="artifact-card-foot"><span class="discipline">${esc(a.meta.discipline||'Unspecified')}</span></div></button>${compactRelations(a)}</article>`).join('')}</div>`}<p class="field-help">Showing ${items.length} of ${state.data.artifacts.length} artifacts · ${readonly()?'Saved baseline · read only':'Changes are saved to Markdown and committed to Git.'}</p>`;}
function traceability(){return heading('Traceability','Follow the relationships. Understand the engineering consequences.',btn('Export matrix','export','download','','data-kind="traceability"'))+
  `<div class="toolbar"><div class="segmented"><button data-action="graph-mode" data-value="graph" class="${state.graphMode==='graph'?'active':''}">${icon('graph',13)}Graph</button><button data-action="graph-mode" data-value="matrix" class="${state.graphMode==='matrix'?'active':''}">${icon('grid',13)}Matrix</button></div><span class="spacer"></span><select id="graph-focus" aria-label="Focus graph on artifact">${options(state.data.artifacts.map(a=>a.id),state.focus,'Entire workspace')}</select></div>
  ${state.graphMode==='graph'?`<section class="panel full-graph" style="display:flex;flex-direction:column">${graphView()}${graphLegend()}</section>`:coverageTable()}`;}
function coverageTable(){return state.data.validation.coverage.length?`<section class="panel"><div class="table-wrap"><table><thead><tr><th>REQUIREMENT</th><th>VERIFIED BY</th><th>EVIDENCE</th><th>APPLICABILITY</th></tr></thead><tbody>${state.data.validation.coverage.map(r=>`<tr><td><button style="text-align:left" data-artifact="${esc(r.id)}"><span style="color:#425e4b">${esc(r.title)}</span><span class="artifact-id">${esc(r.id)}</span></button></td><td class="matrix-cell">${r.verification.map(id=>`<button data-artifact="${esc(id)}">${esc(id)}</button>`).join('')||'<span class="muted">Not linked</span>'}</td><td class="matrix-cell">${r.evidence.map(id=>`<button data-artifact="${esc(id)}">${esc(id)}</button>`).join('')||'<span class="muted">Not recorded</span>'}</td><td>${badge(r.state)}</td></tr>`).join('')}</tbody></table></div><div class="card-note">“Current” means the evidence references the selected revision. It does not imply a passing result. Earlier evidence requires an applicability review.</div></section>`:empty('No requirements yet','Add requirements and link them to verification definitions to build this generated matrix.');}
function verification(){const v=state.data.validation;return heading('Verification & evidence','Know what is planned, what was executed, and what remains uncertain.',btn('Run validation','validate','checkCircle','primary'))+
  `<div class="tabs"><button class="tab ${state.verificationTab==='coverage'?'active':''}" data-action="verification-tab" data-value="coverage">Coverage <span class="count">${v.coverage.length}</span></button><button class="tab ${state.verificationTab==='findings'?'active':''}" data-action="verification-tab" data-value="findings">Engineering checks <span class="count">${v.findings.length}</span></button><button class="tab ${state.verificationTab==='evidence'?'active':''}" data-action="verification-tab" data-value="evidence">Evidence</button></div>
  ${state.verificationTab==='coverage'?coverageTable():state.verificationTab==='evidence'?`<section class="panel">${artifactTable(state.data.artifacts.filter(a=>a.type==='evidence'))}</section>`:`<div class="notice ${v.graph?'info':''}" style="margin-bottom:20px">${v.graph?'EKF v0.1 syntax and graph checks pass.':'Conformance errors need attention.'} ${v.warnings} advisory findings. Advisory checks do not establish engineering correctness.</div><section class="panel"><div class="findings">${v.findings.map(f=>`<button class="finding" ${f.id?`data-artifact="${esc(f.id)}"`:''}><span class="finding-icon ${f.severity}">${icon(f.severity==='error'?'warning':'question',17)}</span><span><h3>${esc(f.message)}</h3><p>${esc(f.id||f.path||'Repository')} · ${esc(f.rule)}</p></span>${badge(f.severity)}</button>`).join('')||empty('All checks are clear','No deterministic errors or advisory findings were found.')}</div></section>`}`;}
function reports(){const reports=[['requirements','Requirements specification','Intent, requirements, constraints, and their relationships.'],['architecture','Architecture & interfaces','System structure, components, interface contracts and decisions.'],['traceability','Traceability matrix','Requirements linked to verification definitions and evidence.'],['verification','Verification report','Coverage, recorded evidence and baseline applicability.'],['safety','Safety traceability','Hazards, risks, assumptions and connected mitigations.'],['review','Design review package','The full engineering graph, content, coverage and findings.']];return heading('Generated views','One engineering source. Different perspectives, always derived.')+`<div class="report-list">${reports.map(([kind,title,description])=>`<button class="report-card" data-action="export" data-kind="${kind}">${icon('file',23)}<span><h3>${title}</h3><p>${description}</p><span class="text-link" style="margin-top:14px">Download Markdown ${icon('download',12)}</span></span></button>`).join('')}</div><div class="notice info" style="margin-top:23px">Every report identifies its source Git revision. Edit the source artifacts to update a report; generated views are not independently maintained documents.</div>`;}
function agent(){const sandbox=state.tools.sandbox;return heading('Agent workbench','Inspect, calculate, create tools, and propose engineering changes.',btn('Connect an agent','connect','link'))+
  `<div class="tabs"><button class="tab ${state.agentTab==='execute'?'active':''}" data-action="agent-tab" data-value="execute">Tool execution</button><button class="tab ${state.agentTab==='capabilities'?'active':''}" data-action="agent-tab" data-value="capabilities">Agent capabilities <span class="count">${state.tools.tools.length}</span></button></div>
  ${state.agentTab==='execute'?`<div class="two-col"><div class="stack"><section class="panel"><div class="panel-head"><div><h2>Engineering tool console</h2><p>Run Python, shell scripts, and installed engineering tools</p></div>${badge(sandbox.available?'ready':'unavailable')}</div><div class="pad" style="padding-top:0"><label class="small muted" for="tool-command">Command or shell script</label><textarea class="code-editor" id="tool-command" spellcheck="false" style="margin-top:10px" placeholder="python3 tools/my_analysis.py">${esc(sessionStorage.getItem('command')||'python3 tools/analyze_shutdown.py test-results/shutdown-042.csv')}</textarea><div style="display:flex;justify-content:space-between;align-items:center;margin-top:13px;gap:10px"><span class="small muted">15 s time limit · 512 MB per process</span>${btn('Run in sandbox','run','play','primary',sandbox.available?'':'disabled')}</div>${!sandbox.available?`<div class="notice" style="margin-top:15px">${esc(sandbox.reason)}<br>No command will run without isolation.</div>`:''}</div></section><section class="panel"><div class="panel-head"><h2>Execution history</h2><span class="subtle">${state.runs.length} runs</span></div>${state.runs.length?state.runs.slice(0,15).map(r=>`<button class="run-item" data-action="run-detail" data-id="${r.id}">${icon('terminal',17)}<span style="min-width:0"><h3 class="mono" style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:370px">${esc(r.command.split('\n')[0])}</h3><p>${date(r.created)} · ${r.revision.slice(0,7)}</p></span>${badge(r.status)}</button>`).join(''):empty('No executions yet','Run a tool to capture reproducible analysis against the current repository.')}</section></div>
    <div class="stack"><section class="panel"><div class="panel-head"><h2>Execution boundaries</h2>${icon('shield',17)}</div><div class="pad" style="padding-top:0">${[['file','Repository snapshot','Read only'],['code','/output directory','Writable'],['globe','Network access','Disabled'],['lock','Home & credentials','Not mounted'],['branch','Engineering changes','Reviewed branch']].map(([i,l,r])=>`<div class="policy-row">${icon(i,15)}${l}<small>${r}</small></div>`).join('')}</div></section><section class="panel"><div class="panel-head"><h2>From calculation to knowledge</h2></div><div class="pad" style="padding-top:0"><p class="small muted">Write temporary scripts in <code>/tmp</code> or <code>/output</code>. Run them against <code>/workspace</code>. Preserve reusable tools through a change proposal.</p><p class="small muted" style="margin-top:14px">Completed runs can become evidence proposals linked to a verification. An engineer reviews the result against its pass criteria.</p></div></section><div class="notice info">This console executes tools. Connect your own MCP-compatible agent to reason over the graph and propose changes; no model or API key is bundled.</div></div></div>`:
    `<section class="panel"><div class="panel-head"><h2>Available MCP tools</h2>${btn('Connection instructions','connect','link','small')}</div>${state.tools.tools.map(t=>`<div class="finding"><span class="finding-icon">${icon('code',16)}</span><span><h3 class="tool-name">${esc(t.name)}</h3><p>${esc(t.description)}</p></span></div>`).join('')}</section>`}`;}
function changes(){return heading('Engineering changes','Review the proposed future state, with its relationships and verification impact.',btn('New proposal','proposal-new','plus','primary'))+
  `<section class="panel"><div class="panel-head"><h2>Change proposals</h2><span class="subtle">${state.proposals.filter(p=>p.status==='pending').length} awaiting review</span></div>${state.proposals.length?state.proposals.map(p=>`<button class="proposal-item" data-action="proposal" data-id="${p.id}">${icon('branch',18)}<span><h3>${esc(p.title)}</h3><p>${esc(p.actor)} · ${p.files.length} files · ${date(p.created)}</p></span>${badge(p.status)}${icon('chevron',13)}</button>`).join(''):empty('A space for thoughtful change','Agents and engineers propose changes on Git branches. Review the diff and impact before bringing them into your workspace.',btn('Create a proposal','proposal-new','plus','primary'))}</section>`;}
function activity(){return heading('History & baselines','Browse saved engineering states and understand what changed.',btn('Create baseline','baseline','tag','primary'))+
  `<div class="tabs"><button class="tab ${state.historyTab==='timeline'?'active':''}" data-action="history-tab" data-value="timeline">History & baselines</button><button class="tab ${state.historyTab==='compare'?'active':''}" data-action="history-tab" data-value="compare">Compare versions</button></div>`+
  (state.historyTab==='compare'?comparisonView():`<div class="two-col"><section class="panel"><div class="panel-head"><h2>Working branch history</h2><span class="subtle">Latest ${state.history.length} commits</span></div><div class="timeline">${state.history.map(h=>`<div class="timeline-item"><span class="timeline-icon">${icon('branch',13)}</span><div><h3>${esc(h.message)}</h3><p>${date(h.at)} · <code>${h.commit.slice(0,7)}</code></p></div></div>`).join('')}</div></section><div class="stack"><section class="panel"><div class="panel-head"><h2>Engineering baselines</h2>${icon('tag',16)}</div><div class="pad" style="padding-top:0">${state.baselines.map(b=>`<div class="baseline-tag baseline-entry"><div><strong>${esc(b.name)}</strong><code>${b.commit.slice(0,7)}</code></div><div class="baseline-actions">${btn('Browse','browse-baseline','file','small',`data-ref="${esc(b.commit)}" data-name="${esc(b.name)}"`)}${btn('Compare','compare-baseline','branch','small',`data-name="${esc(b.name)}"`)}</div></div>`).join('')||'<p class="small muted">No tagged baselines yet. Create one from the current workspace to start browsing and comparing versions.</p>'}</div></section><div class="notice info">Browse a baseline to explore its library, graph, verification and reports in read-only mode. Your working branch stays in place.</div></div></div>`);}

function comparisonView(){
  const versionOptions=selected=>`<option value="" ${!selected?'selected':''}>Current workspace (including uncommitted files)</option>`+state.baselines.map(b=>`<option value="${esc(b.name)}" ${selected===b.name?'selected':''}>${esc(b.name)} · ${b.commit.slice(0,7)}</option>`).join('');
  const controls=`<div class="comparison-controls"><label>From<select id="compare-before" aria-label="Compare from">${versionOptions(state.compareBefore)}</select></label>${btn('Swap','compare-swap','refresh','small')}<label>To<select id="compare-after" aria-label="Compare to">${versionOptions(state.compareAfter)}</select></label>${btn(state.comparisonLoading?'Comparing…':'Compare versions','compare-load','branch','primary',state.comparisonLoading?'disabled':'')}</div>`;
  if(state.comparisonLoading)return controls+'<div class="empty" role="status"><span class="spinner"></span><p>Reading the selected engineering versions…</p></div>';
  const c=state.comparison;if(!c)return controls+empty('Choose versions to compare','Compare two saved baselines, or a baseline and the current workspace.');
  const counts=['added','modified','removed'].map(status=>[status,c.artifacts.filter(a=>a.status===status).length]);
  const version=(side,label)=>`<span><strong>${esc(label||'Current workspace')}</strong> · <code>${side.commit.slice(0,7)}</code>${side.dirty?' · includes uncommitted files':''}</span>`;
  const edgeList=(edges,status)=>edges.map(e=>`<div class="comparison-edge">${badge(status)}<code>${esc(e.source)}</code><span>${esc(e.type)}</span>${icon('right',12)}<code>${esc(e.target||e.resource)}</code>${e.resource?'<small>resource</small>':''}</div>`).join('');
  const coverage=side=>side?`<strong>${esc(side.title)}</strong><div>${badge(side.state)}</div><p>Verification: ${esc(side.verification.join(', ')||'None')}</p><p>Evidence: ${esc(side.evidence.join(', ')||'None')}</p>${side.results.map(r=>`<p>${esc(r.id)}: ${esc(r.result)} · baseline <code>${esc(r.baseline||'unspecified')}</code></p>`).join('')}`:'<span class="muted">Not an active requirement in this version</span>';
  return controls+`<div class="comparison-context">${version(c.before,c.beforeLabel)}${icon('right',15)}${version(c.after,c.afterLabel)}</div><div class="comparison-stats">${counts.map(([status,count])=>`<div class="panel"><strong>${count}</strong>${badge(status)}<span>artifacts</span></div>`).join('')}</div>
    ${c.before.dirty||c.after.dirty?'<div class="notice" style="margin-bottom:18px">This comparison includes uncommitted working files. Run Compare versions again after further edits to update the result.</div>':''}
    <section class="panel"><div class="panel-head"><h2>Artifact changes</h2><span class="subtle">Matched by stable ID</span></div>${c.artifacts.length?`<div class="table-wrap"><table><thead><tr><th>ARTIFACT</th><th>CHANGE</th><th>DETAILS</th><th></th></tr></thead><tbody>${c.artifacts.map(a=>`<tr><td><strong>${esc((a.after||a.before).title)}</strong><span class="artifact-id">${esc(a.id)}</span></td><td>${badge(a.status)}</td><td>${esc([a.content_changed?'Engineering meaning':'',...a.fields,a.moved?'File moved':''].filter(Boolean).join(', ')||(a.status==='modified'?'Formatting':'Entire artifact'))} ${a.moved?`<p class="small">${esc(a.before.path)} → ${esc(a.after.path)}</p>`:''}</td><td>${btn('View changes','compare-artifact','file','small',`data-id="${esc(a.id)}"`)}</td></tr>`).join('')}</tbody></table></div>`:empty('No artifact changes','The artifact source and paths are the same in these versions.')}</section>
    <section class="panel comparison-section"><div class="panel-head"><h2>Relationship changes</h2><span class="subtle">${c.relations_added.length} added · ${c.relations_removed.length} removed</span></div><div class="pad" style="padding-top:0">${edgeList(c.relations_removed,'removed')+edgeList(c.relations_added,'added')||'<p class="small muted">No relationship changes.</p>'}</div></section>
    <section class="panel comparison-section"><div class="panel-head"><h2>Verification coverage changes</h2><span class="subtle">${c.coverage.length} requirements</span></div>${c.coverage.length?`<div class="table-wrap"><table class="comparison-coverage"><thead><tr><th>REQUIREMENT</th><th>FROM</th><th>TO</th></tr></thead><tbody>${c.coverage.map(r=>`<tr><td><code>${esc(r.id)}</code></td><td>${coverage(r.before)}</td><td>${coverage(r.after)}</td></tr>`).join('')}</tbody></table></div>`:'<p class="pad small muted">No coverage changes.</p>'}<div class="card-note">Applicability is calculated against each selected revision. Coverage and evidence results still require engineering review.</div></section>
    <section class="panel comparison-section"><div class="panel-head"><h2>Engineering findings</h2><span class="subtle">${c.findings_added.length} introduced · ${c.findings_removed.length} no longer reported</span></div><div class="pad" style="padding-top:0">${[['removed',c.findings_removed],['added',c.findings_added]].map(([status,items])=>items.map(f=>`<div class="comparison-finding">${badge(status)}<span>${esc(f.id||f.path||'Repository')}: ${esc(f.message)}</span></div>`).join('')).join('')||'<p class="small muted">No changes to deterministic findings.</p>'}</div></section>
    <section class="panel comparison-section"><div class="panel-head"><h2>Other file changes</h2><span class="subtle">${c.resources.length} files</span></div>${c.resources.length?`<div class="table-wrap"><table><thead><tr><th>FILE</th><th>CHANGE</th><th></th></tr></thead><tbody>${c.resources.map(r=>`<tr><td><code>${esc(r.path)}</code></td><td>${badge(r.status)}</td><td>${btn('View changes','compare-resource','file','small',`data-path="${esc(r.path)}"`)}</td></tr>`).join('')}</tbody></table></div>`:'<p class="pad small muted">No changes to the manifest, standalone documents, scripts or other resources.</p>'}</section>
    ${c.manifest_changed?'<div class="notice info comparison-section">The repository manifest changed. Inspect ekf.yaml in Other file changes for details.</div>':''}`;
}

async function loadComparison(){
  const request=++comparisonRequest, before=state.compareBefore, after=state.compareAfter;
  state.comparisonLoading=true;state.comparison=null;renderShell();
  try{
    const c=await api('compare?'+new URLSearchParams({before,after}));
    if(request!==comparisonRequest)return;
    state.comparison={...c,beforeLabel:before,afterLabel:after,beforeRef:before?c.before.commit:'',afterRef:after?c.after.commit:''};
  }finally{if(request===comparisonRequest){state.comparisonLoading=false;renderShell();}}
}

async function comparisonArtifact(id){
  const c=state.comparison,change=c.artifacts.find(a=>a.id===id);
  const detail=await api('compare/artifact?'+new URLSearchParams({before:c.beforeRef,after:c.afterRef,id}));
  if(state.comparison!==c)return;
  if(['hash','path'].some(key=>(detail.artifact_before?.[key]||null)!==(change.before?.[key]||null)||(detail.artifact_after?.[key]||null)!==(change.after?.[key]||null)))throw new Error('The workspace changed. Run Compare versions again before opening this difference.');
  const side=(a,label)=>`<section><h3>${esc(label||'Current workspace')}</h3>${a?`<p class="small muted">${esc(a.path)}</p><pre class="diff comparison-source">${esc(a.raw)}</pre>`:'<p class="small muted">Artifact does not exist in this version.</p>'}</section>`;
  modal('Changes · '+id,`<div class="detail-meta">${badge(change.status)}<strong>${esc((detail.artifact_after||detail.artifact_before).title)}</strong></div><h3>Markdown differences</h3><pre class="diff">${detail.diff?detail.diff.split('\n').map(line=>`<span class="${line.startsWith('+')?'added':line.startsWith('-')?'removed':''}">${esc(line)}</span>`).join('\n'):esc(change.moved?'Content is unchanged; the artifact moved to a different file.':'No Markdown changes.')}</pre>${detail.truncated?'<div class="notice">Difference preview limited to 4,000 lines. Full source is available below.</div>':''}<details><summary class="comparison-source-toggle">View both source versions</summary><div class="comparison-sources">${side(detail.artifact_before,c.beforeLabel)}${side(detail.artifact_after,c.afterLabel)}</div></details>`,btn('Close','close'),true);
}

async function comparisonResource(path){
  const c=state.comparison,change=c.resources.find(r=>r.path===path);
  const detail=await api('compare/resource?'+new URLSearchParams({before:c.beforeRef,after:c.afterRef,path}));
  if(state.comparison!==c)return;
  if((detail.before?.oid||null)!==(change.before?.oid||null)||(detail.after?.oid||null)!==(change.after?.oid||null))throw new Error('The workspace changed. Run Compare versions again before opening this difference.');
  modal('File changes · '+path,`${badge(change.status)}${detail.notice?`<div class="notice" style="margin-top:15px">${esc(detail.notice)}</div>`:`<pre class="diff">${detail.diff?detail.diff.split('\n').map(line=>`<span class="${line.startsWith('+')?'added':line.startsWith('-')?'removed':''}">${esc(line)}</span>`).join('\n'):'No text differences. File bytes or line endings changed.'}</pre>`}${detail.truncated?'<div class="notice">Difference preview limited to 4,000 lines.</div>':''}`,btn('Close','close'),true);
}
function settings(){return heading('Workspace settings','Portable engineering knowledge. Your files, your tools, your repository.')+
  `<div class="settings-grid"><section class="panel"><div class="panel-head"><h2>Repository</h2>${icon('layers',16)}</div><div class="pad" style="padding-top:0"><h3>${esc(state.data.manifest.system?.title||'Engineering workspace')}</h3><p>${esc(state.data.root)}</p><h3>Current state</h3><p>Branch: <code>${esc(state.data.branch)}</code> · ${state.data.dirty?'External changes present':'Clean working tree'}</p><h3>Repository manifest</h3><pre>${esc(yamlDump(state.data.manifest))}</pre><div style="margin-top:17px">${btn('Edit manifest','manifest','edit','small')}</div></div></section>
    <section class="panel"><div class="panel-head"><h2>Agent connection</h2>${icon('spark',16)}</div><div class="pad" style="padding-top:0"><p>Use the stdio MCP adapter with your agent of choice. Credentials permit reading, sandbox execution and change proposals. Human approval is a separate capability.</p><pre>python3 -m ekf.mcp\n  --url http://127.0.0.1:${location.port}\n  --token-file ${esc(state.tools.token_file)}</pre><div style="margin-top:17px">${btn('Connection details','connect','link','small')}</div></div></section>
    <section class="panel"><div class="panel-head"><h2>Extensible by design</h2></div><div class="pad" style="padding-top:0"><p>EKF accepts additional artifact types, relationships and metadata. Use the artifact editor for custom fields or edit the Markdown source directly.</p><h3>Artifact vocabulary in this workspace</h3>${state.data.types.map(t=>`<span class="capability">${esc(t)}</span>`).join('')}<h3>Start another workspace</h3><pre>python3 -m ekf init my-project --title "My project"\npython3 -m ekf serve --repo my-project --port 8841</pre></div></section>
    <section class="panel"><div class="panel-head"><h2>Local execution</h2>${badge(state.tools.sandbox.available?'ready':'unavailable')}</div><div class="pad" style="padding-top:0"><p>${esc(state.tools.sandbox.reason)}</p><h3>Permission policy</h3><p>Read and isolated execution: automatic. Agent file changes: Git proposal. Merging: human review. Network access, hardware control and external system writes: unavailable in this version.</p><div style="margin-top:17px">${btn('Recheck sandbox','probe','refresh','small')}</div></div></section></div>`;}

function yamlDump(value,indent=0){
  const pad=' '.repeat(indent),scalar=v=>JSON.stringify(v);
  if(Array.isArray(value))return value.map(v=>v&&typeof v==='object'?pad+'-\n'+yamlDump(v,indent+2):pad+'- '+scalar(v)+'\n').join('');
  if(value&&typeof value==='object')return Object.entries(value).map(([k,v])=>`${pad}${/^[a-zA-Z_][\w-]*$/.test(k)?k:JSON.stringify(k)}: ${v&&typeof v==='object'?(Object.keys(v).length?'\n'+yamlDump(v,indent+2):(Array.isArray(v)?'[]\n':'{}\n')):scalar(v)+'\n'}`).join('');
  return pad+scalar(value)+'\n';
}
function markdown(text){
  // Render escaped Markdown only. HTML and executable URLs never reach the DOM.
  const blocks=[];let safe=esc(text).replace(/```[^\n]*\n([\s\S]*?)```/g,(_,code)=>{blocks.push(`<pre>${code}</pre>`);return `\u0000${blocks.length-1}\u0000`;});
  safe=safe.replace(/^### (.+)$/gm,'<h3>$1</h3>').replace(/^## (.+)$/gm,'<h2>$1</h2>').replace(/^# (.+)$/gm,'<h1>$1</h1>')
    .replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>').replace(/`([^`]+)`/g,'<code>$1</code>').replace(/^[-*] (.+)$/gm,'<li>$1</li>');
  return safe.split(/\n\n+/).map(b=>b.startsWith('<h')||b.startsWith('<li')||b.startsWith('\u0000')?b:`<p>${b.replaceAll('\n','<br>')}</p>`).join('\n').replace(/\u0000(\d+)\u0000/g,(_,n)=>blocks[n]);
}
let editorLinkUpdates=[],editorParent=null,editorAutoId=true;
const artifactIdPrefixes={intent:'INT',requirement:'REQ',constraint:'CON',interface:'IF',architecture:'ARCH',component:'CMP',decision:'DEC',assumption:'ASM',hazard:'HAZ',risk:'RISK',verification:'VER',evidence:'EVID',tool:'TOOL'};
function suggestArtifactId(type){
  const prefix=Object.hasOwn(artifactIdPrefixes,type)?artifactIdPrefixes[type]:type.toUpperCase().replace(/[^A-Z0-9]+/g,'-').replace(/^-|-$/g,'')||'ITEM';
  const ids=new Set(state.data.artifacts.map(a=>a.id.toUpperCase())),paths=new Set(state.data.artifacts.map(a=>a.path.toLowerCase()));
  let number=0n;
  for(const id of ids){
    if(!id.startsWith(prefix+'-'))continue;
    const tail=id.slice(prefix.length+1);
    if(/^\d+$/.test(tail)&&BigInt(tail)>number)number=BigInt(tail);
  }
  let id;
  do{id=prefix+'-'+String(++number).padStart(3,'0');}
  while(ids.has(id)||paths.has('engineering/'+type.replace(/[^a-zA-Z0-9_-]/g,'-').toLowerCase()+'/'+id.toLowerCase()+'.md'));
  return id;
}
function editorChoice(name,label,value,values,customLabel){
  const choices=[...new Set([...values,value].filter(v=>typeof v==='string'&&v))];
  let custom='__new__';while(choices.includes(custom))custom+='_';
  return `<div class="form-field"><label for="edit-${name}">${label}</label><select id="edit-${name}">${name==='discipline'?`<option value="" ${!value?'selected':''}>Unspecified</option>`:''}${choices.map(v=>`<option value="${esc(v)}" ${v===value?'selected':''}>${esc(v)}</option>`).join('')}<option value="${custom}" data-custom="true">Add custom ${name==='type'?'type':'discipline'}…</option></select><div id="edit-${name}-custom-field" class="editor-custom-choice" hidden><label for="edit-${name}-custom">${customLabel}</label><input class="input" id="edit-${name}-custom" placeholder="${name==='type'?'e.g. manufacturing-requirement':'e.g. Integration'}"></div></div>`;
}
function editorChoiceValue(name){
  const select=$('#edit-'+name);
  return select.selectedOptions[0]?.dataset.custom?$('#edit-'+name+'-custom').value.trim():select.value.trim();
}
function updateEditorIdHelp(){
  if(!$('#edit-id-help'))return;
  $('#edit-id-help').textContent=editorArtifact?'Saved IDs stay fixed, even when the artifact type changes.':editorAutoId?'Suggested from the artifact type. Changing type updates this ID.':'Custom ID kept when type changes. Choose Suggest ID to use the type again.';
  if(!editorArtifact&&$('#edit-id').readOnly)$('#edit-id-help').textContent+=' Direct ID editing is locked while incoming links are pending.';
}
function setSuggestedArtifactId(){
  if(editorArtifact||!$('#edit-id'))return;
  const type=editorChoiceValue('type');if(!type)return;
  const id=suggestArtifactId(type),old=$('#edit-id').value.trim();
  // Incoming links to a new draft must follow an automatic ID change before any files are saved.
  if(old&&old!==id){
    editorLinkUpdates=editorLinkUpdates.map(update=>({...update,relations:update.relations.map(r=>r.target===old?{...r,target:id}:r)}));
    try{
      const relations=JSON.parse($('#edit-relations').value||'[]');
      if(Array.isArray(relations)&&relations.some(r=>r?.target===old))$('#edit-relations').value=JSON.stringify(relations.map(r=>r?.target===old?{...r,target:id}:r),null,2);
    }catch{/* Keep unfinished advanced JSON intact; Save reports its syntax error. */}
  }
  $('#edit-id').value=id;editorAutoId=true;updateEditorIdHelp();updateChildLinkPreview();
}
const linkController=createLinkController({getSnapshot:()=>state.data,modal,esc,api,formError,
  onSaved:async id=>{await refresh();await openArtifact(id);toast('Links saved together and committed to Git');}});
function editorLinksSummary(){
  const count=JSON.parse($('#edit-relations').value||'[]').length;
  $('#editor-links-summary').textContent=`${count} outgoing links${editorLinkUpdates.length?' · incoming changes on '+editorLinkUpdates.length+' source items':''}. Changes are saved with this artifact.`;
}
function openEditorLinks(el){
  const id=$('#edit-id').value.trim();
  if(!id)throw new Error('Enter a stable ID before adding links.');
  if(!editorArtifact&&state.data.artifacts.some(a=>a.id===id))throw new Error('This ID is already used. Choose a unique stable ID first.');
  const relations=JSON.parse($('#edit-relations').value||'[]');
  if(!Array.isArray(relations)||relations.some(r=>!r||typeof r.type!=='string'||(!r.target&&!r.resource)))throw new Error('Correct the relationships in Advanced JSON before using the picker.');
  const artifact=editorArtifact||{id,title:$('#edit-title').value.trim(),meta:{},type:editorChoiceValue('type')};
  linkController.open({artifact,editor:true,relations,pending:editorLinkUpdates,direction:el.dataset.direction,manage:el.dataset.manage==='true',
    onApply:(relations,updates)=>{$('#edit-relations').value=JSON.stringify(relations,null,2);editorLinkUpdates=updates;$('#edit-id').readOnly=Boolean(editorArtifact)||updates.length>0;editorLinksSummary();updateEditorIdHelp();}});
}
let previousFocus=null;
function showOverlay(html){closeGraphMenu(true);if(!$('#overlay').innerHTML)previousFocus=document.activeElement;$('#overlay').innerHTML=html;document.body.style.overflow='hidden';requestAnimationFrame(()=>$$('#overlay button, #overlay input, #overlay textarea').find(el=>!el.disabled&&el.getClientRects().length)?.focus());}
function closeOverlay(force=false){if(linkController.close(force)&&!force)return;detailRequest++;if(currentRun){clearTimeout(pollTimer);currentRun=null;}$('#overlay').innerHTML='';document.body.style.overflow='';previousFocus?.focus();currentDetail=null;}
function modal(title,body,foot='',wide=false){showOverlay(`<div class="modal-backdrop"><section class="modal" role="dialog" aria-modal="true" aria-label="${esc(title)}" ${wide?'style="width:min(950px,100%)"':''}><header class="modal-head"><h2>${esc(title)}</h2><button class="icon-btn" data-action="close" aria-label="Close">${icon('close')}</button></header><div class="modal-body"><div class="form-error" id="form-error" role="alert"></div>${body}</div>${foot?`<footer class="modal-foot">${foot}</footer>`:''}</section></div>`);}
async function openArtifact(id,tab='content'){
  const request=++detailRequest,ref=state.revision?.commit||'';
  const a=await api(revisionPath('artifact?id='+encodeURIComponent(id),ref));
  if(request!==detailRequest||ref!==(state.revision?.commit||''))return;
  currentDetail=id;state.detailTab=tab;
  let content=tab==='source'?`<pre class="diff">${esc(a.raw)}</pre>`:`<div class="markdown">${markdown(a.body)}</div>`;
  if(tab==='context'){const impact=await api(revisionPath('impact?id='+encodeURIComponent(id),ref));content=`<div class="notice info">Potentially affected neighborhood · up to ${impact.depth} relationship steps in both directions. Review dependencies and assumptions before changing this concept.</div><div style="margin-top:20px">${artifactTable(impact.artifacts.filter(x=>x.id!==id),true)}</div>`;}
  if(request!==detailRequest||ref!==(state.revision?.commit||''))return;
  showOverlay(`<div class="overlay-backdrop"><section class="drawer" role="dialog" aria-modal="true" aria-label="${esc(a.title)}"><header class="drawer-head"><div><div class="eyebrow">${esc(a.type)} / ${esc(a.id)}</div><h2>${esc(a.title)}</h2></div><div class="drawer-head-actions"><button class="icon-btn" ${readonly()?'hidden':''} data-action="edit" data-id="${esc(a.id)}" aria-label="Edit artifact">${icon('edit',14)}</button><button class="icon-btn" data-action="close" aria-label="Close artifact">${icon('close',16)}</button></div></header><div class="drawer-body">${readonly()?`<div class="notice info" style="margin-bottom:18px">Baseline ${esc(state.revision.name)} · Read only</div>`:''}<div class="detail-meta">${badge(a.meta.status||'unspecified')}<span class="discipline">${esc(a.meta.discipline||'Unspecified')}</span><code>${esc(a.path)}</code></div>${compactRelations(a,true)}<div class="detail-tabs">${[['content','Engineering meaning'],['source','Markdown source'],['context','Impact & context']].map(([value,label])=>`<button class="${tab===value?'active':''}" data-action="detail-tab" data-id="${esc(a.id)}" data-value="${value}">${label}</button>`).join('')}</div>${content}
    ${tab==='content'?`<div class="detail-section"><h3>Provenance & review</h3><div class="provenance">${a.meta.generated?`Created by ${esc(a.meta.generated.by)}<br>${esc(a.meta.generated.at)}`:'Origin not recorded'}${Array.isArray(a.meta.verified)?a.meta.verified.map(v=>`<br>Reviewed by ${esc(v.by)} · ${esc(v.at)}`).join(''):''}${a.meta.baseline?`<br>Evidence baseline: <code>${esc(a.meta.baseline)}</code>`:''}</div><div class="detail-actions">${btn('Record human review','review','checkCircle','','data-id="'+esc(a.id)+'" data-hash="'+a.hash+'"')}${btn('Edit artifact','edit','edit','primary','data-id="'+esc(a.id)+'"')}</div></div>`:''}</div></section></div>`);
}
function childLinkFields(parent){
  return `<section class="child-link-fields"><h3>Link to parent</h3><p class="field-help"><strong>${esc(parent.title)}</strong> · <code>${esc(parent.id)}</code></p><div class="form-grid"><div class="form-field"><label for="child-relationship">Relationship type</label><input class="input" id="child-relationship" list="child-relationship-types" value="derives-from" autocomplete="off"><datalist id="child-relationship-types">${state.data.relation_types.map(type=>`<option value="${esc(type)}">`).join('')}</datalist><small>Choose a relationship or enter a custom type.</small></div><div class="form-field"><label for="child-link-direction">Link direction</label><select id="child-link-direction"><option value="child-parent">Child → parent</option><option value="parent-child">Parent → child</option></select></div></div><p class="child-link-preview" id="child-link-preview" aria-live="polite"></p><p class="field-help">The child and its parent link are created together when you save.</p></section>`;
}
function updateChildLinkPreview(){
  if(!editorParent||!$('#child-link-preview'))return;
  const child=$('#edit-id').value.trim()||'New child',relation=$('#child-relationship').value.trim()||'relationship';
  $('#child-link-preview').textContent=$('#child-link-direction').value==='child-parent'?`${child} → ${relation} → ${editorParent.id}`:`${editorParent.id} → ${relation} → ${child}`;
}
function editArtifact(a=null,source=false,parent=null){
  editorArtifact=a;editorMode=source?'source':'guided';editorLinkUpdates=[];editorParent=parent;editorAutoId=!a;
  const meta=a?.meta||{ekf:'0.1',id:'',type:parent?.type||'requirement',title:'',status:'draft',discipline:parent?.meta.discipline||'Systems'},core=['ekf','id','type','title','status','discipline','relations'];
  const extra=Object.fromEntries(Object.entries(meta).filter(([k])=>!core.includes(k)));
  const field=(name,label,value,attrs='')=>`<div class="form-field"><label for="edit-${name}">${label}</label><input class="input" id="edit-${name}" value="${esc(value)}" ${attrs}></div>`;
  modal(a?'Edit engineering artifact':source?'Import EKF Markdown':parent?'Create child artifact':'Create engineering artifact',
    `<div class="notice info" style="margin-bottom:20px">${a?'Saving creates a Git commit. Existing baselines remain unchanged.':'Use a stable ID for the engineering concept. Types and metadata are extensible.'}</div>${parent?childLinkFields(parent):''}<div class="form-field"><label for="edit-path">Repository path</label><input class="input mono" id="edit-path" placeholder="engineering/requirements/req-new-001.md" value="${esc(a?.path||'')}" ${a?'readonly':''}></div>
    ${source?`<div class="form-field"><label for="edit-raw">Markdown with YAML frontmatter</label><textarea id="edit-raw" class="code-editor source-editor" spellcheck="false" placeholder="---&#10;ekf: &quot;0.1&quot;&#10;id: REQ-001&#10;type: requirement&#10;title: My requirement&#10;---&#10;&#10;Engineering meaning…">${esc(a?.raw||'')}</textarea></div><input type="file" id="import-file" accept=".md,.markdown,text/markdown,text/plain" aria-label="Choose a Markdown file">`:
    `<div class="form-grid">${editorChoice('type','Artifact type',meta.type,state.data.types,'Custom artifact type')}${editorChoice('discipline','Discipline',meta.discipline||'',['Systems','System of systems','Hardware','Software','Mechanical','Manufacturing',...state.data.artifacts.map(a=>a.meta.discipline)],'Custom discipline')}<div class="form-field"><label for="edit-id">Stable ID</label><div class="editor-id-control"><input class="input" id="edit-id" value="${esc(meta.id)}" ${a?'readonly':''} aria-describedby="edit-id-help">${a?'':btn('Suggest ID','editor-suggest-id','refresh','small')}</div><small id="edit-id-help"></small></div>${field('title','Title',meta.title,'placeholder="A clear engineering concept"')}${field('status','Lifecycle status',meta.status||'draft','list="statuses"')}<datalist id="statuses"><option value="draft"><option value="stable"><option value="deprecated"></datalist></div>
    <div class="form-field" style="margin-top:19px"><label for="edit-body">Engineering meaning · Markdown</label><textarea class="code-editor" id="edit-body" spellcheck="true" style="min-height:230px">${esc(a?.body||'## Statement\n\n\n\n## Acceptance criteria\n\n\n\n## Rationale\n\n')}</textarea></div>
    <section class="editor-links"><h3>Links</h3><p class="field-help" id="editor-links-summary">${(meta.relations||[]).length} outgoing links. Changes are saved with this artifact.</p><div class="link-editor-actions">${btn('Incoming','editor-links','plus','','data-direction="incoming"')}${btn('Outgoing','editor-links','plus','','data-direction="outgoing"')}${btn('Manage links','editor-links','link','','data-manage="true"')}</div><details><summary>Advanced · outgoing links JSON</summary><div class="form-field"><label for="edit-relations">Outgoing relationships · JSON</label><textarea class="code-editor" id="edit-relations" style="min-height:95px" spellcheck="false">${esc(JSON.stringify(meta.relations||[],null,2))}</textarea><small>Custom fields and resource links are preserved. Incoming links are stored on their source items.</small></div></details></section><details><summary class="small muted" style="cursor:pointer;margin-bottom:12px">Additional metadata</summary><div class="form-field"><label for="edit-extra">Custom fields, provenance and review · JSON object</label><textarea class="code-editor" id="edit-extra" style="min-height:120px">${esc(JSON.stringify(extra,null,2))}</textarea></div></details>`}`,
    btn('Cancel','close','','ghost')+btn(parent?'Create child':'Save artifact','save-artifact','check','primary'));
  if(!source){if(!a)setSuggestedArtifactId();updateEditorIdHelp();updateChildLinkPreview();}
}
async function saveArtifact(){
  let raw,path=$('#edit-path').value.trim(),updates=structuredClone(editorLinkUpdates);
  if(editorMode==='source')raw=$('#edit-raw').value;
  else {
    const extra=JSON.parse($('#edit-extra').value||'{}'),relations=JSON.parse($('#edit-relations').value||'[]');
    if(!extra||Array.isArray(extra)||typeof extra!=='object')throw new Error('Additional metadata must be a JSON object');
    if(!Array.isArray(relations))throw new Error('Relationships must be a JSON array');
    const meta={...extra,ekf:'0.1',id:$('#edit-id').value.trim(),type:editorChoiceValue('type'),title:$('#edit-title').value.trim(),status:$('#edit-status').value.trim(),discipline:editorChoiceValue('discipline')};
    if(!meta.type)throw new Error('Choose an artifact type or enter a custom type.');
    if($('#edit-discipline').selectedOptions[0]?.dataset.custom&&!meta.discipline)throw new Error('Enter a custom discipline, or choose Unspecified.');
    if(editorParent){
      const type=$('#child-relationship').value.trim();
      if(!type)throw new Error('Choose a relationship type for the parent link.');
      if(!meta.id||meta.id===editorParent.id)throw new Error('Give the child its own unique stable ID.');
      if($('#child-link-direction').value==='child-parent'){
        if(!relations.some(r=>r.type===type&&r.target===editorParent.id))relations.push({type,target:editorParent.id});
      }else{
        let update=updates.find(u=>u.id===editorParent.id);
        if(!update){update={id:editorParent.id,expected_hash:editorParent.hash,relations:structuredClone(editorParent.meta.relations||[])};updates.push(update);}
        if(!update.relations.some(r=>r.type===type&&r.target===meta.id))update.relations.push({type,target:meta.id});
      }
    }
    if(!meta.generated)meta.generated={by:'human:local',at:new Date().toISOString()};
    if(relations.length)meta.relations=relations;
    raw='---\n'+yamlDump(meta)+'---\n\n'+$('#edit-body').value.trimEnd()+'\n';
    if(!path)path='engineering/'+meta.type.replace(/[^a-zA-Z0-9_-]/g,'-')+'/'+meta.id.toLowerCase().replace(/[^a-z0-9_-]/g,'-')+'.md';
  }
  const draft={path,raw,expected_hash:editorArtifact?.hash};
  const result=updates.length?await api('links',{artifact:draft,updates}):await api('artifact',draft);
  await refresh();toast('Artifact saved and committed to Git');await openArtifact(result.id);
}
function searchModal(){modal('Search engineering knowledge',`<input class="input" id="global-search" placeholder="Search IDs, titles and engineering meaning…" aria-label="Search all artifacts"><div class="search-results" id="search-results"></div>`);$('#global-search').focus();searchResults('');}
function searchResults(query){const items=state.data.artifacts.filter(a=>(a.id+' '+a.title+' '+a.body).toLowerCase().includes(query.toLowerCase())).slice(0,20);$('#search-results').innerHTML=items.map(a=>`<button class="search-result" data-artifact="${esc(a.id)}">${typeIcon(a.type)}<span><h3>${esc(a.title)}</h3><small>${esc(a.id)} · ${esc(a.type)}</small></span></button>`).join('')||empty('No matches','Try a different concept or artifact ID.');}
function connectModal(){const cwd=state.data.root.split('/').slice(0,-1).join('/');modal('Connect your engineering agent',`<p class="small muted">Add this stdio MCP server to your agent configuration. Start Studio first, use the application directory as the working directory, and use a Python environment with the requirements installed.</p><pre class="diff">${esc(JSON.stringify({mcpServers:{'ekf-studio':{command:'python3',args:['-m','ekf.mcp','--url','http://127.0.0.1:'+location.port,'--token-file',state.tools.token_file],cwd}}},null,2))}</pre><div class="notice info">The local token remains in its permission-restricted file. Agent tools can inspect, execute in the sandbox, and propose changes. They cannot approve proposals or directly save artifacts.</div><h3 style="margin-top:20px">A useful first task</h3><p class="small muted" style="margin-top:8px">“Inspect the shutdown requirement and its verification. Run the timing analyzer, explain the result and its limitations, and propose evidence for human review.”</p>`);}
function proposalForm(){modal('Propose an engineering change',`<div class="form-field"><label for="proposal-title">Change title</label><input id="proposal-title" class="input" placeholder="Clarify emergency shutdown acceptance criteria"></div><div class="form-field"><label for="proposal-files">File changes · JSON</label><textarea id="proposal-files" class="code-editor source-editor" spellcheck="false">${esc(JSON.stringify([{path:'tools/my_analysis.py',content:'print("Hello, engineering.")\n'}],null,2))}</textarea><small>Complete UTF-8 file content for each path. Use null to delete a file. Changes are validated and committed on a separate Git branch.</small></div>`,btn('Cancel','close','','ghost')+btn('Create proposal','proposal-create','branch','primary'))}
function proposalDetail(id){const p=state.proposals.find(p=>p.id===id);if(!p)throw new Error('Proposal not found');modal(p.title,`<div class="detail-meta">${badge(p.status)}<span class="small muted">${esc(p.actor)} · ${date(p.created)}</span></div><p class="small muted"><code>${esc(p.branch)}</code><br>Base ${p.base.slice(0,7)} → proposed ${p.commit.slice(0,7)}</p><div class="proposal-summary"><span>${p.files.length} changed files</span><span>${p.relations_added.length} links added</span><span>${p.relations_removed.length} links removed</span><span>${p.affected.length} potentially affected artifacts</span></div><h3>Proposed changes</h3><pre class="diff">${p.diff.split('\n').map(l=>`<span class="${l.startsWith('+')?'added':l.startsWith('-')?'removed':''}">${esc(l)}</span>`).join('\n')}</pre><h3>Impact & unresolved engineering questions</h3><p class="small muted" style="margin:9px 0">${p.affected.map(id=>`<button class="inline-code" data-artifact="${esc(id)}">${esc(id)}</button>`).join(' ')||'No existing artifacts in the affected neighborhood.'}</p><div class="findings">${p.findings.map(f=>`<div class="finding" style="padding:10px 0"><span class="small muted">${esc(f.id||f.path||'Repository')}: ${esc(f.message)}</span></div>`).join('')||'<p class="small muted">No deterministic or advisory findings.</p>'}</div>${p.status==='pending'&&p.base!==state.data.head?'<div class="notice" style="margin-top:15px">The workspace has changed since this proposal. Create an updated proposal before merging.</div>':''}`,
    p.status==='pending'?btn('Reject','proposal-decide','','danger',`data-id="${p.id}" data-decision="reject"`)+btn('Approve & merge','proposal-decide','check','primary',`data-id="${p.id}" data-decision="approve" ${p.base!==state.data.head?'disabled':''}`):btn('Close','close'),true);}
async function showRun(id){
  const run=await api('runs?id='+encodeURIComponent(id));currentRun=id;
  const complete=!['queued','running'].includes(run.status);
  modal('Tool execution',`<div class="detail-meta">${badge(run.status)}<code>${run.id}</code><span class="small muted">${run.duration_ms?run.duration_ms+' ms':''}</span></div><pre class="diff">${esc(run.command)}</pre><p class="small muted" style="margin:10px 0">Source revision <code>${run.revision.slice(0,7)}</code> · ${Object.keys(run.input_hashes).length} hashed inputs · no network</p><div class="terminal">${esc(run.stdout||(!complete?'Executing in the isolated environment…':'No standard output.'))}${run.stderr?'\n\nSTDERR\n'+esc(run.stderr):''}</div>${run.outputs.length?`<div style="margin-top:17px"><h3>Generated outputs</h3>${run.outputs.map(o=>`<div class="relation-row"><button data-action="output" data-id="${id}" data-path="${esc(o.path)}">${esc(o.path)}</button><small>${o.bytes} bytes</small></div>`).join('')}</div>`:''}${complete?`<div class="notice info" style="margin-top:17px">Execution status is not an engineering verdict. Review the result against its pass criteria before marking evidence as accepted.</div><div class="form-field" style="margin-top:18px"><label for="evidence-verification">Link evidence to a verification</label><select id="evidence-verification">${state.data.artifacts.filter(a=>a.type==='verification').map(a=>`<option value="${esc(a.id)}">${esc(a.id+' · '+a.title)}</option>`).join('')}</select></div>`:''}`,
    btn('Close','close','','ghost')+(complete?btn('Propose evidence','evidence','file','primary',`data-id="${id}" ${state.data.artifacts.some(a=>a.type==='verification')?'':'disabled'}`):'<span class="spinner" aria-label="Running"></span>'));
  if(!complete){clearTimeout(pollTimer);pollTimer=setTimeout(()=>{if(currentRun===id)showRun(id).catch(e=>toast(e.message,true));},1200);}
  else {clearTimeout(pollTimer);await refresh();}
}
function showResource(title,text){modal(title,`<pre class="diff" style="max-height:65vh">${esc(text)}</pre>`,btn('Close','close'),true);}
function formError(message){const error=$('#form-error');if(error){error.textContent=message;error.classList.add('visible');error.scrollIntoView({block:'nearest'});}else toast(message,true);}

function highlightGraph(svg,id=''){
  const related=new Set(id?[id]:[]);
  svg.classList.toggle('has-highlight',Boolean(id));
  for(const edge of $$('.graph-edge',svg)){
    const incoming=Boolean(id)&&edge.dataset.target===id;
    const outgoing=Boolean(id)&&edge.dataset.source===id;
    edge.classList.toggle('is-incoming',incoming);
    edge.classList.toggle('is-outgoing',outgoing);
    edge.setAttribute('marker-end',`url(#${svg.dataset.arrow}${outgoing?'-outgoing':incoming?'-incoming':''})`);
    if(incoming||outgoing){
      related.add(edge.dataset.source);related.add(edge.dataset.target);
      // Keep highlighted links visible at crossings, beneath the nodes.
      edge.parentNode.append(edge);
    }
  }
  for(const node of $$('.graph-node',svg)){
    node.classList.toggle('is-active',node.dataset.artifact===id);
    node.classList.toggle('is-related',related.has(node.dataset.artifact));
  }
}
function updateGraphCamera(svg){
  const camera=state.graphViews.get(svg.dataset.graphKey);
  svg.setAttribute('viewBox',graphViewBox(camera,camera.width,camera.height));
  const viewport=svg.closest('.graph-viewport');
  $('.graph-zoom-level',viewport).textContent=Math.round(camera.zoom*100)+'%';
  $('[data-graph-zoom="out"]',viewport).disabled=camera.zoom<=graphZoomSteps[0];
  $('[data-graph-zoom="in"]',viewport).disabled=camera.zoom>=graphZoomSteps.at(-1);
}
function zoomGraph(svg,action,anchor){
  if(!svg)return;
  const camera=state.graphViews.get(svg.dataset.graphKey);
  if(action==='reset'){
    Object.assign(camera,{zoom:1,x:camera.width/2,y:camera.height/2});
  }else{
    const next=action==='in'?graphZoomSteps.find(z=>z>camera.zoom):[...graphZoomSteps].reverse().find(z=>z<camera.zoom);
    if(next===undefined)return;
    anchor??={x:camera.x,y:camera.y};
    camera.x=anchor.x+(camera.x-anchor.x)*camera.zoom/next;
    camera.y=anchor.y+(camera.y-anchor.y)*camera.zoom/next;
    camera.zoom=next;
  }
  updateGraphCamera(svg);
}
function graphPoint(svg,event){return new DOMPoint(event.clientX,event.clientY).matrixTransform(svg.getScreenCTM().inverse());}
let graphMenuNode=null;
function closeGraphMenu(restoreFocus=false){
  $('#graph-context-menu')?.remove();
  if(graphMenuNode){graphMenuNode.setAttribute('aria-expanded','false');if(restoreFocus&&graphMenuNode.isConnected)graphMenuNode.focus({preventScroll:true});}
  graphMenuNode=null;
}
function openGraphMenu(node,x,y){
  const artifact=state.data.artifacts.find(a=>a.id===node.dataset.artifact);
  if(!artifact||$('#overlay').childElementCount)return;
  closeGraphMenu();graphMenuNode=node;node.focus({preventScroll:true});node.setAttribute('aria-expanded','true');
  const menu=document.createElement('div');menu.id='graph-context-menu';menu.className='graph-context-menu';menu.setAttribute('role','menu');menu.setAttribute('aria-label',`Actions for ${artifact.id}`);
  menu.innerHTML=`<div class="graph-menu-heading" role="presentation"><strong>${esc(artifact.title)}</strong><code>${esc(artifact.id)}</code></div>${btn('Create child…','graph-child','plus','',`role="menuitem" data-id="${esc(artifact.id)}"`)}${btn('Open item','graph-open','file','',`role="menuitem" data-id="${esc(artifact.id)}"`)}${readonly()?'<p class="field-help">Baseline · read only</p>':''}`;
  document.body.append(menu);
  const box=menu.getBoundingClientRect(),anchor=node.getBoundingClientRect();
  if(!Number.isFinite(x))x=anchor.left;
  if(!Number.isFinite(y))y=anchor.bottom;
  menu.style.left=Math.max(8,Math.min(x,innerWidth-box.width-8))+'px';
  menu.style.top=Math.max(8,Math.min(y,innerHeight-box.height-8))+'px';
  $('button',menu)?.focus({preventScroll:true});
}
document.addEventListener('contextmenu',event=>{
  const node=event.target.closest('.graph-node');if(!node)return;
  event.preventDefault();openGraphMenu(node,event.clientX,event.clientY);
});
document.addEventListener('pointerdown',event=>{
  const menu=$('#graph-context-menu');if(menu&&!menu.contains(event.target))closeGraphMenu();
});
document.addEventListener('keydown',event=>{
  const node=event.target.closest('.graph-node');
  if(node&&(event.key==='ContextMenu'||(event.shiftKey&&event.key==='F10'))){
    event.preventDefault();const box=node.getBoundingClientRect();openGraphMenu(node,box.left,box.bottom);return;
  }
  const menu=event.target.closest('#graph-context-menu');if(!menu)return;
  const items=$$('button',menu),index=items.indexOf(document.activeElement);
  if(['ArrowDown','ArrowUp','Home','End'].includes(event.key)){
    event.preventDefault();items[event.key==='Home'?0:event.key==='End'?items.length-1:(index+(event.key==='ArrowDown'?1:-1)+items.length)%items.length]?.focus();
  }
  if(event.key==='Tab')closeGraphMenu(true);
});
window.addEventListener('resize',()=>closeGraphMenu());
// Dismiss on a scroll gesture, not on delayed scroll events caused by focusing a graph item.
document.addEventListener('wheel',()=>closeGraphMenu(Boolean($('#graph-context-menu')?.contains(document.activeElement))),{passive:true});
document.addEventListener('click',event=>{
  const control=event.target.closest('[data-graph-zoom]');
  if(control)zoomGraph($('.engineering-graph',control.closest('.graph-viewport')),control.dataset.graphZoom);
});
document.addEventListener('pointerover',event=>{
  const node=event.target.closest('.graph-node');
  if(node&&event.relatedTarget?.closest?.('.graph-node')!==node)highlightGraph(node.closest('svg'),node.dataset.artifact);
});
document.addEventListener('pointerout',event=>{
  const node=event.target.closest('.graph-node');
  if(node&&event.relatedTarget?.closest?.('.graph-node')!==node){
    const svg=node.closest('svg');highlightGraph(svg,$('.graph-node:focus',svg)?.dataset.artifact);
  }
});
document.addEventListener('focusin',event=>{
  if(event.target.matches('.graph-node'))highlightGraph(event.target.closest('svg'),event.target.dataset.artifact);
});
document.addEventListener('focusout',event=>{
  if(event.target.matches('.graph-node')){
    const svg=event.target.closest('svg');highlightGraph(svg,$('.graph-node:hover',svg)?.dataset.artifact);
  }
});
document.addEventListener('wheel',event=>{
  const svg=event.target.closest('.engineering-graph');
  if(!svg||(!event.ctrlKey&&!event.metaKey)||!event.deltaY)return;
  event.preventDefault();
  zoomGraph(svg,event.deltaY<0?'in':'out',graphPoint(svg,event));
},{passive:false});
let graphDrag=null;
document.addEventListener('pointerdown',event=>{
  const svg=event.target.closest('.engineering-graph');
  if(!svg||event.target.closest('.graph-node')||event.button!==0)return;
  const camera=state.graphViews.get(svg.dataset.graphKey);
  graphDrag={svg,pointerId:event.pointerId,point:graphPoint(svg,event),x:camera.x,y:camera.y,inverse:svg.getScreenCTM().inverse()};
  svg.setPointerCapture(event.pointerId);svg.classList.add('is-panning');
  highlightGraph(svg);event.preventDefault();
});
document.addEventListener('pointermove',event=>{
  if(!graphDrag||event.pointerId!==graphDrag.pointerId)return;
  const {svg,point,inverse,x,y}=graphDrag;
  const current=new DOMPoint(event.clientX,event.clientY).matrixTransform(inverse);
  const camera=state.graphViews.get(svg.dataset.graphKey);
  camera.x=x+point.x-current.x;camera.y=y+point.y-current.y;
  updateGraphCamera(svg);
});
function endGraphDrag(event){
  if(!graphDrag||event.pointerId!==graphDrag.pointerId)return;
  const {svg,pointerId}=graphDrag;graphDrag=null;
  svg.classList.remove('is-panning');
  if(svg.hasPointerCapture(pointerId))svg.releasePointerCapture(pointerId);
}
for(const name of ['pointerup','pointercancel','lostpointercapture'])document.addEventListener(name,endGraphDrag);
document.addEventListener('keydown',event=>{
  const svg=event.target.closest('.engineering-graph');
  if(!svg||event.ctrlKey||event.metaKey||event.altKey)return;
  const action={'+':'in','=':'in','-':'out','0':'reset'}[event.key];
  if(action){event.preventDefault();zoomGraph(svg,action);}
});
const actions={
  'graph-child':async el=>{const id=el.dataset.id;closeGraphMenu(true);await refresh(false);if(readonly())return;const parent=state.data.artifacts.find(a=>a.id===id);if(!parent)throw new Error('The selected parent no longer exists. Refresh the graph.');editArtifact(null,false,parent);},
  'graph-open':el=>{closeGraphMenu(true);return openArtifact(el.dataset.id);},
  'explore-overview':()=>{const root=overviewRoot();if(!root)return;navigate('traceability');state.focus=root.id;state.graphMode='graph';renderShell();},
  'browse-baseline':async el=>{await selectVersion(el.dataset.ref,el.dataset.name);navigate('overview');},
  'current-workspace':()=>selectVersion(),
  'history-tab':el=>{state.historyTab=el.dataset.value;if(state.historyTab==='compare'&&!state.comparison&&!state.compareBefore)state.compareBefore=state.revision?.name||state.baselines[0]?.name||'';renderShell();},
  'compare-baseline':el=>{state.historyTab='compare';state.compareBefore=el.dataset.name;state.compareAfter='';return loadComparison();},
  'compare-load':loadComparison,
  'compare-swap':()=>{[state.compareBefore,state.compareAfter]=[state.compareAfter,state.compareBefore];return loadComparison();},
  'compare-artifact':el=>comparisonArtifact(el.dataset.id),
  'compare-resource':el=>comparisonResource(el.dataset.path),
  nav:el=>navigate(el.dataset.page), menu:()=>$('.sidebar').classList.toggle('open'), refresh:async()=>{await refresh();toast('Repository refreshed from source files');},
  new:()=>editArtifact(), import:()=>editArtifact(null,true), close:()=>closeOverlay(), search:searchModal, connect:connectModal,
  artifact:el=>openArtifact(el.dataset.id), edit:async el=>editArtifact(await api('artifact?id='+encodeURIComponent(el.dataset.id))),
  'editor-links':openEditorLinks,
  'editor-suggest-id':async()=>{const input=$('#edit-id');await refresh(false);if(input?.isConnected&&input===$('#edit-id')&&!readonly())setSuggestedArtifactId();},
  'links-open':async el=>{await refresh(false);const artifact=state.data.artifacts.find(a=>a.id===el.dataset.id);if(!artifact)throw new Error('Artifact no longer exists. Refresh the workspace.');linkController.open({artifact,direction:el.dataset.direction,manage:el.dataset.manage==='true'});},
  'save-artifact':saveArtifact,'detail-tab':el=>openArtifact(el.dataset.id,el.dataset.value),
  layout:el=>{state.layout=el.dataset.value;renderShell();},'graph-mode':el=>{state.graphMode=el.dataset.value;renderShell();},
  'verification-tab':el=>{state.verificationTab=el.dataset.value;renderShell();},'agent-tab':el=>{state.agentTab=el.dataset.value;renderShell();},
  validate:async()=>{await refresh(false);state.verificationTab='findings';renderShell();toast(`Validation complete: ${state.data.validation.errors} errors, ${state.data.validation.warnings} advisories`);},
  export:el=>{const a=document.createElement('a');a.href='/api/'+revisionPath('report?kind='+encodeURIComponent(el.dataset.kind));a.download='engineering-report.md';a.click();},
  review:async el=>{await api('review',{id:el.dataset.id,expected_hash:el.dataset.hash});await refresh();toast('Human review recorded in source and Git');await openArtifact(el.dataset.id);},
  resource:async el=>{const r=await api(revisionPath('resource?path='+encodeURIComponent(el.dataset.path)));showResource(r.path,r.content);},
  output:async el=>{const r=await api('output?id='+el.dataset.id+'&path='+encodeURIComponent(el.dataset.path));clearTimeout(pollTimer);currentRun=null;showResource(el.dataset.path,r.content);},
  'proposal-new':proposalForm,'proposal-create':async()=>{const p=await api('proposals',{title:$('#proposal-title').value,changes:JSON.parse($('#proposal-files').value)});await refresh();proposalDetail(p.id);toast('Proposal committed on a separate branch');},
  proposal:el=>proposalDetail(el.dataset.id),'proposal-decide':async el=>{const p=await api('proposals/decide',{id:el.dataset.id,decision:el.dataset.decision});await refresh();proposalDetail(p.id);toast(p.status==='approved'?'Change approved and merged':'Proposal rejected; branch preserved');},
  baseline:()=>modal('Create an engineering baseline',`<p class="small muted" style="margin-bottom:18px">Tag the current committed engineering state. This will not overwrite any existing baseline.</p><div class="form-field"><label for="baseline-name">Baseline name</label><input id="baseline-name" class="input" placeholder="prototype-1"></div><p class="small muted">Commit: <code>${esc(state.data.head)}</code></p>`,btn('Cancel','close','','ghost')+btn('Create baseline','baseline-create','tag','primary')),
  'baseline-create':async()=>{await api('baselines',{name:$('#baseline-name').value.trim()});closeOverlay();await refresh();toast('Engineering baseline created');},
  run:async()=>{const command=$('#tool-command').value;sessionStorage.setItem('command',command);const run=await api('runs',{command});await refresh();await showRun(run.id);},
  'run-detail':el=>showRun(el.dataset.id),evidence:async el=>{const p=await api('evidence',{run_id:el.dataset.id,verification_id:$('#evidence-verification').value,title:'Execution evidence · '+el.dataset.id});currentRun=null;await refresh();proposalDetail(p.id);toast('Evidence is ready for engineering review');},
  probe:async()=>{await api('sandbox/probe',{});await refresh();toast(state.tools.sandbox.reason,!state.tools.sandbox.available);},
  manifest:async()=>{const r=await api('resource?path=ekf.yaml');modal('Edit repository manifest',`<p class="small muted" style="margin-bottom:15px">The manifest remains an ordinary YAML file. Review your change as a Git proposal.</p><textarea id="manifest-editor" class="code-editor source-editor">${esc(r.content)}</textarea>`,btn('Cancel','close','','ghost')+btn('Propose manifest change','manifest-save','branch','primary'));},
  'manifest-save':async()=>{const p=await api('proposals',{title:'Update repository manifest',changes:[{path:'ekf.yaml',content:$('#manifest-editor').value}]});await refresh();proposalDetail(p.id);},
};
document.addEventListener('click',async event=>{
  if(event.target.matches('.overlay-backdrop')){closeOverlay();return;}
  if(event.target.closest('[data-relations]')&&!event.target.closest('button[data-artifact],button[data-action]'))return;
  const artifact=event.target.closest('[data-artifact]');const action=event.target.closest('[data-action]');
  if(artifact&&!action){try{await openArtifact(artifact.dataset.artifact);}catch(e){formError(e.message);}return;}
  if(!action)return;const handler=actions[action.dataset.action];if(!handler)return;
  if(readonly()&&writeActions.has(action.dataset.action)){toast('This baseline is read only. Return to the current workspace to make changes.',true);return;}
  const disabled=action.disabled;action.disabled=true;
  try{await handler(action);}catch(e){formError(e.message);}finally{action.disabled=disabled;}
});
document.addEventListener('input',event=>{
  if(event.target.id==='edit-id'&&!editorArtifact){editorAutoId=false;updateEditorIdHelp();}
  if(event.target.id==='edit-type-custom'&&editorAutoId)setSuggestedArtifactId();
  if(['edit-id','child-relationship'].includes(event.target.id))updateChildLinkPreview();
  if(event.target.id==='global-search')searchResults(event.target.value);
  if(event.target.id==='tool-command')sessionStorage.setItem('command',event.target.value);
  if(event.target.dataset.filter==='query'){
    const pos=event.target.selectionStart;state.query=event.target.value;$('#content').innerHTML=renderPage();const input=$('#library-search');input.focus();input.setSelectionRange(pos,pos);
  }
});
document.addEventListener('change',async event=>{
  if(['edit-type','edit-discipline'].includes(event.target.id)){
    const name=event.target.id.slice(5),custom=Boolean(event.target.selectedOptions[0]?.dataset.custom);
    $('#edit-'+name+'-custom-field').hidden=!custom;
    if(custom)$('#edit-'+name+'-custom').focus();
    if(name==='type'&&(editorAutoId||!$('#edit-id').value.trim()))setSuggestedArtifactId();
    updateEditorIdHelp();return;
  }
  if(event.target.id==='child-link-direction')updateChildLinkPreview();
  if(event.target.id==='overview-root-type'){
    const current=overviewRoot()?.id;
    state.overviewTypes[state.data.root]=event.target.value;
    state.overviewRoots[state.data.root]=overviewRootChoices().some(a=>a.id===current)?current:overviewRoot()?.id;
    sessionStorage.setItem('ekf-overview-types',JSON.stringify(state.overviewTypes));
    sessionStorage.setItem('ekf-overview-roots',JSON.stringify(state.overviewRoots));
    $('.overview-graph-panel').outerHTML=overviewGraphPanel();$('#overview-root-type').focus();return;
  }
  if(event.target.id==='overview-root'){
    state.overviewRoots[state.data.root]=event.target.value;
    state.overviewTypes[state.data.root]=overviewRootType();
    sessionStorage.setItem('ekf-overview-types',JSON.stringify(state.overviewTypes));
    sessionStorage.setItem('ekf-overview-roots',JSON.stringify(state.overviewRoots));
    $('.overview-graph-panel').outerHTML=overviewGraphPanel();$('#overview-root').focus();return;
  }
  if(event.target.id==='workspace-revision'){
    const ref=event.target.value,b=state.baselines.find(b=>b.name===ref);
    try{await selectVersion(b?.commit||ref,b?.name||ref);}catch(e){toast(e.message,true);renderShell();}return;
  }
  if(['compare-before','compare-after'].includes(event.target.id)){
    state[event.target.id==='compare-before'?'compareBefore':'compareAfter']=event.target.value;
    comparisonRequest++;state.comparisonLoading=false;state.comparison=null;renderShell();return;
  }
  if(event.target.dataset.filter&&event.target.dataset.filter!=='query'){state[event.target.dataset.filter]=event.target.value;renderShell();}
  if(event.target.id==='graph-focus'){state.focus=event.target.value;renderShell();}
  if(event.target.id==='import-file'&&event.target.files[0]){const f=event.target.files[0];if(f.size>2*1024*1024){formError('Markdown files must be under 2 MB');return;}$('#edit-raw').value=await f.text();if(!$('#edit-path').value)$('#edit-path').value='engineering/imported/'+f.name;}
});
document.addEventListener('keydown',event=>{
  if((event.metaKey||event.ctrlKey)&&event.key.toLowerCase()==='k'){event.preventDefault();if(!linkController.active)searchModal();}
  if(event.key==='Escape'){if($('#graph-context-menu')){event.preventDefault();closeGraphMenu(true);return;}if($('#overlay').childElementCount)closeOverlay();$('.sidebar')?.classList.remove('open');}
  if(event.key==='Enter'&&event.target.matches('[data-artifact]')){event.preventDefault();openArtifact(event.target.dataset.artifact).catch(e=>toast(e.message,true));}
  if(event.key==='Tab'&&$('#overlay').innerHTML){const focusable=$$('button:not(:disabled),input:not(:disabled),select,textarea,a[href],[tabindex="0"]',$('#overlay')).filter(e=>e.getClientRects().length);const first=focusable[0],last=focusable.at(-1);if(event.shiftKey&&document.activeElement===first){event.preventDefault();last?.focus();}else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first?.focus();}}
});
window.addEventListener('hashchange',()=>{const page=location.hash.slice(1)||'overview';if(page!==state.page)navigate(page);});
refresh().catch(error=>{$('#app').innerHTML=`<div class="empty"><h1>Open your workspace</h1><p>Use the browser access link printed when you start EKF Studio. It authorizes this browser to edit and approve engineering changes.</p><p style="margin-top:14px">${esc(error.message)}</p>${btn('Try again','refresh','refresh','primary')}</div>`;});
