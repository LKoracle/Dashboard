-- 《项目指标与统计口径》初始化：寿险（外勤）=project 32、寿险（内勤）=project 33
-- 外勤「日活跃用户数」(YHHY0002) 为用户自建，仅对齐英文名，不重复插入；编码按 metric_category 前缀续号（用户活跃已用至 0002）
-- 一次性初始化脚本（2026-10-30 已在服务器执行）；含中文必须 --default-character-set=utf8mb4
UPDATE metric SET english_name='DAU / Daily Active Users' WHERE id=34;
INSERT INTO metric (project_id,category_id,code,name,name_key,english_name,unit,value_kind,decimal_places,scope_kind,definition,definition_status,is_key_metric,show_trend,display_order,is_enabled,created_by) VALUES
(32,24,'YHHY0003','日活跃率','日活跃率','DAU Rate / Daily Active User Rate','%','DECIMAL',1,'PROJECT','日活跃用户数（DAU）÷ 同项目截至当日的开通用户数 × 100%。分子、分母采用相同用户范围。','CONFIRMED',0,0,2,1,1),
(32,23,'YHFG0001','开通用户数','开通用户数','Enabled Users','人','DECIMAL',1,'PROJECT','截至统计日，自项目上线以来累计获得使用权限的去重用户数；同一用户多次开通只计 1 人。','CONFIRMED',0,0,3,1,1),
(32,23,'YHFG0002','累计使用用户数','累计使用用户数','Cumulative Unique Users','人','DECIMAL',1,'PROJECT','自项目上线至统计日，至少发生过一次有效使用行为的去重用户数；同一用户跨日、跨会话只计 1 人。','CONFIRMED',0,0,4,1,1),
(32,23,'YHFG0003','累计使用率','累计使用率','Cumulative Adoption Rate','%','DECIMAL',1,'PROJECT','截至统计日的累计使用用户数 ÷ 同口径开通用户数 × 100%。分子、分母使用同一项目、同一统计截止日及用户范围。','CONFIRMED',0,0,5,1,1),
(32,26,'YHLC0001','7日留存率','7日留存率','D7 Retention / Day 7 Retention Rate','%','DECIMAL',1,'PROJECT','基准日 D 的活跃用户中，在 D+7 当天再次有效使用的去重人数 ÷ 基准日 D 的活跃用户数 × 100%。D 不限首次使用日；仅展示 D+7 已结束的批次，不按后续 7 天内任意回访计算。','CONFIRMED',1,0,6,1,1),
(32,25,'SYSD0001','有效会话数','有效会话数',NULL,'人','DECIMAL',1,'PROJECT',NULL,'PENDING',0,0,7,1,1),
(32,25,'SYSD0002','每次会话平均时长','每次会话平均时长','ASD / Average Session Duration','分钟/次','DECIMAL',1,'PROJECT','统计期内已结束的有效会话总时长 ÷ 同期已结束的有效会话数。分子、分母采用同一批会话；单位：分钟/次。会话起止及空闲处理规则待埋点方案确认。','CONFIRMED',1,0,8,1,1),
(32,28,'XNBX0001','平均首字响应时长','平均首字响应时长','Avg. TTFT / Average Time to First Token','秒','DECIMAL',1,'PROJECT','同一批可统计成功请求中，前端呈现首个有效回答内容时间与用户发送指令时间之差的总和 ÷ 请求数；单位：秒。不将加载提示或“思考中”状态计为首字。','CONFIRMED',1,0,9,1,1),
(32,28,'XNBX0002','平均完整响应时长','平均完整响应时长','Avg. Full Response Time','秒','DECIMAL',1,'PROJECT','同一批可统计成功请求中，前端完整呈现回答的结束时间与用户发送指令时间之差的总和 ÷ 请求数；单位：秒。包含开始推理前等待、首字等待及后续生成过程。','CONFIRMED',0,0,10,1,1),
(32,27,'GNSY0001','功能日使用人数','功能日使用人数','Feature UV / Feature Unique Users','人','DECIMAL',1,'PROJECT','统计期内，至少有效使用过一次指定功能的去重用户数；同一用户在同一功能中使用多次只计 1 人。不同功能分别去重。','CONFIRMED',0,0,11,1,1),
(32,27,'GNSY0002','功能日使用人数占比','功能日使用人数占比','Feature User Share','%','DECIMAL',1,'PROJECT','统计期内指定功能的去重使用人数 ÷ 同项目同期活跃用户数 × 100%。分子、分母采用相同用户范围；同一用户可使用多个功能，各功能占比之和可能超过 100%。','CONFIRMED',0,0,12,1,1),
(32,27,'GNSY0003','功能累计使用人数','功能累计使用人数','Cumulative Feature Unique Users','人','DECIMAL',1,'PROJECT','自指定功能上线至统计日，至少有效使用过一次该功能的去重用户数；同一用户跨日、跨会话只计 1 人。','CONFIRMED',0,0,13,1,1),
(32,27,'GNSY0004','功能累计使用人数占比','功能累计使用人数占比','Cumulative Feature User Share','%','DECIMAL',1,'PROJECT','截至统计日，指定功能累计去重使用人数 ÷ 同项目、同用户范围的累计使用用户数 × 100%。分子、分母使用同一截止日；各功能分别统计，占比之和可能超过 100%。','CONFIRMED',0,0,14,1,1),
(33,24,'YHHY0004','日活跃用户数','日活跃用户数','DAU / Daily Active Users','人','DECIMAL',1,'PROJECT','统计自然日内，至少发生过一次有效使用行为的去重用户数；同一用户当日多次使用只计 1 人。','CONFIRMED',1,0,1,1,1),
(33,24,'YHHY0005','日活跃率','日活跃率','DAU Rate / Daily Active User Rate','%','DECIMAL',1,'PROJECT','日活跃用户数（DAU）÷ 同项目截至当日的开通用户数 × 100%。分子、分母采用相同用户范围。','CONFIRMED',0,0,2,1,1),
(33,23,'YHFG0004','开通用户数','开通用户数','Enabled Users','人','DECIMAL',1,'PROJECT','截至统计日，自项目上线以来累计获得使用权限的去重用户数；同一用户多次开通只计 1 人。','CONFIRMED',0,0,3,1,1),
(33,23,'YHFG0005','累计使用用户数','累计使用用户数','Cumulative Unique Users','人','DECIMAL',1,'PROJECT','自项目上线至统计日，至少发生过一次有效使用行为的去重用户数；同一用户跨日、跨会话只计 1 人。','CONFIRMED',0,0,4,1,1),
(33,23,'YHFG0006','累计使用率','累计使用率','Cumulative Adoption Rate','%','DECIMAL',1,'PROJECT','截至统计日的累计使用用户数 ÷ 同口径开通用户数 × 100%。分子、分母使用同一项目、同一统计截止日及用户范围。','CONFIRMED',0,0,5,1,1),
(33,26,'YHLC0002','7日留存率','7日留存率','D7 Retention / Day 7 Retention Rate','%','DECIMAL',1,'PROJECT','基准日 D 的活跃用户中，在 D+7 当天再次有效使用的去重人数 ÷ 基准日 D 的活跃用户数 × 100%。D 不限首次使用日；仅展示 D+7 已结束的批次，不按后续 7 天内任意回访计算。','CONFIRMED',1,0,6,1,1),
(33,25,'SYSD0003','有效会话数','有效会话数',NULL,'人','DECIMAL',1,'PROJECT',NULL,'PENDING',0,0,7,1,1),
(33,25,'SYSD0004','每次会话平均时长','每次会话平均时长','ASD / Average Session Duration','分钟/次','DECIMAL',1,'PROJECT','统计期内已结束的有效会话总时长 ÷ 同期已结束的有效会话数。分子、分母采用同一批会话；单位：分钟/次。会话起止及空闲处理规则待埋点方案确认。','CONFIRMED',1,0,8,1,1),
(33,28,'XNBX0003','平均首字响应时长','平均首字响应时长','Avg. TTFT / Average Time to First Token','秒','DECIMAL',1,'PROJECT','同一批可统计成功请求中，前端呈现首个有效回答内容时间与用户发送指令时间之差的总和 ÷ 请求数；单位：秒。不将加载提示或“思考中”状态计为首字。','CONFIRMED',1,0,9,1,1),
(33,28,'XNBX0004','平均完整响应时长','平均完整响应时长','Avg. Full Response Time','秒','DECIMAL',1,'PROJECT','同一批可统计成功请求中，前端完整呈现回答的结束时间与用户发送指令时间之差的总和 ÷ 请求数；单位：秒。包含开始推理前等待、首字等待及后续生成过程。','CONFIRMED',0,0,10,1,1),
(33,27,'GNSY0005','功能日使用人数','功能日使用人数','Feature UV / Feature Unique Users','人','DECIMAL',1,'PROJECT','统计期内，至少有效使用过一次指定功能的去重用户数；同一用户在同一功能中使用多次只计 1 人。不同功能分别去重。','CONFIRMED',0,0,11,1,1),
(33,27,'GNSY0006','功能日使用人数占比','功能日使用人数占比','Feature User Share','%','DECIMAL',1,'PROJECT','统计期内指定功能的去重使用人数 ÷ 同项目同期活跃用户数 × 100%。分子、分母采用相同用户范围；同一用户可使用多个功能，各功能占比之和可能超过 100%。','CONFIRMED',0,0,12,1,1),
(33,27,'GNSY0007','功能累计使用人数','功能累计使用人数','Cumulative Feature Unique Users','人','DECIMAL',1,'PROJECT','自指定功能上线至统计日，至少有效使用过一次该功能的去重用户数；同一用户跨日、跨会话只计 1 人。','CONFIRMED',0,0,13,1,1),
(33,27,'GNSY0008','功能累计使用人数占比','功能累计使用人数占比','Cumulative Feature User Share','%','DECIMAL',1,'PROJECT','截至统计日，指定功能累计去重使用人数 ÷ 同项目、同用户范围的累计使用用户数 × 100%。分子、分母使用同一截止日；各功能分别统计，占比之和可能超过 100%。','CONFIRMED',0,0,14,1,1);
UPDATE metric_category SET last_sequence=6 WHERE id=23;
UPDATE metric_category SET last_sequence=5 WHERE id=24;
UPDATE metric_category SET last_sequence=4 WHERE id=25;
UPDATE metric_category SET last_sequence=2 WHERE id=26;
UPDATE metric_category SET last_sequence=4 WHERE id=28;
UPDATE metric_category SET last_sequence=8 WHERE id=27;
SELECT project_id,COUNT(*) cnt FROM metric GROUP BY project_id;
