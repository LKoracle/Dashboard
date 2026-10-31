-- 项目级绑定：非功能使用类的启用指标
INSERT INTO dashboard.metric_binding(project_id,metric_id,feature_id,subject_key)
SELECT m.project_id,m.id,NULL,'PROJECT' FROM dashboard.metric m
JOIN dashboard.metric_category cat ON cat.id=m.category_id
WHERE m.is_enabled=1 AND m.archived_at IS NULL AND cat.code<>'feature'
AND NOT EXISTS (SELECT 1 FROM dashboard.metric_binding b
  WHERE b.metric_id=m.id AND b.feature_id IS NULL AND b.archived_at IS NULL);

-- 功能级绑定：功能使用类启用指标 × 项目功能
INSERT INTO dashboard.metric_binding(project_id,metric_id,feature_id,subject_key)
SELECT m.project_id,m.id,f.id,CONCAT('FEATURE:',f.id) FROM dashboard.metric m
JOIN dashboard.metric_category cat ON cat.id=m.category_id
JOIN dashboard.project_feature f ON f.project_id=m.project_id AND f.archived_at IS NULL
WHERE m.is_enabled=1 AND m.archived_at IS NULL AND cat.code='feature'
AND NOT EXISTS (SELECT 1 FROM dashboard.metric_binding b
  WHERE b.metric_id=m.id AND b.feature_id=f.id AND b.archived_at IS NULL);

SELECT project_id,COUNT(*) FROM dashboard.metric_binding WHERE archived_at IS NULL GROUP BY project_id;
