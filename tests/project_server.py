"""Browser fixture: real application and Git transfers, simulated GitHub account."""
from pathlib import Path
import sys
import time
from http.server import ThreadingHTTPServer

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ekf.core import Repository, Problem
from ekf.seed import init_repo
from ekf.server import Application, make_handler
from test_projects import LocalGitHub

folder=Path(sys.argv[1]); port=int(sys.argv[2]); app=Application(projects_folder=folder)

class BrowserGitHub(LocalGitHub):
    signed_in=False

    def status(self):
        return {'installed':self.signed_in,'signed_in':self.signed_in,'login':'gardener' if self.signed_in else None}

    def sign_in(self,progress):
        progress(message='Enter this code on GitHub to finish signing in.',code='ABCD-1234',url='https://github.com/login/device')
        for _ in range(200):
            if (folder/'.ekf/auth-complete').exists():
                self.signed_in=True;return {'login':'gardener'}
            time.sleep(.1)
        raise Problem('The test sign-in was not completed.')

app.github=BrowserGitHub(app.projects.state,folder.parent/'remotes')
source=folder.parent/'ExistingGarden';init_repo(source,demo=False,title='Existing garden')
app.github.publish(Repository(source),'gardener','ExistingGarden','private')
app.github.api('user/repos','POST',{'name':'EmptyGarden','private':True})
server=ThreadingHTTPServer(('127.0.0.1',port),make_handler(app))
print('EKF Studio: test project manager',flush=True)
try: server.serve_forever()
finally: server.server_close()
