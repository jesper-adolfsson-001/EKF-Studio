"""Local project catalog and short-lived background setup jobs."""
import hashlib
import json
from pathlib import Path
import re
import threading
import uuid
import yaml

from .core import Problem, Repository, load_yaml
from .seed import init_repo


class Projects:
    def __init__(self, folder, initial=None):
        self.folder = Path(folder).expanduser().resolve()
        self.folder.mkdir(parents=True, exist_ok=True)
        self.state = self.folder / '.ekf'
        self.state.mkdir(exist_ok=True, mode=0o700)
        self.path = self.state / 'projects.json'
        self.lock = threading.RLock()
        self.data = json.loads(self.path.read_text()) if self.path.exists() else {'projects':{}, 'hidden':[], 'selected':None}
        if initial:
            self.register(initial)
        self.discover()

    @staticmethod
    def identity(path):
        return hashlib.sha256(str(Path(path).resolve()).encode()).hexdigest()[:20]

    def write(self):
        tmp = self.path.with_suffix('.tmp')
        tmp.write_text(json.dumps(self.data, indent=2), encoding='utf-8')
        tmp.replace(self.path)

    def discover(self):
        with self.lock:
            for path in self.folder.iterdir():
                if path.name.startswith('.') or not path.is_dir() or path.is_symlink():
                    continue
                identity = self.identity(path)
                if (path/'.git').exists() and (path/'ekf.yaml').is_file() and identity not in self.data['hidden']:
                    self.data['projects'][identity] = str(path.resolve())
            self.write()

    def register(self, path):
        path = Path(path).expanduser().resolve()
        if not (path/'ekf.yaml').is_file() or not (path/'.git').exists():
            raise Problem('Choose an existing EKF project folder containing ekf.yaml and its own Git repository.')
        with self.lock:
            identity = self.identity(path)
            self.data['projects'][identity] = str(path)
            self.data['hidden'] = [x for x in self.data['hidden'] if x != identity]
            self.write()
            return identity

    def root(self, identity):
        if identity not in self.data['projects']:
            raise Problem('Project not found. Open its local folder again.',404)
        return Path(self.data['projects'][identity])

    def select(self, identity):
        with self.lock:
            if identity is not None:
                self.root(identity)
            self.data['selected'] = identity
            self.write()

    def target(self, name):
        if not isinstance(name,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9 _.-]{0,79}',name) or name.endswith(('.', ' ')):
            raise Problem('Use a folder name starting with a letter or number, up to 80 characters.')
        if name.split('.')[0].upper() in {'CON','PRN','AUX','NUL',*[f'COM{x}' for x in range(1,10)],*[f'LPT{x}' for x in range(1,10)]}:
            raise Problem('Choose another folder name; this one is reserved by Windows.')
        path = self.folder/name
        if path.exists() or path.is_symlink():
            raise Problem('That local folder already exists. Choose another name or open the existing project.',409)
        return path

    def create(self, title, name):
        if not isinstance(title,str) or not title.strip() or len(title)>200:
            raise Problem('Give your project a name of up to 200 characters.')
        with self.lock:
            target = self.target(name)
            init_repo(target, demo=False, title=title.strip())
            return self.register(target)

    def forget(self, identity):
        with self.lock:
            self.root(identity)
            if self.data['selected']==identity:
                raise Problem('Open another project before removing this one from the list.',409)
            self.data['projects'].pop(identity)
            self.data['hidden'].append(identity)
            self.write()

    def list(self):
        self.discover()
        result=[]
        for identity, value in self.data['projects'].items():
            root=Path(value); title=root.name; available=False
            try:
                manifest=load_yaml((root/'ekf.yaml').read_text(encoding='utf-8'))
                title=manifest.get('system',{}).get('title',title)
                available=(root/'.git').exists()
            except (OSError,ValueError,TypeError,AttributeError,yaml.YAMLError):
                pass
            result.append({'id':identity,'title':title,'path':value,'available':available,'active':identity==self.data['selected']})
        return sorted(result,key=lambda p:str(p['title']).lower())


class Jobs:
    def __init__(self):
        self.lock=threading.RLock(); self.items={}; self.active=None

    def start(self, label, action):
        with self.lock:
            if self.active:
                raise Problem('Wait for the current project or GitHub setup to finish.',409)
            identity=uuid.uuid4().hex[:16]
            job={'id':identity,'status':'running','message':label}
            self.items[identity]=job; self.active=identity
            # Keep only recent results. Credentials are never job fields.
            if len(self.items)>30: self.items.pop(next(iter(self.items)))
        def update(**values):
            with self.lock: job.update(values)
        def run():
            try:
                result=action(update)
                update(status='succeeded',result=result)
            except Exception as exc:
                update(status='failed',error=str(exc) if isinstance(exc,Problem) else 'Setup could not finish. Your local project files have been kept. Try again.')
            finally:
                with self.lock: self.active=None
        threading.Thread(target=run,daemon=True).start()
        return self.get(identity)

    def get(self, identity):
        with self.lock:
            if identity not in self.items: raise Problem('Setup task not found.',404)
            return json.loads(json.dumps(self.items[identity]))
