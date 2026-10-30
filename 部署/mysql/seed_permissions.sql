-- Dashboard 权限数据扩充脚本（幂等，可重复执行）
-- 说明：补齐「数据维护」菜单缺失的「查看修改记录」权限项，并将该权限授予超级管理员。
-- 背景：数据维护原型含 4 个功能入口（指标录入 / 批量导入 / 校验与修改记录 / 云文档同步），
--       原权限数据仅覆盖「查看 / 编辑 / 批量导入 / 云文档同步」，缺少「查看修改记录」。
-- 执行方式（在服务器上）：
--   docker exec -i pet-db sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot --default-character-set=utf8mb4' < seed_permissions.sql

USE `dashboard`;
SET NAMES utf8mb4;

-- 1) 菜单「数据维护」缺失的权限项：查看修改记录
INSERT INTO `sys_permission`
  (`menu_id`, `code`, `name`, `action_key`, `display_order`, `is_enabled`, `created_by`, `updated_by`)
SELECT m.`id`, 'maintain.record_view', '查看修改记录', 'record_view', 4, 1, u.`id`, u.`id`
FROM `sys_menu` m
CROSS JOIN (SELECT `id` FROM `sys_user` WHERE `login_id`='admin' LIMIT 1) u
WHERE m.`code`='maintain'
  AND NOT EXISTS (
    SELECT 1 FROM `sys_permission` p WHERE p.`code`='maintain.record_view'
  );

-- 2) 将新权限授予超级管理员角色（幂等）
INSERT INTO `sys_role_permission` (`role_id`, `permission_id`, `created_by`)
SELECT r.`id`, p.`id`, u.`id`
FROM `sys_role` r
JOIN `sys_permission` p ON p.`code`='maintain.record_view'
CROSS JOIN (SELECT `id` FROM `sys_user` WHERE `login_id`='admin' LIMIT 1) u
WHERE r.`code`='super_admin'
  AND NOT EXISTS (
    SELECT 1 FROM `sys_role_permission` rp WHERE rp.`role_id`=r.`id` AND rp.`permission_id`=p.`id`
  );
