"""Run once as root on the target server, after installing requirements.
Reads admin Argon2 hash from stdin. Existing admin / runtime account are never reset.
"""
import json, os, re, secrets, subprocess, sys
from pathlib import Path
os.umask(0o077)
root=Path('/opt/dashboard')

def run(args,**kwargs):
    return subprocess.run(args,check=True,**kwargs)
def sql(query):
    return subprocess.check_output(['docker','exec','-i','pet-db','sh','-c',
      'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot --default-character-set=utf8mb4 --batch --skip-column-names'],input=query.encode()).decode().strip()
def literal(s):
    if s is None:return 'NULL'
    return "CONVERT(0x"+str(s).encode().hex()+" USING utf8mb4)"

hash_value=sys.stdin.read().strip()
if not re.fullmatch(r'\$argon2id\$[^\n]{50,240}',hash_value):
    raise SystemExit('Expected Argon2id hash on stdin')
if sql("SELECT COUNT(*) FROM dashboard.sys_user WHERE login_id='admin';")!='0':
    raise SystemExit('admin exists: refusing any password or role replacement')
if sql("SELECT COUNT(*) FROM mysql.user WHERE User='dashboard_app';")!='0':
    raise SystemExit('dashboard_app exists: inspect existing deployment first')
if (root/'app.env').exists():
    raise SystemExit('app.env exists: refusing credential overwrite')
if subprocess.run(['id','dashboard'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode:
    run(['useradd','--system','--home-dir','/opt/dashboard','--shell','/sbin/nologin','dashboard'])
# Import seed definitions without connecting as root or exposing its password.
os.environ['SESSION_SECRET']=secrets.token_urlsafe(48)
from bootstrap import MENUS,ACTIONS
statements=['USE dashboard;','START TRANSACTION;',
 'INSERT INTO sys_user(login_id,display_name,password_hash,must_change_password,password_changed_at) VALUES(\'admin\','+literal('管理员')+','+literal(hash_value)+',0,UTC_TIMESTAMP(6));',
 'SET @uid=LAST_INSERT_ID();',
 'INSERT INTO sys_role(code,name) VALUES(\'super_admin\','+literal('超级管理员')+');',
 'SET @rid=LAST_INSERT_ID();','INSERT INTO sys_user_role(user_id,role_id,created_by) VALUES(@uid,@rid,@uid);']
for n,(code,name,parent,route,permissions) in enumerate(MENUS,1):
    statements.append('INSERT INTO sys_menu(code,name,parent_id,route_path,display_order,created_by,updated_by) VALUES('+','.join([literal(code),literal(name),'@m_'+parent if parent else 'NULL',literal(route),str(n),'@uid','@uid'])+');')
    statements.append('SET @m_'+code+'=LAST_INSERT_ID();')
    for i,label in enumerate(permissions):
        action=ACTIONS[label]
        statements.append('INSERT INTO sys_permission(menu_id,code,name,action_key,display_order,created_by,updated_by) VALUES('+','.join(['@m_'+code,literal(code+'.'+action),literal(label),literal(action),str(i),'@uid','@uid'])+');')
        statements.append('INSERT INTO sys_role_permission(role_id,permission_id,created_by) VALUES(@rid,LAST_INSERT_ID(),@uid);')
statements.extend(["INSERT INTO audit_log(actor_user_id,source_type,action_code,entity_type,entity_id,result,after_payload) VALUES(@uid,'SYSTEM','system.bootstrap','sys_user',@uid,'SUCCESS',JSON_OBJECT('login_id','admin','role','super_admin'));",'COMMIT;'])
sql('\n'.join(statements))
password=secrets.token_urlsafe(36)
# Only the Docker bridge host may use this runtime account; no root password is copied.
sql("CREATE USER 'dashboard_app'@'172.17.0.1' IDENTIFIED BY '"+password+"';\n"+
    '\n'.join("GRANT SELECT ON dashboard.`"+t+"` TO 'dashboard_app'@'172.17.0.1';" for t in ['sys_user','sys_role','sys_user_role','sys_menu','sys_permission','sys_role_permission'])+
    "\nGRANT UPDATE(last_login_at) ON dashboard.sys_user TO 'dashboard_app'@'172.17.0.1';\nGRANT UPDATE(is_enabled,row_version,updated_by,updated_at) ON dashboard.sys_menu TO 'dashboard_app'@'172.17.0.1';\nGRANT SELECT,INSERT,UPDATE(revoked_at) ON dashboard.auth_session TO 'dashboard_app'@'172.17.0.1';\nGRANT INSERT ON dashboard.audit_log TO 'dashboard_app'@'172.17.0.1';")
env='\n'.join(['DB_HOST=127.0.0.1','DB_PORT=3306','DB_NAME=dashboard','DB_USER=dashboard_app','DB_PASSWORD='+password,'SESSION_SECRET='+os.environ['SESSION_SECRET'],'BASE_PATH=/dashboard','PUBLIC_ORIGIN=https://129.226.194.82','COOKIE_SECURE=1'])+'\n'
(root/'app.env').write_text(env)
(root/'app.env').chmod(0o600)
service='''[Unit]
Description=Dashboard application
After=network.target docker.service
Requires=docker.service

[Service]
User=dashboard
Group=dashboard
WorkingDirectory=/opt/dashboard/app
EnvironmentFile=/opt/dashboard/app.env
ExecStart=/opt/dashboard/venv/bin/uvicorn app:app --host 127.0.0.1 --port 8321 --workers 1 --proxy-headers --forwarded-allow-ips 127.0.0.1
Restart=on-failure
RestartSec=4
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
UMask=0077

[Install]
WantedBy=multi-user.target
'''
Path('/etc/systemd/system/dashboard.service').write_text(service)
root.chmod(0o755)
run(['chmod','-R','a+rX','/opt/dashboard/app','/opt/dashboard/venv'])
run(['systemctl','daemon-reload'])
run(['systemctl','enable','--now','dashboard'])
print(json.dumps({'admin_created':True,'menus':len(MENUS),'service':'dashboard','runtime_user':'dashboard_app@172.17.0.1'}))
