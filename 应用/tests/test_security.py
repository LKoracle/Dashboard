import os, sys
from pathlib import Path
from contextlib import contextmanager
import pytest
from fastapi.testclient import TestClient
os.environ.setdefault('SESSION_SECRET','test-only-secret-not-for-deployment-123456789')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app as module

@pytest.fixture
def client():
    return TestClient(module.app,base_url='https://129.226.194.82')

def test_pages_and_data_require_login(client):
    for path in ['/dashboard/','/dashboard/settings/menus']:
        r=client.get(path,follow_redirects=False)
        assert r.status_code==303 and r.headers['location']=='/dashboard/login'
    for path in ['/me','/menus']:
        assert client.get('/dashboard/api'+path).status_code==401
    assert client.patch('/dashboard/api/menus/1',json={'is_enabled':False,'row_version':1}).status_code==401

def test_login_page_and_headers(client):
    r=client.get('/dashboard/login')
    assert r.status_code==200 and '用户 ID' in r.text
    assert 'no-store' in r.headers['cache-control']
    assert "frame-ancestors 'none'" in r.headers['content-security-policy']
    assert 'max-age' in r.headers['strict-transport-security']

def test_login_requires_trusted_origin(client):
    for origin in [None,'https://evil.example']:
        headers={'origin':origin} if origin else {}
        r=client.post('/dashboard/api/login',json={'login_id':'admin','password':'wrong'},headers=headers)
        assert r.status_code==403

def test_csrf_and_permissions_enforced(client,monkeypatch):
    monkeypatch.setattr(module,'actor',lambda r:{'id':1,'is_super':1})
    for headers in [{},{'origin':module.ORIGIN},{'origin':'https://evil.example','x-csrf-token':module.csrf('')}]:
        assert client.patch('/dashboard/api/menus/1',json={'is_enabled':False,'row_version':1},headers=headers).status_code==403
    monkeypatch.setattr(module,'check_permission',lambda u,a:(_ for _ in ()).throw(module.HTTPException(403,'denied')))
    assert client.get('/dashboard/api/menus').status_code==403

def test_update_validation(client,monkeypatch):
    monkeypatch.setattr(module,'actor',lambda r:{'id':1,'is_super':1})
    for payload in [{'is_enabled':'false','row_version':1},{'is_enabled':False,'row_version':0}]:
        assert client.patch('/dashboard/api/menus/1',json=payload).status_code==422

def test_conflict_missing_and_audit(client,monkeypatch):
    monkeypatch.setattr(module,'actor',lambda r:{'id':1,'is_super':1})
    monkeypatch.setattr(module,'mutation',lambda r:None)
    class Cursor:
        def __init__(self):
            self.row={'id':1,'code':'home','is_enabled':1,'row_version':2}
            self.statements=[]
        def execute(self,sql,args):self.statements.append((sql,args))
        def fetchone(self):return self.row
    c=Cursor()
    @contextmanager
    def db():yield c
    monkeypatch.setattr(module,'database',db)
    assert client.patch('/dashboard/api/menus/1',json={'is_enabled':False,'row_version':1}).status_code==409
    assert len(c.statements)==1
    c.row=None
    assert client.patch('/dashboard/api/menus/1',json={'is_enabled':False,'row_version':2}).status_code==404
    c.row={'id':1,'code':'home','is_enabled':1,'row_version':2}
    r=client.patch('/dashboard/api/menus/1',json={'is_enabled':False,'row_version':2})
    assert r.status_code==200 and r.json()['row_version']==3
    assert any('INSERT INTO audit_log' in s for s,a in c.statements)

def test_throttle_bounds():
    key=('test','one')
    module._attempts.clear()
    for _ in range(10):module.throttle(key)
    with pytest.raises(module.HTTPException) as e:module.throttle(key)
    assert e.value.status_code==429

def test_hash_and_csrf():
    value=module.ph.hash('test-password')
    assert value.startswith('$argon2id$') and module.ph.verify(value,'test-password')
    assert module.csrf('token1')!=module.csrf('token2')
