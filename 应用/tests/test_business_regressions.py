import os,sys
from pathlib import Path
from datetime import date
import pytest
from fastapi.testclient import TestClient
os.environ.setdefault('SESSION_SECRET','local-regression-secret-at-least-32-characters')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from regression_db import LocalDB
import app as module

@pytest.fixture
def db(monkeypatch):
 db=LocalDB().seed();monkeypatch.setattr(module,'database',db.database)
 monkeypatch.setattr(module,'_business_today',lambda:date(2026,10,31))
 monkeypatch.setattr(module,'actor',lambda r:{'id':2,'login_id':'operator','display_name':'操作员','is_super':False})
 monkeypatch.setattr(module,'mutation',lambda r:None)
 yield db
 db.connection.close()
@pytest.fixture
def client(db):return TestClient(module.app,base_url='https://129.226.194.82')

def test_reserved_entities_hidden_and_protected(client):
 assert all(r['code']!='super_admin' for r in client.get('/dashboard/api/roles').json()['items'])
 data=client.get('/dashboard/api/users').json()
 assert all(r['login_id']!='admin' for r in data['items'])
 assert all(r['id']!=1 for r in data['roles'])
 assert client.get('/dashboard/api/roles/1').status_code==404
 for method,path,body in [('get','/users/1',None),('put','/users/1',{'login_id':'renamed','display_name':'名字','role_ids':[],'row_version':1}),('patch','/users/1',{'is_enabled':False,'row_version':1}),('post','/users/1/reset-password',None)]:
  kwargs={'json':body} if body is not None else {}
  assert getattr(client,method)('/dashboard/api'+path,**kwargs).status_code==403

def test_cannot_assign_super_role_or_reserved_login(client):
 for method,path,body in [('put','/users/2',{'login_id':'operator','display_name':'操作员','role_ids':[1],'row_version':1}),('post','/users',{'login_id':'newuser','display_name':'新用户','role_ids':[1]}),('post','/users',{'login_id':'ADMIN','display_name':'新用户','role_ids':[]})]:
  assert getattr(client,method)('/dashboard/api'+path,json=body).status_code==403

def test_same_role_and_disabled_role_scope(db):
 with db.database() as c:
  assert {p['id'] for p in module.scoped_projects(c,{'id':2,'is_super':False},'maintain.edit')}=={1}
  assert {p['id'] for p in module.scoped_projects(c,{'id':2,'is_super':False},'maintain.view')}=={1,2}

def test_cross_project_read_write_and_options(client,db):
 # Operator may view B but cannot edit B; disable B view to test direct read denial.
 db.execute('DELETE FROM sys_user_role WHERE user_id=2 AND role_id=3')
 for path in ['/maintain/data?project_id=2&stat_date=2026-10-30','/home/data?project_id=2&stat_date=2026-10-30','/metrics/99','/projects/2']:
  assert client.get('/dashboard/api'+path).status_code==403,path
 data=client.get('/dashboard/api/maintain/bootstrap').json();assert [p['id'] for p in data['projects']]==[1]
 options=client.get('/dashboard/api/funnels').json()['options'];assert all(o['project_id']==1 for o in options)
 assert client.post('/dashboard/api/maintain/data',json={'project_id':2,'stat_date':'2026-10-30','items':[{'metric_id':99,'value':'5'}]}).status_code==403
 assert client.post('/dashboard/api/funnels',json={'project_id':2,'name':'非法','steps':[{'step_name':'曝光','binding_id':99}]}).status_code==403
 assert client.patch('/dashboard/api/funnels/1/enabled',json={'enabled':False,'row_version':1}).status_code==200

def test_navigation_without_menu_management_permission(client,db):
 db.execute('DELETE FROM sys_role_permission WHERE permission_id=?',(db.permissions['menu.view'],))
 assert client.get('/dashboard/api/menus').status_code==403
 nav=client.get('/dashboard/api/navigation');assert nav.status_code==200
 assert 'maintain' in [m['code'] for m in nav.json()['items']]
 assert 'menu' not in [m['code'] for m in nav.json()['items']]
 assert client.get('/dashboard/maintain').status_code==200

def test_features_preserve_ids_and_archive(client,db):
 body={'name':'测试项目A改名','is_enabled':True,'features':['测试功能'],'row_version':1}
 assert client.put('/dashboard/api/projects/1',json=body).status_code==200
 assert db.execute('SELECT id FROM project_feature WHERE name=?',('测试功能',)).fetchone()['id']==1
 body.update(row_version=2,features=[])
 assert client.put('/dashboard/api/projects/1',json=body).status_code==200
 assert db.execute('SELECT archived_at FROM project_feature WHERE id=1').fetchone()['archived_at'] is not None
 assert db.execute('SELECT COUNT(*) FROM metric_entry WHERE feature_id=1').fetchone()[0]==1
 assert client.get('/dashboard/api/projects/1').json()['features']==[]

def test_stale_project_form_rejected(client):
 payload={'name':'测试项目A','features':['测试功能'],'row_version':1}
 assert client.put('/dashboard/api/projects/1',json=payload).status_code==200
 assert client.put('/dashboard/api/projects/1',json=payload).status_code==409

def test_retention_observation_date_mapping_and_completion(client,db):
 items=client.get('/dashboard/api/maintain/data?project_id=1&stat_date=2026-10-23').json()['items']
 assert next(r for r in items if r['metric_id']==31)['value']=='68'
 payload={'project_id':1,'stat_date':'2026-10-30','items':[{'metric_id':31,'value':'70.5'}]}
 assert client.post('/dashboard/api/maintain/data',json=payload).status_code==200
 assert db.execute("SELECT value_number FROM metric_entry WHERE metric_id=31 AND stat_date='2026-10-23'").fetchone()[0]==70.5
 payload['stat_date']='2026-10-31';assert client.post('/dashboard/api/maintain/data',json=payload).status_code==400

def test_saved_versions_and_atomic_conflict(client,db):
 payload={'project_id':1,'stat_date':'2026-10-29','items':[{'metric_id':61,'feature_id':1,'value':'12','expected_version':1}]}
 r=client.post('/dashboard/api/maintain/data',json=payload);assert r.status_code==200,r.text
 assert r.json()['versions'][0]['row_version']==2
 payload['items'].insert(0,{'metric_id':11,'value':'100','expected_version':0})
 assert client.post('/dashboard/api/maintain/data',json=payload).status_code==409
 assert db.execute("SELECT COUNT(*) FROM metric_entry WHERE metric_id=11 AND stat_date='2026-10-29'").fetchone()[0]==0

def test_rename_keeps_identity_and_history_meaning(client,db):
 detail=client.get('/dashboard/api/metrics/31').json()
 payload={k:detail[k] for k in ['name','category_id','project_id','english_name','unit','decimal_places','definition','beidou_metric_code','row_version']}
 payload['name']='D7回访率';assert client.put('/dashboard/api/metrics/31',json=payload).status_code==200
 data=client.get('/dashboard/api/home/data?project_id=1&stat_date=2026-10-30').json()
 metric=next(m for m in data['metrics'] if m['id']==31);assert metric['name']=='D7回访率' and metric['semantic_name']=='7日留存率'
 payload['row_version']=2;payload['unit']='人';assert client.put('/dashboard/api/metrics/31',json=payload).status_code==409
 payload['unit']='%';payload['project_id']=2;assert client.put('/dashboard/api/metrics/31',json=payload).status_code in [403,409]

def test_funnel_migration_deletes_old_refs_first(client,db,monkeypatch):
 # Give the same valid role B edit scope for this migration.
 db.execute('INSERT INTO sys_role_project(role_id,project_id) VALUES(2,2)')
 r=client.put('/dashboard/api/funnels/1',json={'project_id':2,'name':'迁移漏斗','row_version':1,'steps':[{'step_name':'曝光','binding_id':99}]})
 assert r.status_code==200,r.text
 assert db.execute('SELECT project_id FROM funnel_step WHERE funnel_id=1').fetchone()[0]==2
 assert client.put('/dashboard/api/funnels/1',json={'project_id':2,'name':'旧表单','row_version':1,'steps':[{'step_name':'曝光','binding_id':99}]}).status_code==409

def test_csv_validate_import_skip_and_history_scope(client,db):
 text='项目,指标编码,指标名称,功能,统计日期,数值\n测试项目A,M11,开通用户数,,2026-10-30,100\n测试项目A,M12,累计使用用户数,,2026-10-30,60\n'
 payload={'project_id':1,'csv_text':text}
 preview=client.post('/dashboard/api/maintain/import/validate',json=payload);assert preview.status_code==200,preview.text
 assert len(preview.json()['rows'])==2
 r=client.post('/dashboard/api/maintain/import',json=payload);assert r.status_code==200,r.text
 assert r.json()['saved']==2
 assert client.post('/dashboard/api/maintain/import',json=payload).json()['skipped']==2
 history=client.get('/dashboard/api/maintain/history?project_id=1&q=CSV').json()['items'];assert len(history)==2
 assert all(h['source']=='CSV 导入' and h['operator']=='测试操作员' for h in history)
 db.execute('DELETE FROM sys_user_role WHERE user_id=2 AND role_id=3')
 assert client.get('/dashboard/api/maintain/history?project_id=2').status_code==403

def test_delegation_cannot_combine_other_role_scope(client,db):
 data={'name':'错误授权角色','permission_ids':[db.permissions['maintain.edit']],'project_ids':[2]}
 assert client.post('/dashboard/api/roles',json=data).status_code==403

def test_numeric_overflow_is_business_error():
 with pytest.raises(module.HTTPException):module._validate_value('9'*19,{'name':'人数','unit':'人','decimal_places':0})


def test_cannot_assign_or_enable_role_beyond_own_scope(client,db):
 # Active A operator cannot delegate B write via an existing disabled normal role.
 payload={'display_name':'测试操作员','login_id':'operator','role_ids':[4],'row_version':1}
 assert client.put('/dashboard/api/users/2',json=payload).status_code==403
 assert client.patch('/dashboard/api/roles/4',json={'is_enabled':True,'row_version':1}).status_code==403

def test_system_entities_hidden_even_for_system_login(client,monkeypatch):
 monkeypatch.setattr(module,'actor',lambda r:{'id':1,'login_id':'admin','is_super':True})
 assert all(r['code']!='super_admin' for r in client.get('/dashboard/api/roles').json()['items'])
 assert all(r['login_id']!='admin' for r in client.get('/dashboard/api/users').json()['items'])
 assert client.post('/dashboard/api/users/1/reset-password').status_code==403

def test_user_password_reset_cannot_take_over_broader_normal_role(client,db):
 db.execute('INSERT INTO sys_user_role(user_id,role_id) VALUES(3,4)')
 assert client.post('/dashboard/api/users/3/reset-password').status_code==403

def test_home_retention_fetches_full_14_observation_days(client,db):
 # Viewing Oct 30 needs baseline Oct 10..23, displayed as observation Oct 17..30.
 for day,value in [('2026-10-09',60),('2026-10-10',65),('2026-10-23',70)]:
  db.execute('INSERT INTO metric_entry(project_id,metric_id,stat_date,value_number) VALUES(1,31,?,?)',(day,value))
 db.execute("INSERT INTO metric_entry(project_id,metric_id,stat_date,value_number) VALUES(1,71,'2026-10-10',20)")
 response=client.get('/dashboard/api/home/data?project_id=1&stat_date=2026-10-30');assert response.status_code==200
 values=response.json()['values'];retention={r['date']:r['value'] for r in values if r['metric_id']==31}
 assert retention['2026-10-10']=='65' and retention['2026-10-23']=='70'
 assert '2026-10-09' not in retention
 assert not any(r['metric_id']==71 and r['date']=='2026-10-10' for r in values)
