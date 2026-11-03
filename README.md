# Y's Blog · v4.0

个人博客与个人数字空间合一的单站：公开面只负责展示，`/space` 负责使用与管理。
后端 FastAPI 模块化单体 + SQLite；前端 Vue 3 + Vite，无 UI 库，玻璃材质自绘。

## v4 主要变化

- **前后台合成一套产物**：删除 v2 静态多页与根目录 `public/`，`/` 由 SPA 构建产物接管；
  生产 nginx 直接挂 `frontend/dist`。
- **新增资源库** `/library`：`content/resources.json` + 只读接口 `GET /api/public/resources`，
  支持分类筛选与搜索，改 JSON 即生效。
- **首页收为单屏落地页**：只保留 Hero（标题 / 副题 / 阅读入口 / 社交 / 数字空间入口 / 可拖拽玻璃透镜）。
- **公开项目页下线**：导航第三项改为「资源库」；后台「项目」面板保留（管数据）。
- **全站玻璃控件层**：按钮 / 标签 / 分段项统一半透明玻璃 + 外描边；选中球用一个元素在容器内弹性平移。
- **站点设置清理**：移除已无承载位置的公告 / 精选 / 头像 / 简介字段，表单显示前台实际生效的兜底文案。

## 技术栈

| 层 | 选型 |
|---|---|
| 后端 | Python 3.12 · FastAPI · SQLite（blog / music / workspace 三库，WAL + ATTACH） |
| 鉴权 | JWT 双令牌（access 15min / refresh 7d，`typ` 校验）· bcrypt · 登录失败限流 · 审计日志 |
| 前端 | Vue 3.5 · vue-router 4（history 路由）· Vite · 原生 CSS |
| 视觉 | iOS 26 Liquid Glass：Canvas SDF 折射贴图 + SVG feDisplacementMap + `backdrop-filter`；CSS rim light；`cubic-bezier(.3,1.42,.42,1)` 弹性 |

## 目录

```
app/
  core/       配置 / 数据库 / 安全 / 清洗 / 限流 / 审计
  modules/    auth blog tags workspace music cloud projects space ai audit resources
  scripts/    启动时自愈迁移（migrate_v2.py）
content/      静态内容源（resources.json）
deploy/       Dockerfile（后端）· nginx.conf（SPA + /api 反代）
frontend/     Vue 源码（src/）与构建产物（dist/，不入库）
docs/         架构与升级规划
docker-compose.yml
```

## 本地运行

```bash
# 1. 后端
python -m venv .venv && . .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                               # 填 JWT_SECRET / ADMIN_PASSWORD
uvicorn app.main:app --host 127.0.0.1 --port 3002

# 2. 前端（两种方式任选）
cd frontend
npm install
npm run dev        # 开发服务器 http://localhost:8080（热更新）
npm run build      # 构建到 frontend/dist，3002 会直接托管这份产物
```

- `3002` 是应用端口：`/api/*` 走后端，`/` 与页面型深链回落到 `frontend/dist/index.html`。
- `8080` 是 Vite 开发端口：源码热更新；接口默认同源，需要时改 `frontend/vite.config.js` 的代理。
- Windows 上 5141–5240 是系统保留端口段，不要用 5173/5174。

## 生产部署

```bash
cd frontend && npm ci && npm run build && cd ..
docker compose up -d --build
```

compose 会把 `frontend/dist` 挂给 nginx（站点根）、`.env` 喂给后端；`data/ uploads/ logs/` 走卷。
nginx 已配 SPA 回落（`try_files $uri $uri/ /index.html`）与 CSP（`img-src 'self' data: blob:` 是折射贴图所需）。

## 数据与备份

- `data/` 运行时生成三库与 WAL，`uploads/` 存媒体，`logs/` 存运行日志，`backups/` 存备份——都不入库。
- 表结构变更走启动自愈迁移（`app/scripts/migrate_v2.py`），幂等，可重复执行。

## 已知边界

- 仍是「规划中」的分区：页面管理、友链管理、媒体资源、学习记录、日程、智能体、工作流
  （缺对应数据表与接口，需先做 schema 与迁移）。
- 已实装的空间分区：工作台、云文件、知识库、待办、番茄钟、项目中心、个人资料、账号与安全、
  界面设置、书签、AI 对话、系统状态，以及网站管理的 12 个面板。
- AI 对话需要服务端 `.env` 配置 `AI_API_KEY / AI_BASE_URL / AI_MODEL`，未配置时页面会明确提示。
- 单管理员；文章与留言列表未分页；文章编辑器是 HTML 文本 + 预览，不是所见即所得。
- 资源库内容为示例条目，替换 `content/resources.json` 即可。

## 版本

当前 `4.0.0`（见 `VERSION` 与 `CHANGELOG.md`）。
