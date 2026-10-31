import os,sys
from pathlib import Path
from contextlib import contextmanager
os.environ.setdefault('SESSION_SECRET','local-test-session-secret-with-32-characters')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app as module
from fastapi.testclient import TestClient
import pytest

@pytest.fixture
def client():return TestClient(module.app)

def test_home_requires_login(client):
 for endpoint in ['/home/projects','/home/data?project_id=1&stat_date=2026-10-20']:
  assert client.get('/dashboard/api'+endpoint).status_code==401

def test_home_permission_and_future_date(client,monkeypatch):
 monkeypatch.setattr(module,'actor',lambda r:{'id':2,'is_super':False})
 monkeypatch.setattr(module,'check_permission',lambda u,a:(_ for _ in ()).throw(module.HTTPException(403)))
 assert client.get('/dashboard/api/home/projects').status_code==403
 monkeypatch.setattr(module,'check_permission',lambda u,a:None)
 assert client.get('/dashboard/api/home/data?project_id=1&stat_date=bad').status_code==400
 assert client.get('/dashboard/api/home/data?project_id=1&stat_date=2099-01-01').status_code==400

def test_project_scope_before_data_read(client,monkeypatch):
 monkeypatch.setattr(module,'actor',lambda r:{'id':2,'is_super':False})
 monkeypatch.setattr(module,'check_permission',lambda u,a:None)
 monkeypatch.setattr(module,'_home_projects',lambda c,u:[{'id':7}])
 class C:
  def execute(self,*a):raise AssertionError('Unauthorized data query')
 @contextmanager
 def db():yield C()
 monkeypatch.setattr(module,'database',db)
 assert client.get('/dashboard/api/home/data?project_id=8&stat_date=2026-10-20').status_code==403

def test_same_role_scope_query():
 class C:
  def execute(self,query,args):
   assert 'rp.role_id=r.id' in query and 'sp.role_id' in query
   assert "pm.code=%s" in query
   assert args==(2,'home.view')
  def fetchall(self):return []
 assert module._home_projects(C(),{'id':2,'is_super':False})==[]

def test_real_values_and_incomplete_funnel(client,monkeypatch):
 from datetime import date
 from decimal import Decimal
 monkeypatch.setattr(module,'actor',lambda r:{'id':1,'is_super':True})
 monkeypatch.setattr(module,'check_permission',lambda u,a:None)
 monkeypatch.setattr(module,'_home_projects',lambda c,u:[{'id':7}])
 class C:
  def execute(self,sql,args):self.sql=sql
  def fetchall(self):
   if 'COUNT(*)' in self.sql:return [{'funnel_id':1,'total':4}]
   if 'FROM funnel_step s' in self.sql:return []
   if 'FROM funnel WHERE' in self.sql:return [{'id':1,'name':'漏斗'}]
   if 'FROM metric_entry e' in self.sql:return [{'metric_id':1,'feature_id':None,'stat_date':date(2026,10,20),'value_number':Decimal('0')}]
   return []
 @contextmanager
 def db():yield C()
 monkeypatch.setattr(module,'database',db)
 d=client.get('/dashboard/api/home/data?project_id=7&stat_date=2026-10-20').json()
 assert d['values'][0]['value']=='0'
 assert d['funnels'][0]['complete_configuration'] is False
