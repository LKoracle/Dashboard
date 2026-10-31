-- 005: 移除「数据维护-云文档同步」权限（功能已在数据维护改版中删除）
-- 幂等：可重复执行。
DELETE rp FROM sys_role_permission rp
  JOIN sys_permission p ON p.id=rp.permission_id
  WHERE p.code='maintain.sync';
DELETE FROM sys_permission WHERE code='maintain.sync';
SELECT COUNT(*) AS sync_left FROM sys_permission WHERE code='maintain.sync';
