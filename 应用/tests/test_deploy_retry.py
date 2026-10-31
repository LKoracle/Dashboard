"""Exercise the real deployment script against a disposable local fake service."""
import os,shutil,subprocess
from pathlib import Path

def test_failed_release_rolls_back_and_retries_same_git_head(tmp_path):
 root=tmp_path;repo=root/'repo';src=repo/'应用';app=root/'app';bin=root/'bin'
 for d in [src,app,bin,root/'venv/bin']:d.mkdir(parents=True)
 (src/'requirements.txt').write_text('');(app/'requirements.txt').write_text('')
 (src/'app.py').write_text('version="new"');(app/'app.py').write_text('version="old"')
 (root/'deployed-commit').write_text('oldhash\n')
 scripts={'git':'[ "$1" != rev-parse ] || echo newhash','flock':'exit 0','systemctl':'exit 0','curl':'[ -f "$DASHBOARD_ROOT_DIR/healthy" ]'}
 for name,body in scripts.items():
  file=bin/name;file.write_text('#!/bin/sh\n'+body+'\n');file.chmod(0o755)
 for name in ['python','pip']:
  file=root/'venv/bin'/name;file.write_text('#!/bin/sh\nexit 0\n');file.chmod(0o755)
 script=Path(__file__).resolve().parents[2]/'部署/deploy-pull.sh'
 env={**os.environ,'PATH':str(bin)+':'+os.environ['PATH'],'DASHBOARD_ROOT_DIR':str(root),'DASHBOARD_REPO_DIR':str(repo),'DASHBOARD_APP_DIR':str(app),'DASHBOARD_HEALTH_ATTEMPTS':'1','DASHBOARD_HEALTH_DELAY':'0'}
 first=subprocess.run(['bash',str(script)],env=env,capture_output=True,text=True)
 assert first.returncode==1,first.stderr
 assert (app/'app.py').read_text()=='version="old"'
 assert (root/'deployed-commit').read_text().strip()=='oldhash'
 (root/'healthy').touch()
 second=subprocess.run(['bash',str(script)],env=env,capture_output=True,text=True)
 assert second.returncode==0,second.stderr
 assert (app/'app.py').read_text()=='version="new"'
 assert (root/'deployed-commit').read_text().strip()=='newhash'
 third=subprocess.run(['bash',str(script)],env=env,capture_output=True,text=True)
 assert third.returncode==0
