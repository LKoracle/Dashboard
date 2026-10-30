-- 指标手工录入数据表（数据维护功能）
-- 定位规则：同一项目 + 同一指标 + 同一功能（功能使用类，其他类型为 NULL）+ 同一统计日唯一定位一条数据。
-- value_number 为 NULL 的行不落库：清空保存即删除行，等价于「未维护」状态。
-- feature_key 为生成列（IFNULL(feature_id,0)）：MySQL 唯一索引对 NULL 不去重，用 0 占位保证唯一性。
-- 执行方式（在服务器上）：docker exec -i pet-db sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot --default-character-set=utf8mb4 dashboard' < 002_metric_entry.sql

CREATE TABLE IF NOT EXISTS dashboard.metric_entry (
  id BIGINT NOT NULL AUTO_INCREMENT,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  created_by BIGINT NULL,
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_by BIGINT NULL,
  row_version BIGINT NOT NULL DEFAULT 1,
  project_id BIGINT NOT NULL,
  metric_id BIGINT NOT NULL,
  feature_id BIGINT NULL,
  feature_key BIGINT AS (IFNULL(feature_id, 0)) STORED NOT NULL,
  stat_date DATE NOT NULL,
  value_number DECIMAL(24,6) NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_metric_entry (project_id, metric_id, feature_key, stat_date),
  KEY ix_metric_entry_1 (project_id, stat_date),
  KEY ix_metric_entry_2 (metric_id),
  CONSTRAINT fk_me_user_create FOREIGN KEY (created_by) REFERENCES dashboard.sys_user (id),
  CONSTRAINT fk_me_user_update FOREIGN KEY (updated_by) REFERENCES dashboard.sys_user (id),
  CONSTRAINT fk_me_project FOREIGN KEY (project_id) REFERENCES dashboard.project (id),
  CONSTRAINT fk_me_metric FOREIGN KEY (metric_id) REFERENCES dashboard.metric (id),
  CONSTRAINT fk_me_feature FOREIGN KEY (feature_id) REFERENCES dashboard.project_feature (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_as_cs COMMENT='指标手工录入数据表';
