// One shared, staged relationship editor for the item pane and artifact drafts.
export function createLinkController({getSnapshot, modal, esc, api, onSaved, formError}) {
  const $ = s => document.querySelector(s);
  const clone = value => structuredClone(value);
  const same = (a,b) => JSON.stringify(a) === JSON.stringify(b);
  const key = r => JSON.stringify([r.type, r.target, r.resource]);
  const descriptions = {
    'derives-from':'The source is derived from the target.', refines:'The source adds detail to the target.',
    'depends-on':'The source depends on the target.', 'allocated-to':'The source is allocated to the target.',
    'implemented-by':'The source is implemented by the target.', 'verified-by':'The source is verified by the target.',
    'validated-by':'The source is validated by the target.', mitigates:'The source mitigates the target.',
    'interfaces-with':'The source interfaces with the target.', supersedes:'The source replaces the target.',
    produces:'The source produces the target.'
  };
  let session = null;
  const button = (label, action, attrs='', cls='') => `<button class="btn ${cls}" data-link-action="${action}" ${attrs}>${label}</button>`;
  const optionList = (values,all) => `<option value="">${all}</option>`+values.map(v=>`<option value="${esc(v)}">${esc(v)}</option>`).join('');
  const relationList = id => session.changes.get(id) || session.artifacts.get(id)?.meta.relations || [];
  const setRelations = (id,relations) => session.changes.set(id,relations);
  function changes() {
    return [...session.changes].filter(([id,relations])=>!same(relations,session.original.get(id)||[]));
  }
  function updates() {
    return changes().map(([id,relations])=>({id, relations:clone(relations), expected_hash:session.artifacts.get(id)?.hash}));
  }
  function open({artifact, direction='outgoing', editor=false, relations, pending=[], onApply, manage=false}) {
    if(session) return;
    const snapshot=getSnapshot();
    if(snapshot.readonly) throw new Error('Return to the current workspace to edit links.');
    const artifacts=new Map(snapshot.artifacts.map(a=>[a.id,a]));
    artifacts.set(artifact.id,artifact);
    const original=new Map([...artifacts].map(([id,a])=>[id,clone(a.meta.relations||[])]));
    const initial=new Map(pending.map(u=>[u.id,clone(u.relations)]));
    if(relations) initial.set(artifact.id,clone(relations));
    // Keep the original source hashes when reopening an editor with pending incoming links.
    for(const update of pending) {
      const a=artifacts.get(update.id);
      if(a) artifacts.set(a.id,{...a,hash:update.expected_hash});
    }
    session={project:snapshot.root,workspace:snapshot.workflow?.context,artifact, artifacts, original, changes:initial, editor, onApply, direction,
      selected:new Set(), page:0, managePage:0, tab:manage?'manage':'add', busy:false,
      parent:[...$('#overlay').childNodes], focus:document.activeElement};
    const types=[...new Set([...snapshot.relation_types,...Object.keys(descriptions)])].sort();
    modal('Manage links', `<div class="link-context"><strong>${esc(artifact.title||artifact.id)}</strong><code>${esc(artifact.id)}</code></div>
      <p class="field-help">Outgoing: this item → another item. Incoming: another item → this item. Incoming changes are saved on the source items.</p>
      <div class="tabs link-tabs">${button('Add links','tab','data-tab="add"')}${button('Existing links','tab','data-tab="manage"')}</div>
      <datalist id="link-types">${types.map(t=>`<option value="${esc(t)}">${esc(descriptions[t]||'Custom relationship')}</option>`).join('')}</datalist>
      <section id="link-add">
        <div class="form-grid"><div class="form-field"><label for="link-direction">Direction</label><select id="link-direction"><option value="outgoing">Outgoing · this item → selected items</option><option value="incoming">Incoming · selected items → this item</option></select></div>
        <div class="form-field"><label for="link-type">Relationship</label><input class="input" id="link-type" list="link-types" value="depends-on" placeholder="Choose or type a relationship" autocomplete="off"><small id="link-type-help"></small></div></div>
        <div class="link-direction-preview" id="link-direction-preview" aria-live="polite"></div>
        <div class="link-filters"><input class="input" id="link-query" aria-label="Search items to link" placeholder="Search by ID or title…"><select id="link-item-type" aria-label="Filter link items by type">${optionList(snapshot.types,'All types')}</select><select id="link-discipline" aria-label="Filter link items by discipline">${optionList([...new Set(snapshot.artifacts.map(a=>a.meta.discipline).filter(Boolean))].sort(),'All disciplines')}</select></div>
        <div id="link-results" class="link-results"></div><div id="link-pagination" class="link-pagination"></div>
        <div class="link-selected" id="link-selected"></div><div class="link-stage">${button('Add selected links','stage','','primary')}<span class="field-help">Review changes below before saving.</span></div>
      </section>
      <section id="link-manage" hidden><div class="link-filters"><input id="link-manage-query" class="input" aria-label="Search existing links" placeholder="Search ID, title, relationship or resource…"><select id="link-manage-direction" aria-label="Filter existing links by direction"><option value="">Both directions</option><option value="incoming">Incoming</option><option value="outgoing">Outgoing</option></select></div><div id="link-existing" class="link-results"></div><div id="link-manage-pagination" class="link-pagination"></div></section>
      <section class="link-review"><h3 id="link-review-title" aria-live="polite">No pending changes</h3><div id="link-review-list"></div></section>`,
      button('Cancel','cancel')+button(editor?'Apply to draft':'Save changes','save','','primary'),true);
    $('#link-direction').value=direction;
    render();
  }
  function close(force=false) {
    if(!session) return false;
    if(session.busy&&!force) return true;
    const old=session;session=null;
    if(!force) {$('#overlay').replaceChildren(...old.parent);old.focus?.focus();}
    return true;
  }
  function render() {
    if(!session) return;
    $('#link-add').hidden=session.tab!=='add';$('#link-manage').hidden=session.tab!=='manage';
    document.querySelectorAll('[data-link-action="tab"]').forEach(el=>{el.classList.toggle('active',el.dataset.tab===session.tab);el.setAttribute('aria-pressed',String(el.dataset.tab===session.tab));});
    renderResults();renderExisting();renderReview();
  }
  function candidate(id) {
    const type=$('#link-type').value.trim();
    return session.direction==='incoming'?{source:id,relation:{type,target:session.artifact.id}}:{source:session.artifact.id,relation:{type,target:id}};
  }
  function duplicate(id) {
    const {source,relation}=candidate(id);
    return relationList(source).some(r=>key(r)===key(relation));
  }
  function renderResults() {
    const s=session, query=$('#link-query').value.trim().toLowerCase(), type=$('#link-item-type').value, discipline=$('#link-discipline').value;
    const candidates=[...s.artifacts.values()].filter(a=>a.id!==s.artifact.id&&(!query||(a.id+' '+a.title).toLowerCase().includes(query))&&(!type||a.type===type)&&(!discipline||a.meta.discipline===discipline)).sort((a,b)=>a.id.localeCompare(b.id));
    const pages=Math.max(1,Math.ceil(candidates.length/20));s.page=Math.min(s.page,pages-1);
    $('#link-type-help').textContent=descriptions[$('#link-type').value.trim()]||'Custom relationship type; use a clear name such as supports.';
    $('#link-direction-preview').textContent=s.direction==='incoming'?`Selected source items → ${$('#link-type').value.trim()||'relationship'} → ${s.artifact.id}`:`${s.artifact.id} → ${$('#link-type').value.trim()||'relationship'} → selected target items`;
    // A relationship/direction change may make a previous selection already linked.
    for(const id of s.selected) if(duplicate(id)) s.selected.delete(id);
    $('#link-results').innerHTML=candidates.slice(s.page*20,s.page*20+20).map(a=>{
      const exists=duplicate(a.id);
      return `<label class="link-result ${exists?'is-linked':''}"><input type="checkbox" data-link-select="${esc(a.id)}" ${s.selected.has(a.id)?'checked':''} ${exists?'disabled':''}><span><strong>${esc(a.title)}</strong><small><code>${esc(a.id)}</code> · ${esc(a.type)}${a.meta.discipline?' · '+esc(a.meta.discipline):''}</small></span>${exists?'<span class="badge">Already linked</span>':''}</label>`;
    }).join('')||'<p class="field-help">No matching items. Try another search or filter.</p>';
    $('#link-pagination').innerHTML=pagination('page',s.page,pages,candidates.length);
    $('#link-selected').innerHTML=`<strong>${s.selected.size} selected</strong><div class="link-selection-chips">${[...s.selected].map(id=>button(esc(id)+' ×','unselect',`data-id="${esc(id)}" aria-label="Unselect ${esc(id)}"`)).join('')}</div>`;
    $('[data-link-action="stage"]').disabled=!s.selected.size||!$('#link-type').value.trim();
  }
  function pagination(action,page,pages,total) {
    return `<span>${total} items · Page ${page+1} of ${pages}</span><div>${button('Previous',action,`data-page="${page-1}" ${page===0?'disabled':''}`)}${button('Next',action,`data-page="${page+1}" ${page>=pages-1?'disabled':''}`)}</div>`;
  }
  function adjacent() {
    const list=[];
    for(const [id] of session.artifacts) relationList(id).forEach((relation,index)=>{
      if(id===session.artifact.id||relation.target===session.artifact.id) list.push({source:id,relation,index,direction:id===session.artifact.id?'outgoing':'incoming'});
    });
    return list;
  }
  function renderExisting() {
    const query=$('#link-manage-query').value.trim().toLowerCase(), direction=$('#link-manage-direction').value;
    const items=adjacent().filter(e=>(!direction||e.direction===direction)&&(!query||[e.source,session.artifacts.get(e.source)?.title,e.relation.target,session.artifacts.get(e.relation.target)?.title,e.relation.resource,e.relation.type].join(' ').toLowerCase().includes(query)));
    const pages=Math.max(1,Math.ceil(items.length/15));session.managePage=Math.min(session.managePage,pages-1);
    $('#link-existing').innerHTML=items.slice(session.managePage*15,session.managePage*15+15).map(e=>`<div class="link-existing-row"><div><small class="${e.direction}">${e.direction==='incoming'?'← Incoming':'→ Outgoing'}</small><div class="link-endpoints"><code title="${esc(session.artifacts.get(e.source)?.title)}">${esc(e.source)}</code><span>→</span><code title="${esc(session.artifacts.get(e.relation.target)?.title||e.relation.resource)}">${esc(e.relation.target||e.relation.resource)}</code></div></div><label><span class="sr-only">Relationship from ${esc(e.source)} to ${esc(e.relation.target||e.relation.resource)}</span><input class="input" list="link-types" value="${esc(e.relation.type)}" data-link-retype="${e.index}" data-source="${esc(e.source)}"></label>${button('Remove','remove',`data-source="${esc(e.source)}" data-index="${e.index}" aria-label="Remove ${esc(e.relation.type)} link from ${esc(e.source)} to ${esc(e.relation.target||e.relation.resource)}"`,'ghost danger')}</div>`).join('')||'<p class="field-help">No links match this view.</p>';
    $('#link-manage-pagination').innerHTML=pagination('manage-page',session.managePage,pages,items.length);
  }
  function renderReview() {
    const pending=changes(), rows=[];
    // Compare as multisets so duplicate entries remain individually removable.
    for(const [id,after] of pending) {
      const remaining=clone(after);
      for(const r of session.original.get(id)||[]) {
        const index=remaining.findIndex(n=>same(r,n));
        if(index>=0) remaining.splice(index,1);else rows.push({id,r,kind:'Remove'});
      }
      for(const r of remaining) rows.push({id,r,kind:'Add'});
    }
    $('#link-review-title').textContent=rows.length?`${rows.length} pending link changes · ${pending.length} source item${pending.length===1?'':'s'}`:'No pending changes';
    $('#link-review-list').innerHTML=rows.map(({id,r,kind})=>`<div class="link-review-row"><span class="badge ${kind==='Add'?'added':'removed'}">${kind}</span><code>${esc(id)}</code><span>→ ${esc(r.type)} →</span><code>${esc(r.target||r.resource)}</code></div>`).join('');
    // Applying an unchanged session is useful after undoing earlier draft changes.
    $('[data-link-action="save"]').disabled=session.busy||(!session.editor&&!pending.length);
  }
  async function act(el) {
    if(!session||session.busy) return;
    const s=session, action=el.dataset.linkAction;
    if(action==='cancel'){close();return;}
    if(action==='tab')s.tab=el.dataset.tab;
    if(action==='page')s.page=Number(el.dataset.page);
    if(action==='manage-page')s.managePage=Number(el.dataset.page);
    if(action==='unselect')s.selected.delete(el.dataset.id);
    if(action==='stage') {
      if(!$('#link-type').value.trim())throw new Error('Choose a relationship first.');
      for(const id of s.selected) {
        if(duplicate(id))continue;
        const {source,relation}=candidate(id);setRelations(source,[...relationList(source),relation]);
      }
      s.selected.clear();
    }
    if(action==='remove') {
      const list=[...relationList(el.dataset.source)];list.splice(Number(el.dataset.index),1);setRelations(el.dataset.source,list);
    }
    if(action==='save') {
      if(s.selected.size)throw new Error('Click Add selected links, or clear the selection before saving.');
      const pending=updates();
      if(s.editor) {
        const relations=clone(relationList(s.artifact.id));close();s.onApply(relations,pending.filter(u=>u.id!==s.artifact.id));return;
      }
      s.busy=true;
      // Freeze the dialog during the transaction; Escape cannot discard a save in flight.
      $('#overlay').querySelectorAll('input,select,button').forEach(e=>e.disabled=true);
      try {if(getSnapshot().root!==s.project)throw new Error('The active project changed. Reopen the link editor before saving.');await api('links',{workspace:s.workspace,updates:pending});}
      catch(error) {s.busy=false;$('#overlay').querySelectorAll('input,select,button').forEach(e=>e.disabled=false);render();throw error;}
      close(true);await onSaved(s.artifact.id);return;
    }
    render();
  }
  document.addEventListener('click',event=>{
    const el=event.target.closest('[data-link-action]');if(!el||el.disabled)return;
    act(el).catch(e=>formError(e.message));
  });
  document.addEventListener('input',event=>{
    if(!session)return;
    if(['link-query','link-type'].includes(event.target.id)){session.page=0;renderResults();}
    if(event.target.id==='link-manage-query'){session.managePage=0;renderExisting();}
  });
  document.addEventListener('change',event=>{
    if(!session)return;
    const el=event.target;
    if(el.hasAttribute('data-link-select')) {el.checked?session.selected.add(el.dataset.linkSelect):session.selected.delete(el.dataset.linkSelect);renderResults();$(`[data-link-select="${CSS.escape(el.dataset.linkSelect)}"]`)?.focus();}
    if(['link-direction','link-item-type','link-discipline'].includes(el.id)){session.direction=$('#link-direction').value;session.page=0;renderResults();}
    if(el.id==='link-manage-direction'){session.managePage=0;renderExisting();}
    if(el.hasAttribute('data-link-retype')) {
      const type=el.value.trim(), source=el.dataset.source, index=Number(el.dataset.linkRetype), list=[...relationList(source)], changed={...list[index],type};
      if(!type||list.some((r,i)=>i!==index&&key(r)===key(changed))) {
        el.value=list[index].type;formError(!type?'A relationship type is required.':'That link already exists.');return;
      }
      list[index]=changed;setRelations(source,list);renderReview();renderResults();
    }
  });
  return {open,close,get active(){return Boolean(session);}};
}
