"""Read schema metadata; transactional integrity tests; full rollback; no credentials printed."""
import json,subprocess,pathlib,re,uuid,hashlib,datetime,os
ROOT=pathlib.Path('/opt/dashboard/database/mysql')
SQL=ROOT.joinpath('001_schema.sql').read_text()
def run(sql):
 return subprocess.run(['docker','exec','-i','pet-db','sh','-c','MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysql -uroot --default-character-set=utf8mb4 -NB'],input=sql,text=True,capture_output=True)
def query(sql):
 r=run(sql)
 if r.returncode:raise RuntimeError(r.stderr)
 return r.stdout.strip()
expected={name:re.findall(r'^  `([^`]+)` ',body,re.M) for name,body in re.findall(r'CREATE TABLE `([^`]+)` \((.*?)\n\) ENGINE',SQL,re.S)}
actual={}
for row in query("SELECT TABLE_NAME,COLUMN_NAME FROM information_schema.COLUMNS WHERE TABLE_SCHEMA='dashboard' ORDER BY TABLE_NAME,ORDINAL_POSITION;").splitlines():
 t,c=row.split('\t');actual.setdefault(t,[]).append(c)
assert actual==expected,'Actual columns differ from DDL'
expected_fk=[]
for child,key,cols,parent,pcols in re.findall(r'ALTER TABLE `([^`]+)` ADD CONSTRAINT `([^`]+)` FOREIGN KEY \((.*?)\) REFERENCES `([^`]+)` \((.*?)\);',SQL):
 expected_fk.append((child,key,','.join(re.findall('`([^`]+)`',cols)),parent,','.join(re.findall('`([^`]+)`',pcols))))
actual_fk=[tuple(line.split('\t')) for line in query("SELECT TABLE_NAME,CONSTRAINT_NAME,GROUP_CONCAT(COLUMN_NAME ORDER BY ORDINAL_POSITION),REFERENCED_TABLE_NAME,GROUP_CONCAT(REFERENCED_COLUMN_NAME ORDER BY ORDINAL_POSITION) FROM information_schema.KEY_COLUMN_USAGE WHERE CONSTRAINT_SCHEMA='dashboard' AND REFERENCED_TABLE_NAME IS NOT NULL GROUP BY TABLE_NAME,CONSTRAINT_NAME,REFERENCED_TABLE_NAME;").splitlines()]
assert sorted(actual_fk)==sorted(expected_fk),'Foreign key targets differ'
checks=int(query("SELECT COUNT(*) FROM information_schema.TABLE_CONSTRAINTS WHERE CONSTRAINT_SCHEMA='dashboard' AND CONSTRAINT_TYPE='CHECK';"))
assert checks==SQL.count(' CHECK ('),(checks,SQL.count(' CHECK ('))
assert query("SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA='dashboard' AND (ENGINE<>'InnoDB' OR TABLE_COLLATION<>'utf8mb4_0900_as_cs');")=='0'
prefix='__schema_test_'+uuid.uuid4().hex
fixture=f"""
SET NAMES utf8mb4; SET time_zone='+00:00'; USE dashboard; START TRANSACTION;
INSERT INTO project(code,name) VALUES('{prefix}p1','验证项目甲'); SET @p1=LAST_INSERT_ID();
INSERT INTO project(code,name) VALUES('{prefix}p2','验证项目乙'); SET @p2=LAST_INSERT_ID();
INSERT INTO metric_category(code,name,metric_code_prefix) VALUES('{prefix[:25]}','{prefix}','{prefix[:12]}'); SET @cat=LAST_INSERT_ID();
INSERT INTO metric(project_id,category_id,code,name,name_key,value_kind,decimal_places,scope_kind,definition_status) VALUES(@p1,@cat,'{prefix[:28]}m1','测试指标甲','test1','COUNT',0,'PROJECT','PENDING'); SET @m1=LAST_INSERT_ID();
INSERT INTO metric(project_id,category_id,code,name,name_key,value_kind,decimal_places,scope_kind,definition_status) VALUES(@p2,@cat,'{prefix[:28]}m2','测试指标乙','test2','COUNT',0,'PROJECT','PENDING'); SET @m2=LAST_INSERT_ID();
INSERT INTO metric_revision(metric_id,revision_no,name,value_kind,decimal_places,scope_kind,definition_status) VALUES(@m1,1,'测试指标甲','COUNT',0,'PROJECT','PENDING'); SET @r1=LAST_INSERT_ID();
INSERT INTO metric_revision(metric_id,revision_no,name,value_kind,decimal_places,scope_kind,definition_status) VALUES(@m2,1,'测试指标乙','COUNT',0,'PROJECT','PENDING'); SET @r2=LAST_INSERT_ID();
UPDATE metric SET current_revision_id=@r1 WHERE id=@m1;
INSERT INTO metric_binding(project_id,metric_id,subject_key) VALUES(@p1,@m1,'PROJECT'); SET @b1=LAST_INSERT_ID();
INSERT INTO metric_binding(project_id,metric_id,subject_key) VALUES(@p2,@m2,'PROJECT'); SET @b2=LAST_INSERT_ID();
INSERT INTO ingestion_batch(batch_no,project_id,source_type,idempotency_key,status) VALUES('{prefix}batch1',@p1,'MANUAL','{prefix}key1','SUCCEEDED'); SET @batch1=LAST_INSERT_ID();
INSERT INTO ingestion_batch(batch_no,project_id,source_type,idempotency_key,status) VALUES('{prefix}batch2',@p2,'MANUAL','{prefix}key2','SUCCEEDED'); SET @batch2=LAST_INSERT_ID();
INSERT INTO funnel(project_id,name,name_key) VALUES(@p1,'验证漏斗','{prefix}'); SET @f1=LAST_INSERT_ID();
"""
insert="INSERT INTO metric_value(project_id,binding_id,metric_id,metric_revision_id,stat_date,value_number,value_status,is_period_complete,ingestion_batch_id) VALUES(@p1,@b1,@m1,@r1,'2026-10-28',0,'VALID',1,@batch1);"
tests=[
('zero_value_roundtrip',insert+"SELECT value_number FROM metric_value WHERE binding_id=@b1;",None),
('duplicate_daily_value',insert+insert,'1062'),
('cross_project_metric_binding',"UPDATE metric_binding SET project_id=@p2 WHERE id=@b1;",'1452'),
('cross_project_funnel_binding',"INSERT INTO funnel_step(funnel_id,project_id,step_name,binding_id,position) VALUES(@f1,@p1,'非法跨项目',@b2,1);",'1452'),
('wrong_metric_revision',insert.replace('@r1,','@r2,'),'1452'),
('cross_project_batch',insert.replace('@batch1','@batch2'),'1452'),
('valid_value_cannot_be_null',insert.replace(",0,'VALID'",",NULL,'VALID'"),'3819'),
('pending_value_must_be_null',insert.replace("'VALID'","'PENDING'"),'3819'),
('invalid_subject_key',"INSERT INTO metric_binding(project_id,metric_id,subject_key) VALUES(@p1,@m1,'ARBITRARY');",'3819'),
('duplicate_funnel_position',"INSERT INTO funnel_step(funnel_id,project_id,step_name,binding_id,position) VALUES(@f1,@p1,'一步',@b1,1),(@f1,@p1,'二步',@b1,1);",'1062'),
('wrong_current_revision',"UPDATE metric SET current_revision_id=@r2 WHERE id=@m1;",'1452'),
('invalid_boolean',"UPDATE project SET is_enabled=2 WHERE id=@p1;",'3819')]
results=[]
for name,statement,error in tests:
 r=run(fixture+statement+'\nROLLBACK;')
 if error:assert r.returncode and ('ERROR '+error+' ') in r.stderr,(name,r.stdout,r.stderr)
 else:assert r.returncode==0 and r.stdout.strip()=='0.000000',(name,r.stdout,r.stderr)
 results.append({'test':name,'passed':True,'expected_mysql_error':error})
counts={t:int(query('SELECT COUNT(*) FROM dashboard.`'+t+'`;')) for t in expected}
assert not any(counts.values()),'Transactional test left rows behind'
result={'verified_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'mysql_version':query('SELECT VERSION();'),'database':'dashboard','tables':len(actual),'columns':sum(map(len,actual.values())),'foreign_keys':len(actual_fk),'check_constraints':checks,'schema_sha256':hashlib.sha256(SQL.encode()).hexdigest(),'tests':results,'remaining_test_rows':sum(counts.values()),'app_accounts_created':False}
p=ROOT/'verification.json';p.write_text(json.dumps(result,ensure_ascii=False,indent=2));p.chmod(0o600)
print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)
