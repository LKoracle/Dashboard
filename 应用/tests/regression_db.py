"""Isolated SQLite adapter for business-flow regressions. Never connects to production."""
import sqlite3,re
from datetime import datetime,date
from contextlib import contextmanager

class Cursor:
 def __init__(self,connection):self.connection=connection;self.cursor=connection.cursor()
 def execute(self,sql,args=()):
  sql=sql.replace('%s','?').replace('<=>',' IS ').replace(' FOR UPDATE','').replace('UTC_TIMESTAMP(6)','CURRENT_TIMESTAMP')
  self.cursor.execute(sql,args);return self
 @property
 def lastrowid(self):return self.cursor.lastrowid
 def row(self,row):
  if row is None:return None
  result=dict(row)
  for key in ['created_at','saved_at']:
   if isinstance(result.get(key),str):result[key]=datetime.fromisoformat(result[key])
  if isinstance(result.get("stat_date"),str):result["stat_date"]=date.fromisoformat(result["stat_date"])
  return result
 def fetchone(self):return self.row(self.cursor.fetchone())
 def fetchall(self):return [self.row(row) for row in self.cursor.fetchall()]

class LocalDB:
 def __init__(self):
  self.connection=sqlite3.connect(':memory:',check_same_thread=False,isolation_level=None);self.connection.row_factory=sqlite3.Row
  self.connection.execute('PRAGMA foreign_keys=ON')
  self.connection.executescript('''
CREATE TABLE project(id INTEGER PRIMARY KEY AUTOINCREMENT,code TEXT UNIQUE,name TEXT UNIQUE,is_enabled INT DEFAULT 1,display_order INT DEFAULT 0,row_version INT DEFAULT 1,created_by INT,updated_by INT,updated_at TEXT);
CREATE TABLE project_feature(id INTEGER PRIMARY KEY AUTOINCREMENT,project_id INT REFERENCES project(id),code TEXT,name TEXT,display_order INT DEFAULT 0,archived_at TEXT,created_by INT,updated_by INT,updated_at TEXT,UNIQUE(project_id,name),UNIQUE(project_id,id));
CREATE TABLE sys_menu(id INTEGER PRIMARY KEY,code TEXT,parent_id INT,name TEXT,is_enabled INT,route_path TEXT,display_order INT,row_version INT DEFAULT 1,updated_by INT,updated_at TEXT);
CREATE TABLE sys_permission(id INTEGER PRIMARY KEY,menu_id INT,code TEXT UNIQUE,name TEXT,action_key TEXT,display_order INT DEFAULT 0,is_enabled INT DEFAULT 1);
CREATE TABLE sys_role(id INTEGER PRIMARY KEY AUTOINCREMENT,code TEXT UNIQUE,name TEXT UNIQUE,is_enabled INT DEFAULT 1,row_version INT DEFAULT 1,created_by INT,updated_by INT,updated_at TEXT);
CREATE TABLE sys_user(id INTEGER PRIMARY KEY AUTOINCREMENT,login_id TEXT UNIQUE,display_name TEXT,is_enabled INT DEFAULT 1,row_version INT DEFAULT 1,auth_version INT DEFAULT 1,password_hash TEXT,must_change_password INT DEFAULT 0,password_changed_at TEXT,last_login_at TEXT,created_by INT,updated_by INT,updated_at TEXT);
CREATE TABLE sys_user_role(user_id INT,role_id INT,created_by INT,PRIMARY KEY(user_id,role_id));
CREATE TABLE sys_role_project(role_id INT,project_id INT,created_by INT,PRIMARY KEY(role_id,project_id));
CREATE TABLE sys_role_permission(role_id INT,permission_id INT,created_by INT,PRIMARY KEY(role_id,permission_id));
CREATE TABLE auth_session(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INT,credential_hash TEXT,auth_version INT,expires_at TEXT,revoked_at TEXT);
CREATE TABLE metric_category(id INTEGER PRIMARY KEY,code TEXT,name TEXT,metric_code_prefix TEXT,last_sequence INT DEFAULT 100,display_order INT,is_enabled INT DEFAULT 1);
CREATE TABLE metric(id INTEGER PRIMARY KEY AUTOINCREMENT,project_id INT REFERENCES project(id),category_id INT,code TEXT UNIQUE,name TEXT,name_key TEXT,english_name TEXT,unit TEXT,decimal_places INT,value_kind TEXT DEFAULT 'DECIMAL',currency_code TEXT,scope_kind TEXT DEFAULT 'PROJECT',definition TEXT,definition_status TEXT DEFAULT 'CONFIRMED',retention_window_days INT,current_revision_id INT,beidou_metric_code TEXT,is_key_metric INT DEFAULT 0,show_trend INT DEFAULT 0,is_enabled INT DEFAULT 1,archived_at TEXT,display_order INT DEFAULT 0,row_version INT DEFAULT 1,created_by INT,updated_by INT,updated_at TEXT,UNIQUE(project_id,name_key),UNIQUE(project_id,id));
CREATE TABLE metric_revision(id INTEGER PRIMARY KEY AUTOINCREMENT,metric_id INT,revision_no INT,name TEXT,english_name TEXT,unit TEXT,value_kind TEXT,decimal_places INT,currency_code TEXT,scope_kind TEXT,definition TEXT,definition_status TEXT,retention_window_days INT,created_by INT,UNIQUE(metric_id,revision_no));
CREATE TABLE metric_binding(id INTEGER PRIMARY KEY AUTOINCREMENT,project_id INT,metric_id INT,feature_id INT REFERENCES project_feature(id),subject_key TEXT,archived_at TEXT,UNIQUE(metric_id,subject_key),UNIQUE(project_id,id),FOREIGN KEY(project_id,metric_id) REFERENCES metric(project_id,id));
CREATE TABLE metric_entry(id INTEGER PRIMARY KEY AUTOINCREMENT,project_id INT REFERENCES project(id),metric_id INT REFERENCES metric(id),feature_id INT REFERENCES project_feature(id),feature_key INT GENERATED ALWAYS AS(COALESCE(feature_id,0)) STORED,stat_date DATE,value_number NUMERIC,row_version INT DEFAULT 1,created_by INT,updated_by INT,updated_at TEXT,UNIQUE(project_id,metric_id,feature_key,stat_date));
CREATE TABLE funnel(id INTEGER PRIMARY KEY AUTOINCREMENT,project_id INT,name TEXT,name_key TEXT,is_enabled INT DEFAULT 1,display_order INT DEFAULT 0,row_version INT DEFAULT 1,created_by INT,updated_by INT,updated_at TEXT,UNIQUE(project_id,name_key),UNIQUE(project_id,id));
CREATE TABLE funnel_step(id INTEGER PRIMARY KEY AUTOINCREMENT,funnel_id INT,project_id INT,step_name TEXT,binding_id INT,position INT,UNIQUE(funnel_id,position),FOREIGN KEY(project_id,funnel_id) REFERENCES funnel(project_id,id),FOREIGN KEY(project_id,binding_id) REFERENCES metric_binding(project_id,id));
CREATE TABLE audit_log(id INTEGER PRIMARY KEY AUTOINCREMENT,actor_user_id INT,source_type TEXT,action_code TEXT,entity_type TEXT,entity_id INT,before_payload TEXT,after_payload TEXT,result TEXT,project_id INT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
''')
 @contextmanager
 def database(self):
  own=not self.connection.in_transaction
  if own:self.connection.execute('BEGIN')
  try:
   yield Cursor(self.connection)
   if own:self.connection.commit()
  except:
   if own:self.connection.rollback()
   raise
 def execute(self,sql,args=()):return self.connection.execute(sql,args)
 def seed(self,password_hash='test-only-not-a-login-hash'):
  c=self.connection
  c.executemany('INSERT INTO project(id,code,name,is_enabled,display_order) VALUES(?,?,?,?,?)',[(1,'A','测试项目A',1,1),(2,'B','测试项目B',1,2),(3,'C','停用测试项目',0,3)])
  menus=[(1,'home',None,'首页','/'),(2,'maintain',None,'数据维护','/maintain'),(3,'settings',None,'设置管理',None),(4,'project',3,'项目管理','/settings/projects'),(5,'metric',3,'指标管理','/settings/metrics'),(6,'funnel',3,'漏斗管理','/settings/funnels'),(7,'permission',3,'权限配置',None),(8,'menu',7,'菜单管理','/settings/menus'),(9,'role',7,'角色管理','/settings/roles'),(10,'user',7,'用户管理','/settings/users')]
  c.executemany('INSERT INTO sys_menu(id,code,parent_id,name,route_path,is_enabled,display_order) VALUES(?,?,?,?,?,1,?)',[(*r,r[0]) for r in menus])
  permissions={};index=0
  for prefix,menu_id,actions in [('home',1,['view']),('maintain',2,['view','edit','import']),('project',4,['view','edit','create']),('metric',5,['view','edit','create']),('funnel',6,['view','edit','create','enable','disable']),('menu',8,['view','edit']),('role',9,['view','edit','create']),('user',10,['view','edit','create','reset_password'])]:
   for action in actions:
    index+=1;code=prefix+'.'+action;permissions[code]=index
    c.execute('INSERT INTO sys_permission(id,menu_id,code,name,action_key) VALUES(?,?,?,?,?)',(index,menu_id,code,action,action))
  self.permissions=permissions
  c.executemany('INSERT INTO sys_role(id,code,name,is_enabled) VALUES(?,?,?,?)',[(1,'super_admin','超级管理员',1),(2,'operator','项目A操作员',1),(3,'viewer','项目B只读',1),(4,'disabled','已停用角色',0)])
  c.executemany('INSERT INTO sys_user(id,login_id,display_name,password_hash) VALUES(?,?,?,?)',[(1,'admin','保留管理员',password_hash),(2,'operator','测试操作员',password_hash),(3,'viewer','测试查看员',password_hash)])
  c.executemany('INSERT INTO sys_user_role(user_id,role_id) VALUES(?,?)',[(1,1),(2,2),(2,3),(2,4),(3,3)])
  c.executemany('INSERT INTO sys_role_project(role_id,project_id) VALUES(?,?)',[(2,1),(3,2),(4,2)])
  for code,pid in permissions.items():
   c.execute('INSERT INTO sys_role_permission(role_id,permission_id) VALUES(2,?)',(pid,))
   if code.endswith('.view'):c.execute('INSERT INTO sys_role_permission(role_id,permission_id) VALUES(3,?)',(pid,))
  c.execute('INSERT INTO sys_role_permission(role_id,permission_id) VALUES(4,?)',(permissions['maintain.edit'],))
  for i,code,name,prefix in [(1,'coverage','用户覆盖','YHFG'),(2,'activity','用户活跃','YHHY'),(3,'retention','用户留存','YHLC'),(4,'depth','使用深度','SYSD'),(5,'performance','性能表现','XNBX'),(6,'feature','功能使用','GNSY'),(7,'funnel','漏斗指标','LDZB')]:
   c.execute('INSERT INTO metric_category(id,code,name,metric_code_prefix,display_order) VALUES(?,?,?,?,?)',(i,code,name,prefix,i))
  values=[(11,1,1,'开通用户数','人',0),(12,1,1,'累计使用用户数','人',0),(13,1,1,'累计使用率','%',1),(21,1,2,'日活跃用户数','人',0),(31,1,3,'7日留存率','%',1),(41,1,4,'有效会话数','次',0),(42,1,4,'每次会话平均时长','分钟／次',1),(51,1,5,'平均首字响应时长','秒',2),(52,1,5,'平均完整响应时长','秒',2),(61,1,6,'功能日使用人数','人',0),(62,1,6,'功能日使用人数占比','%',1),(63,1,6,'功能累计使用人数','人',0),(64,1,6,'功能累计使用人数占比','%',1),(71,1,7,'曝光人数','人',0),(72,1,7,'点击人数','人',0),(99,2,7,'B项目曝光人数','人',0)]
  for mid,project,cat,name,unit,dp in values:
   c.execute('INSERT INTO metric(id,project_id,category_id,code,name,name_key,unit,decimal_places,definition,show_trend,is_key_metric) VALUES(?,?,?,?,?,?,?,?,?,?,?)',(mid,project,cat,'M'+str(mid),name,name,unit,dp,'测试口径',int(cat in [2,3,4,5]),int(mid in [21,31,42,51])))
   c.execute('INSERT INTO metric_revision(metric_id,revision_no,name,unit,decimal_places,definition,definition_status) VALUES(?,1,?,?,?,? ,?)',(mid,name,unit,dp,'测试口径','CONFIRMED'))
  c.executemany('INSERT INTO project_feature(id,project_id,code,name,display_order) VALUES(?,?,?,?,?)',[(1,1,'f1','测试功能',1),(2,2,'f2','B功能',1)])
  for bid,project,mid,fid,subject in [(71,1,71,None,'PROJECT'),(72,1,72,None,'PROJECT'),(99,2,99,None,'PROJECT'),(611,1,61,1,'FEATURE:1')]:c.execute('INSERT INTO metric_binding(id,project_id,metric_id,feature_id,subject_key) VALUES(?,?,?,?,?)',(bid,project,mid,fid,subject))
  c.execute("INSERT INTO metric_entry(project_id,metric_id,feature_id,stat_date,value_number) VALUES(1,61,1,'2026-10-29',10)")
  c.execute("INSERT INTO metric_entry(project_id,metric_id,stat_date,value_number) VALUES(1,31,'2026-10-16',68)")
  c.execute("INSERT INTO funnel(id,project_id,name,name_key) VALUES(1,1,'测试漏斗','测试漏斗')")
  c.execute("INSERT INTO funnel_step(funnel_id,project_id,step_name,binding_id,position) VALUES(1,1,'曝光',71,1)")
  return self
