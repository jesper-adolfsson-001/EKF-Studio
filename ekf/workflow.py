"""Single-user proposal workflow, with isolated worktrees and commit-bound checks."""
import copy
import json
from pathlib import Path
import re
import subprocess
import threading
import uuid

from . import core as c


class ChangeWorkflow:
    def __init__(self, repo):
        self.repo = repo
        self.active = None
        self.folder = repo.state / 'proposals'
        self.folder.mkdir(exist_ok=True)
        branches = repo.git('for-each-ref', '--format=%(refname:short)', 'refs/heads').splitlines()
        self.main = 'main' if 'main' in branches else 'master' if 'master' in branches else repo.git('branch', '--show-current').strip()
        if not self.main:
            raise c.Problem('Check out the main project branch before starting Studio.')

    def write(self, proposal):
        target = self.folder / (proposal['id'] + '.json')
        tmp = target.with_suffix('.tmp')
        tmp.write_text(json.dumps(proposal, indent=2), encoding='utf-8')
        tmp.replace(target)

    def records(self):
        return sorted([json.loads(p.read_text(encoding='utf-8')) for p in self.folder.glob('*.json')], key=lambda p:p['created'], reverse=True)

    def record(self, identity):
        if not isinstance(identity, str) or not re.fullmatch(r'[a-f0-9]{12}', identity):
            raise c.Problem('Invalid proposal ID')
        path = self.folder / (identity + '.json')
        if not path.is_file():
            raise c.Problem('Proposal not found', 404)
        return json.loads(path.read_text(encoding='utf-8'))

    def main_head(self):
        return self.repo.git('rev-parse', 'refs/heads/' + self.main).strip()

    def branch_head(self, p):
        return self.repo.git('rev-parse', '--verify', 'refs/heads/' + p['branch']).strip()

    def tree(self, p):
        return self.repo.state / 'worktrees' / p['id']

    def ensure_tree(self, p):
        root = self.tree(p)
        if not root.exists():
            root.parent.mkdir(exist_ok=True)
            self.repo.git('worktree', 'add', str(root), p['branch'])
        if self.repo.git('branch', '--show-current', cwd=root).strip() != p['branch']:
            raise c.Problem('The proposal working folder is on another branch. Restore its branch with Git.', 409)
        return root

    def persist_active(self):
        target = self.repo.state / 'active-change.json'
        tmp = target.with_suffix('.tmp')
        tmp.write_text(json.dumps({'id':self.active}), encoding='utf-8')
        tmp.replace(target)

    def restore(self):
        target = self.repo.state / 'active-change.json'
        if target.exists():
            identity = json.loads(target.read_text()).get('id')
            if identity:
                p = self.record(identity)
                if p['status'] == 'pending':
                    self.repo.root = self.ensure_tree(p)
                    self.active = identity

    def require_main(self):
        r = self.repo
        if r.git('branch', '--show-current', cwd=r.project_root).strip() != self.main:
            raise c.Problem(f'The project folder must stay on {self.main}. Switch it back using Git.', 409)
        if r.git('status', '--porcelain', '--untracked-files=all', cwd=r.project_root).strip():
            raise c.Problem('Main has external changes. Commit or move them before updating or merging a proposal.', 409)

    def start(self, title, actor='human:local', activate=True):
        if not isinstance(title, str) or not title.strip() or len(title) > 200:
            raise c.Problem('Give this change a name of up to 200 characters.')
        with self.repo.lock:
            self.require_main()
            identity = uuid.uuid4().hex[:12]
            p = {'id':identity, 'title':title.strip(), 'created':c.now(), 'actor':actor, 'status':'pending',
                 'base':self.main_head(), 'branch':'change/' + (re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')[:45] or 'edit') + '-' + identity[:6],
                 'checks':None, 'files':[], 'diff':'', 'affected':[], 'findings':[], 'relations_added':[], 'relations_removed':[]}
            p['commit'] = p['base']
            root = self.tree(p)
            root.parent.mkdir(exist_ok=True)
            self.repo.git('worktree', 'add', '-b', p['branch'], str(root), p['base'])
            self.write(p)
            if activate:
                self.switch(identity)
            return self.describe(p)

    def switch(self, identity=None):
        with self.repo.lock:
            if identity:
                p = self.record(identity)
                if p['status'] != 'pending':
                    raise c.Problem('Only an open proposal can be edited.', 409)
                self.repo.root = self.ensure_tree(p)
                self.active = identity
            else:
                self.repo.root = self.repo.project_root
                self.active = None
            self.persist_active()
            return self.context()

    def context(self):
        p = self.record(self.active) if self.active else None
        return {'id':self.active, 'context':self.active or 'main', 'title':p['title'] if p else self.main,
                'main_branch':self.main, 'main_commit':self.main_head(), 'branch':p['branch'] if p else self.main,
                'working_root':str(self.repo.root)}

    def assert_context(self, context):
        if context is not None and context != (self.active or 'main'):
            raise c.Problem('The active proposal changed in another tab. Refresh before saving; your draft was not saved.', 409)

    def conflicts(self, p):
        root = self.tree(p)
        if not root.exists():
            return []
        return sorted(set(self.repo.git('diff', '--name-only', '--diff-filter=U', '-z', cwd=root).strip('\0').split('\0')) - {''})

    def merging(self, root):
        return bool(self.repo.git('rev-parse', '--verify', '-q', 'MERGE_HEAD', cwd=root, check=False).strip())

    def ensure_draft(self, title):
        if not self.active:
            self.start(title[:200])
        p = self.record(self.active)
        if p['status'] != 'pending' or self.conflicts(p) or self.merging(self.repo.root):
            raise c.Problem('Resolve the proposal update before editing more artifacts.', 409)
        if self.repo.git('branch', '--show-current').strip() != p['branch']:
            raise c.Problem('The working branch changed outside Studio. Reopen the proposal.', 409)

    def saved(self):
        if self.active:
            p = self.record(self.active)
            p['checks'] = None
            self.write(self.refresh(p))

    def save_files(self, changes, title='Edit project files'):
        """Human resource/manifest edits accumulate in the active proposal too."""
        if not isinstance(changes,list) or not 1<=len(changes)<=50:
            raise c.Problem('Supply between 1 and 50 file changes.')
        with self.repo.lock:
            if not self.repo.clean(): raise c.Problem('Commit external edits before saving.',409)
            validated_head=self.repo.head()
            prepared=[]; paths=set(); root=self.repo.root
            for change in changes:
                path=change['path']; target=c.safe_path(root,path); content=change.get('content')
                if path in paths: raise c.Problem('Each file can only be edited once.')
                paths.add(path)
                if content is not None and (not isinstance(content,str) or len(content.encode())>c.MAX_FILE):
                    raise c.Problem('Use text under 2 MB, or null to delete a file.')
                old=target.read_bytes() if target.is_file() else None
                if content is None and old is None: raise c.Problem('Cannot delete a missing file.')
                if content is not None and target.suffix.lower()=='.md' and 'assets' not in Path(path).parts:
                    previous=None
                    if old is not None:
                        try: previous=c.parse_artifact(old.decode('utf-8'),path)
                        except (ValueError,UnicodeError): pass
                    if previous:
                        proposed=c.parse_artifact(content,path)
                        if proposed['id']!=previous['id']: raise c.Problem('Preserve existing artifact IDs.')
                if path=='ekf.yaml':
                    value=c.load_yaml(content or '')
                    if not isinstance(value,dict) or value.get('ekf')!='0.1': raise c.Problem('The manifest must declare ekf: "0.1".')
                prepared.append((path,content,old))
            self.ensure_draft(title); root=self.repo.root
            if self.repo.head()!=validated_head or not self.repo.clean():
                raise c.Problem('The working branch changed while preparing this save. Reopen the editor; no changes were saved.',409)
            try:
                for path,content,_ in prepared:
                    target=c.safe_path(root,path)
                    if content is None: target.unlink()
                    else: target.parent.mkdir(parents=True,exist_ok=True); target.write_text(content,encoding='utf-8')
                report=c.analyze(c.scan(root),self.repo.head())
                if not report['graph']: raise c.Problem('The file edits fail EKF validation.')
                self.repo.git('add','--',*sorted(paths))
                if self.repo.git('diff','--cached','--name-only').strip():
                    self.repo.git('commit','-m','human:local: '+title)
            except Exception:
                for path,_,old in prepared:
                    target=c.safe_path(root,path)
                    if old is None: target.unlink(missing_ok=True)
                    else: target.write_bytes(old)
                self.repo.git('reset','--',*sorted(paths),check=False)
                raise
            self.saved()
            return self.describe(self.record(self.active))

    def refresh(self, p):
        r = self.repo
        head = self.branch_head(p)
        base = r.git('merge-base', self.main_head(), head).strip()
        if p.get('diff_base') == base and p.get('commit') == head:
            return p
        left, right = r.snapshot(base), r.snapshot(head)
        a = {x['id']:x for x in left['artifacts']}
        b = {x['id']:x for x in right['artifacts']}
        affected = {key for key in a.keys() | b.keys() if a.get(key,{}).get('hash') != b.get(key,{}).get('hash') or a.get(key,{}).get('path') != b.get(key,{}).get('path')}
        old = {json.dumps(e,sort_keys=True) for e in left['edges']}
        new = {json.dumps(e,sort_keys=True) for e in right['edges']}
        diff = r.git('diff', '--no-ext-diff', '--no-textconv', '--stat', '--patch', base, head, '--', errors='replace')
        p.update(commit=head, diff_base=base,
                 files=r.git('diff', '--name-only', '-z', base, head, '--').strip('\0').split('\0') if base != head else [],
                 diff=diff[:500000], diff_truncated=len(diff)>500000,
                 affected=sorted(affected), findings=right['validation']['findings'],
                 relations_added=[json.loads(e) for e in sorted(new-old)], relations_removed=[json.loads(e) for e in sorted(old-new)])
        p['files'] = [f for f in p['files'] if f]
        return p

    def describe(self, proposal):
        p = copy.deepcopy(proposal)
        if p['status'] != 'pending':
            return {**p, 'merge_ready':False, 'active':False, 'conflicts':[]}
        try:
            p = self.refresh(p)
            main = self.main_head()
            conflicts = self.conflicts(p)
            root = self.tree(p)
            dirty = root.exists() and bool(self.repo.git('status', '--porcelain', '--untracked-files=all', cwd=root).strip())
            checks = p.get('checks') or {}
            fresh = checks.get('main') == main and checks.get('commit') == p['commit'] and checks.get('rules') == 1
            p.update(active=self.active == p['id'], main_commit=main, conflicts=conflicts, dirty=bool(dirty),
                     behind=int(self.repo.git('rev-list', '--count', p['commit'] + '..' + main).strip()),
                     checks_current=fresh, merge_ready=bool(fresh and checks.get('passed') and not dirty and not conflicts and p['files']))
        except c.Problem:
            p.update(unavailable=True, merge_ready=False, active=False, conflicts=[])
        return p

    def list(self):
        return [self.describe(p) for p in self.records()]

    def rename(self, identity, title):
        if not isinstance(title,str) or not title.strip() or len(title)>200:
            raise c.Problem('Give this change a name of up to 200 characters.')
        with self.repo.lock:
            p = self.record(identity)
            if p['status'] != 'pending':
                raise c.Problem('This proposal is archived.',409)
            p['title'] = title.strip()
            self.write(p)
            return self.describe(p)

    def update(self, identity, run_checks=True):
        if not isinstance(run_checks, bool):
            raise c.Problem('Choose whether to run checks after updating.')
        with self.repo.lock:
            p = self.record(identity)
            if p['status'] != 'pending':
                raise c.Problem('This proposal is archived.',409)
            self.require_main()
            root = self.ensure_tree(p)
            if self.conflicts(p):
                return self.describe(p)
            if self.merging(root):
                self.repo.git('commit','-m','Merge main into proposal',cwd=root)
                return self.finish_update(p)
            if self.repo.git('status','--porcelain','--untracked-files=all',cwd=root).strip():
                raise c.Problem('Commit external changes in the proposal before checking it.',409)
            p['checks'] = None
            p['sync_main'] = self.main_head()
            p['update_started'] = {'before':self.branch_head(p), 'main':p['sync_main'], 'run_checks':run_checks}
            self.write(p)
            try:
                self.repo.git('merge','--no-ff','--no-edit','-m','Merge main into proposal',p['sync_main'],cwd=root)
            except c.Problem:
                if self.conflicts(p):
                    return self.describe(p)
                raise
            return self.finish_update(p)

    def finish_update(self, p):
        update = p.pop('update_started', None)
        if update:
            after = self.branch_head(p)
            diff = self.repo.git('diff','--no-ext-diff','--no-textconv',update['before'],after,'--',errors='replace')
            paths = self.repo.git('diff','--name-only','-z',update['before'],after,'--').strip('\0')
            p['last_update'] = {'before':update['before'], 'after':after, 'main':update['main'], 'at':c.now(),
                                'files':paths.split('\0') if paths else [], 'diff':diff[:200000], 'truncated':len(diff)>200000}
        p['checks'] = None
        self.write(self.refresh(p))
        if update is None or update['run_checks']:
            return self.check(p)
        return self.describe(p)

    def check_proposal(self, identity):
        """Check the combined branch without silently merging main into it."""
        with self.repo.lock:
            p = self.record(identity)
            if p['status'] != 'pending':
                raise c.Problem('This proposal is archived.',409)
            self.require_main()
            root = self.ensure_tree(p)
            if self.conflicts(p) or self.merging(root):
                raise c.Problem('Resolve the update from main before checking this proposal.',409)
            if self.repo.git('status','--porcelain','--untracked-files=all',cwd=root).strip():
                raise c.Problem('Commit external changes in the proposal before checking it.',409)
            main, head = self.main_head(), self.branch_head(p)
            if self.repo.git('merge-base',main,head).strip() != main:
                raise c.Problem('Bring in latest main before checking this proposal. Main has newer changes.',409)
            p['sync_main'] = main
            return self.check(p)

    def check(self, p):
        head = self.branch_head(p)
        snap = self.repo.snapshot(head)
        report = copy.deepcopy(snap['validation'])
        if snap['manifest'].get('ekf') != '0.1':
            report['findings'].append({'severity':'error','rule':'manifest','message':'The manifest must declare ekf: "0.1".'})
        self.check_attachments(snap, report['findings'])
        passed = not any(f['severity']=='error' for f in report['findings'])
        main = p.get('sync_main',self.main_head())
        p['checks'] = {'main':main, 'commit':head, 'rules':1, 'at':c.now(), 'passed':passed, 'findings':report['findings']}
        p['base'] = main
        self.write(self.refresh(p))
        return self.describe(p)

    def check_attachments(self, snap, findings):
        from html.parser import HTMLParser
        from urllib.parse import unquote, urlsplit
        import posixpath
        entries = self.repo.revision_tree(snap['head'])
        class Links(HTMLParser):
            def __init__(self):
                super().__init__(); self.urls=[]
            def handle_starttag(self, tag, attrs):
                if tag=='img': self.urls.append(dict(attrs).get('src',''))
        for a in snap['artifacts']:
            parser=Links(); parser.feed(a['body'])
            urls=parser.urls + re.findall(r'!?\[[^\]\n]*\]\(<?([^\s)>]+)',a['body'])
            for url in urls:
                if not url or url.startswith('#') or urlsplit(url).scheme or url.startswith('//'):
                    continue
                path=posixpath.normpath(posixpath.join(posixpath.dirname(a['path']),unquote(urlsplit(url).path)))
                if 'assets' in path.split('/') and path not in entries:
                    findings.append({'severity':'error','rule':'attachment','id':a['id'],'path':path,'message':f'Attachment is missing: {url}'})

    def conflict(self, identity, path):
        p = self.record(identity)
        if path not in self.conflicts(p):
            raise c.Problem('This file is no longer conflicted.',409)
        root=self.tree(p); c.safe_path(root,path)
        stages={}
        for record in self.repo.git('ls-files','-u','-z','--',path,cwd=root).split('\0'):
            if record:
                info,_=record.split('\t',1); mode,oid,stage=info.split(); stages[stage]={'oid':oid,'mode':mode}
        result={'path':path,'commit':self.branch_head(p),'main':p.get('sync_main'),'binary':False}
        for key,stage in [('base','1'),('ours','2'),('main_content','3')]:
            entry=stages.get(stage)
            result[key]=None
            if not entry: continue
            size=int(self.repo.git('cat-file','-s',entry['oid']).strip())
            if size>c.MAX_FILE or entry['mode']=='120000': result['binary']=True; continue
            try:
                value=self.repo.git('cat-file','blob',entry['oid'])
                if '\0' in value: result['binary']=True
                else: result[key]=value
            except UnicodeError: result['binary']=True
        result['ours_exists']='2' in stages; result['main_exists']='3' in stages
        return result

    def resolve(self, identity, path, choice, content=None, expected_commit=None, expected_main=None):
        with self.repo.lock:
            p=self.record(identity); root=self.ensure_tree(p)
            current=self.conflict(identity,path)
            if expected_commit != current['commit'] or expected_main != current['main']:
                raise c.Problem('The conflict changed. Reopen it before resolving.',409)
            target=c.safe_path(root,path)
            if choice in ('ours','main'):
                stage='2' if choice=='ours' else '3'
                records=self.repo.git('ls-files','-u','-z','--',path,cwd=root).split('\0')
                entry=next((s.split('\t',1)[0].split() for s in records if s and s.split('\t',1)[0].split()[2]==stage),None)
                if entry is None: target.unlink(missing_ok=True)
                else:
                    if entry[0] not in ('100644','100755'): raise c.Problem('Resolve this file type using Git in the proposal working folder.')
                    size=int(self.repo.git('cat-file','-s',entry[1]).strip())
                    if size>c.MAX_ASSET: raise c.Problem('Resolve files larger than 10 MB using Git.')
                    blob=subprocess.run(['git','cat-file','blob',entry[1]],cwd=root,capture_output=True,check=True,timeout=30).stdout
                    target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(blob)
                    target.chmod(0o755 if entry[0]=='100755' else 0o644)
            elif choice=='manual':
                if not isinstance(content,str) or len(content.encode())>c.MAX_FILE or re.search(r'^(<<<<<<<|>>>>>>>)( |$)',content,re.M):
                    raise c.Problem('Supply text under 2 MB with all conflict markers resolved.')
                target.parent.mkdir(parents=True,exist_ok=True); target.write_text(content,encoding='utf-8')
            elif choice=='delete': target.unlink(missing_ok=True)
            else: raise c.Problem('Choose proposal, main, edited text, or deletion.')
            self.repo.git('add','--',path,cwd=root)
            p['checks']=None; self.write(p)
            if not self.conflicts(p):
                self.repo.git('commit','-m','Resolve main update conflicts',cwd=root)
                return self.finish_update(p)
            return self.describe(p)

    def accept(self, p):
        r=self.repo; self.require_main()
        described=self.describe(p)
        if not described.get('merge_ready'):
            raise c.Problem('Update from main and pass checks on the latest proposal commit before merging.',409)
        main=p['checks']['main']; head=p['checks']['commit']
        if r.git('merge-base',main,head).strip()!=main:
            raise c.Problem('Merge the current main into this proposal first.',409)
        message=f"human:local: approve {p['title']}\n\nReviewed-commit: {head}\nChecked-main: {main}\nProposal-branch: {p['branch']}"
        tree=r.git('rev-parse',head+'^{tree}').strip()
        merged=r.git('commit-tree',tree,'-p',main,'-p',head,'-m',message).strip()
        # A prepared ref transaction locks BOTH commits until main's files and ref
        # are updated. Git refuses a changed main or proposal, even from external Git.
        proc=subprocess.Popen(['git','-c','core.hooksPath=/dev/null','update-ref','--stdin','-m',message],cwd=r.project_root,
                              stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1)
        timer=threading.Timer(30,proc.kill); timer.start(); materialized=False; committed=False
        try:
            proc.stdin.write(f"start\nupdate refs/heads/{self.main} {merged} {main}\nverify refs/heads/{p['branch']} {head}\nprepare\n"); proc.stdin.flush()
            if proc.stdout.readline().strip()!='start: ok' or proc.stdout.readline().strip()!='prepare: ok':
                raise c.Problem('Main or the proposal changed during approval. Update and check again.',409)
            self.require_main()
            r.git('read-tree','-u','-m',main,merged,cwd=r.project_root); materialized=True
            proc.stdin.write('commit\n'); proc.stdin.flush()
            if proc.stdout.readline().strip()!='commit: ok': raise c.Problem('Could not finish the Git merge transaction.',409)
            materialized=False; committed=True
        finally:
            if not committed and proc.poll() is None:
                try: proc.stdin.write('abort\n'); proc.stdin.flush()
                except BrokenPipeError: pass
            proc.stdin.close()
            proc.wait(timeout=30); timer.cancel()
            proc.stdout.close(); proc.stderr.close()
            if materialized and self.main_head()==main:
                r.git('read-tree','-u','-m',merged,main,cwd=r.project_root)
        return merged

    def decide(self, identity, decision):
        if decision not in ('approve','reject'): raise c.Problem('Choose approve or reject.')
        with self.repo.lock:
            p=self.record(identity)
            if p['status']!='pending': raise c.Problem('This proposal is already archived.',409)
            try: p=self.refresh(p)
            except c.Problem:
                if decision=='approve': raise
            if decision=='approve': p['merged_commit']=self.accept(p)
            p.update(status='approved' if decision=='approve' else 'rejected',reviewed_by='human:local',reviewed_at=c.now())
            self.write(p)
            if self.active==identity: self.switch()
            return self.describe(p)
