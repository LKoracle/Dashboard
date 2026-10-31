"""One-time seed. Expects an Argon2 hash on stdin; never resets an existing admin."""
import json, re, sys
from app import database, audit

MENUS=[
 ('home','首页',None,'/', ['查看']),
 ('maintain','数据维护',None,None,['查看','编辑','批量导入','云文档同步']),
 ('settings','设置管理',None,None,[]),
 ('project','项目管理','settings',None,['查看','新增项目','编辑项目']),
 ('metric','指标管理','settings',None,['查看','新增指标','编辑指标']),
 ('funnel','漏斗管理','settings',None,['查看','新增漏斗','编辑漏斗','启用','停用']),
 ('permission','权限配置','settings',None,[]),
 ('menu','菜单管理','permission','/settings/menus',['查看','编辑','新增']),
 ('role','角色管理','permission',None,['查看','编辑','新增']),
 ('user','用户管理','permission',None,['查看','编辑','新增','重置密码'])]
ACTIONS={'查看':'view','编辑':'edit','新增':'create','重置密码':'reset_password','批量导入':'import','云文档同步':'sync','启用':'enable','停用':'disable','新增项目':'create','编辑项目':'edit','新增指标':'create','编辑指标':'edit','新增漏斗':'create','编辑漏斗':'edit'}

def seed(password_hash):
    if not re.fullmatch(r'\$argon2id\$[^\n]{50,240}',password_hash):
        raise ValueError('Provide an Argon2id hash, not a plaintext password')
    with database() as c:
        c.execute('SELECT id FROM sys_user WHERE login_id=%s',('admin',))
        existing=c.fetchone()
        if existing:
            raise RuntimeError('admin already exists; bootstrap refuses to alter credentials')
        c.execute('INSERT INTO sys_user(login_id,display_name,password_hash,must_change_password,password_changed_at) VALUES(%s,%s,%s,0,UTC_TIMESTAMP(6))',('admin','管理员',password_hash))
        uid=c.lastrowid
        c.execute("INSERT INTO sys_role(code,name) VALUES('super_admin','超级管理员')")
        rid=c.lastrowid
        c.execute('INSERT INTO sys_user_role(user_id,role_id,created_by) VALUES(%s,%s,%s)',(uid,rid,uid))
        ids={}
        for order,(code,name,parent,route,permissions) in enumerate(MENUS,1):
            c.execute('INSERT INTO sys_menu(code,name,parent_id,route_path,display_order,created_by,updated_by) VALUES(%s,%s,%s,%s,%s,%s,%s)',(code,name,ids.get(parent),route,order,uid,uid))
            mid=c.lastrowid
            ids[code]=mid
            for n,label in enumerate(permissions):
                action=ACTIONS[label]
                c.execute('INSERT INTO sys_permission(menu_id,code,name,action_key,display_order,created_by,updated_by) VALUES(%s,%s,%s,%s,%s,%s,%s)',(mid,code+'.'+action,label,action,n,uid,uid))
                c.execute('INSERT INTO sys_role_permission(role_id,permission_id,created_by) VALUES(%s,%s,%s)',(rid,c.lastrowid,uid))
        audit(c,uid,'system.bootstrap','sys_user',uid,after={'login_id':'admin','role':'super_admin','menus':len(ids)})
    print(json.dumps({'admin_created':True,'menus':len(ids),'role':'super_admin'}))

if __name__=='__main__':
    seed(sys.stdin.read().strip())
