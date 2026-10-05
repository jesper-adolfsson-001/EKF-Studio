import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from ekf.core import Problem, Repository
from ekf.github import GitHub, github_name
from ekf.projects import Projects
from ekf.seed import init_repo
from ekf.server import Application


class LocalGitHub(GitHub):
    """A simulated GitHub API over real, isolated bare Git repositories."""
    def __init__(self,state,remote_folder):
        super().__init__(state); self.remotes=remote_folder; self.metadata={}; self.created=[]

    def api(self,endpoint,method='GET',data=None):
        if endpoint=='user': return {'login':'gardener'}
        if endpoint=='user/orgs?per_page=100': return []
        if method=='POST':
            name='gardener/'+data['name']; self.created.append(data)
            root=self.remotes/(name+'.git'); root.parent.mkdir(parents=True,exist_ok=True)
            subprocess.run(['git','init','--bare','-b','main',str(root)],check=True,capture_output=True)
            self.metadata[name]={'full_name':name,'private':data['private'],'default_branch':'main','permissions':{'push':True}}
            return self.metadata[name]
        if endpoint.startswith('repos/'): return self.metadata[endpoint[6:]]
        if endpoint.startswith('user/repos?'): return list(self.metadata.values())
        raise AssertionError(endpoint)

    def git(self,root,*args,check=True):
        result=subprocess.run(['git','-c','core.hooksPath=/dev/null','-c','protocol.file.allow=always',
                               '-c',f'url.{self.remotes}/.insteadOf=https://github.com/',*args],cwd=root,capture_output=True,text=True)
        if result.returncode and check: raise Problem('Test Git transfer failed: '+result.stderr,409)
        return result.stdout


class ProjectTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.folder=Path(self.temp.name)/'projects'; self.catalog=Projects(self.folder)

    def tearDown(self): self.temp.cleanup()

    def test_create_discover_select_and_forget_preserve_files(self):
        identity=self.catalog.create('My garden','MyGarden'); root=self.catalog.root(identity)
        repo=Repository(root)
        self.assertTrue(repo.clean()); self.assertEqual(repo.snapshot()['artifacts'],[])
        self.assertEqual(repo.snapshot()['manifest']['system']['title'],'My garden')
        self.catalog.select(identity)
        self.assertEqual(Projects(self.folder).data['selected'],identity)
        self.catalog.select(None); self.catalog.forget(identity)
        self.assertEqual(self.catalog.list(),[]); self.assertTrue((root/'ekf.yaml').exists())
        self.assertEqual(self.catalog.register(root),identity)
        self.assertEqual(len(self.catalog.list()),1)

    def test_folder_collisions_and_path_traversal_never_overwrite(self):
        identity=self.catalog.create('Garden','Garden'); original=(self.catalog.root(identity)/'ekf.yaml').read_bytes()
        for name in ('Garden','../elsewhere','/tmp/outside','hidden/.folder','NUL','ending.'):
            with self.subTest(name=name),self.assertRaises(Problem): self.catalog.create('Other',name)
        self.assertEqual((self.catalog.root(identity)/'ekf.yaml').read_bytes(),original)

    def test_project_switch_preserves_drafts_and_rejects_stale_context(self):
        a=self.catalog.create('A','A'); b=self.catalog.create('B','B')
        app=Application(Repository(self.catalog.root(a)),self.folder)
        app.repo.workflow.start('A draft'); draft=app.repo.workflow.active; first_token=app.agent_token
        app.open_project(b)
        self.assertIsNone(app.repo.workflow.active)
        self.assertNotEqual(app.agent_token,first_token)
        with self.assertRaises(Problem): app.project_context(a)
        app.open_project(a); self.assertEqual(app.repo.workflow.active,draft)
        restarted=Application(projects_folder=self.folder)
        self.assertEqual(restarted.repo.project_root,self.catalog.root(a))
        self.assertEqual(restarted.repo.workflow.active,draft)

    def test_publish_uploads_main_only_and_clone_keeps_projects_separate(self):
        identity=self.catalog.create('Garden','Garden'); repo=Repository(self.catalog.root(identity)); original=repo.head()
        repo.workflow.save_files([{'path':'draft-only.txt','content':'not approved'}])
        hub=LocalGitHub(self.catalog.state,Path(self.temp.name)/'remotes')
        with self.assertRaises(Problem): hub.publish(repo,'gardener','Garden','unspecified')
        self.assertEqual(hub.created,[])
        result=hub.publish(repo,'gardener','Garden','private')
        self.assertTrue(result['private']); self.assertTrue(hub.created[0]['private'])
        remote=hub.remotes/'gardener/Garden.git'
        self.assertEqual(hub.git(remote,'rev-parse','main').strip(),original)
        self.assertNotIn('draft-only.txt',hub.git(remote,'ls-tree','--name-only','main'))
        self.assertNotIn('.ekf',hub.git(remote,'ls-tree','--name-only','main'))
        clone=hub.clone(self.catalog,'gardener/Garden','OtherCopy')
        copied=Repository(self.catalog.root(clone['project']))
        self.assertEqual(copied.head(),original); self.assertIsNone(copied.workflow.active)
        self.assertNotEqual(copied.project_root,repo.project_root)
        self.assertIsNotNone(repo.workflow.active)

    def test_connect_refuses_unrelated_history_and_publication_is_explicit(self):
        a=self.catalog.create('A','A'); b=self.catalog.create('B','B')
        first=Repository(self.catalog.root(a)); second=Repository(self.catalog.root(b))
        hub=LocalGitHub(self.catalog.state,Path(self.temp.name)/'remotes')
        result=hub.publish(first,'gardener','Shared','public')
        self.assertFalse(result['private']); self.assertFalse(hub.created[0]['private'])
        remote=hub.remotes/'gardener/Shared.git'; before=hub.git(remote,'rev-parse','main')
        with self.assertRaises(Problem): hub.connect(second,'gardener/Shared')
        self.assertIsNone(hub.remote(second)); self.assertEqual(hub.git(remote,'rev-parse','main'),before)
        with self.assertRaises(Problem): hub.connect(second,'gardener/Shared',upload=True)

    def test_existing_empty_repository_can_receive_local_main(self):
        identity=self.catalog.create('Garden','Garden'); repo=Repository(self.catalog.root(identity))
        hub=LocalGitHub(self.catalog.state,Path(self.temp.name)/'remotes')
        hub.api('user/repos','POST',{'name':'Empty','private':True})
        with self.assertRaises(Problem): hub.connect(repo,'gardener/Empty')
        hub.connect(repo,'gardener/Empty',upload=True)
        self.assertEqual(hub.remote(repo),'gardener/Empty')
        self.assertEqual(hub.git(hub.remotes/'gardener/Empty.git','rev-parse','main').strip(),repo.head())

    def test_failed_upload_keeps_created_remote_and_local_work(self):
        identity=self.catalog.create('Garden','Garden'); repo=Repository(self.catalog.root(identity)); before=repo.head()
        hub=LocalGitHub(self.catalog.state,Path(self.temp.name)/'remotes')
        with patch.object(hub,'connect',side_effect=Problem('Offline')),self.assertRaisesRegex(Problem,'was created'):
            hub.publish(repo,'gardener','Retry','private')
        self.assertTrue((hub.remotes/'gardener/Retry.git').is_dir()); self.assertEqual(repo.head(),before)
        hub.connect(repo,'gardener/Retry',upload=True)
        self.assertEqual(hub.remote(repo),'gardener/Retry')

    def test_runtime_history_cannot_be_published(self):
        identity=self.catalog.create('Garden','Garden'); repo=Repository(self.catalog.root(identity))
        (repo.state/'example-token').write_text('not a real credential')
        repo.git('add','-f','.ekf/example-token'); repo.git('commit','-m','Bad runtime file')
        hub=LocalGitHub(self.catalog.state,Path(self.temp.name)/'remotes')
        with self.assertRaisesRegex(Problem,'runtime files'): hub.publish(repo,'gardener','NoSecrets','public')
        self.assertEqual(hub.created,[])

    def test_repository_urls_are_limited_to_github_without_embedded_credentials(self):
        self.assertEqual(github_name('https://github.com/gardener/Garden.git'),'gardener/Garden')
        for value in ('https://token@github.com/a/b','https://elsewhere/a/b','../project','a/..','--upload-pack=bad','https://github.com/a/b?token=x'):
            with self.subTest(value=value),self.assertRaises(Problem): github_name(value)

    def test_helper_download_verifies_archive_before_installing(self):
        hub=GitHub(self.catalog.state); archive=io.BytesIO()
        with tarfile.open(fileobj=archive,mode='w:gz') as bundle:
            member=tarfile.TarInfo('gh_1.0.0_linux_amd64/bin/gh'); payload=b'fixture helper';member.size=len(payload)
            bundle.addfile(member,io.BytesIO(payload))
        content=archive.getvalue(); url='https://github.com/cli/cli/releases/download/v1.0.0/gh_1.0.0_linux_amd64.tar.gz'
        release={'assets':[{'name':'gh_1.0.0_linux_amd64.tar.gz','browser_download_url':url,'digest':'sha256:'+hashlib.sha256(content).hexdigest()}]}
        with patch.object(hub,'executable',return_value=None),patch('ekf.github.platform.system',return_value='Linux'),patch('ekf.github.platform.machine',return_value='x86_64'):
            with patch.object(hub,'download',side_effect=[json.dumps(release).encode(),b'corrupt']),self.assertRaises(Problem): hub.install(lambda **kw:None)
            self.assertFalse(hub.binary.exists())
            with patch.object(hub,'download',side_effect=[json.dumps(release).encode(),content]): hub.install(lambda **kw:None)
            self.assertEqual(hub.binary.read_bytes(),payload)

    def test_device_login_reports_only_the_code_and_account(self):
        hub=GitHub(self.catalog.state)
        hub.binary.write_text('#!/usr/bin/env python3\nimport sys,json\nif "--help" in sys.argv: print("--git-protocol --web --clipboard")\nelif sys.argv[1]=="auth":\n print("First copy your one-time code: ABCD-1234",flush=True)\n input()\nelse: print(json.dumps({"login":"gardener"}))\n')
        hub.binary.chmod(0o700); updates=[]
        self.assertEqual(hub.sign_in(lambda **values:updates.append(values)),{'login':'gardener'})
        self.assertTrue(any(x.get('code')=='ABCD-1234' for x in updates))
        self.assertIsNone(hub.login)

    def test_old_installed_cli_is_replaced_with_compatible_helper(self):
        hub=GitHub(self.catalog.state); archive=io.BytesIO()
        payload=b'#!/bin/sh\necho "--git-protocol --web --clipboard"\n'
        with tarfile.open(fileobj=archive,mode='w:gz') as bundle:
            member=tarfile.TarInfo('gh_fixture/bin/gh'); member.size=len(payload)
            bundle.addfile(member,io.BytesIO(payload))
        content=archive.getvalue()
        release={'assets':[{'name':'gh_1.0.0_linux_amd64.tar.gz','browser_download_url':'https://github.com/cli/cli/releases/download/v1.0.0/gh_1.0.0_linux_amd64.tar.gz','digest':'sha256:'+hashlib.sha256(content).hexdigest()}]}
        old=Path(self.temp.name)/'old-gh'
        old.write_text('#!/bin/sh\necho "--hostname --web --with-token"\n'); old.chmod(0o700)
        with patch('ekf.github.shutil.which',return_value=str(old)),patch('ekf.github.platform.system',return_value='Linux'),patch('ekf.github.platform.machine',return_value='x86_64'),patch.object(hub,'download',side_effect=[json.dumps(release).encode(),content]) as download:
            self.assertFalse(hub.supports_web_login())
            hub.install(lambda **values:None)
            self.assertTrue(hub.supports_web_login())
            self.assertEqual(hub.executable(),str(hub.binary))
            hub.install(lambda **values:None)
            self.assertEqual(download.call_count,2)
        self.assertIn('--with-token',old.read_text())

    def test_clipboard_login_message_still_displays_code(self):
        hub=GitHub(self.catalog.state)
        hub.binary.write_text('#!/usr/bin/env python3\nimport sys,json\nif "--help" in sys.argv: print("--git-protocol --web --clipboard")\nelif sys.argv[1]=="auth":\n assert "--clipboard=false" in sys.argv\n print("! One-time code (ABCD-1234) copied to clipboard",flush=True)\n input()\nelse: print(json.dumps({"login":"gardener"}))\n')
        hub.binary.chmod(0o700); updates=[]
        self.assertEqual(hub.sign_in(lambda **values:updates.append(values)),{'login':'gardener'})
        self.assertTrue(any(value.get('code')=='ABCD-1234' for value in updates))

    def test_login_failure_messages_are_specific_without_exposing_output(self):
        for output,code,expected in [('unknown flag: --git-protocol',1,'compatible helper'),('expired_token',1,'expired'),('access_denied',1,'declined'),('dial tcp: no such host',1,'internet or proxy'),('x509: certificate signed by unknown authority',1,'certificate'),('permission denied',1,'writable'),('',-15,'cancelled')]:
            self.assertIn(expected,GitHub.login_error(output,code,False))
        self.assertNotIn('ghp_secret',GitHub.login_error('unrecognized failure ghp_secret',1,False))


if __name__=='__main__': unittest.main()
