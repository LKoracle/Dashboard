import os,sys
from pathlib import Path
from contextlib import contextmanager
os.environ.setdefault('SESSION_SECRET','local-test-session-secret-with-32-characters')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app as module
import pytest

class Cursor:
 def __init__(self,binding):self.binding=binding
 def execute(self,sql,args=()):self.sql=sql
 def fetchone(self):
  if 'FROM project WHERE' in self.sql:return {'id':1,'is_enabled':True}
  if 'FROM funnel WHERE' in self.sql:return None
  if 'FROM metric_binding b' in self.sql:
   assert 'metric_category' in self.sql
   return self.binding
  raise AssertionError(self.sql)

def binding(**changes):
 return dict(project_id=1,archived_at=None,is_enabled=True,metric_archived=None,category_code='funnel',category_enabled=True,**changes)

def payload():return module.FunnelPayload(project_id=1,name='测试漏斗',steps=[{'step_name':'曝光','binding_id':7}])

def test_funnel_metric_allowed():
 assert module._validate_funnel(Cursor(binding()),payload())==('测试漏斗','测试漏斗')

@pytest.mark.parametrize('category',['coverage','activity','feature',None])
def test_other_types_rejected(category):
 b=binding();b['category_code']=category
 with pytest.raises(module.HTTPException) as e:module._validate_funnel(Cursor(b),payload())
 assert e.value.status_code==400 and '漏斗指标' in e.value.detail

@pytest.mark.parametrize('field,value',[('project_id',2),('category_enabled',False),('is_enabled',False),('archived_at','archived')])
def test_existing_scope_and_enabled_rules(field,value):
 b=binding();b[field]=value
 with pytest.raises(module.HTTPException):module._validate_funnel(Cursor(b),payload())

def test_dropdown_query_limits_type(monkeypatch):
 queries=[]
 class C:
  def execute(self,sql,args=()):queries.append(sql)
  def fetchall(self):return []
 @contextmanager
 def db():yield C()
 monkeypatch.setattr(module,'database',db)
 monkeypatch.setattr(module,'actor',lambda r:{'id':1,'is_super':True})
 monkeypatch.setattr(module,'check_permission',lambda *a:None)
 assert module.list_funnels(None)['options']==[]
 query=next(q for q in queries if 'AS binding_id' in q)
 assert "cat.code='funnel'" in query and 'cat.is_enabled=1' in query

@pytest.mark.parametrize('enabled',[True,False])
def test_enabling_metric_ensures_binding(monkeypatch,enabled):
 ensured=[]
 class C:
  def execute(self,*a):pass
  def fetchone(self):return {'id':7,'code':'T','name':'曝光','project_id':1,'is_enabled':not enabled,'row_version':1}
 @contextmanager
 def db():yield C()
 monkeypatch.setattr(module,'database',db)
 monkeypatch.setattr(module,'actor',lambda r:{'id':1})
 monkeypatch.setattr(module,'check_permission',lambda *a:None)
 monkeypatch.setattr(module,'mutation',lambda *a:None)
 monkeypatch.setattr(module,'require_project',lambda *a,**k:None)
 monkeypatch.setattr(module,'audit',lambda *a:None)
 monkeypatch.setattr(module,'_ensure_funnel_metric_binding',lambda c,mid:ensured.append(mid))
 module.toggle_metric(7,module.MetricSwitch(is_enabled=enabled,row_version=1),None)
 assert ensured==([7] if enabled else [])
