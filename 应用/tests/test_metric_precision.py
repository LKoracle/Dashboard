import os,sys
from pathlib import Path
from contextlib import contextmanager
os.environ.setdefault('SESSION_SECRET','local-test-session-secret-with-32-characters')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app as module
import pytest
from pydantic import ValidationError

@pytest.mark.parametrize('dp',range(6))
def test_supported_precision(dp):
 assert module.MetricPayload(name='测试',category_id=1,project_id=1,decimal_places=dp).decimal_places==dp

@pytest.mark.parametrize('dp',[-1,6,1.5,True,'2',None])
def test_reject_invalid_precision(dp):
 with pytest.raises(ValidationError):module.MetricPayload(name='测试',category_id=1,project_id=1,decimal_places=dp)

@pytest.mark.parametrize('dp',[0,5])
@pytest.mark.parametrize('create',[False,True])
def test_save_and_revision_use_precision(monkeypatch,dp,create):
 calls=[]
 class C:
  lastrowid=101
  def execute(self,sql,args=()):
   assert sql.count('%s')==len(args)
   self.sql=sql;calls.append((sql,args))
  def fetchone(self):
   if 'FOR UPDATE' in self.sql:return dict(id=7,code='T0001',name='测试',name_key='测试',english_name=None,unit='%',definition=None,definition_status='PENDING',category_id=1,project_id=1,decimal_places=1,row_version=1)
   if 'metric_code_prefix' in self.sql:return dict(metric_code_prefix='T',last_sequence=1)
   return {'next':2}
 @contextmanager
 def db():yield C()
 monkeypatch.setattr(module,'database',db)
 monkeypatch.setattr(module,'actor',lambda r:{'id':1})
 monkeypatch.setattr(module,'check_permission',lambda *a:None)
 monkeypatch.setattr(module,'mutation',lambda *a:None)
 monkeypatch.setattr(module,'_validate_metric',lambda *a:'测试')
 monkeypatch.setattr(module,'audit',lambda *a:None)
 data=module.MetricPayload(name='测试',category_id=1,project_id=1,unit='%',decimal_places=dp)
 if create:module.create_metric(data,None)
 else:module.update_metric(7,data,None)
 revision=next(args for sql,args in calls if 'INSERT INTO metric_revision' in sql)
 assert revision[6]==dp
 if create:assert next(args for sql,args in calls if 'INSERT INTO metric(' in sql)[7]==dp
 else:assert next(args for sql,args in calls if 'UPDATE metric SET name=' in sql)[8]==dp

def test_zero_precision_and_fraction_limits():
 metric={'name':'比例','unit':'%','decimal_places':0}
 assert module._validate_value('12',metric)=='12'
 with pytest.raises(module.HTTPException):module._validate_value('12.1',metric)
 metric['decimal_places']=5
 assert module._validate_value('12.12345',metric)=='12.12345'
 with pytest.raises(module.HTTPException):module._validate_value('12.123456',metric)

@pytest.mark.parametrize('unit,expected',[('人',0),('次',0),('%',1),('秒',2),('分钟／次',1)])
def test_unit_default_and_manual_override(unit,expected):
 assert module.MetricPayload(name='测试',category_id=1,project_id=1,unit=unit).decimal_places==expected
 assert module.MetricPayload(name='测试',category_id=1,project_id=1,unit=unit,decimal_places=4).decimal_places==4
