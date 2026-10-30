-- Dashboard 应用账号 dashboard_app 的最小权限授权
-- 说明：本文件用于统一管理应用运行账号的数据库授权，便于新增功能/表时同步补权、以及重装时一键复现。
-- 账号 host 为 Docker 网关 IP（pet-db 容器映射），当前为 172.17.0.1；若重建容器导致 host 变化需同步调整。
-- 执行方式（在服务器上）：docker exec -i pet-db sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot' < grants_app.sql

-- 用户与权限（应用运行账号）
-- 已存在账号时 GRANT 为幂等操作，可重复执行。

-- 审计日志：仅插入
GRANT INSERT ON dashboard.audit_log TO 'dashboard_app'@'172.17.0.1';

-- 会话：查询 + 插入 + 更新 revoked_at（登出/吊销）
GRANT SELECT, INSERT, UPDATE (`revoked_at`) ON dashboard.auth_session TO 'dashboard_app'@'172.17.0.1';

-- 菜单：查询 + 启停/版本维护
GRANT SELECT, UPDATE (`is_enabled`, `row_version`, `updated_at`, `updated_by`) ON dashboard.sys_menu TO 'dashboard_app'@'172.17.0.1';

-- 权限：仅查询
GRANT SELECT ON dashboard.sys_permission TO 'dashboard_app'@'172.17.0.1';

-- 角色：查询 + 增删改（角色管理功能）
GRANT SELECT, INSERT, UPDATE, DELETE ON dashboard.sys_role TO 'dashboard_app'@'172.17.0.1';

-- 角色-权限关联：查询 + 增删（角色授权配置）
GRANT SELECT, INSERT, DELETE ON dashboard.sys_role_permission TO 'dashboard_app'@'172.17.0.1';

-- 角色-项目关联：查询 + 增删（角色项目范围）
GRANT SELECT, INSERT, DELETE ON dashboard.sys_role_project TO 'dashboard_app'@'172.17.0.1';

-- 用户-角色关联：查询 + 增删（用户管理：分配/调整角色）
GRANT SELECT, INSERT, DELETE ON dashboard.sys_user_role TO 'dashboard_app'@'172.17.0.1';

-- 用户：查询 + 插入 + 更新（登录记录 + 用户管理：新增/编辑/启停/重置密码）
GRANT SELECT, INSERT, UPDATE (`last_login_at`, `display_name`, `login_id`, `password_hash`, `is_enabled`, `must_change_password`, `password_changed_at`, `auth_version`, `row_version`, `updated_at`, `updated_by`) ON dashboard.sys_user TO 'dashboard_app'@'172.17.0.1';

-- 项目：查询 + 增删改（项目管理功能：新增/编辑/启停/排序）
GRANT SELECT, INSERT, UPDATE, DELETE ON dashboard.project TO 'dashboard_app'@'172.17.0.1';

-- 项目功能清单：查询 + 增删改（项目管理功能清单维护）
GRANT SELECT, INSERT, UPDATE, DELETE ON dashboard.project_feature TO 'dashboard_app'@'172.17.0.1';

FLUSH PRIVILEGES;
