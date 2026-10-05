export function createChangeController({getState,api,refresh,modal,close,toast,esc,btn,badge,icon,navigate}) {
  const $=s=>document.querySelector(s);
  const button=(label,action,attrs='',cls='')=>`<button class="btn ${cls}" data-change-action="${action}" ${attrs}>${label}</button>`;
  let busy=false, conflict=null;
  const workflow=()=>getState().data?.workflow;
  function banner() {
    const w=workflow();
    if(!w?.id)return '';
    return `<div class="change-banner"><span>${icon('branch',15)} Editing <strong>${esc(w.title)}</strong><small>Changes accumulate in this proposal. Main stays unchanged.</small></span>${button('Review proposal','detail',`data-id="${w.id}"`,'small')}</div>`;
  }
  function picker() {
    const state=getState(),w=workflow(),pending=state.proposals.filter(p=>p.status==='pending');
    modal('Working branch',`<p class="small muted">Choose main to view the approved state, or resume a change proposal. Your other drafts stay saved.</p><div class="branch-options">${button(`${esc(w.main_branch)} · Approved state`,'switch','data-id=""',!w.id?'primary':'')}${pending.map(p=>button(`${esc(p.title)}${p.active?' · Editing':''}${p.unavailable?' · Unavailable':''}`,'switch',`data-id="${p.id}" ${p.unavailable?'disabled':''}`,p.active?'primary':'')).join('')}</div><p class="small muted">Editing an artifact on main automatically starts a proposal on its first save.</p>`,button('Start a new change','new','','primary'));
  }
  function newChange() {
    modal('Start a change',`<p class="small muted">Start from the latest approved main. All subsequent edits will accumulate in this proposal.</p><div class="form-field"><label for="change-title">Change name</label><input id="change-title" class="input" maxlength="200" placeholder="For example: Add irrigation controls"></div>`,btn('Cancel','close','','ghost')+button('Start change','start','','primary'));
  }
  function updatePanel(p) {
    const incoming=p.behind?`${p.behind} newer commit${p.behind===1?'':'s'} on main to bring into this branch.`:'Your branch already contains the current main.';
    const blocked=p.unavailable||p.dirty||p.conflicts?.length;
    const last=p.last_update;
    return `<section class="proposal-workflow" aria-label="Prepare for approval"><div class="proposal-step"><span class="step-number">1</span><div><h3>Bring approved changes into your draft</h3><p class="merge-direction">Main → your branch</p><p>${esc(incoming)} Main stays unchanged by this step.</p>${button('Bring in latest main','update',`data-id="${p.id}" ${blocked?'disabled':''}`)}</div></div>
      <div class="proposal-step"><span class="step-number">2</span><div><h3>Inspect and check the combined result</h3><p>Read the updated requirements, links and evidence in your branch. Make any adjustments, then run checks.</p><div class="proposal-step-actions">${button('Inspect updated branch','resume',`data-id="${p.id}" ${p.unavailable?'disabled':''}`)}${button('Check proposal','check',`data-id="${p.id}" ${blocked||p.behind?'disabled':''}`)}</div></div></div>
      <div class="proposal-step"><span class="step-number">3</span><div><h3>Approve when you are satisfied</h3><p class="merge-direction">Your branch → main</p><p>Use Approve &amp; merge below to add your reviewed changes to the approved project.</p></div></div></section>
      ${last?`<details class="proposal-update-result"><summary>Last update from main · ${last.files.length} changed file${last.files.length===1?'':'s'}</summary><p class="small muted">${esc(new Date(last.at).toLocaleString())} · Changes made to your branch by this update, including conflict resolutions. Later edits appear in the accumulated changes below.</p>${last.files.length?`<ul class="proposal-files">${last.files.map(path=>`<li><code>${esc(path)}</code></li>`).join('')}</ul><pre class="diff">${esc(last.diff)}</pre>`:'<p class="small muted">No file content changed. Your branch already had the same content.</p>'}${last.truncated?'<p class="notice info">This update preview is truncated. Inspect the full files in your branch or Git.</p>':''}</details>`:''}`;
  }
  function detail(identity) {
    const p=getState().proposals.find(p=>p.id===identity);if(!p)throw new Error('Proposal not found.');
    const pending=p.status==='pending',checks=p.checks;
    const status=p.unavailable?'The Git branch is unavailable. Restore it from a backup to resume this proposal.':p.conflicts?.length?'Resolve the conflicting files below to complete the update from main.':p.dirty?'This proposal has uncommitted files. Resolve conflicts or commit external edits before checking.':p.behind?`Main has ${p.behind} newer commit${p.behind===1?'':'s'}. Bring in latest main, then inspect and check your branch.`:p.merge_ready?'Checks passed for the current main and proposal commits. Review the combined result before approval.':checks&&p.checks_current&&!checks.passed?'Checks found errors. Correct them in the proposal and check again.':'Inspect your branch, then select Check proposal before approval. Every edit or new main commit invalidates earlier checks.';
    modal(p.title,`<div class="detail-meta">${badge(p.status)}<span class="small muted">${esc(p.actor)}</span>${p.active?'<span class="badge">Currently editing</span>':''}</div><p class="small muted"><code>${esc(p.branch)}</code><br>Proposal ${esc(p.commit?.slice(0,7))}${p.main_commit?` · Main ${esc(p.main_commit.slice(0,7))}`:''}</p>
      ${pending?`<div class="proposal-check-state ${p.merge_ready?'ready':''}" role="status">${esc(status)}</div><div class="proposal-tools"><div class="form-field"><label for="proposal-rename">Change name</label><input id="proposal-rename" class="input" maxlength="200" value="${esc(p.title)}"></div>${button('Rename','rename',`data-id="${p.id}"`)}${button(p.active?'Continue editing':'Resume editing','resume',`data-id="${p.id}" ${p.unavailable?'disabled':''}`)}</div>`:''}
      ${p.conflicts?.length?`<section class="proposal-conflicts"><h3>Conflicts with main</h3>${p.conflicts.map(path=>`<div><code>${esc(path)}</code>${button('Resolve','conflict',`data-id="${p.id}" data-path="${esc(path)}"`,'small')}</div>`).join('')}</section>`:''}
      ${pending&&!p.unavailable?updatePanel(p):''}
      <div class="proposal-summary"><span>${p.files.length} changed files</span><span>${p.relations_added.length} links added</span><span>${p.relations_removed.length} links removed</span><span>${p.affected.length} affected artifacts</span></div>
      ${checks?`<p class="small muted">Last check: ${esc(new Date(checks.at).toLocaleString())} · main <code>${esc(checks.main.slice(0,7))}</code> · proposal <code>${esc(checks.commit.slice(0,7))}</code>${pending&&!p.checks_current?' · Outdated':''}</p>`:''}
      <h3>Accumulated changes</h3>${p.files.length?`<details><summary>Changed files</summary><ul class="proposal-files">${p.files.map(path=>`<li><code>${esc(path)}</code></li>`).join('')}</ul></details><pre class="diff">${esc(p.diff)}</pre>`:'<p class="small muted">No saved changes yet. Resume editing to add artifacts, links or files.</p>'}
      ${p.diff_truncated?'<p class="notice info">This diff preview is truncated. Review the complete changes in Git before approving.</p>':''}
      <h3>Validation & engineering findings</h3><div class="findings">${(checks?.findings||p.findings).map(f=>`<div class="finding"><span class="small muted">${esc(f.severity)} · ${esc(f.id||f.path||'Repository')}: ${esc(f.message)}</span></div>`).join('')||'<p class="small muted">No findings recorded.</p>'}</div>`,
      btn('Workflow help','nav','question','','data-page="help"')+(pending?button('Reject','reject',`data-id="${p.id}"`,'danger')+button('Approve & merge','approve',`data-id="${p.id}" ${p.merge_ready?'':'disabled'}`,'primary'):btn('Close','close')),true);
  }
  async function showConflict(identity,path) {
    conflict={...(await api('proposals/conflict?'+new URLSearchParams({id:identity,path}))),id:identity};
    const f=conflict;
    modal('Resolve conflict',`<p><code>${esc(f.path)}</code></p><p class="small muted">Choose a complete version or edit the combined text. Both original versions remain in Git history.</p>
      ${f.binary?'<p class="notice info">This is a binary or large file. Choose which version to keep.</p>':`<div class="conflict-versions"><details><summary>Proposal version${!f.ours_exists?' · Deleted':''}</summary><pre class="diff">${esc(f.ours??'Deleted')}</pre></details><details><summary>Main version${!f.main_exists?' · Deleted':''}</summary><pre class="diff">${esc(f.main_content??'Deleted')}</pre></details></div><div class="form-field"><label for="conflict-content">Resolved file content</label><textarea id="conflict-content" class="code-editor source-editor" spellcheck="false">${esc(f.ours??f.main_content??'')}</textarea></div>`}`,
      button('Back to proposal','detail',`data-id="${identity}"`)+button(f.ours_exists?'Keep proposal version':'Keep proposal deletion','resolve','data-choice="ours"')+button(f.main_exists?'Keep main version':'Keep main deletion','resolve','data-choice="main"')+(!f.binary?button('Save resolved text','resolve','data-choice="manual"','primary'):''),true);
  }
  document.addEventListener('click',async event=>{
    const el=event.target.closest('[data-change-action]');if(!el||busy)return;
    event.preventDefault();event.stopPropagation();
    if(getState().revision)return;
    busy=true;
    const controls=[...document.querySelectorAll('[data-change-action]')].map(control=>[control,control.disabled]);
    controls.forEach(([control])=>control.disabled=true);
    el.setAttribute('aria-busy','true');
    try {
      const action=el.dataset.changeAction,id=el.dataset.id;
      if(action==='picker')picker();
      if(action==='new')newChange();
      if(action==='start'){await api('changes/start',{title:$('#change-title').value});close(true);await refresh();toast('Working branch created. Your edits will accumulate in this proposal.');}
      if(action==='switch'||action==='resume'){await api('changes/switch',{id:id||null});close(true);await refresh();if(action==='resume')navigate('knowledge');}
      if(action==='detail'){await refresh(false);detail(id);}
      if(action==='rename'){await api('proposals/rename',{id,title:$('#proposal-rename').value});await refresh();detail(id);}
      if(action==='update'){const p=await api('proposals/update',{id,run_checks:false});await refresh();detail(id);toast(p.conflicts?.length?'Resolve conflicts, then inspect and check your branch.':'Your branch contains the latest main. Inspect it, then select Check proposal.');}
      if(action==='check'){await api('proposals/check',{id});await refresh();detail(id);}
      if(action==='approve'||action==='reject'){await api('proposals/decide',{id,decision:action});await refresh();detail(id);toast(action==='approve'?'Proposal approved and merged into main.':'Proposal rejected and archived. Its branch is preserved.');}
      if(action==='conflict')await showConflict(id,el.dataset.path);
      if(action==='resolve'){const f=conflict;await api('proposals/resolve',{id:f.id,path:f.path,choice:el.dataset.choice,content:$('#conflict-content')?.value,expected_commit:f.commit,expected_main:f.main});await refresh();detail(f.id);}
    } catch(error) {const out=$('#form-error');if(out){out.textContent=error.message;out.classList.add('visible');}else toast(error.message,true);}
    finally{busy=false;controls.forEach(([control,disabled])=>{if(control.isConnected)control.disabled=disabled;});el.removeAttribute('aria-busy');}
  });
  return {banner,picker,newChange,detail};
}
