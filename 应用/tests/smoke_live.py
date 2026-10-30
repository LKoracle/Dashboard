"""Live integration check. Password comes from stdin, never a file or argv.
Temporarily toggles the metric menu and restores it, retaining audit evidence.
"""
import getpass,json,sys
import httpx
origin='https://129.226.194.82'
password=getpass.getpass('Admin password: ') if sys.stdin.isatty() else sys.stdin.readline().rstrip('\n')
results={}
with httpx.Client(base_url=origin,trust_env=False,timeout=20) as c:
    root='/dashboard'
    assert c.get(root+'/settings/menus',follow_redirects=False).status_code==303
    assert c.get(root+'/api/menus').status_code==401
    results['unauthenticated_blocked']=True
    response=c.post(root+'/api/login',headers={'origin':origin},json={'login_id':'admin','password':password})
    password=None
    assert response.status_code==200, (response.status_code,response.text)
    cookie=response.headers['set-cookie'].lower()
    assert 'secure' in cookie and 'httponly' in cookie and 'samesite=strict' in cookie
    results['login_secure_session']=True
    user=c.get(root+'/api/me').json()
    assert user['login_id']=='admin' and user['is_super']
    results['super_admin_verified']=True
    headers={'origin':origin,'x-csrf-token':user['csrf_token']}
    menus=c.get(root+'/api/menus').json()
    assert len(menus['items'])==10 and menus['can_edit']
    assert all(m['name']!='项目指标详情' for m in menus['items'])
    results['menu_tree_and_permissions']=True
    row=next(m for m in menus['items'] if m['code']=='metric')
    url=root+'/api/menus/'+str(row['id'])
    state=bool(row['is_enabled']); version=row['row_version']
    try:
        response=c.patch(url,headers=headers,json={'is_enabled':not state,'row_version':version})
        assert response.status_code==200,response.text
        changed=next(m for m in c.get(root+'/api/menus').json()['items'] if m['id']==row['id'])
        assert bool(changed['is_enabled'])!=state and changed['row_version']==version+1
        results['menu_change_persisted']=True
        assert c.patch(url,headers=headers,json={'is_enabled':state,'row_version':version}).status_code==409
        results['optimistic_lock']=True
        assert c.patch(url,headers={'origin':origin},json={'is_enabled':state,'row_version':version+1}).status_code==403
        results['csrf_enforced']=True
    finally:
        current=next(m for m in c.get(root+'/api/menus').json()['items'] if m['id']==row['id'])
        if bool(current['is_enabled'])!=state:
            r=c.patch(url,headers=headers,json={'is_enabled':state,'row_version':current['row_version']})
            assert r.status_code==200,'RESTORE FAILED'
    results['menu_original_state_restored']=True
    assert c.post(root+'/api/logout',headers=headers).status_code==200
    assert c.get(root+'/api/me').status_code==401
    results['logout_revokes_session']=True
print(json.dumps(results,ensure_ascii=False,indent=2))
