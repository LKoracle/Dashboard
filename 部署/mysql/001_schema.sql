-- Dashboard physical schema v1; MySQL 8.0.45; 2026-10-30

-- Single-run migration. No DROP, no overwrite, no account/password changes.

SET NAMES utf8mb4 COLLATE utf8mb4_0900_as_cs;

SET SESSION time_zone = '+00:00';

CREATE DATABASE `dashboard` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_as_cs;

USE `dashboard`;

CREATE TABLE `project` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `created_by` BIGINT NULL DEFAULT NULL,
  `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_by` BIGINT NULL DEFAULT NULL,
  `row_version` BIGINT NOT NULL DEFAULT 1,
  `code` VARCHAR(64) NOT NULL,
  `name` VARCHAR(100) NOT NULL,
  `is_enabled` BOOLEAN NOT NULL DEFAULT 1,
  `display_order` INT NOT NULL DEFAULT 0,
  `business_timezone` VARCHAR(64) NOT NULL DEFAULT 'Asia/Shanghai',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_project_1` (`code`),
  KEY `ix_project_1` (`is_enabled`, `display_order`, `id`),
  CONSTRAINT `ck_project_1` CHECK (`row_version` >= 1),
  CONSTRAINT `ck_project_2` CHECK (`is_enabled` IN (0,1)),
  CONSTRAINT `ck_project_3` CHECK (`display_order` >= 0)
) ENGINE=InnoDB COMMENT='项目表';

CREATE TABLE `project_feature` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `created_by` BIGINT NULL DEFAULT NULL,
  `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_by` BIGINT NULL DEFAULT NULL,
  `row_version` BIGINT NOT NULL DEFAULT 1,
  `project_id` BIGINT NOT NULL,
  `code` VARCHAR(64) NOT NULL,
  `name` VARCHAR(100) NOT NULL,
  `display_order` INT NOT NULL DEFAULT 0,
  `archived_at` DATETIME(6) NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_project_feature_1` (`project_id`, `code`),
  UNIQUE KEY `uq_project_feature_2` (`project_id`, `name`),
  UNIQUE KEY `uq_project_feature_3` (`project_id`, `id`),
  CONSTRAINT `ck_project_feature_1` CHECK (`row_version` >= 1),
  CONSTRAINT `ck_project_feature_2` CHECK (`display_order` >= 0)
) ENGINE=InnoDB COMMENT='项目功能表';

CREATE TABLE `metric_category` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `created_by` BIGINT NULL DEFAULT NULL,
  `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_by` BIGINT NULL DEFAULT NULL,
  `row_version` BIGINT NOT NULL DEFAULT 1,
  `code` VARCHAR(32) NOT NULL,
  `name` VARCHAR(50) NOT NULL,
  `metric_code_prefix` VARCHAR(16) NOT NULL,
  `last_sequence` BIGINT NOT NULL DEFAULT 0,
  `display_order` INT NOT NULL DEFAULT 0,
  `is_enabled` BOOLEAN NOT NULL DEFAULT 1,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_metric_category_1` (`code`),
  UNIQUE KEY `uq_metric_category_2` (`name`),
  UNIQUE KEY `uq_metric_category_3` (`metric_code_prefix`),
  CONSTRAINT `ck_metric_category_1` CHECK (`row_version` >= 1),
  CONSTRAINT `ck_metric_category_2` CHECK (`last_sequence` >= 0),
  CONSTRAINT `ck_metric_category_3` CHECK (`display_order` >= 0),
  CONSTRAINT `ck_metric_category_4` CHECK (`is_enabled` IN (0,1))
) ENGINE=InnoDB COMMENT='指标类型表';

CREATE TABLE `metric` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `created_by` BIGINT NULL DEFAULT NULL,
  `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_by` BIGINT NULL DEFAULT NULL,
  `row_version` BIGINT NOT NULL DEFAULT 1,
  `project_id` BIGINT NOT NULL,
  `category_id` BIGINT NOT NULL,
  `code` VARCHAR(32) NOT NULL,
  `name` VARCHAR(100) NOT NULL,
  `name_key` VARCHAR(100) NOT NULL,
  `english_name` VARCHAR(200) NULL DEFAULT NULL,
  `unit` VARCHAR(32) NULL DEFAULT NULL,
  `value_kind` VARCHAR(16) NOT NULL,
  `decimal_places` SMALLINT NOT NULL,
  `currency_code` VARCHAR(3) NULL DEFAULT NULL,
  `scope_kind` VARCHAR(16) NOT NULL,
  `definition` TEXT NULL,
  `definition_status` VARCHAR(16) NOT NULL,
  `retention_window_days` SMALLINT NULL DEFAULT NULL,
  `current_revision_id` BIGINT NULL DEFAULT NULL,
  `beidou_metric_code` VARCHAR(100) NULL DEFAULT NULL,
  `is_key_metric` BOOLEAN NOT NULL DEFAULT 0,
  `show_trend` BOOLEAN NOT NULL DEFAULT 0,
  `display_order` INT NOT NULL DEFAULT 0,
  `is_enabled` BOOLEAN NOT NULL DEFAULT 1,
  `archived_at` DATETIME(6) NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_metric_1` (`code`),
  UNIQUE KEY `uq_metric_2` (`project_id`, `name_key`),
  UNIQUE KEY `uq_metric_3` (`project_id`, `id`),
  KEY `ix_metric_1` (`project_id`, `is_enabled`, `display_order`, `id`),
  KEY `ix_metric_2` (`project_id`, `is_key_metric`, `is_enabled`),
  KEY `ix_metric_3` (`project_id`, `category_id`, `is_enabled`),
  CONSTRAINT `ck_metric_1` CHECK (value_kind IN ('COUNT','RATE','DURATION','AMOUNT','DECIMAL')),
  CONSTRAINT `ck_metric_2` CHECK (scope_kind IN ('PROJECT','FEATURE')),
  CONSTRAINT `ck_metric_3` CHECK (definition_status IN ('PENDING','CONFIRMED')),
  CONSTRAINT `ck_metric_4` CHECK (decimal_places BETWEEN 0 AND 6),
  CONSTRAINT `ck_metric_5` CHECK (value_kind <> 'COUNT' OR decimal_places = 0),
  CONSTRAINT `ck_metric_6` CHECK (retention_window_days IS NULL OR retention_window_days > 0),
  CONSTRAINT `ck_metric_7` CHECK (`row_version` >= 1),
  CONSTRAINT `ck_metric_8` CHECK (`is_key_metric` IN (0,1)),
  CONSTRAINT `ck_metric_9` CHECK (`show_trend` IN (0,1)),
  CONSTRAINT `ck_metric_10` CHECK (`display_order` >= 0),
  CONSTRAINT `ck_metric_11` CHECK (`is_enabled` IN (0,1))
) ENGINE=InnoDB COMMENT='指标表';

CREATE TABLE `metric_revision` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `metric_id` BIGINT NOT NULL,
  `revision_no` INT NOT NULL,
  `name` VARCHAR(100) NOT NULL,
  `english_name` VARCHAR(200) NULL DEFAULT NULL,
  `unit` VARCHAR(32) NULL DEFAULT NULL,
  `value_kind` VARCHAR(16) NOT NULL,
  `decimal_places` SMALLINT NOT NULL,
  `currency_code` VARCHAR(3) NULL DEFAULT NULL,
  `scope_kind` VARCHAR(16) NOT NULL,
  `definition` TEXT NULL,
  `definition_status` VARCHAR(16) NOT NULL,
  `retention_window_days` SMALLINT NULL DEFAULT NULL,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `created_by` BIGINT NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_metric_revision_1` (`metric_id`, `revision_no`),
  UNIQUE KEY `uq_metric_revision_2` (`metric_id`, `id`),
  CONSTRAINT `ck_metric_revision_1` CHECK (value_kind IN ('COUNT','RATE','DURATION','AMOUNT','DECIMAL')),
  CONSTRAINT `ck_metric_revision_2` CHECK (scope_kind IN ('PROJECT','FEATURE')),
  CONSTRAINT `ck_metric_revision_3` CHECK (definition_status IN ('PENDING','CONFIRMED')),
  CONSTRAINT `ck_metric_revision_4` CHECK (decimal_places BETWEEN 0 AND 6),
  CONSTRAINT `ck_metric_revision_5` CHECK (value_kind <> 'COUNT' OR decimal_places = 0),
  CONSTRAINT `ck_metric_revision_6` CHECK (revision_no >= 1),
  CONSTRAINT `ck_metric_revision_7` CHECK (retention_window_days IS NULL OR retention_window_days > 0)
) ENGINE=InnoDB COMMENT='指标口径版本表';

CREATE TABLE `metric_binding` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `project_id` BIGINT NOT NULL,
  `metric_id` BIGINT NOT NULL,
  `feature_id` BIGINT NULL DEFAULT NULL,
  `subject_key` VARCHAR(80) NOT NULL,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `archived_at` DATETIME(6) NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_metric_binding_1` (`metric_id`, `subject_key`),
  UNIQUE KEY `uq_metric_binding_2` (`project_id`, `id`),
  UNIQUE KEY `uq_metric_binding_3` (`metric_id`, `id`),
  CONSTRAINT `ck_metric_binding_1` CHECK ((feature_id IS NULL AND subject_key = 'PROJECT') OR (feature_id IS NOT NULL AND subject_key = (CONCAT('FEATURE:', CAST(feature_id AS CHAR)) COLLATE utf8mb4_0900_as_cs)))
) ENGINE=InnoDB COMMENT='指标数据项表';

CREATE TABLE `metric_value` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `project_id` BIGINT NOT NULL,
  `binding_id` BIGINT NOT NULL,
  `metric_id` BIGINT NOT NULL,
  `metric_revision_id` BIGINT NOT NULL,
  `stat_date` DATE NOT NULL,
  `baseline_date` DATE NULL DEFAULT NULL,
  `value_number` DECIMAL(24,6) NULL DEFAULT NULL,
  `value_status` VARCHAR(24) NOT NULL,
  `status_reason` VARCHAR(255) NULL DEFAULT NULL,
  `is_period_complete` BOOLEAN NOT NULL DEFAULT 0,
  `ingestion_batch_id` BIGINT NULL DEFAULT NULL,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `created_by` BIGINT NULL DEFAULT NULL,
  `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_by` BIGINT NULL DEFAULT NULL,
  `row_version` BIGINT NOT NULL DEFAULT 1,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_metric_value_1` (`binding_id`, `stat_date`),
  KEY `ix_metric_value_1` (`project_id`, `stat_date`, `metric_id`),
  KEY `ix_metric_value_2` (`stat_date`, `binding_id`),
  CONSTRAINT `ck_metric_value_1` CHECK (value_status IN ('VALID','PENDING','NOT_APPLICABLE')),
  CONSTRAINT `ck_metric_value_2` CHECK ((value_status = 'VALID' AND value_number IS NOT NULL) OR (value_status IN ('PENDING','NOT_APPLICABLE') AND value_number IS NULL)),
  CONSTRAINT `ck_metric_value_3` CHECK (baseline_date IS NULL OR baseline_date <= stat_date),
  CONSTRAINT `ck_metric_value_4` CHECK (`is_period_complete` IN (0,1)),
  CONSTRAINT `ck_metric_value_5` CHECK (`row_version` >= 1)
) ENGINE=InnoDB COMMENT='指标每日数据表';

CREATE TABLE `funnel` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `created_by` BIGINT NULL DEFAULT NULL,
  `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_by` BIGINT NULL DEFAULT NULL,
  `row_version` BIGINT NOT NULL DEFAULT 1,
  `project_id` BIGINT NOT NULL,
  `name` VARCHAR(100) NOT NULL,
  `name_key` VARCHAR(100) NOT NULL,
  `is_enabled` BOOLEAN NOT NULL DEFAULT 1,
  `display_order` INT NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_funnel_1` (`project_id`, `name_key`),
  UNIQUE KEY `uq_funnel_2` (`project_id`, `id`),
  KEY `ix_funnel_1` (`project_id`, `is_enabled`, `display_order`, `id`),
  CONSTRAINT `ck_funnel_1` CHECK (`row_version` >= 1),
  CONSTRAINT `ck_funnel_2` CHECK (`is_enabled` IN (0,1)),
  CONSTRAINT `ck_funnel_3` CHECK (`display_order` >= 0)
) ENGINE=InnoDB COMMENT='漏斗表';

CREATE TABLE `funnel_step` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `funnel_id` BIGINT NOT NULL,
  `project_id` BIGINT NOT NULL,
  `step_name` VARCHAR(100) NOT NULL,
  `binding_id` BIGINT NOT NULL,
  `position` INT NOT NULL,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_funnel_step_1` (`funnel_id`, `position`),
  CONSTRAINT `ck_funnel_step_1` CHECK (position >= 1)
) ENGINE=InnoDB COMMENT='漏斗步骤表';

CREATE TABLE `sys_user` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `created_by` BIGINT NULL DEFAULT NULL,
  `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_by` BIGINT NULL DEFAULT NULL,
  `row_version` BIGINT NOT NULL DEFAULT 1,
  `login_id` VARCHAR(100) NOT NULL,
  `display_name` VARCHAR(100) NOT NULL,
  `password_hash` VARCHAR(255) NOT NULL,
  `is_enabled` BOOLEAN NOT NULL DEFAULT 1,
  `must_change_password` BOOLEAN NOT NULL DEFAULT 1,
  `password_changed_at` DATETIME(6) NULL DEFAULT NULL,
  `auth_version` BIGINT NOT NULL DEFAULT 1,
  `last_login_at` DATETIME(6) NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_sys_user_1` (`login_id`),
  CONSTRAINT `ck_sys_user_1` CHECK (`row_version` >= 1),
  CONSTRAINT `ck_sys_user_2` CHECK (`is_enabled` IN (0,1)),
  CONSTRAINT `ck_sys_user_3` CHECK (`must_change_password` IN (0,1)),
  CONSTRAINT `ck_sys_user_4` CHECK (`auth_version` >= 1)
) ENGINE=InnoDB COMMENT='用户表';

CREATE TABLE `sys_role` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `created_by` BIGINT NULL DEFAULT NULL,
  `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_by` BIGINT NULL DEFAULT NULL,
  `row_version` BIGINT NOT NULL DEFAULT 1,
  `code` VARCHAR(64) NOT NULL,
  `name` VARCHAR(100) NOT NULL,
  `is_enabled` BOOLEAN NOT NULL DEFAULT 1,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_sys_role_1` (`code`),
  CONSTRAINT `ck_sys_role_1` CHECK (`row_version` >= 1),
  CONSTRAINT `ck_sys_role_2` CHECK (`is_enabled` IN (0,1))
) ENGINE=InnoDB COMMENT='角色表';

CREATE TABLE `sys_user_role` (
  `user_id` BIGINT NOT NULL,
  `role_id` BIGINT NOT NULL,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `created_by` BIGINT NULL DEFAULT NULL,
  PRIMARY KEY (`user_id`, `role_id`),
  KEY `ix_sys_user_role_1` (`role_id`, `user_id`)
) ENGINE=InnoDB COMMENT='用户角色关系表';

CREATE TABLE `sys_menu` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `created_by` BIGINT NULL DEFAULT NULL,
  `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_by` BIGINT NULL DEFAULT NULL,
  `row_version` BIGINT NOT NULL DEFAULT 1,
  `code` VARCHAR(64) NOT NULL,
  `parent_id` BIGINT NULL DEFAULT NULL,
  `name` VARCHAR(100) NOT NULL,
  `route_path` VARCHAR(200) NULL DEFAULT NULL,
  `display_order` INT NOT NULL DEFAULT 0,
  `is_enabled` BOOLEAN NOT NULL DEFAULT 1,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_sys_menu_1` (`code`),
  KEY `ix_sys_menu_1` (`parent_id`, `display_order`, `id`),
  CONSTRAINT `ck_sys_menu_1` CHECK (`row_version` >= 1),
  CONSTRAINT `ck_sys_menu_2` CHECK (`display_order` >= 0),
  CONSTRAINT `ck_sys_menu_3` CHECK (`is_enabled` IN (0,1))
) ENGINE=InnoDB COMMENT='菜单表';

CREATE TABLE `sys_permission` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `created_by` BIGINT NULL DEFAULT NULL,
  `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_by` BIGINT NULL DEFAULT NULL,
  `row_version` BIGINT NOT NULL DEFAULT 1,
  `menu_id` BIGINT NOT NULL,
  `code` VARCHAR(100) NOT NULL,
  `name` VARCHAR(100) NOT NULL,
  `action_key` VARCHAR(64) NOT NULL,
  `display_order` INT NOT NULL DEFAULT 0,
  `is_enabled` BOOLEAN NOT NULL DEFAULT 1,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_sys_permission_1` (`code`),
  UNIQUE KEY `uq_sys_permission_2` (`menu_id`, `action_key`),
  CONSTRAINT `ck_sys_permission_1` CHECK (`row_version` >= 1),
  CONSTRAINT `ck_sys_permission_2` CHECK (`display_order` >= 0),
  CONSTRAINT `ck_sys_permission_3` CHECK (`is_enabled` IN (0,1))
) ENGINE=InnoDB COMMENT='操作权限表';

CREATE TABLE `sys_role_permission` (
  `role_id` BIGINT NOT NULL,
  `permission_id` BIGINT NOT NULL,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `created_by` BIGINT NULL DEFAULT NULL,
  PRIMARY KEY (`role_id`, `permission_id`),
  KEY `ix_sys_role_permission_1` (`permission_id`, `role_id`)
) ENGINE=InnoDB COMMENT='角色权限关系表';

CREATE TABLE `sys_role_project` (
  `role_id` BIGINT NOT NULL,
  `project_id` BIGINT NOT NULL,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `created_by` BIGINT NULL DEFAULT NULL,
  PRIMARY KEY (`role_id`, `project_id`),
  KEY `ix_sys_role_project_1` (`project_id`, `role_id`)
) ENGINE=InnoDB COMMENT='角色项目范围表';

CREATE TABLE `ingestion_batch` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `batch_no` VARCHAR(64) NOT NULL,
  `project_id` BIGINT NOT NULL,
  `source_type` VARCHAR(24) NOT NULL,
  `data_source_id` BIGINT NULL DEFAULT NULL,
  `idempotency_key` VARCHAR(128) NOT NULL,
  `status` VARCHAR(24) NOT NULL,
  `original_file_name` VARCHAR(255) NULL DEFAULT NULL,
  `file_storage_key` VARCHAR(255) NULL DEFAULT NULL,
  `file_checksum` VARCHAR(128) NULL DEFAULT NULL,
  `input_row_count` INT NOT NULL DEFAULT 0,
  `success_row_count` INT NOT NULL DEFAULT 0,
  `error_row_count` INT NOT NULL DEFAULT 0,
  `skipped_row_count` INT NOT NULL DEFAULT 0,
  `written_value_count` INT NOT NULL DEFAULT 0,
  `created_by` BIGINT NULL DEFAULT NULL,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `finished_at` DATETIME(6) NULL DEFAULT NULL,
  `error_summary` TEXT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_ingestion_batch_1` (`batch_no`),
  UNIQUE KEY `uq_ingestion_batch_2` (`idempotency_key`),
  UNIQUE KEY `uq_ingestion_batch_3` (`project_id`, `id`),
  KEY `ix_ingestion_batch_1` (`project_id`, `created_at`, `id`),
  KEY `ix_ingestion_batch_2` (`status`, `created_at`),
  CONSTRAINT `ck_ingestion_batch_1` CHECK (status IN ('PENDING','VALIDATED','SUCCEEDED','PARTIAL_FAILED','FAILED')),
  CONSTRAINT `ck_ingestion_batch_2` CHECK (finished_at IS NULL OR finished_at >= created_at),
  CONSTRAINT `ck_ingestion_batch_3` CHECK (`input_row_count` >= 0),
  CONSTRAINT `ck_ingestion_batch_4` CHECK (`success_row_count` >= 0),
  CONSTRAINT `ck_ingestion_batch_5` CHECK (`error_row_count` >= 0),
  CONSTRAINT `ck_ingestion_batch_6` CHECK (`skipped_row_count` >= 0),
  CONSTRAINT `ck_ingestion_batch_7` CHECK (`written_value_count` >= 0)
) ENGINE=InnoDB COMMENT='数据写入批次表';

CREATE TABLE `ingestion_row` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `batch_id` BIGINT NOT NULL,
  `row_no` INT NOT NULL,
  `raw_payload` JSON NULL,
  `normalized_payload` JSON NULL,
  `validation_errors` JSON NULL,
  `status` VARCHAR(24) NOT NULL,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `processed_at` DATETIME(6) NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_ingestion_row_1` (`batch_id`, `row_no`),
  KEY `ix_ingestion_row_1` (`batch_id`, `status`, `row_no`),
  CONSTRAINT `ck_ingestion_row_1` CHECK (row_no >= 1),
  CONSTRAINT `ck_ingestion_row_2` CHECK (status IN ('VALID','INVALID','SKIPPED','SAVED'))
) ENGINE=InnoDB COMMENT='导入行结果表';

CREATE TABLE `audit_log` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `project_id` BIGINT NULL DEFAULT NULL,
  `actor_user_id` BIGINT NULL DEFAULT NULL,
  `source_type` VARCHAR(24) NOT NULL,
  `action_code` VARCHAR(100) NOT NULL,
  `entity_type` VARCHAR(64) NOT NULL,
  `entity_id` BIGINT NULL DEFAULT NULL,
  `entity_version` BIGINT NULL DEFAULT NULL,
  `before_payload` JSON NULL,
  `after_payload` JSON NULL,
  `batch_id` BIGINT NULL DEFAULT NULL,
  `request_id` VARCHAR(100) NULL DEFAULT NULL,
  `result` VARCHAR(16) NOT NULL,
  `error_code` VARCHAR(64) NULL DEFAULT NULL,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`),
  KEY `ix_audit_log_1` (`project_id`, `created_at`, `id`),
  KEY `ix_audit_log_2` (`entity_type`, `entity_id`, `created_at`, `id`),
  KEY `ix_audit_log_3` (`actor_user_id`, `created_at`, `id`),
  KEY `ix_audit_log_4` (`batch_id`, `id`),
  CONSTRAINT `ck_audit_log_1` CHECK (result IN ('SUCCESS','FAILED')),
  CONSTRAINT `ck_audit_log_2` CHECK (batch_id IS NULL OR project_id IS NOT NULL)
) ENGINE=InnoDB COMMENT='操作与修改日志表';

CREATE TABLE `data_source` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `created_by` BIGINT NULL DEFAULT NULL,
  `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_by` BIGINT NULL DEFAULT NULL,
  `row_version` BIGINT NOT NULL DEFAULT 1,
  `project_id` BIGINT NOT NULL,
  `name` VARCHAR(100) NOT NULL,
  `provider` VARCHAR(64) NULL DEFAULT NULL,
  `external_resource_ref` VARCHAR(500) NULL DEFAULT NULL,
  `credential_ref` VARCHAR(255) NULL DEFAULT NULL,
  `sync_mode` VARCHAR(24) NULL DEFAULT NULL,
  `sync_config` JSON NULL,
  `is_enabled` BOOLEAN NOT NULL DEFAULT 1,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_data_source_1` (`project_id`, `name`),
  UNIQUE KEY `uq_data_source_2` (`project_id`, `id`),
  CONSTRAINT `ck_data_source_1` CHECK (`row_version` >= 1),
  CONSTRAINT `ck_data_source_2` CHECK (`is_enabled` IN (0,1))
) ENGINE=InnoDB COMMENT='云文档来源表；预留扩展，未接入';

CREATE TABLE `data_source_mapping` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `created_by` BIGINT NULL DEFAULT NULL,
  `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_by` BIGINT NULL DEFAULT NULL,
  `row_version` BIGINT NOT NULL DEFAULT 1,
  `data_source_id` BIGINT NOT NULL,
  `project_id` BIGINT NOT NULL,
  `binding_id` BIGINT NOT NULL,
  `stat_date_field` VARCHAR(100) NOT NULL,
  `value_field` VARCHAR(100) NOT NULL,
  `baseline_date_field` VARCHAR(100) NULL DEFAULT NULL,
  `parser_config` JSON NULL,
  `is_enabled` BOOLEAN NOT NULL DEFAULT 1,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_data_source_mapping_1` (`data_source_id`, `binding_id`),
  CONSTRAINT `ck_data_source_mapping_1` CHECK (`row_version` >= 1),
  CONSTRAINT `ck_data_source_mapping_2` CHECK (`is_enabled` IN (0,1))
) ENGINE=InnoDB COMMENT='来源字段映射表；预留扩展，未接入';

CREATE TABLE `auth_session` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `user_id` BIGINT NOT NULL,
  `credential_hash` VARCHAR(255) NOT NULL,
  `auth_version` BIGINT NOT NULL DEFAULT 1,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `expires_at` DATETIME(6) NOT NULL,
  `revoked_at` DATETIME(6) NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_auth_session_1` (`credential_hash`),
  KEY `ix_auth_session_1` (`user_id`, `revoked_at`, `expires_at`),
  CONSTRAINT `ck_auth_session_1` CHECK (expires_at > created_at),
  CONSTRAINT `ck_auth_session_2` CHECK (revoked_at IS NULL OR revoked_at >= created_at),
  CONSTRAINT `ck_auth_session_3` CHECK (`auth_version` >= 1)
) ENGINE=InnoDB COMMENT='登录会话表；预留扩展，未接入';

ALTER TABLE `project_feature` ADD CONSTRAINT `fk_r1` FOREIGN KEY (`project_id`) REFERENCES `project` (`id`);

ALTER TABLE `metric` ADD CONSTRAINT `fk_r2` FOREIGN KEY (`project_id`) REFERENCES `project` (`id`);

ALTER TABLE `metric` ADD CONSTRAINT `fk_r3` FOREIGN KEY (`category_id`) REFERENCES `metric_category` (`id`);

ALTER TABLE `metric_revision` ADD CONSTRAINT `fk_r4` FOREIGN KEY (`metric_id`) REFERENCES `metric` (`id`);

ALTER TABLE `metric` ADD CONSTRAINT `fk_r5` FOREIGN KEY (`id`, `current_revision_id`) REFERENCES `metric_revision` (`metric_id`, `id`);

ALTER TABLE `metric_binding` ADD CONSTRAINT `fk_r6` FOREIGN KEY (`project_id`, `metric_id`) REFERENCES `metric` (`project_id`, `id`);

ALTER TABLE `metric_binding` ADD CONSTRAINT `fk_r7` FOREIGN KEY (`project_id`, `feature_id`) REFERENCES `project_feature` (`project_id`, `id`);

ALTER TABLE `metric_value` ADD CONSTRAINT `fk_r8` FOREIGN KEY (`project_id`, `binding_id`) REFERENCES `metric_binding` (`project_id`, `id`);

ALTER TABLE `metric_value` ADD CONSTRAINT `fk_r9` FOREIGN KEY (`metric_id`, `binding_id`) REFERENCES `metric_binding` (`metric_id`, `id`);

ALTER TABLE `metric_value` ADD CONSTRAINT `fk_r10` FOREIGN KEY (`metric_id`, `metric_revision_id`) REFERENCES `metric_revision` (`metric_id`, `id`);

ALTER TABLE `funnel` ADD CONSTRAINT `fk_r11` FOREIGN KEY (`project_id`) REFERENCES `project` (`id`);

ALTER TABLE `funnel_step` ADD CONSTRAINT `fk_r12` FOREIGN KEY (`project_id`, `funnel_id`) REFERENCES `funnel` (`project_id`, `id`);

ALTER TABLE `funnel_step` ADD CONSTRAINT `fk_r13` FOREIGN KEY (`project_id`, `binding_id`) REFERENCES `metric_binding` (`project_id`, `id`);

ALTER TABLE `sys_user_role` ADD CONSTRAINT `fk_r14` FOREIGN KEY (`user_id`) REFERENCES `sys_user` (`id`);

ALTER TABLE `sys_user_role` ADD CONSTRAINT `fk_r15` FOREIGN KEY (`role_id`) REFERENCES `sys_role` (`id`);

ALTER TABLE `sys_menu` ADD CONSTRAINT `fk_r16` FOREIGN KEY (`parent_id`) REFERENCES `sys_menu` (`id`);

ALTER TABLE `sys_permission` ADD CONSTRAINT `fk_r17` FOREIGN KEY (`menu_id`) REFERENCES `sys_menu` (`id`);

ALTER TABLE `sys_role_permission` ADD CONSTRAINT `fk_r18` FOREIGN KEY (`role_id`) REFERENCES `sys_role` (`id`);

ALTER TABLE `sys_role_permission` ADD CONSTRAINT `fk_r19` FOREIGN KEY (`permission_id`) REFERENCES `sys_permission` (`id`);

ALTER TABLE `sys_role_project` ADD CONSTRAINT `fk_r20` FOREIGN KEY (`role_id`) REFERENCES `sys_role` (`id`);

ALTER TABLE `sys_role_project` ADD CONSTRAINT `fk_r21` FOREIGN KEY (`project_id`) REFERENCES `project` (`id`);

ALTER TABLE `ingestion_batch` ADD CONSTRAINT `fk_r22` FOREIGN KEY (`project_id`) REFERENCES `project` (`id`);

ALTER TABLE `ingestion_batch` ADD CONSTRAINT `fk_r23` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`);

ALTER TABLE `ingestion_row` ADD CONSTRAINT `fk_r24` FOREIGN KEY (`batch_id`) REFERENCES `ingestion_batch` (`id`);

ALTER TABLE `metric_value` ADD CONSTRAINT `fk_r25` FOREIGN KEY (`project_id`, `ingestion_batch_id`) REFERENCES `ingestion_batch` (`project_id`, `id`);

ALTER TABLE `metric_value` ADD CONSTRAINT `fk_r26` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`);

ALTER TABLE `metric_value` ADD CONSTRAINT `fk_r27` FOREIGN KEY (`updated_by`) REFERENCES `sys_user` (`id`);

ALTER TABLE `metric_revision` ADD CONSTRAINT `fk_r28` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`);

ALTER TABLE `audit_log` ADD CONSTRAINT `fk_r29` FOREIGN KEY (`actor_user_id`) REFERENCES `sys_user` (`id`);

ALTER TABLE `audit_log` ADD CONSTRAINT `fk_r30` FOREIGN KEY (`project_id`) REFERENCES `project` (`id`);

ALTER TABLE `audit_log` ADD CONSTRAINT `fk_r31` FOREIGN KEY (`project_id`, `batch_id`) REFERENCES `ingestion_batch` (`project_id`, `id`);

ALTER TABLE `data_source` ADD CONSTRAINT `fk_r32` FOREIGN KEY (`project_id`) REFERENCES `project` (`id`);

ALTER TABLE `data_source_mapping` ADD CONSTRAINT `fk_r33` FOREIGN KEY (`project_id`, `data_source_id`) REFERENCES `data_source` (`project_id`, `id`);

ALTER TABLE `data_source_mapping` ADD CONSTRAINT `fk_r34` FOREIGN KEY (`project_id`, `binding_id`) REFERENCES `metric_binding` (`project_id`, `id`);

ALTER TABLE `ingestion_batch` ADD CONSTRAINT `fk_r35` FOREIGN KEY (`project_id`, `data_source_id`) REFERENCES `data_source` (`project_id`, `id`);

ALTER TABLE `auth_session` ADD CONSTRAINT `fk_r36` FOREIGN KEY (`user_id`) REFERENCES `sys_user` (`id`);

ALTER TABLE `project` ADD CONSTRAINT `fk_r37` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`);

ALTER TABLE `project` ADD CONSTRAINT `fk_r38` FOREIGN KEY (`updated_by`) REFERENCES `sys_user` (`id`);

ALTER TABLE `project_feature` ADD CONSTRAINT `fk_r39` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`);

ALTER TABLE `project_feature` ADD CONSTRAINT `fk_r40` FOREIGN KEY (`updated_by`) REFERENCES `sys_user` (`id`);

ALTER TABLE `metric_category` ADD CONSTRAINT `fk_r41` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`);

ALTER TABLE `metric_category` ADD CONSTRAINT `fk_r42` FOREIGN KEY (`updated_by`) REFERENCES `sys_user` (`id`);

ALTER TABLE `metric` ADD CONSTRAINT `fk_r43` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`);

ALTER TABLE `metric` ADD CONSTRAINT `fk_r44` FOREIGN KEY (`updated_by`) REFERENCES `sys_user` (`id`);

ALTER TABLE `funnel` ADD CONSTRAINT `fk_r45` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`);

ALTER TABLE `funnel` ADD CONSTRAINT `fk_r46` FOREIGN KEY (`updated_by`) REFERENCES `sys_user` (`id`);

ALTER TABLE `sys_user` ADD CONSTRAINT `fk_r47` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`);

ALTER TABLE `sys_user` ADD CONSTRAINT `fk_r48` FOREIGN KEY (`updated_by`) REFERENCES `sys_user` (`id`);

ALTER TABLE `sys_role` ADD CONSTRAINT `fk_r49` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`);

ALTER TABLE `sys_role` ADD CONSTRAINT `fk_r50` FOREIGN KEY (`updated_by`) REFERENCES `sys_user` (`id`);

ALTER TABLE `sys_menu` ADD CONSTRAINT `fk_r51` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`);

ALTER TABLE `sys_menu` ADD CONSTRAINT `fk_r52` FOREIGN KEY (`updated_by`) REFERENCES `sys_user` (`id`);

ALTER TABLE `sys_permission` ADD CONSTRAINT `fk_r53` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`);

ALTER TABLE `sys_permission` ADD CONSTRAINT `fk_r54` FOREIGN KEY (`updated_by`) REFERENCES `sys_user` (`id`);

ALTER TABLE `data_source` ADD CONSTRAINT `fk_r55` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`);

ALTER TABLE `data_source` ADD CONSTRAINT `fk_r56` FOREIGN KEY (`updated_by`) REFERENCES `sys_user` (`id`);

ALTER TABLE `data_source_mapping` ADD CONSTRAINT `fk_r57` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`);

ALTER TABLE `data_source_mapping` ADD CONSTRAINT `fk_r58` FOREIGN KEY (`updated_by`) REFERENCES `sys_user` (`id`);

ALTER TABLE `sys_user_role` ADD CONSTRAINT `fk_r59` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`);

ALTER TABLE `sys_role_permission` ADD CONSTRAINT `fk_r60` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`);

ALTER TABLE `sys_role_project` ADD CONSTRAINT `fk_r61` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`);

-- Application layer must implement role/project authorization and cross-row business validations.
