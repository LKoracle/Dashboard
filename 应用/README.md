# Dashboard 应用

部署日期：2026-10-30。

访问入口：<https://129.226.194.82/dashboard/login>。账号 `admin`，使用本次指定密码；本文和代码不记录密码明文或密码哈希。

## 本轮已实现

- 独立登录页面；成功登录默认进入首页。首页已接入项目、指标配置及 `metric_entry` 真实数据；缺失显示空状态，不使用原型样例。
- 未登录访问业务页面跳转登录；未登录访问数据接口返回 401。
- `admin` 为已启用的 `super_admin` 超级管理员，拥有全局管理能力；普通角色通过操作权限判断访问。
- 菜单管理展示菜单、层级、上级菜单、操作权限、状态、操作。10 个菜单沿用确认原型，不包含“项目指标详情”。
- 支持每页 10 / 20 / 50 条及分页，启用 / 停用前确认；保存至 MySQL，重新进入后保持。
- 停用普通用户菜单时，父菜单状态同时限制子菜单访问。超级管理员保留菜单恢复能力，避免误停后无法恢复。
- 菜单修改以 `row_version` 检查并发，旧版本返回 409；变更和登录、退出写入 `audit_log`。
- 不在本轮扩展菜单新增、编辑结构与操作权限的配置界面；原型菜单列表当前操作为启用 / 停用，已有操作权限定义供后续角色管理复用。
- 项目管理、指标配置、角色管理、用户管理和数据维护已实现；漏斗管理界面。首页可读取数据库中已启用且步骤配置完整的漏斗。

## 认证与部署

密码采用 Argon2id；8 小时数据库会话，Cookie 带 Secure、HttpOnly、SameSite=Strict。接口校验用户启用状态与 auth_version，退出立即撤销会话。写操作同时检查 Origin 和 CSRF，登录尝试有频率限制。页面与接口禁缓存。

运行环境：Python 3.11、FastAPI 0.162.0、Uvicorn 0.54.0、PyMySQL 1.2.3、argon2-cffi 25.1.0。源文件和运行位置：

| 位置 | 说明 |
|---|---|
| `/opt/dashboard/app/` | 应用代码，与本目录核心代码一致 |
| `/opt/dashboard/venv/` | 独立 Python 环境，包含 Certbot 5.9.0 |
| `/opt/dashboard/app.env` | 仅 root 可读写，权限 600；数据库应用密码和会话密钥，不复制到本地或仓库 |
| `dashboard.service` | 应用，系统用户 dashboard，仅监听 127.0.0.1:8321 |
| `dashboard-proxy.service` | 独立 Nginx 实例，公网 HTTPS 443；不更改既有网关路由 |
| `/opt/dashboard/nginx.conf` | 该实例的主配置，独立 PID 与日志 |
| `/opt/dashboard/dashboard-site.conf` | 站点与反向代理配置 |
| `/etc/letsencrypt/live/dashboard-ip/` | IP 证书与私钥，私钥不外传 |
| `/opt/dashboard/acme-hook.py` | 使用已有 my-gateway 静态目录完成 HTTP-01 验证 |
| `dashboard-cert-renew.timer` | 每天两次检查续期，成功后重载 dashboard-proxy |

数据库复用 `pet-db` 内的独立 `dashboard` 库。新增应用数据库账号只允许 Docker 网桥主机 `172.17.0.1` 连接，只授予当前登录与菜单管理需要的表和字段权限；不使用 root 作为应用账号，不授予库结构修改权限，不开放数据库公网端口。

防火墙仅新增本次确认的 IPv4 TCP 443 允许规则，备注 Dashboard HTTPS。原有 22 / 80 / 2026 / 8080 / 9000 规则保持原状。

## 验证

- 本地 8 项安全与接口单元检查通过：`tests/test_security.py`。
- 正式 HTTPS 接口 9 项集成检查通过：`tests/smoke_live.py`，包含真实 admin 登录、安全 Cookie、菜单读写持久化、旧版本冲突、CSRF 拦截、退出会话失效。
- 集成测试临时切换“指标配置”状态，已恢复初始状态；审计日志保留测试操作记录。
- HTTPS 使用可信证书验证，未关闭证书校验；证书续期 dry-run 演练成功，应用、独立代理和续期定时器均已设为开机启用。
- 浏览器已验收正式站点登录、成功后默认首页、10 条菜单列表和启停确认弹窗。

## 运维命令

```sh
systemctl status dashboard dashboard-proxy --no-pager
journalctl -u dashboard -n 50 --no-pager
systemctl restart dashboard
systemctl reload dashboard-proxy
systemctl list-timers dashboard-cert-renew.timer
/opt/dashboard/venv/bin/certbot renew --cert-name dashboard-ip --dry-run
```

`deploy.py` / `bootstrap.py` 仅用于首次初始化；发现现有 admin 时拒绝覆盖，不能用于重置密码。升级仅替换已确认的应用代码并重启服务。密码变更流程与账号管理在后续实现。

IP 证书为短期证书，必须保持定时续期、Docker 网关以及 HTTP 80 验证入口可用；服务器 IP 变更后需要重新签发并同步 PUBLIC_ORIGIN。数据库仍需完善异机备份与恢复演练。

## 首页（2026-10-31）

- `GET /api/home/projects`：有权访问的启用项目及业务日期（北京时间）。普通用户由同一启用角色同时授予 `home.view` 和项目范围。
- `GET /api/home/data?project_id=…&stat_date=YYYY-MM-DD`：项目、统计日期联动的只读接口，拒绝未来日期和越权项目。
- 页面保留深色原型布局：关键指标、14 天日活跃趋势、用户覆盖、按填写统计日期展示的 14 天 D7 留存、左右各半屏的 7 天使用深度与性能趋势、功能使用及动态漏斗。
- 关键指标受 `is_key_metric` 控制；四类既定趋势按 `show_trend` 独立控制系列。禁用或归档指标不展示数据；真实零值保留，缺失数据不补零、曲线断开。
- 当前维护表的留存 `stat_date` 为基准日；首页转换为 D+7 观察日，观察日未结束不展示完整留存。首页不将累计快照跨日求和。
- 上线前需按 `部署/mysql/grants_app.sql` 补充 funnel、funnel_step、metric_binding 的 SELECT 权限；自动拉取部署不会执行 SQL。
- 本地验收：`tests/test_home.py` 与 `tests/test_security.py` 共 13 项通过；浏览器验证日期联动、项目切换、空数据和图表布局。临时验收数据及认证替身均未纳入应用或仓库。


## Excel 批量导入（2026-10-31）

- `excel_import.py` 提供模板、上传预览、按批次确认及标注原表下载；页面在“数据维护—数据导入”。仅 `.xlsx`，2 MB／1,000 条，支持多项目多日期新增和更新。
- Excel 处理依赖 `openpyxl` 与 `defusedxml`；公式不执行。每个项目＋日期使用独立事务，同组失败回滚；原表右侧标注逐行结果，并附统计表。
- `GET /api/maintain/import/template` 下载授权项目模板；`POST /api/maintain/import/excel/preview` 接收 `file_name`、`file_base64`；`POST /api/maintain/import/excel/{batch_id}/commit` 确认；`GET /api/maintain/import/excel/{batch_id}/report` 下载。完整路径带 `/dashboard`。
- 所有接口要求 `maintain.import`；预览与提交都按同一有效角色的项目范围鉴权，批次和回执绑定上传者。校验后不立即写入，提交时复查数据和指标配置版本。完成批次重复确认不重放。
- `IMPORT_DIR` 默认 `/opt/dashboard/imports`，由 dashboard 用户独占（0700，文件 0600）；原文件及结果 24 小时后不可下载，过期目录在后续上传时清理。该目录在应用运行目录之外，不随 rsync 发布删除。
- 首次启用：`install -d -o dashboard -g dashboard -m 700 /opt/dashboard/imports`；将 `deployment/dashboard-imports.conf` 安装到 `/etc/systemd/system/dashboard.service.d/imports.conf`，执行 daemon-reload 并重启 dashboard.service 后发布。即使代码已被 cron 提前拉取，也必须重启一次让目录权限生效。仅该目录设为可写，应用目录继续只读；不需要新增数据库授权或迁移表。
- 旧 CSV 接口保留原有兼容行为，不作为新页面的批量更新入口。
