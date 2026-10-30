"""Dashboard: authenticated administration. All database timestamps are UTC."""
import hashlib, hmac, json, os, secrets, threading, time
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

@app.get(BASE+'/login')
def login_page():
    return FileResponse(ROOT/'static/login.html')

@app.get(BASE+'/')
@app.get(BASE+'/settings/menus')
def protected_page(request:Request):
    try:
        user=actor(request)
        if request.url.path.endswith('/settings/menus'):
            check_permission(user,'menu.view')
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
