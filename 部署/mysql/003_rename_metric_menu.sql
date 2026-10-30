-- 用户确认的菜单文案调整；保持菜单编码、路由、权限及启用状态不变。
-- 使用 utf8mb4 连接执行；按旧名称匹配，可重复执行。
START TRANSACTION;
INSERT INTO audit_log(source_type,action_code,entity_type,entity_id,entity_version,before_payload,after_payload,result)
SELECT 'SYSTEM','menu.rename','sys_menu',id,row_version+1,
       JSON_OBJECT('name',name),JSON_OBJECT('name','指标管理'),'SUCCESS'
FROM sys_menu WHERE code='metric' AND name='指标配置';
UPDATE sys_menu SET name='指标管理',row_version=row_version+1,updated_at=UTC_TIMESTAMP(6)
WHERE code='metric' AND name='指标配置';
COMMIT;
SELECT code,name FROM sys_menu WHERE code='metric';
