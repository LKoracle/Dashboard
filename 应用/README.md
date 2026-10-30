# Dashboard 应用 · 登录与菜单管理

部署日期：2026-10-30。

访问入口：<https://129.226.194.82/dashboard/login>。账号 `admin`，使用本次指定密码；本文和代码不记录密码明文或密码哈希。

## 本轮已实现

- 独立登录页面；成功登录默认进入首页。首页当前展示暂无指标数据，后续接入完整看板。
- 未登录访问业务页面跳转登录；未登录访问数据接口返回 401。
- `admin` 为已启用的 `super_admin` 超级管理员，拥有全局管理能力；普通角色通过操作权限判断访问。
- 菜单管理展示菜单、层级、上级菜单、操作权限、状态、操作。10 个菜单沿用确认原型，不包含“项目指标详情”。
- 支持每页 10 / 20 / 50 条及分页，启用 / 停用前确认；保存至 MySQL，重新进入后保持。
- 停用普通用户菜单时，父菜单状态同时限制子菜单访问。超级管理员保留菜单恢复能力，避免误停后无法恢复。
- 菜单修改以 `row_version` 检查并发，旧版本返回 409；变更和登录、退出写入 `audit_log`。
- 不在本轮扩展菜单新增、编辑结构与操作权限的配置界面；原型菜单列表当前操作为启用 / 停用，已有操作权限定义供后续角色管理复用。
- 项目管理、指标配置、漏斗配置、角色管理、用户管理及完整首页数据暂未开放。

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
