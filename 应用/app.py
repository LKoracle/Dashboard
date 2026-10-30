"""Dashboard: authenticated administration. All database timestamps are UTC."""
import hashlib, hmac, json, os, re, secrets, threading, time
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

import pymysql
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, StrictBool

BASE = os.getenv('BASE_PATH', '/dashboard').rstrip('/')
ORIGIN = os.getenv('PUBLIC_ORIGIN', 'https://129.226.194.82').rstrip('/')
SECURE = os.getenv('COOKIE_SECURE', '1') == '1'
SECRET = os.environ['SESSION_SECRET']
if len(SECRET) < 32:
    raise RuntimeError('SESSION_SECRET must contain at least 32 characters')
ROOT = Path(__file__).parent
ph = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2)
DUMMY = ph.hash(secrets.token_urlsafe(24))
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

@contextmanager
def database():
    connection = pymysql.connect(host=os.getenv('DB_HOST','127.0.0.1'),
        port=int(os.getenv('DB_PORT','3306')), user=os.environ['DB_USER'],
        password=os.environ['DB_PASSWORD'], database=os.getenv('DB_NAME','dashboard'),
        charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor,
        init_command="SET time_zone = '+00:00'", connect_timeout=5, read_timeout=10, write_timeout=10)
    try:
        with connection.cursor() as cursor:
            yield cursor
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

def digest(token):
    return hashlib.sha256(token.encode()).hexdigest()

def csrf(token):
    return hmac.new(SECRET.encode(), token.encode(), hashlib.sha256).hexdigest()

def actor(request):
    token = request.cookies.get('dashboard_session','')
    if not token or len(token) > 128:
        raise HTTPException(401, '请先登录')
    with database() as c:
        c.execute('''SELECT u.id,u.login_id,u.display_name,s.id AS session_id,
          EXISTS(SELECT 1 FROM sys_user_role ur JOIN sys_role r ON r.id=ur.role_id
          WHERE ur.user_id=u.id AND r.code='super_admin' AND r.is_enabled=1) AS is_super
          FROM auth_session s JOIN sys_user u ON u.id=s.user_id
          WHERE s.credential_hash=%s AND s.revoked_at IS NULL AND s.expires_at>UTC_TIMESTAMP(6)
          AND s.auth_version=u.auth_version AND u.is_enabled=1''', (digest(token),))
        user = c.fetchone()
    if not user:
        raise HTTPException(401,'登录已失效，请重新登录')
    return user

def check_permission(user, action):
    if user['is_super']:
        return
    with database() as c:
        c.execute('''SELECT DISTINCT m.id FROM sys_user_role ur
          JOIN sys_role r ON r.id=ur.role_id AND r.is_enabled=1
          JOIN sys_role_permission rp ON rp.role_id=r.id
          JOIN sys_permission p ON p.id=rp.permission_id AND p.is_enabled=1
          JOIN sys_menu m ON m.id=p.menu_id
          WHERE ur.user_id=%s AND p.code=%s''', (user['id'],action))
        granted = c.fetchall()
        c.execute('SELECT id,parent_id,is_enabled FROM sys_menu')
        menus = {m['id']:m for m in c.fetchall()}
    for row in granted:
        mid, seen = row['id'], set()
        while mid is not None:
            if mid in seen or mid not in menus or not menus[mid]['is_enabled']:
                break
            seen.add(mid)
            mid=menus[mid]['parent_id']
        else:
            return
    raise HTTPException(403,'没有此操作权限')

def mutation(request):
    if request.headers.get('origin') != ORIGIN:
        raise HTTPException(403,'请求来源不受信任')
    expected = csrf(request.cookies.get('dashboard_session',''))
    if not hmac.compare_digest(request.headers.get('x-csrf-token',''), expected):
        raise HTTPException(403,'页面已过期，请刷新后重试')

def audit(c, uid, action, entity, eid=None, before=None, after=None):
    c.execute('''INSERT INTO audit_log(actor_user_id,source_type,action_code,entity_type,
      entity_id,before_payload,after_payload,result) VALUES(%s,'WEB',%s,%s,%s,%s,%s,'SUCCESS')''',
      (uid,action,entity,eid,json.dumps(before,ensure_ascii=False) if before is not None else None,
       json.dumps(after,ensure_ascii=False) if after is not None else None))

@app.middleware('http')
async def security_headers(request, call_next):
    if request.url.path.startswith(BASE+'/api/') and request.headers.get('content-length','').isdigit() and int(request.headers['content-length'])>8192:
        response=JSONResponse({'detail':'请求过大'},status_code=413)
    else:
        response=await call_next(request)
    response.headers.update({'Cache-Control':'no-store','X-Content-Type-Options':'nosniff',
       'X-Frame-Options':'DENY','Referrer-Policy':'same-origin',
       'Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'"})
    if SECURE:
        response.headers['Strict-Transport-Security']='max-age=31536000'
    return response

class Login(BaseModel):
    login_id: str = Field(min_length=1,max_length=100)
    password: str = Field(min_length=1,max_length=256)

# Single worker deployment; bounded rate-limit buckets, never records plaintext passwords.
_attempts={}
_lock=threading.Lock()
def throttle(key):
    now=time.monotonic()
    with _lock:
        for k in list(_attempts):
            if _attempts[k][0] < now-900:
                del _attempts[k]
        started,count=_attempts.get(key,(now,0))
        if count>=10:
            raise HTTPException(429,'尝试次数过多，请 15 分钟后再试')
        _attempts[key]=(started,count+1)

@app.post(BASE+'/api/login')
def login(data:Login,request:Request):
    if request.headers.get('origin') != ORIGIN:
        raise HTTPException(403,'请求来源不受信任')
    host=request.client.host if request.client else 'unknown'
    throttle(('ip',host))
    throttle(('user',data.login_id))
    with database() as c:
        c.execute('SELECT id,password_hash,is_enabled,auth_version,must_change_password FROM sys_user WHERE login_id=%s', (data.login_id,))
        u=c.fetchone()
        valid=False
        try:
            valid=ph.verify(u['password_hash'] if u else DUMMY,data.password)
        except (VerificationError,InvalidHashError):
            pass
        if not u or not valid or not u['is_enabled']:
            raise HTTPException(401,'用户 ID 或密码不正确')
        if u['must_change_password']:
            raise HTTPException(403,'账号需要管理员完成密码更新后才能登录')
        token=secrets.token_urlsafe(32)
        c.execute('INSERT INTO auth_session(user_id,credential_hash,auth_version,expires_at) VALUES(%s,%s,%s,%s)',
            (u['id'],digest(token),u['auth_version'],datetime.utcnow()+timedelta(hours=8)))
        c.execute('UPDATE sys_user SET last_login_at=UTC_TIMESTAMP(6) WHERE id=%s',(u['id'],))
        audit(c,u['id'],'auth.login','sys_user',u['id'])
    with _lock:
        _attempts.pop(('user',data.login_id),None)
    response=JSONResponse({'redirect':BASE+'/'})
    response.set_cookie('dashboard_session',token,max_age=28800,httponly=True,secure=SECURE,samesite='strict',path=BASE+'/')
    return response

@app.post(BASE+'/api/logout')
def logout(request:Request):
    user=actor(request)
    mutation(request)
    with database() as c:
        c.execute('UPDATE auth_session SET revoked_at=UTC_TIMESTAMP(6) WHERE id=%s',(user['session_id'],))
        audit(c,user['id'],'auth.logout','sys_user',user['id'])
    response=JSONResponse({'ok':True})
    response.delete_cookie('dashboard_session',path=BASE+'/',secure=SECURE,httponly=True,samesite='strict')
    return response

@app.get(BASE+'/api/me')
def me(request:Request):
    user=actor(request)
    return {'login_id':user['login_id'],'display_name':user['display_name'],
            'is_super':bool(user['is_super']),'csrf_token':csrf(request.cookies['dashboard_session'])}

@app.get(BASE+'/api/menus')
def menus(request:Request):
    user=actor(request)
    check_permission(user,'menu.view')
    with database() as c:
        c.execute('SELECT id,code,parent_id,name,route_path,display_order,is_enabled,row_version FROM sys_menu ORDER BY display_order,id')
        rows=c.fetchall()
        c.execute('SELECT menu_id,name FROM sys_permission WHERE is_enabled=1 ORDER BY display_order,id')
        permissions=c.fetchall()
    for row in rows:
        row['permissions']=[p['name'] for p in permissions if p['menu_id']==row['id']]
    can_edit=True
    try:
        check_permission(user,'menu.edit')
    except HTTPException:
        can_edit=False
    return {'items':rows,'can_edit':can_edit}

class MenuUpdate(BaseModel):
    is_enabled: StrictBool
    row_version: int = Field(ge=1)

@app.patch(BASE+'/api/menus/{menu_id}')
def update_menu(menu_id:int,data:MenuUpdate,request:Request):
    user=actor(request)
    check_permission(user,'menu.edit')
    mutation(request)
    with database() as c:
        c.execute('SELECT id,code,is_enabled,row_version FROM sys_menu WHERE id=%s FOR UPDATE',(menu_id,))
        row=c.fetchone()
        if not row:
            raise HTTPException(404,'菜单不存在')
        if row['row_version']!=data.row_version:
            raise HTTPException(409,'此菜单已被其他操作更新，请刷新后重试')
        before={'is_enabled':bool(row['is_enabled']),'row_version':row['row_version']}
        if bool(row['is_enabled'])==data.is_enabled:
            return {'ok':True,'row_version':row['row_version']}
        c.execute('UPDATE sys_menu SET is_enabled=%s,row_version=row_version+1,updated_by=%s,updated_at=UTC_TIMESTAMP(6) WHERE id=%s',
                  (int(data.is_enabled),user['id'],menu_id))
        after={'is_enabled':data.is_enabled,'row_version':row['row_version']+1}
        audit(c,user['id'],'menu.enable' if data.is_enabled else 'menu.disable','sys_menu',menu_id,before,after)
    return {'ok':True,**after}

# ---- 角色管理 ----

def _role_tree(c):
    c.execute('''SELECT id,code,parent_id,name,route_path,display_order,is_enabled FROM sys_menu ORDER BY display_order,id''')
    menus = c.fetchall()
    c.execute('''SELECT id,menu_id,code,name,action_key,display_order,is_enabled FROM sys_permission ORDER BY display_order,id''')
    perms = c.fetchall()
    return menus, perms

@app.get(BASE+'/api/roles')
def list_roles(request:Request):
    user=actor(request)
    check_permission(user,'role.view')
    can_edit=True
    try:
        check_permission(user,'role.edit')
    except HTTPException:
        can_edit=False
    with database() as c:
        c.execute('''SELECT id,code,name,is_enabled,row_version FROM sys_role ORDER BY id''')
        roles=c.fetchall()
        c.execute('''SELECT role_id,COUNT(*) AS cnt FROM sys_role_permission GROUP BY role_id''')
        perm_counts={r['role_id']:r['cnt'] for r in c.fetchall()}
        c.execute('''SELECT rp.role_id, p.name FROM sys_role_project rp JOIN project p ON p.id=rp.project_id ORDER BY p.display_order,p.id''')
        projects={}
        for r in c.fetchall():
            projects.setdefault(r['role_id'],[]).append(r['name'])
        c.execute('''SELECT role_id,COUNT(*) AS cnt FROM sys_user_role GROUP BY role_id''')
        user_counts={r['role_id']:r['cnt'] for r in c.fetchall()}
        c.execute('''SELECT DISTINCT rp.role_id, m.name, m.display_order, m.id
                     FROM sys_role_permission rp
                     JOIN sys_permission p ON p.id=rp.permission_id
                     JOIN sys_menu m ON m.id=p.menu_id
                     ORDER BY m.display_order, m.id''')
        menus={}
        for r in c.fetchall():
            menus.setdefault(r['role_id'],[]).append(r['name'])
    items=[]
    for r in roles:
        items.append({'id':r['id'],'code':r['code'],'name':r['name'],'is_enabled':bool(r['is_enabled']),
            'row_version':r['row_version'],'permission_count':perm_counts.get(r['id'],0),
            'projects':projects.get(r['id'],[]),'project_count':len(projects.get(r['id'],[])),
            'user_count':user_counts.get(r['id'],0),'menus':menus.get(r['id'],[])})
    return {'items':items,'can_edit':can_edit}

@app.get(BASE+'/api/roles/meta')
def roles_meta(request:Request):
    user=actor(request)
    check_permission(user,'role.view')
    with database() as c:
        menus, perms = _role_tree(c)
        c.execute('SELECT id,code,name,is_enabled FROM project ORDER BY display_order,id')
        projects=c.fetchall()
    # 构建菜单树（含权限项），供表单复用
    tree=[]
    for m in menus:
        node={'id':m['id'],'code':m['code'],'parent_id':m['parent_id'],'name':m['name'],
              'is_enabled':bool(m['is_enabled']),'permissions':[]}
        for p in perms:
            if p['menu_id']==m['id']:
                node['permissions'].append({'id':p['id'],'code':p['code'],'name':p['name'],'is_enabled':bool(p['is_enabled'])})
        tree.append(node)
    return {'menus':tree,'projects':[{'id':p['id'],'code':p['code'],'name':p['name'],'is_enabled':bool(p['is_enabled'])} for p in projects]}

class RolePayload(BaseModel):
    name: str = Field(min_length=1,max_length=100)
    permission_ids: list[int] = Field(default_factory=list)
    project_ids: list[int] = Field(default_factory=list)
    is_enabled: bool = True

@app.post(BASE+'/api/roles')
def create_role(data:RolePayload,request:Request):
    user=actor(request)
    check_permission(user,'role.create')
    mutation(request)
    name=data.name.strip()
    if not name:
        raise HTTPException(400,'角色名称不能为空')
    with database() as c:
        c.execute('SELECT id FROM sys_role WHERE name=%s',(name,))
        if c.fetchone():
            raise HTTPException(409,'已存在同名角色')
        # 校验权限 ID 有效
        if data.permission_ids:
            fmt=','.join(['%s']*len(data.permission_ids))
            c.execute(f'SELECT id FROM sys_permission WHERE id IN ({fmt})',tuple(data.permission_ids))
            valid={r['id'] for r in c.fetchall()}
            if len(valid)!=len(set(data.permission_ids)):
                raise HTTPException(400,'包含无效的权限项')
        # 校验项目 ID 有效
        if data.project_ids:
            fmt=','.join(['%s']*len(data.project_ids))
            c.execute(f'SELECT id FROM project WHERE id IN ({fmt})',tuple(data.project_ids))
            valid_proj={r['id'] for r in c.fetchall()}
            if len(valid_proj)!=len(set(data.project_ids)):
                raise HTTPException(400,'包含无效的项目')
        code='role_'+secrets.token_hex(4)
        c.execute('INSERT INTO sys_role(code,name,is_enabled,created_by,updated_by) VALUES(%s,%s,%s,%s,%s)',
                  (code,name,int(bool(data.is_enabled)),user['id'],user['id']))
        role_id=c.lastrowid
        for pid in set(data.permission_ids):
            c.execute('INSERT INTO sys_role_permission(role_id,permission_id,created_by) VALUES(%s,%s,%s)',
                      (role_id,pid,user['id']))
        for pid in set(data.project_ids):
            c.execute('INSERT INTO sys_role_project(role_id,project_id,created_by) VALUES(%s,%s,%s)',
                      (role_id,pid,user['id']))
        audit(c,user['id'],'role.create','sys_role',role_id,None,
              {'name':name,'permission_ids':sorted(set(data.permission_ids)),'project_ids':sorted(set(data.project_ids))})
    return {'ok':True,'id':role_id}

@app.get(BASE+'/api/roles/{role_id}')
def get_role(role_id:int,request:Request):
    user=actor(request)
    check_permission(user,'role.view')
    with database() as c:
        c.execute('SELECT id,code,name,is_enabled,row_version FROM sys_role WHERE id=%s',(role_id,))
        row=c.fetchone()
        if not row:
            raise HTTPException(404,'角色不存在')
        c.execute('SELECT permission_id FROM sys_role_permission WHERE role_id=%s',(role_id,))
        permission_ids=[r['permission_id'] for r in c.fetchall()]
        c.execute('SELECT project_id FROM sys_role_project WHERE role_id=%s',(role_id,))
        project_ids=[r['project_id'] for r in c.fetchall()]
    return {'id':row['id'],'code':row['code'],'name':row['name'],'is_enabled':bool(row['is_enabled']),
            'row_version':row['row_version'],'permission_ids':permission_ids,'project_ids':project_ids}

@app.put(BASE+'/api/roles/{role_id}')
def update_role(role_id:int,data:RolePayload,request:Request):
    user=actor(request)
    check_permission(user,'role.edit')
    mutation(request)
    name=data.name.strip()
    if not name:
        raise HTTPException(400,'角色名称不能为空')
    with database() as c:
        c.execute('SELECT id,code,name,is_enabled,row_version FROM sys_role WHERE id=%s FOR UPDATE',(role_id,))
        row=c.fetchone()
        if not row:
            raise HTTPException(404,'角色不存在')
        if row['code']=='super_admin':
            raise HTTPException(403,'不能修改超级管理员角色')
        c.execute('SELECT id FROM sys_role WHERE name=%s AND id<>%s',(name,role_id))
        if c.fetchone():
            raise HTTPException(409,'已存在同名角色')
        if data.permission_ids:
            fmt=','.join(['%s']*len(data.permission_ids))
            c.execute(f'SELECT id FROM sys_permission WHERE id IN ({fmt})',tuple(data.permission_ids))
            valid={r['id'] for r in c.fetchall()}
            if len(valid)!=len(set(data.permission_ids)):
                raise HTTPException(400,'包含无效的权限项')
        if data.project_ids:
            fmt=','.join(['%s']*len(data.project_ids))
            c.execute(f'SELECT id FROM project WHERE id IN ({fmt})',tuple(data.project_ids))
            valid_proj={r['id'] for r in c.fetchall()}
            if len(valid_proj)!=len(set(data.project_ids)):
                raise HTTPException(400,'包含无效的项目')
        before={'name':row['name'],'is_enabled':bool(row['is_enabled'])}
        c.execute('UPDATE sys_role SET name=%s,is_enabled=%s,row_version=row_version+1,updated_by=%s,updated_at=UTC_TIMESTAMP(6) WHERE id=%s',
                  (name,int(bool(data.is_enabled)),user['id'],role_id))
        c.execute('DELETE FROM sys_role_permission WHERE role_id=%s',(role_id,))
        for pid in set(data.permission_ids):
            c.execute('INSERT INTO sys_role_permission(role_id,permission_id,created_by) VALUES(%s,%s,%s)',
                      (role_id,pid,user['id']))
        c.execute('DELETE FROM sys_role_project WHERE role_id=%s',(role_id,))
        for pid in set(data.project_ids):
            c.execute('INSERT INTO sys_role_project(role_id,project_id,created_by) VALUES(%s,%s,%s)',
                      (role_id,pid,user['id']))
        after={'name':name,'is_enabled':bool(data.is_enabled),
               'permission_ids':sorted(set(data.permission_ids)),'project_ids':sorted(set(data.project_ids))}
        audit(c,user['id'],'role.edit','sys_role',role_id,before,after)
    return {'ok':True,'row_version':row['row_version']+1}

class RoleStatus(BaseModel):
    is_enabled: StrictBool
    row_version: int = Field(ge=1)

@app.patch(BASE+'/api/roles/{role_id}')
def toggle_role(role_id:int,data:RoleStatus,request:Request):
    user=actor(request)
    check_permission(user,'role.edit')
    mutation(request)
    with database() as c:
        c.execute('SELECT id,code,is_enabled,row_version FROM sys_role WHERE id=%s FOR UPDATE',(role_id,))
        row=c.fetchone()
        if not row:
            raise HTTPException(404,'角色不存在')
        if row['code']=='super_admin':
            raise HTTPException(403,'不能停用超级管理员角色')
        if row['row_version']!=data.row_version:
            raise HTTPException(409,'此角色已被其他操作更新，请刷新后重试')
        if bool(row['is_enabled'])==data.is_enabled:
            return {'ok':True,'row_version':row['row_version']}
        before={'is_enabled':bool(row['is_enabled']),'row_version':row['row_version']}
        c.execute('UPDATE sys_role SET is_enabled=%s,row_version=row_version+1,updated_by=%s,updated_at=UTC_TIMESTAMP(6) WHERE id=%s',
                  (int(data.is_enabled),user['id'],role_id))
        after={'is_enabled':data.is_enabled,'row_version':row['row_version']+1}
        audit(c,user['id'],'role.enable' if data.is_enabled else 'role.disable','sys_role',role_id,before,after)
    return {'ok':True,**after}

@app.delete(BASE+'/api/roles/{role_id}')
def delete_role(role_id:int,request:Request):
    user=actor(request)
    check_permission(user,'role.edit')
    mutation(request)
    with database() as c:
        c.execute('SELECT id,code,name FROM sys_role WHERE id=%s FOR UPDATE',(role_id,))
        row=c.fetchone()
        if not row:
            raise HTTPException(404,'角色不存在')
        if row['code']=='super_admin':
            raise HTTPException(403,'不能删除超级管理员角色')
        c.execute('SELECT COUNT(*) AS cnt FROM sys_user_role WHERE role_id=%s',(role_id,))
        if c.fetchone()['cnt']>0:
            raise HTTPException(409,'该角色仍分配给了用户，无法删除')
        c.execute('DELETE FROM sys_role_permission WHERE role_id=%s',(role_id,))
        c.execute('DELETE FROM sys_role_project WHERE role_id=%s',(role_id,))
        c.execute('DELETE FROM sys_role WHERE id=%s',(role_id,))
        audit(c,user['id'],'role.delete','sys_role',role_id,{'name':row['name']},None)
    return {'ok':True}

# ---- 项目管理 ----

class ProjectPayload(BaseModel):
    name: str = Field(min_length=1,max_length=100)
    is_enabled: bool = True
    features: list[str] = Field(default_factory=list)

class ProjectStatus(BaseModel):
    is_enabled: StrictBool
    row_version: int = Field(ge=1)

class ProjectMove(BaseModel):
    direction: str = Field(pattern='^(up|down)$')
    row_version: int = Field(ge=1)

def _project_feature_names(c, project_id):
    c.execute('SELECT name FROM project_feature WHERE project_id=%s ORDER BY display_order,id',(project_id,))
    return [r['name'] for r in c.fetchall()]

@app.get(BASE+'/api/projects')
def list_projects(request:Request):
    user=actor(request)
    check_permission(user,'project.view')
    can_edit=True
    try:
        check_permission(user,'project.edit')
    except HTTPException:
        can_edit=False
    with database() as c:
        c.execute('SELECT id,code,name,is_enabled,display_order,row_version FROM project ORDER BY display_order,id')
        rows=c.fetchall()
    items=[]
    for r in rows:
        with database() as c:
            features=_project_feature_names(c,r['id'])
        items.append({'id':r['id'],'code':r['code'],'name':r['name'],'is_enabled':bool(r['is_enabled']),
                      'display_order':r['display_order'],'row_version':r['row_version'],'features':features})
    return {'items':items,'can_edit':can_edit}

@app.get(BASE+'/api/projects/{project_id}')
def get_project(project_id:int,request:Request):
    user=actor(request)
    check_permission(user,'project.view')
    with database() as c:
        c.execute('SELECT id,code,name,is_enabled,display_order,row_version FROM project WHERE id=%s',(project_id,))
        row=c.fetchone()
        if not row:
            raise HTTPException(404,'项目不存在')
        features=_project_feature_names(c,project_id)
    return {'id':row['id'],'code':row['code'],'name':row['name'],'is_enabled':bool(row['is_enabled']),
            'display_order':row['display_order'],'row_version':row['row_version'],'features':features}

def _write_features(c, project_id, features, uid):
    names=[]
    seen=set()
    for f in features:
        name=str(f).strip()
        if not name or name in seen:
            continue
        seen.add(name)
        names.append(name)
    c.execute('DELETE FROM project_feature WHERE project_id=%s',(project_id,))
    for i,name in enumerate(names,start=1):
        code='feat_'+secrets.token_hex(4)
        c.execute('''INSERT INTO project_feature(project_id,code,name,display_order,created_by,updated_by)
                     VALUES(%s,%s,%s,%s,%s,%s)''',(project_id,code,name,i,uid,uid))
    return names

@app.post(BASE+'/api/projects')
def create_project(data:ProjectPayload,request:Request):
    user=actor(request)
    check_permission(user,'project.create')
    mutation(request)
    name=data.name.strip()
    if not name:
        raise HTTPException(400,'项目名称不能为空')
    with database() as c:
        c.execute('SELECT id FROM project WHERE name=%s',(name,))
        if c.fetchone():
            raise HTTPException(409,'已存在同名项目')
        c.execute('SELECT COALESCE(MAX(display_order),0)+1 FROM project')
        display_order=c.fetchone()['COALESCE(MAX(display_order),0)+1']
        code='proj_'+secrets.token_hex(4)
        c.execute('''INSERT INTO project(code,name,is_enabled,display_order,created_by,updated_by)
                     VALUES(%s,%s,%s,%s,%s,%s)''',(code,name,int(bool(data.is_enabled)),display_order,user['id'],user['id']))
        project_id=c.lastrowid
        features=_write_features(c,project_id,data.features,user['id'])
        audit(c,user['id'],'project.create','project',project_id,None,
              {'name':name,'is_enabled':bool(data.is_enabled),'features':features})
    return {'ok':True,'id':project_id}

@app.put(BASE+'/api/projects/{project_id}')
def update_project(project_id:int,data:ProjectPayload,request:Request):
    user=actor(request)
    check_permission(user,'project.edit')
    mutation(request)
    name=data.name.strip()
    if not name:
        raise HTTPException(400,'项目名称不能为空')
    with database() as c:
        c.execute('SELECT id,code,name,is_enabled,row_version FROM project WHERE id=%s FOR UPDATE',(project_id,))
        row=c.fetchone()
        if not row:
            raise HTTPException(404,'项目不存在')
        c.execute('SELECT id FROM project WHERE name=%s AND id<>%s',(name,project_id))
        if c.fetchone():
            raise HTTPException(409,'已存在同名项目')
        before={'name':row['name'],'is_enabled':bool(row['is_enabled'])}
        c.execute('''UPDATE project SET name=%s,is_enabled=%s,row_version=row_version+1,updated_by=%s,updated_at=UTC_TIMESTAMP(6)
                     WHERE id=%s''',(name,int(bool(data.is_enabled)),user['id'],project_id))
        features=_write_features(c,project_id,data.features,user['id'])
        after={'name':name,'is_enabled':bool(data.is_enabled),'features':features}
        audit(c,user['id'],'project.edit','project',project_id,before,after)
    return {'ok':True,'row_version':row['row_version']+1}

@app.patch(BASE+'/api/projects/{project_id}')
def toggle_project(project_id:int,data:ProjectStatus,request:Request):
    user=actor(request)
    check_permission(user,'project.edit')
    mutation(request)
    with database() as c:
        c.execute('SELECT id,code,is_enabled,row_version FROM project WHERE id=%s FOR UPDATE',(project_id,))
        row=c.fetchone()
        if not row:
            raise HTTPException(404,'项目不存在')
        if row['row_version']!=data.row_version:
            raise HTTPException(409,'此项目已被其他操作更新，请刷新后重试')
        if bool(row['is_enabled'])==data.is_enabled:
            return {'ok':True,'row_version':row['row_version']}
        before={'is_enabled':bool(row['is_enabled']),'row_version':row['row_version']}
        c.execute('''UPDATE project SET is_enabled=%s,row_version=row_version+1,updated_by=%s,updated_at=UTC_TIMESTAMP(6)
                     WHERE id=%s''',(int(data.is_enabled),user['id'],project_id))
        after={'is_enabled':data.is_enabled,'row_version':row['row_version']+1}
        audit(c,user['id'],'project.enable' if data.is_enabled else 'project.disable','project',project_id,before,after)
    return {'ok':True,**after}

@app.patch(BASE+'/api/projects/{project_id}/move')
def move_project(project_id:int,data:ProjectMove,request:Request):
    user=actor(request)
    check_permission(user,'project.edit')
    mutation(request)
    with database() as c:
        c.execute('SELECT id,code,display_order,row_version FROM project WHERE id=%s FOR UPDATE',(project_id,))
        row=c.fetchone()
        if not row:
            raise HTTPException(404,'项目不存在')
        if row['row_version']!=data.row_version:
            raise HTTPException(409,'此项目已被其他操作更新，请刷新后重试')
        c.execute('SELECT id,display_order FROM project ORDER BY display_order,id')
        rows=c.fetchall()
        idx=next((i for i,r in enumerate(rows) if r['id']==project_id),None)
        if idx is None:
            raise HTTPException(404,'项目不存在')
        target=idx-1 if data.direction=='up' else idx+1
        if target<0 or target>=len(rows):
            return {'ok':True,'row_version':row['row_version']}
        other=rows[target]
        a,b=rows[idx]['display_order'],other['display_order']
        c.execute('UPDATE project SET display_order=%s,row_version=row_version+1,updated_by=%s,updated_at=UTC_TIMESTAMP(6) WHERE id=%s',
                  (b,user['id'],project_id))
        c.execute('UPDATE project SET display_order=%s,row_version=row_version+1,updated_by=%s,updated_at=UTC_TIMESTAMP(6) WHERE id=%s',
                  (a,user['id'],other['id']))
        audit(c,user['id'],'project.move','project',project_id,{'from':a,'to':b},{'from':b,'to':a})
    return {'ok':True,'row_version':row['row_version']+1}

# ---- 用户管理 ----

INITIAL_PASSWORD = os.getenv('INITIAL_PASSWORD', '123456')

class UserPayload(BaseModel):
    display_name: str = Field(min_length=1,max_length=100)
    login_id: str = Field(min_length=1,max_length=100)
    role_ids: list[int] = Field(default_factory=list)
    is_enabled: bool = True

class UserStatus(BaseModel):
    is_enabled: StrictBool
    row_version: int = Field(ge=1)

def _user_role_ids(c, user_id):
    c.execute('''SELECT ur.role_id FROM sys_user_role ur
                 JOIN sys_role r ON r.id=ur.role_id
                 WHERE ur.user_id=%s ORDER BY r.id''',(user_id,))
    return [r['role_id'] for r in c.fetchall()]

def _user_is_super(c, user_id):
    c.execute('''SELECT 1 FROM sys_user_role ur JOIN sys_role r ON r.id=ur.role_id
                 WHERE ur.user_id=%s AND r.code='super_admin' LIMIT 1''',(user_id,))
    return c.fetchone() is not None

@app.get(BASE+'/api/users')
def list_users(request:Request):
    user=actor(request)
    check_permission(user,'user.view')
    can_edit=True
    try:
        check_permission(user,'user.edit')
    except HTTPException:
        can_edit=False
    can_create=True
    try:
        check_permission(user,'user.create')
    except HTTPException:
        can_create=False
    can_reset=True
    try:
        check_permission(user,'user.reset_password')
    except HTTPException:
        can_reset=False
    with database() as c:
        c.execute('SELECT id,login_id,display_name,is_enabled,row_version FROM sys_user ORDER BY id')
        rows=c.fetchall()
        c.execute('SELECT id,name,is_enabled FROM sys_role ORDER BY id')
        role_options=c.fetchall()
        c.execute('''SELECT ur.user_id, ur.role_id, r.name FROM sys_user_role ur
                     JOIN sys_role r ON r.id=ur.role_id ORDER BY r.id''')
        user_roles={}
        for r in c.fetchall():
            user_roles.setdefault(r['user_id'],[]).append({'id':r['role_id'],'name':r['name']})
    items=[]
    for r in rows:
        roles=user_roles.get(r['id'],[])
        items.append({'id':r['id'],'login_id':r['login_id'],'display_name':r['display_name'],
            'is_enabled':bool(r['is_enabled']),'row_version':r['row_version'],
            'roles':roles,'role_ids':[x['id'] for x in roles]})
    return {'items':items,'roles':[{'id':r['id'],'name':r['name'],'is_enabled':bool(r['is_enabled'])} for r in role_options],
            'can_edit':can_edit,'can_create':can_create,'can_reset':can_reset}

@app.get(BASE+'/api/users/{user_id}')
def get_user(user_id:int,request:Request):
    user=actor(request)
    check_permission(user,'user.view')
    with database() as c:
        c.execute('SELECT id,login_id,display_name,is_enabled,row_version FROM sys_user WHERE id=%s',(user_id,))
        row=c.fetchone()
        if not row:
            raise HTTPException(404,'用户不存在')
        role_ids=_user_role_ids(c,user_id)
    return {'id':row['id'],'login_id':row['login_id'],'display_name':row['display_name'],
            'is_enabled':bool(row['is_enabled']),'row_version':row['row_version'],'role_ids':role_ids}

@app.post(BASE+'/api/users')
def create_user(data:UserPayload,request:Request):
    user=actor(request)
    check_permission(user,'user.create')
    mutation(request)
    login_id=data.login_id.strip()
    display_name=data.display_name.strip()
    if not login_id:
        raise HTTPException(400,'用户ID不能为空')
    if not display_name:
        raise HTTPException(400,'用户名称不能为空')
    with database() as c:
        c.execute('SELECT id FROM sys_user WHERE login_id=%s',(login_id,))
        if c.fetchone():
            raise HTTPException(409,'已存在同用户ID')
        if data.role_ids:
            fmt=','.join(['%s']*len(data.role_ids))
            c.execute(f'SELECT id FROM sys_role WHERE id IN ({fmt})',tuple(set(data.role_ids)))
            valid={r['id'] for r in c.fetchall()}
            if len(valid)!=len(set(data.role_ids)):
                raise HTTPException(400,'包含无效的角色')
        c.execute('''INSERT INTO sys_user(login_id,display_name,password_hash,is_enabled,must_change_password,password_changed_at,created_by,updated_by)
                     VALUES(%s,%s,%s,%s,0,UTC_TIMESTAMP(6),%s,%s)''',
                  (login_id,display_name,ph.hash(INITIAL_PASSWORD),int(bool(data.is_enabled)),user['id'],user['id']))
        uid=c.lastrowid
        for rid in set(data.role_ids):
            c.execute('INSERT INTO sys_user_role(user_id,role_id,created_by) VALUES(%s,%s,%s)',(uid,rid,user['id']))
        audit(c,user['id'],'user.create','sys_user',uid,None,
              {'login_id':login_id,'display_name':display_name,'is_enabled':bool(data.is_enabled),
               'role_ids':sorted(set(data.role_ids))})
    return {'ok':True,'id':uid}

@app.put(BASE+'/api/users/{user_id}')
def update_user(user_id:int,data:UserPayload,request:Request):
    user=actor(request)
    check_permission(user,'user.edit')
    mutation(request)
    login_id=data.login_id.strip()
    display_name=data.display_name.strip()
    if not login_id:
        raise HTTPException(400,'用户ID不能为空')
    if not display_name:
        raise HTTPException(400,'用户名称不能为空')
    with database() as c:
        c.execute('SELECT id,login_id,display_name,is_enabled,auth_version,row_version FROM sys_user WHERE id=%s FOR UPDATE',(user_id,))
        row=c.fetchone()
        if not row:
            raise HTTPException(404,'用户不存在')
        c.execute('SELECT id FROM sys_user WHERE login_id=%s AND id<>%s',(login_id,user_id))
        if c.fetchone():
            raise HTTPException(409,'已存在同用户ID')
        if data.role_ids:
            fmt=','.join(['%s']*len(data.role_ids))
            c.execute(f'SELECT id FROM sys_role WHERE id IN ({fmt})',tuple(set(data.role_ids)))
            valid={r['id'] for r in c.fetchall()}
            if len(valid)!=len(set(data.role_ids)):
                raise HTTPException(400,'包含无效的角色')
        if not data.is_enabled and user_id==user['id']:
            raise HTTPException(403,'不能停用当前登录账号')
        before={'login_id':row['login_id'],'display_name':row['display_name'],
                'is_enabled':bool(row['is_enabled']),'role_ids':_user_role_ids(c,user_id)}
        bump_auth=int(not data.is_enabled and bool(row['is_enabled']))
        c.execute('''UPDATE sys_user SET login_id=%s,display_name=%s,is_enabled=%s,
                     auth_version=auth_version+%s,row_version=row_version+1,updated_by=%s,updated_at=UTC_TIMESTAMP(6)
                     WHERE id=%s''',(login_id,display_name,int(bool(data.is_enabled)),bump_auth,user['id'],user_id))
        c.execute('DELETE FROM sys_user_role WHERE user_id=%s',(user_id,))
        for rid in set(data.role_ids):
            c.execute('INSERT INTO sys_user_role(user_id,role_id,created_by) VALUES(%s,%s,%s)',(user_id,rid,user['id']))
        after={'login_id':login_id,'display_name':display_name,'is_enabled':bool(data.is_enabled),
               'role_ids':sorted(set(data.role_ids))}
        audit(c,user['id'],'user.edit','sys_user',user_id,before,after)
    return {'ok':True,'row_version':row['row_version']+1}

@app.patch(BASE+'/api/users/{user_id}')
def toggle_user(user_id:int,data:UserStatus,request:Request):
    user=actor(request)
    check_permission(user,'user.edit')
    mutation(request)
    with database() as c:
        c.execute('SELECT id,login_id,is_enabled,auth_version,row_version FROM sys_user WHERE id=%s FOR UPDATE',(user_id,))
        row=c.fetchone()
        if not row:
            raise HTTPException(404,'用户不存在')
        if not data.is_enabled and user_id==user['id']:
            raise HTTPException(403,'不能停用当前登录账号')
        if not data.is_enabled and _user_is_super(c,user_id):
            c.execute('''SELECT COUNT(*) AS cnt FROM sys_user u
                         JOIN sys_user_role ur ON ur.user_id=u.id
                         JOIN sys_role r ON r.id=ur.role_id AND r.code='super_admin'
                         WHERE u.is_enabled=1''')
            if c.fetchone()['cnt']<=1:
                raise HTTPException(403,'不能停用唯一可用的超级管理员')
        if row['row_version']!=data.row_version:
            raise HTTPException(409,'该用户已被其他操作更新，请刷新后重试')
        if bool(row['is_enabled'])==data.is_enabled:
            return {'ok':True,'row_version':row['row_version']}
        before={'is_enabled':bool(row['is_enabled']),'row_version':row['row_version']}
        bump_auth=0 if data.is_enabled else 1
        c.execute('''UPDATE sys_user SET is_enabled=%s,auth_version=auth_version+%s,
                     row_version=row_version+1,updated_by=%s,updated_at=UTC_TIMESTAMP(6) WHERE id=%s''',
                  (int(data.is_enabled),bump_auth,user['id'],user_id))
        after={'is_enabled':data.is_enabled,'row_version':row['row_version']+1}
        audit(c,user['id'],'user.enable' if data.is_enabled else 'user.disable','sys_user',user_id,before,after)
    return {'ok':True,**after}

@app.post(BASE+'/api/users/{user_id}/reset-password')
def reset_user_password(user_id:int,request:Request):
    user=actor(request)
    check_permission(user,'user.reset_password')
    mutation(request)
    with database() as c:
        c.execute('SELECT id,login_id,display_name FROM sys_user WHERE id=%s FOR UPDATE',(user_id,))
        row=c.fetchone()
        if not row:
            raise HTTPException(404,'用户不存在')
        c.execute('''UPDATE sys_user SET password_hash=%s,must_change_password=0,
                     password_changed_at=UTC_TIMESTAMP(6),auth_version=auth_version+1,
                     row_version=row_version+1,updated_by=%s,updated_at=UTC_TIMESTAMP(6) WHERE id=%s''',
                  (ph.hash(INITIAL_PASSWORD),user['id'],user_id))
        audit(c,user['id'],'user.reset_password','sys_user',user_id,
              {'login_id':row['login_id']},{'password':'系统初始密码'})
    return {'ok':True}

# ---- 指标配置 ----

class MetricPayload(BaseModel):
    name: str = Field(min_length=1,max_length=100)
    category_id: int
    project_id: int
    english_name: str = Field(default='',max_length=200)
    unit: str = Field(default='',max_length=32)
    definition: str = ''
    beidou_metric_code: str = Field(default='',max_length=100)

class MetricSwitch(BaseModel):
    is_enabled: StrictBool | None = None
    is_key_metric: StrictBool | None = None
    show_trend: StrictBool | None = None
    row_version: int = Field(ge=1)

def _metric_categories(c):
    c.execute('''SELECT id,code,name,metric_code_prefix,last_sequence,display_order,is_enabled
                 FROM metric_category ORDER BY display_order,id''')
    rows=c.fetchall()
    for r in rows:
        r['next_code']=r['metric_code_prefix']+str(r['last_sequence']+1).zfill(4)
    return rows

@app.get(BASE+'/api/metrics')
def list_metrics(request:Request):
    user=actor(request)
    check_permission(user,'metric.view')
    can_edit=True
    try:
        check_permission(user,'metric.edit')
    except HTTPException:
        can_edit=False
    can_create=True
    try:
        check_permission(user,'metric.create')
    except HTTPException:
        can_create=False
    with database() as c:
        c.execute('''SELECT m.id,m.code,m.name,m.english_name,m.unit,m.definition,m.definition_status,
                     m.is_key_metric,m.show_trend,m.is_enabled,m.row_version,m.project_id,m.category_id,
                     m.beidou_metric_code,m.display_order,p.name AS project_name,cat.name AS category_name
                     FROM metric m JOIN project p ON p.id=m.project_id
                     JOIN metric_category cat ON cat.id=m.category_id
                     ORDER BY m.display_order,m.id''')
        rows=c.fetchall()
        categories=_metric_categories(c)
        c.execute('SELECT id,name,is_enabled FROM project ORDER BY display_order,id')
        projects=c.fetchall()
    items=[]
    for r in rows:
        items.append({'id':r['id'],'code':r['code'],'name':r['name'],'english_name':r['english_name'] or '',
            'unit':r['unit'] or '','definition':r['definition'] or '',
            'definition_status':r['definition_status'],
            'is_key_metric':bool(r['is_key_metric']),'show_trend':bool(r['show_trend']),
            'is_enabled':bool(r['is_enabled']),'row_version':r['row_version'],
            'project_id':r['project_id'],'project_name':r['project_name'],
            'category_id':r['category_id'],'category_name':r['category_name'],
            'beidou_metric_code':r['beidou_metric_code'] or ''})
    return {'items':items,'can_edit':can_edit,'can_create':can_create,
            'categories':categories,
            'projects':[{'id':p['id'],'name':p['name'],'is_enabled':bool(p['is_enabled'])} for p in projects]}

@app.get(BASE+'/api/metrics/{metric_id}')
def get_metric(metric_id:int,request:Request):
    user=actor(request)
    check_permission(user,'metric.view')
    with database() as c:
        c.execute('''SELECT m.id,m.code,m.name,m.english_name,m.unit,m.definition,m.beidou_metric_code,
                     m.category_id,m.project_id,m.is_enabled,m.row_version
                     FROM metric m WHERE m.id=%s''',(metric_id,))
        row=c.fetchone()
        if not row:
            raise HTTPException(404,'指标不存在')
    return {'id':row['id'],'code':row['code'],'name':row['name'],'english_name':row['english_name'] or '',
            'unit':row['unit'] or '','definition':row['definition'] or '',
            'beidou_metric_code':row['beidou_metric_code'] or '','category_id':row['category_id'],
            'project_id':row['project_id'],'is_enabled':bool(row['is_enabled']),'row_version':row['row_version']}

def _validate_metric(c, data, metric_id=None):
    name=data.name.strip()
    if not name:
        raise HTTPException(400,'指标名称不能为空')
    c.execute('SELECT id,name,is_enabled FROM metric_category WHERE id=%s',(data.category_id,))
    cat=c.fetchone()
    if not cat:
        raise HTTPException(400,'类型不存在')
    if not cat['is_enabled']:
        raise HTTPException(400,'该类型已停用，不能用于新指标')
    c.execute('SELECT id FROM project WHERE id=%s',(data.project_id,))
    if not c.fetchone():
        raise HTTPException(400,'适用项目不存在')
    c.execute('SELECT id FROM metric WHERE project_id=%s AND name_key=%s'+(' AND id<>%s' if metric_id else ''),
              ((data.project_id,name)+(metric_id,)) if metric_id else (data.project_id,name))
    if c.fetchone():
        raise HTTPException(409,'该项目已存在同名指标，请修改指标名称或选择其他项目')
    return name

def _insert_metric_revision(c, metric_id, row, uid, changed):
    c.execute('SELECT COALESCE(MAX(revision_no),0)+1 AS next FROM metric_revision WHERE metric_id=%s',(metric_id,))
    revision_no=c.fetchone()['next']
    c.execute('''INSERT INTO metric_revision(metric_id,revision_no,name,english_name,unit,value_kind,
                 decimal_places,currency_code,scope_kind,definition,definition_status,retention_window_days,created_by)
                 VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',
              (metric_id,revision_no,changed['name'],changed['english_name'],changed['unit'],'DECIMAL',1,
               None,'PROJECT',changed['definition'],changed['definition_status'],None,uid))
    c.execute('UPDATE metric SET current_revision_id=%s WHERE id=%s',(c.lastrowid,metric_id))

@app.post(BASE+'/api/metrics')
def create_metric(data:MetricPayload,request:Request):
    user=actor(request)
    check_permission(user,'metric.create')
    mutation(request)
    with database() as c:
        name=_validate_metric(c,data)
        # 原子分配编码：类型序号递增
        c.execute('UPDATE metric_category SET last_sequence=last_sequence+1 WHERE id=%s',(data.category_id,))
        c.execute('SELECT metric_code_prefix,last_sequence FROM metric_category WHERE id=%s',(data.category_id,))
        cat=c.fetchone()
        code=cat['metric_code_prefix']+str(cat['last_sequence']).zfill(4)
        c.execute('SELECT COALESCE(MAX(display_order),0)+1 AS next FROM metric')
        display_order=c.fetchone()['next']
        english=data.english_name.strip() or None
        unit=data.unit.strip() or None
        definition=data.definition.strip() or None
        definition_status='CONFIRMED' if definition else 'PENDING'
        beidou=data.beidou_metric_code.strip() or None
        c.execute('''INSERT INTO metric(project_id,category_id,code,name,name_key,english_name,unit,
                     value_kind,decimal_places,currency_code,scope_kind,definition,definition_status,
                     retention_window_days,current_revision_id,beidou_metric_code,is_key_metric,show_trend,
                     display_order,is_enabled,created_by,updated_by)
                     VALUES(%s,%s,%s,%s,%s,%s,%s,'DECIMAL',1,NULL,'PROJECT',%s,%s,NULL,NULL,%s,0,0,%s,1,%s,%s)''',
                  (data.project_id,data.category_id,code,name,name,english,unit,definition,definition_status,
                   beidou,display_order,user['id'],user['id']))
        metric_id=c.lastrowid
        _insert_metric_revision(c,metric_id,None,user['id'],
            {'name':name,'english_name':english,'unit':unit,'definition':definition,'definition_status':definition_status})
        audit(c,user['id'],'metric.create','metric',metric_id,None,
              {'code':code,'name':name,'project_id':data.project_id,'category_id':data.category_id})
    return {'ok':True,'id':metric_id,'code':code}

@app.put(BASE+'/api/metrics/{metric_id}')
def update_metric(metric_id:int,data:MetricPayload,request:Request):
    user=actor(request)
    check_permission(user,'metric.edit')
    mutation(request)
    with database() as c:
        c.execute('''SELECT id,code,name,name_key,english_name,unit,definition,definition_status,
                     category_id,project_id,row_version FROM metric WHERE id=%s FOR UPDATE''',(metric_id,))
        row=c.fetchone()
        if not row:
            raise HTTPException(404,'指标不存在')
        name=_validate_metric(c,data,metric_id)
        if data.category_id!=row['category_id']:
            c.execute('SELECT id,is_enabled FROM metric_category WHERE id=%s',(data.category_id,))
            cat=c.fetchone()
            if not cat:
                raise HTTPException(400,'类型不存在')
            if not cat['is_enabled']:
                raise HTTPException(400,'该类型已停用，不能用于新指标')
        english=data.english_name.strip() or None
        unit=data.unit.strip() or None
        definition=data.definition.strip() or None
        definition_status='CONFIRMED' if definition else 'PENDING'
        beidou=data.beidou_metric_code.strip() or None
        before={'name':row['name'],'english_name':row['english_name'],'unit':row['unit'],
                'definition':row['definition'],'category_id':row['category_id']}
        c.execute('''UPDATE metric SET name=%s,name_key=%s,english_name=%s,unit=%s,definition=%s,
                     definition_status=%s,beidou_metric_code=%s,category_id=%s,
                     row_version=row_version+1,updated_by=%s,updated_at=UTC_TIMESTAMP(6) WHERE id=%s''',
                  (name,name,english,unit,definition,definition_status,beidou,data.category_id,
                   user['id'],metric_id))
        revision_changed=(name!=row['name'] or english!=row['english_name'] or unit!=row['unit']
                          or definition!=row['definition'] or definition_status!=row['definition_status'])
        if revision_changed:
            _insert_metric_revision(c,metric_id,row,user['id'],
                {'name':name,'english_name':english,'unit':unit,'definition':definition,'definition_status':definition_status})
        after={'name':name,'english_name':english,'unit':unit,'definition':definition,
               'category_id':data.category_id,'beidou_metric_code':beidou}
        audit(c,user['id'],'metric.edit','metric',metric_id,before,after)
    return {'ok':True,'row_version':row['row_version']+1}

@app.patch(BASE+'/api/metrics/{metric_id}')
def toggle_metric(metric_id:int,data:MetricSwitch,request:Request):
    user=actor(request)
    check_permission(user,'metric.edit')
    mutation(request)
    fields=[f for f in ('is_enabled','is_key_metric','show_trend') if getattr(data,f) is not None]
    if len(fields)!=1:
        raise HTTPException(400,'一次只能切换一个开关')
    field=fields[0]
    value=bool(getattr(data,field))
    with database() as c:
        c.execute('SELECT id,code,name,is_enabled,is_key_metric,show_trend,row_version FROM metric WHERE id=%s FOR UPDATE',(metric_id,))
        row=c.fetchone()
        if not row:
            raise HTTPException(404,'指标不存在')
        if row['row_version']!=data.row_version:
            raise HTTPException(409,'该指标已被其他操作更新，请刷新后重试')
        if bool(row[field])==value:
            return {'ok':True,'row_version':row['row_version']}
        c.execute(f'UPDATE metric SET {field}=%s,row_version=row_version+1,updated_by=%s,updated_at=UTC_TIMESTAMP(6) WHERE id=%s',
                  (int(value),user['id'],metric_id))
        if field=='is_enabled':
            action='metric.enable' if value else 'metric.disable'
        elif field=='is_key_metric':
            action='metric.key'
        else:
            action='metric.trend'
        audit(c,user['id'],action,'metric',metric_id,
              {field:bool(row[field])},{field:value})
    return {'ok':True,'row_version':row['row_version']+1}

# ---- 数据维护 ----

def _business_today():
    # 业务时区 Asia/Shanghai
    return (datetime.utcnow()+timedelta(hours=8)).date()

def _maintain_categories(c):
    c.execute('SELECT id,name,code FROM metric_category WHERE is_enabled=1 ORDER BY display_order,id')
    return c.fetchall()

@app.get(BASE+'/api/maintain/bootstrap')
def maintain_bootstrap(request:Request):
    user=actor(request)
    check_permission(user,'maintain.view')
    can_edit=True
    try:
        check_permission(user,'maintain.edit')
    except HTTPException:
        can_edit=False
    with database() as c:
        categories=_maintain_categories(c)
        c.execute('''SELECT m.id,m.code,m.name,m.unit,m.definition,m.definition_status,m.decimal_places,
                     m.project_id,m.category_id FROM metric m JOIN project p ON p.id=m.project_id
                     WHERE m.is_enabled=1 AND p.is_enabled=1
                     ORDER BY m.category_id,m.display_order,m.id''')
        metrics=c.fetchall()
        c.execute('SELECT id,name FROM project WHERE is_enabled=1 ORDER BY display_order,id')
        projects=c.fetchall()
        c.execute('SELECT id,project_id,name FROM project_feature WHERE archived_at IS NULL ORDER BY project_id,display_order,id')
        features=c.fetchall()
    return {'can_edit':can_edit,
            'categories':[{'id':r['id'],'name':r['name'],'code':r['code']} for r in categories],
            'projects':[{'id':r['id'],'name':r['name']} for r in projects],
            'features':[{'id':r['id'],'project_id':r['project_id'],'name':r['name']} for r in features],
            'metrics':[{'id':r['id'],'code':r['code'],'name':r['name'],'unit':r['unit'] or '',
                        'definition':r['definition'] or '','definition_status':r['definition_status'],
                        'decimal_places':r['decimal_places'],'project_id':r['project_id'],
                        'category_id':r['category_id']} for r in metrics]}

@app.get(BASE+'/api/maintain/data')
def maintain_data(request:Request, project_id:int, stat_date:str):
    user=actor(request)
    check_permission(user,'maintain.view')
    try:
        date=datetime.strptime(stat_date,'%Y-%m-%d').date()
    except ValueError:
        raise HTTPException(400,'统计日期格式无效')
    with database() as c:
        c.execute('''SELECT metric_id,feature_id,value_number FROM metric_entry
                     WHERE project_id=%s AND stat_date=%s''',(project_id,date))
        rows=c.fetchall()
    return {'items':[{'metric_id':r['metric_id'],'feature_id':r['feature_id'],
                      'value':str(r['value_number'])} for r in rows]}

class MaintainItem(BaseModel):
    metric_id: int
    feature_id: int | None = None
    value: str | None = Field(default=None,max_length=32)

class MaintainSave(BaseModel):
    project_id: int
    stat_date: str
    items: list[MaintainItem] = Field(min_length=1,max_length=500)

def _validate_value(raw, metric):
    unit=metric['unit'] or ''
    dp=metric['decimal_places'] if metric['decimal_places'] and 1<=metric['decimal_places']<=6 else 6
    if unit in ('人','次'):
        if not re.fullmatch(r'\d+',raw):
            raise HTTPException(400,f'「{metric["name"]}」请输入非负整数')
        return raw
    if not re.fullmatch(r'\d+(\.\d{1,'+str(dp)+r'})?',raw):
        raise HTTPException(400,f'「{metric["name"]}」请输入非负数，最多 {dp} 位小数')
    if unit=='%' and float(raw)>100:
        raise HTTPException(400,f'「{metric["name"]}」比例应在 0～100 之间')
    return raw

@app.post(BASE+'/api/maintain/data')
def maintain_save(data:MaintainSave,request:Request):
    user=actor(request)
    check_permission(user,'maintain.edit')
    mutation(request)
    try:
        date=datetime.strptime(data.stat_date,'%Y-%m-%d').date()
    except ValueError:
        raise HTTPException(400,'统计日期格式无效')
    today=_business_today()
    if date>today:
        raise HTTPException(400,'不能保存未来统计日的数据')
    with database() as c:
        c.execute('''SELECT m.id,m.name,m.unit,m.decimal_places,m.category_id,cat.code AS cat_code
                     FROM metric m JOIN metric_category cat ON cat.id=m.category_id
                     WHERE m.project_id=%s AND m.is_enabled=1''',(data.project_id,))
        metric_map={r['id']:r for r in c.fetchall()}
        c.execute('SELECT id FROM project_feature WHERE project_id=%s AND archived_at IS NULL',(data.project_id,))
        feature_ids={r['id'] for r in c.fetchall()}
        has_retention=False
        prepared=[]
        for item in data.items:
            mrow=metric_map.get(item.metric_id)
            if not mrow:
                raise HTTPException(400,'指标不存在或已停用，请刷新后重试')
            if mrow['cat_code']=='retention':
                has_retention=True
            if item.feature_id is not None:
                if item.feature_id not in feature_ids:
                    raise HTTPException(400,'所选功能不存在或已归档')
                if mrow['cat_code']!='feature':
                    raise HTTPException(400,f'「{mrow["name"]}」不支持按功能录入')
            elif mrow['cat_code']=='feature':
                raise HTTPException(400,f'「{mrow["name"]}」为功能使用指标，需按功能逐行录入')
            raw=(item.value or '').strip()
            prepared.append((item.metric_id,item.feature_id,_validate_value(raw,mrow) if raw else None))
        if has_retention and date>today-timedelta(days=7):
            raise HTTPException(400,'7日留存仅可保存第 7 天观察日已结束的数据（统计日期不晚于 7 天前）')
        # 生效值 = 库中已有值 + 本次提交值，用于跨指标校验
        c.execute('''SELECT metric_id,feature_id,value_number FROM metric_entry
                     WHERE project_id=%s AND stat_date=%s''',(data.project_id,date))
        effective={(r['metric_id'],r['feature_id'] or 0):str(r['value_number']) for r in c.fetchall()}
        for mid,fid,raw in prepared:
            key=(mid,fid or 0)
            if raw is None:
                effective.pop(key,None)
            else:
                effective[key]=raw
        by_name={}
        for m in metric_map.values():
            by_name.setdefault(m['cat_code'],{})[m['name']]=m['id']
        def val(code,name):
            mid=by_name.get(code,{}).get(name)
            return effective.get((mid,0)) if mid is not None else None
        cov_cum,cov_en=val('coverage','累计使用用户数'),val('coverage','开通用户数')
        if cov_cum and cov_en and float(cov_cum)>float(cov_en):
            raise HTTPException(400,'累计使用用户数不能超过开通用户数')
        ttft,full=val('performance','平均首字响应时长'),val('performance','平均完整响应时长')
        if ttft and full and float(ttft)>float(full):
            raise HTTPException(400,'平均完整响应时长不能小于平均首字响应时长')
        sessions,avg=val('depth','有效会话数'),val('depth','每次会话平均时长')
        if sessions is not None and float(sessions)==0 and avg is not None:
            raise HTTPException(400,'有效会话数为 0 时，每次会话平均时长应留空')
        # 功能使用：同一功能 日使用人数 <= 累计使用人数
        feature_day={}
        for (mid,fkey),v in effective.items():
            m=metric_map.get(mid)
            if m and m['cat_code']=='feature' and m['name']=='功能日使用人数':
                feature_day[fkey]=v
        for (mid,fkey),v in effective.items():
            m=metric_map.get(mid)
            if m and m['cat_code']=='feature' and m['name']=='功能累计使用人数':
                day=feature_day.get(fkey)
                if day is not None and float(day)>float(v):
                    raise HTTPException(400,'功能日使用人数不能超过其累计使用人数')
        saved=0
        for mid,fid,raw in prepared:
            c.execute('''SELECT id,value_number FROM metric_entry
                         WHERE project_id=%s AND metric_id=%s AND stat_date=%s AND feature_id<=>%s''',
                      (data.project_id,mid,date,fid))
            row=c.fetchone()
            mname=metric_map[mid]['name']
            if raw is None:
                if row:
                    c.execute('DELETE FROM metric_entry WHERE id=%s',(row['id'],))
                    audit(c,user['id'],'maintain.clear','metric_entry',row['id'],
                          {'metric':mname,'stat_date':data.stat_date,'value':str(row['value_number'])},None)
                    saved+=1
            elif row is None:
                c.execute('''INSERT INTO metric_entry(project_id,metric_id,feature_id,stat_date,value_number,created_by,updated_by)
                             VALUES(%s,%s,%s,%s,%s,%s,%s)''',
                          (data.project_id,mid,fid,date,raw,user['id'],user['id']))
                audit(c,user['id'],'maintain.save','metric_entry',c.lastrowid,None,
                      {'metric':mname,'stat_date':data.stat_date,'value':raw})
                saved+=1
            elif str(row['value_number'])!=raw:
                c.execute('''UPDATE metric_entry SET value_number=%s,row_version=row_version+1,
                             updated_by=%s,updated_at=UTC_TIMESTAMP(6) WHERE id=%s''',
                          (raw,user['id'],row['id']))
                audit(c,user['id'],'maintain.save','metric_entry',row['id'],
                      {'metric':mname,'stat_date':data.stat_date,'value':str(row['value_number'])},
                      {'metric':mname,'stat_date':data.stat_date,'value':raw})
                saved+=1
    return {'ok':True,'saved':saved}

@app.get(BASE+'/login')
def login_page():
    return FileResponse(ROOT/'static/login.html')

@app.get(BASE+'/')
@app.get(BASE+'/maintain')
@app.get(BASE+'/settings/menus')
@app.get(BASE+'/settings/roles')
@app.get(BASE+'/settings/projects')
@app.get(BASE+'/settings/users')
@app.get(BASE+'/settings/metrics')
def protected_page(request:Request):
    try:
        user=actor(request)
        if request.url.path.endswith('/maintain'):
            check_permission(user,'maintain.view')
        elif request.url.path.endswith('/settings/menus'):
            check_permission(user,'menu.view')
        elif request.url.path.endswith('/settings/roles'):
            check_permission(user,'role.view')
        elif request.url.path.endswith('/settings/projects'):
            check_permission(user,'project.view')
        elif request.url.path.endswith('/settings/users'):
            check_permission(user,'user.view')
        elif request.url.path.endswith('/settings/metrics'):
            check_permission(user,'metric.view')
    except HTTPException as e:
        if e.status_code==401:
            return RedirectResponse(BASE+'/login',status_code=303)
        raise
    return FileResponse(ROOT/'static/app.html')

@app.get(BASE)
def slash():
    return RedirectResponse(BASE+'/',status_code=307)

@app.get(BASE+'/health')
def health():
    with database() as c:
        c.execute('SELECT 1')
    return {'status':'ok'}

app.mount(BASE+'/assets',StaticFiles(directory=ROOT/'static'),name='assets')
