-- 指标类型初始化（metric_category）：7 个类型与原型编码前缀
-- 幂等：依赖 code/name/metric_code_prefix 唯一键，重复执行不会产生重复行
-- 执行方式（在服务器上）：docker exec -i pet-db sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot dashboard' < seed_metric_categories.sql

INSERT IGNORE INTO metric_category(code,name,metric_code_prefix,last_sequence,display_order,is_enabled,created_by,updated_by) VALUES
 ('coverage','用户覆盖','YHFG',0,1,1,1,1),
 ('activity','用户活跃','YHHY',0,2,1,1,1),
 ('depth','使用深度','SYSD',0,3,1,1,1),
 ('retention','用户留存','YHLC',0,4,1,1,1),
 ('feature','功能使用','GNSY',0,5,1,1,1),
 ('performance','性能表现','XNBX',0,6,1,1,1),
 ('funnel','漏斗指标','LDZB',0,7,1,1,1);
