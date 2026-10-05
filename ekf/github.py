"""User-initiated GitHub setup using the official CLI and ordinary Git."""
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import threading
from urllib.error import URLError
from urllib.request import Request, urlopen
import zipfile

from .core import Problem, Repository, load_yaml


def github_name(value):
    if not isinstance(value,str): raise Problem('Enter a GitHub repository URL or owner/repository.')
    value=value.strip().removeprefix('https://github.com/').removeprefix('git@github.com:').rstrip('/').removesuffix('.git')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9_.-]{1,100}',value) or value.split('/')[1] in ('.','..'):
        raise Problem('Use a github.com repository, for example https://github.com/your-name/MyGarden.')
    return value


class GitHub:
    def __init__(self, state):
        self.state=Path(state)/'github'; self.state.mkdir(exist_ok=True,mode=0o700)
        self.config=self.state/'account'; self.config.mkdir(exist_ok=True,mode=0o700)
        self.binary=self.state/('gh.exe' if os.name=='nt' else 'gh')
        self.login=None

    def executable(self):
        return str(self.binary) if self.binary.is_file() else shutil.which('gh')

    def supports_web_login(self):
        executable=self.executable()
        if not executable: return False
        try:
            result=subprocess.run([executable,'auth','login','--help'],capture_output=True,text=True,
                                  encoding='utf-8',env=self.env(),timeout=10)
        except (OSError,subprocess.TimeoutExpired):
            return False
        return result.returncode==0 and all(flag in result.stdout for flag in ('--git-protocol','--web','--clipboard'))

    def env(self):
        result={k:v for k,v in os.environ.items() if k not in ('GH_TOKEN','GITHUB_TOKEN','GH_ENTERPRISE_TOKEN','GITHUB_ENTERPRISE_TOKEN','GH_HOST','GH_DEBUG')}
        browser=[sys.executable,'-c','pass']
        result.update(GH_CONFIG_DIR=str(self.config),GH_HOST='github.com',GH_PROMPT_DISABLED='1',GH_NO_UPDATE_NOTIFIER='1',
                      NO_COLOR='1',CLICOLOR='0',GIT_TERMINAL_PROMPT='0',GIT_ASKPASS='',
                      GH_BROWSER=subprocess.list2cmdline(browser) if os.name=='nt' else shlex.join(browser))
        return result

    def run(self, args, payload=None, timeout=45):
        executable=self.executable()
        if not executable: raise Problem('Select Sign in to GitHub to set up the connection first.',409)
        try:
            p=subprocess.run([executable,*args],input=payload,capture_output=True,text=True,encoding='utf-8',env=self.env(),timeout=timeout)
        except subprocess.TimeoutExpired:
            raise Problem('GitHub took too long to respond. Check your connection and try again.',502)
        if p.returncode:
            raise Problem('GitHub could not complete the request. Check your sign-in, repository access and connection.',502)
        return p.stdout

    def api(self, endpoint, method='GET', data=None):
        args=['api','--hostname','github.com','--method',method,endpoint]
        if data is not None: args+=['--input','-']
        return json.loads(self.run(args,json.dumps(data) if data is not None else None) or '{}')

    @staticmethod
    def download(url, limit):
        try:
            with urlopen(Request(url,headers={'User-Agent':'EKF-Studio','Accept':'application/vnd.github+json'}),timeout=60) as response:
                data=response.read(limit+1)
        except (URLError,TimeoutError):
            raise Problem('Could not download the GitHub connection helper. Check your internet connection and retry.',502)
        if len(data)>limit: raise Problem('The GitHub helper download exceeded its size limit.',502)
        return data

    def install(self, progress):
        if self.supports_web_login(): return
        progress(message='Downloading the official GitHub connection helper…')
        system={'Linux':'linux','Windows':'windows','Darwin':'macOS'}.get(platform.system())
        arch={'x86_64':'amd64','AMD64':'amd64','arm64':'arm64','aarch64':'arm64'}.get(platform.machine())
        if not system or not arch: raise Problem('Automatic GitHub setup is unavailable on this platform. Install GitHub CLI, then retry.')
        release=json.loads(self.download('https://api.github.com/repos/cli/cli/releases/latest',4*1024*1024))
        suffix=f'_{system}_{arch}.'+('zip' if system=='windows' else 'tar.gz')
        asset=next((a for a in release['assets'] if a['name'].endswith(suffix)),None)
        if not asset: raise Problem('GitHub has no connection helper for this platform.',502)
        def release_url(a):
            url=a['browser_download_url']
            if not re.fullmatch(r'https://github.com/cli/cli/releases/download/v[0-9.]+/[A-Za-z0-9_.-]+',url):
                raise Problem('GitHub returned an unexpected helper download URL.',502)
            return url
        checksum=asset.get('digest','') or ''
        if not checksum.startswith('sha256:'):
            checks=next((a for a in release['assets'] if a['name'].endswith('_checksums.txt')),None)
            if not checks: raise Problem('The GitHub helper has no checksum to verify.',502)
            content=self.download(release_url(checks),1024*1024).decode()
            checksum='sha256:'+next((line.split()[0] for line in content.splitlines() if len(line.split())==2 and line.split()[1]==asset['name']),'')
        archive=self.download(release_url(asset),100*1024*1024)
        if checksum!='sha256:'+hashlib.sha256(archive).hexdigest(): raise Problem('GitHub helper verification failed. Retry the download.',502)
        if system=='windows':
            with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
                member=next((m for m in bundle.infolist() if m.filename.endswith('bin/gh.exe') and m.file_size<100*1024*1024),None)
                if not member: raise Problem('The GitHub helper archive has no executable.',502)
                binary=bundle.read(member)
        else:
            with tarfile.open(fileobj=io.BytesIO(archive),mode='r:gz') as bundle:
                member=next((m for m in bundle.getmembers() if m.name.endswith('/bin/gh') and m.isfile() and m.size<100*1024*1024),None)
                if not member: raise Problem('The GitHub helper archive has no executable.',502)
                binary=bundle.extractfile(member).read()
        tmp=self.binary.with_suffix('.download'); tmp.write_bytes(binary); tmp.chmod(0o700); tmp.replace(self.binary)

    def sign_in(self, progress):
        self.install(progress)
        progress(message='Starting GitHub sign-in…')
        proc=subprocess.Popen([self.executable(),'auth','login','--hostname','github.com','--git-protocol','https','--web','--clipboard=false'],
                              stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=self.env())
        self.login=proc
        timer=threading.Timer(60,proc.kill); timer.start()
        output=''; shown=False
        try:
            proc.stdin.write(b'\n'); proc.stdin.flush(); proc.stdin.close()
            while True:
                value=proc.stdout.read(1)
                if not value: break
                output=(output+value.decode('utf-8',errors='ignore'))[-4096:]
                plain=re.sub(r'\x1b\[[0-9;]*m','',output)
                match=re.search(r'one-time code(?:\s*:\s*|\s*\(\s*)([A-Z0-9]{4}-[A-Z0-9]{4})',plain,re.IGNORECASE)
                if match and not shown:
                    shown=True; timer.cancel()
                    timer=threading.Timer(900,proc.kill); timer.start()
                    progress(message='Enter this code on GitHub to finish signing in.',code=match[1].upper(),url='https://github.com/login/device')
            code=proc.wait()
            if code!=0: raise Problem(self.login_error(output,code,shown),409)
        finally:
            timer.cancel(); proc.stdout.close(); self.login=None
        user=self.api('user'); progress(message='Signed in to GitHub.',code=None)
        return {'login':user['login']}

    @staticmethod
    def login_error(output, code, shown):
        # Classify known failures without exposing CLI output or credentials.
        detail=output.lower()
        if code<0:
            return ('GitHub sign-in was cancelled or timed out. Start sign-in again to get a new code.' if shown else
                    'GitHub sign-in was cancelled or could not obtain a code within one minute. Check the internet or proxy connection on the computer running Studio, then retry.')
        if 'unknown flag' in detail:
            return 'The GitHub helper does not support this sign-in flow. Retry sign-in to download a compatible helper.'
        if any(value in detail for value in ('expired_token','code has expired','token expired')):
            return 'The GitHub sign-in code expired. Start sign-in again to get a new code.'
        if any(value in detail for value in ('access_denied','authorization was denied')):
            return 'GitHub authorization was declined. Retry sign-in and authorize GitHub CLI to continue.'
        if any(value in detail for value in ('x509:','certificate signed by unknown authority','certificate verify failed')):
            return 'The computer running Studio could not verify GitHub’s HTTPS certificate. Check its certificate or company proxy settings, then retry.'
        if any(value in detail for value in ('no such host','connection refused','network is unreachable','timeout','timed out','proxyconnect','connection reset','failed to connect')):
            return 'The computer running Studio could not connect to GitHub. Check its internet or proxy connection, then retry sign-in.'
        if 'permission denied' in detail:
            return 'Studio could not save the GitHub sign-in. Check that its local account folder is writable, then retry.'
        stage='after authorization started' if shown else 'before it could display a sign-in code'
        return f'The GitHub helper stopped {stage} (exit {code}). Retry sign-in; if it repeats, check GitHub access from the computer running Studio.'

    def cancel_login(self):
        if self.login and self.login.poll() is None: self.login.terminate()

    def status(self):
        if not self.executable(): return {'installed':False,'signed_in':False}
        try:
            user=self.api('user')
            return {'installed':True,'signed_in':True,'login':user['login']}
        except Problem:
            return {'installed':True,'signed_in':False}

    def repositories(self, page=1):
        page=max(1,min(int(page),1000))
        repos=self.api(f'user/repos?per_page=30&page={page}&sort=updated&affiliation=owner,collaborator,organization_member')
        return {'repositories':[self.describe(r) for r in repos], 'page':page,'more':len(repos)==30}

    @staticmethod
    def describe(repo):
        name=github_name(repo['full_name'])
        return {'name':name,'url':'https://github.com/'+name,'private':bool(repo['private']),
                'default_branch':repo.get('default_branch') or 'main','can_push':bool(repo.get('permissions',{}).get('push')),
                'archived':bool(repo.get('archived'))}

    def owners(self):
        user=self.api('user'); orgs=self.api('user/orgs?per_page=100')
        return {'owners':[user['login'],*[org['login'] for org in orgs]]}

    def inspect(self, value):
        name=github_name(value)
        info=self.describe(self.api('repos/'+name))
        info['empty']=not self.git(self.state,'ls-remote','--heads','https://github.com/'+name+'.git').strip()
        return info

    def git(self, root, *args, check=True):
        executable=self.executable()
        if not executable: raise Problem('Sign in to GitHub first.',409)
        helper='!'+shlex.quote(executable)+' auth git-credential'
        command=['git','-c','core.hooksPath='+os.devnull,'-c','credential.helper=',
                 '-c','credential.https://github.com.helper='+helper,'-c','protocol.allow=never','-c','protocol.https.allow=always',*args]
        try:
            result=subprocess.run(command,cwd=root,env=self.env(),capture_output=True,text=True,encoding='utf-8',timeout=180)
        except subprocess.TimeoutExpired:
            raise Problem('The GitHub transfer timed out. Your local files are safe; retry when your connection is available.',502)
        if check and result.returncode:
            raise Problem('GitHub transfer failed. Check repository access, branch rules and your connection. No history was overwritten.',409)
        return result.stdout

    def remote(self, repo):
        value=repo.git('config','--get','remote.origin.url',check=False).strip()
        if not value: return None
        try: return github_name(value)
        except Problem: raise Problem('This project already has a non-GitHub origin. Open another project to connect GitHub.',409)

    def connect(self, repo, value, upload=False):
        name=github_name(value); info=self.inspect(name)
        with repo.lock:
            existing=self.remote(repo)
            if existing and existing.lower()!=name.lower(): raise Problem('This project is already connected to another repository.',409)
            repo.workflow.require_main()
            if upload and repo.git('rev-list','--objects',repo.workflow.main_head(),'--','.ekf',cwd=repo.project_root).strip():
                raise Problem('This Git history contains local Studio runtime files. Remove that sensitive history before publishing.',409)
            url='https://github.com/'+name+'.git'
            heads=self.git(repo.project_root,'ls-remote','--heads',url)
            if upload:
                if heads.strip(): raise Problem('This repository already has branches. Connect it without uploading or open it as a separate local project.',409)
                if not info['can_push'] or info['archived']: raise Problem('You need write access to an active GitHub repository to upload.',403)
                self.git(repo.project_root,'push',url,'refs/heads/'+repo.workflow.main+':refs/heads/'+repo.workflow.main)
            elif not heads.strip():
                raise Problem('This GitHub repository is empty. Choose Connect and upload to publish the approved local project.',409)
            else:
                self.git(repo.project_root,'fetch','--no-tags',url,'refs/heads/'+info['default_branch'])
                p=subprocess.run(['git','merge-base',repo.workflow.main_head(),'FETCH_HEAD'],cwd=repo.project_root,capture_output=True)
                if p.returncode: raise Problem('These projects have separate histories. Use Open from GitHub to keep a separate local copy.',409)
            if not existing: repo.git('remote','add','origin',url,cwd=repo.project_root)
            self.git(repo.project_root,'fetch','--no-tags','origin')
            repo.git('config','branch.'+repo.workflow.main+'.remote','origin',cwd=repo.project_root)
            repo.git('config','branch.'+repo.workflow.main+'.merge','refs/heads/'+(repo.workflow.main if upload else info['default_branch']),cwd=repo.project_root)
            return {**info,'uploaded':upload}

    def publish(self, repo, owner, name, visibility, description=''):
        full=github_name(f'{owner}/{name}')
        if visibility not in ('private','public'): raise Problem('Choose Private or Public repository visibility.')
        if not isinstance(description,str) or len(description)>350: raise Problem('Use a description of up to 350 characters.')
        with repo.lock:
            repo.workflow.require_main()
            if repo.git('rev-list','--objects',repo.workflow.main_head(),'--','.ekf',cwd=repo.project_root).strip():
                raise Problem('This Git history contains local Studio runtime files. Remove that sensitive history before publishing.',409)
            if self.remote(repo): raise Problem('This project is already connected. Use its existing repository.',409)
            user=self.api('user')['login']; endpoint='user/repos' if owner.lower()==user.lower() else f'orgs/{owner}/repos'
            self.api(endpoint,'POST',{'name':name,'private':visibility=='private','description':description,'auto_init':False})
            try: return self.connect(repo,full,upload=True)
            except Problem as exc:
                raise Problem(f'GitHub repository {full} was created, but uploading did not finish. Use Connect existing repository with that name to retry. {exc}',409)

    def clone(self, catalog, value, name):
        info=self.inspect(value); target=catalog.target(name)
        try: self.git(catalog.folder,'clone','--no-recurse-submodules','--','https://github.com/'+info['name']+'.git',str(target))
        except Problem:
            raise Problem('The download could not finish. Choose another folder name to retry; any partial files have been kept.',502)
        if not (target/'ekf.yaml').is_file():
            raise Problem(f'The repository was downloaded to {target}, but it is not an EKF project: ekf.yaml is missing. Open an EKF repository, or connect an empty GitHub repository to a new local project.',409)
        manifest=load_yaml((target/'ekf.yaml').read_text(encoding='utf-8'))
        if not isinstance(manifest,dict) or manifest.get('ekf')!='0.1': raise Problem('The downloaded repository has an unsupported EKF manifest.',409)
        Repository(target)
        return {'project':catalog.register(target)}
