export function createProjectController({getState,api,refresh,openProject,modal,close,toast,esc,icon,navigate}) {
  const $=s=>document.querySelector(s);
  const button=(label,action,attrs='',cls='')=>`<button class="btn ${cls}" data-project-action="${action}" ${attrs}>${label}</button>`;
  let busy=false, mode=sessionStorage.getItem('ekf-github-mode')||'clone', pageNumber=1, mainCommit=null, timer=null, jobId=null, selected=null;
  function page() {
    const catalog=getState().projectCatalog;
    return `<div class="page-heading"><div><h1>Your projects</h1><p>Create locally, keep working offline, and connect to GitHub when you are ready.</p></div><div class="heading-actions">${button('New local project','new','','primary')}${button('Open local folder','folder')}${button('Open from GitHub','github','data-mode="clone"')}</div></div>
      <div class="project-location">${icon('layers',16)} New projects are stored in <code>${esc(catalog.folder)}</code></div>
      ${catalog.setup_job?`<div class="notice info">GitHub setup is in progress. ${button('View setup progress','resume',`data-id="${esc(catalog.setup_job)}"`)}</div>`:''}
      <div class="project-cards">${catalog.projects.map(p=>`<article class="panel project-card"><div class="project-card-title">${icon('layers',22)}<h2>${esc(p.title)}</h2>${p.active?'<span class="badge approved">Open</span>':''}</div><p class="project-path">${esc(p.path)}</p><p class="small muted">${p.available?'Local files and Git history': 'Folder unavailable · open its new location to reconnect'}</p><div class="project-card-actions">${button(p.active?'Continue working':'Open project','open',`data-id="${p.id}" ${p.available?'':'disabled'}`,'primary')}${!p.active?button('Remove from list','forget',`data-id="${p.id}"`,'ghost'):button('GitHub setup','github','data-mode="connect"')}</div></article>`).join('')||`<div class="empty project-empty">${icon('layers',36)}<h2>Your first project starts here</h2><p>Create a local project, or bring an existing EKF project from GitHub.</p>${button('Create a project','new','','primary')}</div>`}</div>`;
  }
  function newProject() {
    modal('Create a local project',`<p class="small muted">Studio creates the project folder, initial files and Git history for you. A GitHub connection is optional.</p><div class="form-field"><label for="project-title">Project name</label><input class="input" id="project-title" maxlength="200" placeholder="MyGarden"></div><div class="form-field"><label for="project-folder">Folder name</label><input class="input" id="project-folder" maxlength="80" placeholder="MyGarden"><small>Inside ${esc(getState().projectCatalog.folder)}</small></div>`,button('Create project','create','','primary'));
    let changed=false;$('#project-folder').addEventListener('input',()=>changed=true);
    $('#project-title').addEventListener('input',()=>{if(!changed)$('#project-folder').value=$('#project-title').value.replace(/[^A-Za-z0-9 _.-]/g,'').replace(/^[^A-Za-z0-9]+/,'').slice(0,80);});
  }
  function folder() {
    modal('Open a local project',`<p class="small muted">Enter the folder containing your project's ekf.yaml and Git history. The files stay in their current location.</p><div class="form-field"><label for="project-path">Project folder on this computer</label><input class="input" id="project-path" placeholder="${esc(getState().projectCatalog.folder)}/MyGarden"><small>Use the path seen by the running Studio server, including its WSL path when running in WSL.</small></div>`,button('Open project','open-path','','primary'));
  }
  async function github(nextMode=mode) {
    const catalog=await api('projects');
    if(catalog.setup_job)return resume(catalog.setup_job);
    mode=nextMode; selected=null;sessionStorage.setItem('ekf-github-mode',mode);
    modal('GitHub connection','<p role="status">Checking your GitHub connection…</p>');
    const status=await api('github/status');
    if(!status.signed_in) {
      modal('Connect your GitHub account',`<p>Sign in once, then choose repositories and publish projects from Studio.</p><p class="small muted">${status.installed?'Studio will use the official GitHub CLI to sign in.':'Studio will download and verify the official GitHub CLI helper for this computer.'} Your browser will ask you to authorize GitHub CLI on github.com. Your password stays with GitHub.</p>`,button('Sign in to GitHub','login','','primary'));
      return;
    }
    if(mode==='clone')return repositories(1);
    const connection=await api('github/connection'); mainCommit=connection.commit;
    if(connection.repository){
      modal('Project connected to GitHub',`<p>Your project is connected to <strong>${esc(connection.repository)}</strong>.</p><p><a class="btn primary" href="${esc(connection.url)}" target="_blank" rel="noopener noreferrer">Open repository on GitHub ${icon('right',14)}</a></p><p class="small muted">GitHub setup shares the approved project and its history. Proposal submission and shared approval through GitHub are not connected to Studio's local review buttons yet.</p><p><a href="${esc(connection.url)}/settings/access" target="_blank" rel="noopener noreferrer">Manage repository access on GitHub</a></p>`);
      return;
    }
    if(mode==='publish')return publishForm(status);
    modal('Connect this project',`<p>Choose an existing GitHub repository, or create one for this local project.</p><div class="project-setup-options">${button('Choose existing repository','repositories')}${button('Publish as a new repository','publish-form','','primary')}</div><p class="small muted">Your approved main and its history can be uploaded. Draft proposals remain local.</p>`);
  }
  async function publishForm(status) {
    const data=await api('github/owners');
    const title=getState().data.manifest.system?.title||'MyProject';
    modal('Publish this project on GitHub',`<p class="small muted">Create a GitHub repository and upload your approved main, including its saved history. Draft proposals remain local.</p><div class="form-grid"><div class="form-field"><label for="github-owner">Owner</label><select id="github-owner">${data.owners.map(o=>`<option>${esc(o)}</option>`).join('')}</select></div><div class="form-field"><label for="github-name">Repository name</label><input class="input" id="github-name" maxlength="100" value="${esc(title.replace(/[^A-Za-z0-9_.-]/g,'-'))}"></div></div><div class="form-field"><label for="github-description">Description (optional)</label><input class="input" id="github-description" maxlength="350"></div><fieldset class="github-visibility"><legend>Who can access the repository?</legend><label><input type="radio" name="github-visibility" value="private" checked><span><strong>Private</strong><small>Only you and people you grant access to.</small></span></label><label><input type="radio" name="github-visibility" value="public"><span><strong>Public</strong><small>Anyone can read and copy the published files and history.</small></span></label></fieldset><div id="github-publish-summary" class="notice info">This will create a private repository.</div>`,button('Create private repository & upload','publish','','primary'));
    document.querySelectorAll('[name="github-visibility"]').forEach(input=>input.addEventListener('change',()=>{
      const visibility=$('[name="github-visibility"]:checked').value;
      $('#github-publish-summary').textContent=visibility==='public'?'This will publish the approved files and their history for anyone to read.':'This will create a private repository.';
      $('[data-project-action="publish"]').textContent=`Create ${visibility} repository & upload`;
    }));
  }
  async function repositories(number=1) {
    pageNumber=number;
    const data=await api('github/repositories?page='+number);
    modal(mode==='clone'?'Open a project from GitHub':'Choose an existing repository',`<p class="small muted">${mode==='clone'?'Studio downloads a separate local copy of an existing EKF project.':'Connect this local project to an existing repository. Empty repositories can receive your approved main; repositories with separate histories stay separate.'}</p><div class="form-field"><label for="github-repository">GitHub repository URL or owner/name</label><input class="input" id="github-repository" placeholder="https://github.com/your-name/MyGarden"></div>${button('Use this repository','inspect','','primary')}<h3 class="github-list-title">Your repositories</h3><input class="input" id="github-filter" placeholder="Filter this page…" aria-label="Filter repository page"><div class="github-repositories">${data.repositories.map(r=>`<button class="github-repository" data-project-action="choose" data-repository="${esc(r.name)}"><span>${esc(r.name)}</span><small>${r.private?'Private':'Public'}${r.archived?' · Archived':''}</small></button>`).join('')||'<p class="small muted">No repositories on this page. Paste a repository URL above.</p>'}</div><div class="github-pagination">${button('Previous','repos-prev',number<=1?'disabled':'')}<span>Page ${number}</span>${button('Next','repos-next',data.more?'':'disabled')}</div>`,mode!=='clone'?button('Create a new GitHub repository','publish-form'):'' );
    $('#github-filter').addEventListener('input',event=>document.querySelectorAll('.github-repository').forEach(el=>el.hidden=!el.dataset.repository.toLowerCase().includes(event.target.value.toLowerCase())));
  }
  async function inspect(repository) {
    const info=await api('github/inspect?'+new URLSearchParams({repository})); selected=info;
    const opening=mode==='clone';
    modal(opening?'Download this project':'Review repository connection',`<p><strong>${esc(info.name)}</strong> <span class="badge">${info.private?'Private':'Public'}</span></p><p class="small muted">${info.empty?'This repository is empty.': 'This repository contains existing Git history.'}</p>${opening?`<div class="form-field"><label for="github-local-folder">Local folder name</label><input class="input" id="github-local-folder" value="${esc(info.name.split('/')[1])}"><small>Inside ${esc(getState().projectCatalog.folder)}</small></div>${info.empty?'<p class="notice info">Create a local project first, then connect it to this empty repository.</p>':''}`:`<p>${info.empty?'Your approved main and its history will be uploaded.':'Studio will connect only if this repository shares history with your local project.'}</p>${info.empty&&!info.private?'<p class="notice info">Anyone will be able to read the uploaded files and history.</p>':''}<p class="small muted">Draft proposals remain local.</p>`}`,button('Back','repositories')+button(opening?'Download & open project':info.empty?'Connect and upload':'Connect repository',opening?'clone':'connect',` ${(opening&&info.empty)||(!opening&&info.empty&&(!info.can_push||info.archived))?'disabled':''}`,'primary'));
  }
  async function follow(job, done) {
    clearTimeout(timer);
    jobId=job.id; let previous='';
    const poll=async()=>{
      try {
        const value=await api('setup-jobs?id='+job.id);
        if(jobId!==job.id)return;
        if(value.status==='failed'){jobId=null;modal('Setup needs attention',`<p role="alert">${esc(value.error)}</p>`,button('Back to GitHub setup','github',`data-mode="${mode}"`));return;}
        if(value.status==='succeeded'){jobId=null;await done(value.result);return;}
        const fingerprint=JSON.stringify([value.message,value.code]);
        if(previous!==fingerprint){previous=fingerprint;modal('GitHub setup',`<p role="status">${value.code?'':'<span class="spinner"></span> '}${esc(value.message)}</p>${value.code?`<div class="github-device-code"><code>${esc(value.code)}</code>${button('Copy code','copy',`data-code="${esc(value.code)}"`)}</div><p><a class="btn primary" href="https://github.com/login/device" target="_blank" rel="noopener noreferrer">Continue on GitHub ${icon('right',14)}</a></p><p class="small muted">Authorize GitHub CLI, then return here. Studio will continue automatically.</p>`:''}`,(value.code||/sign.in/i.test(value.message))?button('Cancel sign-in','cancel-login'):'' );}
        timer=setTimeout(poll,1000);
      } catch(error){jobId=null;toast(error.message,true);}
    };
    await poll();
  }
  async function resume(id) {
    await follow({id},async result=>{
      if(result?.project){await openProject(result.project);toast('GitHub project downloaded and opened');}
      else {await refresh();await github(result?.login?mode:'connect');}
    });
  }
  document.addEventListener('click',async event=>{
    const el=event.target.closest('[data-project-action]');if(!el||busy)return;
    event.preventDefault();busy=true;const disabled=el.disabled;el.disabled=true;
    try {
      const action=el.dataset.projectAction;
      if(action==='new')newProject();
      if(action==='folder')folder();
      if(action==='create'){const p=await api('projects/create',{title:$('#project-title').value,folder:$('#project-folder').value});await openProject(p.project,true);toast('Local project created. You can start working now.');}
      if(action==='open')await openProject(el.dataset.id);
      if(action==='open-path'){const p=await api('projects/open',{path:$('#project-path').value});await openProject(p.project,true);}
      if(action==='forget'){await api('projects/forget',{id:el.dataset.id});await refresh();toast('Removed from the list. The project files are still on your computer.');}
      if(action==='github')await github(el.dataset.mode||mode);
      if(action==='resume')await resume(el.dataset.id);
      if(action==='login')await follow(await api('github/login',{}),()=>github());
      if(action==='copy'){await navigator.clipboard.writeText(el.dataset.code);toast('Sign-in code copied');}
      if(action==='cancel-login'){await api('github/login/cancel',{});}
      if(action==='repositories')await repositories(1);
      if(action==='repos-prev')await repositories(pageNumber-1);
      if(action==='repos-next')await repositories(pageNumber+1);
      if(action==='choose')await inspect(el.dataset.repository);
      if(action==='inspect')await inspect($('#github-repository').value);
      if(action==='publish-form'){mode='publish';await github('publish');}
      if(action==='publish')await follow(await api('github/publish',{owner:$('#github-owner').value,name:$('#github-name').value,description:$('#github-description').value,visibility:$('[name="github-visibility"]:checked').value,expected_main:mainCommit}),async()=>{await refresh();await github('connect');toast('Project published on GitHub');});
      if(action==='connect')await follow(await api('github/connect',{repository:selected.name,upload:selected.empty,expected_main:mainCommit}),async()=>{await refresh();await github('connect');toast('GitHub repository connected');});
      if(action==='clone')await follow(await api('github/clone',{repository:selected.name,folder:$('#github-local-folder').value}),async result=>{await openProject(result.project);toast('GitHub project downloaded and opened');});
    } catch(error){const out=$('#form-error');if(out){out.textContent=error.message;out.classList.add('visible');}else toast(error.message,true);}
    finally{busy=false;if(el.isConnected)el.disabled=disabled;}
  });
  return {page};
}
