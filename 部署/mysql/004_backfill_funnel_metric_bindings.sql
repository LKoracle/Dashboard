-- 补齐已有、启用、未归档漏斗指标的项目级数据项；不修改现有绑定。
INSERT INTO metric_binding(project_id,metric_id,feature_id,subject_key)
SELECT m.project_id,m.id,NULL,'PROJECT' FROM metric m
JOIN metric_category cat ON cat.id=m.category_id
WHERE cat.code='funnel' AND m.is_enabled=1 AND m.archived_at IS NULL
AND NOT EXISTS (SELECT 1 FROM metric_binding b
                WHERE b.metric_id=m.id AND b.subject_key='PROJECT');
SELECT ROW_COUNT() AS created_bindings;
