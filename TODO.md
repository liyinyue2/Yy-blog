# Y's Blog — Delivery Checklist

- [x] **首页只保留 Home Hero。** `/` 现在只承载第一版双手动态点阵 Hero、中文品牌导航、Hero 文案和底部 RSS/GitHub/Twitter(X) 入口，不再把文章、分类、关于和订阅内容堆在首页向下滚动。

- [x] **第一版双手点阵背景。** 首页恢复 Canvas 代码绘制的双手点阵背景：使用指定 Higgsfield 图像的四个裁切、两组离屏采样画布、五级黑色 LED 点阵、20 秒漂移/呼吸/滚动动画，以及左右手交替的点对点姿态 glitch dissolve。

- [x] **独立内容页面。** 新增 `/articles.html` 文章页、`/categories.html` 分类页、`/tags.html` 标签页、`/about.html` 关于页和 `/subscribe.html` 订阅页，每个页面都有独立标题、内容和共享导航。

- [x] **真实文章详情页。** 三张文章卡片现在分别进入 `/post-interaction.html`、`/post-whitespace.html` 和 `/post-workflow.html`；详情页提供标题、分类、摘要、正文、引用、上一篇/下一篇和返回文章列表。

- [x] **导航与响应式体验。** 桌面导航指向真实页面路由并高亮当前页面；移动端保留菜单按钮、展开面板、ARIA 状态和点击后自动收起；共享 CSS 适配桌面与移动端页面布局。

- [x] **内容交互。** 文章页保留可扩展的卡片筛选与阅读交互基础；标签和分类页面提供可点击入口；订阅页提供邮箱表单反馈；登录按钮提供准备中提示。

- [x] **验证与保存。** `manus-routes.json` 已声明 9 个页面路由；所有页面、共享 CSS/JS 通过语法检查，9 个路由均返回 200，并完成首页、文章列表、文章详情的桌面/移动预览检查。

# v1.1 全栈升级（2026-11-01）

- [x] **SQLite 数据库。** 新增 `blog.db`：articles / categories / tags / article_tags / subscribers 五张表，首次启动自动建表并从原静态页迁移 3 篇文章。

- [x] **REST API。** serve.py 升级为全栈后端（纯标准库）：`/api/articles`（支持 ?category= / ?tag= / ?q= 搜索）、`/api/articles/<slug>`、`/api/categories`、`/api/tags`、`/api/stats`、`POST /api/subscribe`；管理接口 `/api/admin/*`（X-Admin-Token 鉴权，ADMIN_TOKEN 环境变量配置）。

- [x] **动态页面。** 文章/分类/标签页改为从 API 动态渲染，支持分类筛选与标签过滤（/articles.html?tag=xxx）；`/post-<slug>.html` 由数据库实时渲染，含阅读计数与上一篇/下一篇导航；新增 `/rss.xml` 订阅源。

- [x] **订阅入库。** 订阅表单提交到后端，邮箱校验 + 去重，写入 subscribers 表。

- [x] **管理后台。** 新增 `/admin.html`：令牌登录、站点统计、文章增删改查（含标签编辑）、订阅者列表。

# v1.2 留言板 + 完整后台（2026-11-01）

- [x] **导航栏完整化。** 所有页面（含后台）导航统一为：首页 / 文章 / 分类 / 标签 / 留言 / 关于 + 订阅，桌面与移动端菜单同步更新。

- [x] **留言板。** 新增 `/messages.html`：游客留言（昵称可匿名、联系方式选填仅博主可见）；留言默认公开展示，博主可在后台回复、隐藏或删除。

- [x] **数据库扩展。** 新增 `messages`（留言）与 `settings`（站点设置）两张表。

- [x] **完整后台管理面板（/admin.html）。** 六大模块：文章（新建/编辑/删除，含标签编辑）、分类（增删改，非空分类保护）、标签（删除）、留言（回复/隐藏/删除）、订阅者（列表）、站点设置（站点名称、首页 Hero 文案、关于页内容，实时生效于前台）。

- [x] **验证。** 留言发布/回复/隐藏、分类增删改、设置读写、全部 10 个页面路由均通过；管理接口统一令牌鉴权。

# v1.3 社交链接改造（2026-11-01）

- [x] **首页底部社交链接。** 删除 RSS订阅 与 Twitter(X) 入口，新增 微信 / QQ / 抖音 三个入口（GitHub 保留）。

- [x] **点击行为。** 后台填主页链接（http 开头）则新窗口跳转；填微信号 / QQ 号则点击自动复制并弹提示。

- [x] **关于页「找到我」。** 新增社交账号展示区，与首页共享同一份配置；空值自动隐藏。

- [x] **后台可控。** 站点设置新增「社交链接」分组：微信号 / QQ 号 / 抖音主页三项，保存后前台实时生效。

- [x] **补充：GitHub 链接入库。** GitHub 入口原为占位符，现纳入站点设置（默认 https://github.com/liyinyue2），与微信/QQ/抖音共用同一套跳转/复制/隐藏逻辑，并同步展示在关于页。

# v1.4 Y 字图标 + Word/PDF 导入（2026-11-01）

- [x] **网站图标。** 全站 Logo 与浏览器标签页图标（favicon）更换为艺术字 Y（/y-mark.svg），与原极简风格一致；kindred-mark.svg 与 app.config.ts 同步更新。

- [x] **Word/PDF 转文章。** 后台文章页新增「导入 Word / PDF」按钮：上传 .docx / .pdf（≤15MB），服务端解析后自动填入标题与正文 HTML。Word 支持标题层级（Title/Heading→h2/h3/h4）、项目/编号列表、加粗与斜体；PDF 提取元数据标题并按句末标点智能分段。旧版 .doc 提示另存为 .docx。

- [x] **依赖。** 新增 python-docx；PDF 使用环境内已有的 PyMuPDF。

# v1.5 代码审计与完善（2026-11-01）

- [x] **导航精简。** 所有页面（含后台与移动端菜单）删除左上角「订阅」入口；订阅页与 RSS 源保留（/subscribe.html、/rss.xml）。

- [x] **审计修复（后端）。** 标签 slug 由随机的 hash() 改为确定性 md5 并迁移存量数据（修复重启后标签链接失效）；RSS 输出补 XML 转义（特殊字符不再破坏订阅源）；文章详情页标题/分类/摘要 HTML 转义；管理令牌改用常数时间比较（hmac.compare_digest）；请求体加 25MB 上限（超限返回 413）。

- [x] **审计修复（内容与前端）。** 删除 3 个旧静态文章页僵尸副本；访问不存在的文章返回样式化 404 页面；修复 site.js 残留的旧品牌名；清理 admin.html 重复死代码。

- [x] **新功能。** 文章列表页新增搜索框（防抖 300ms，按标题/摘要实时检索）。

- [x] **补充：导入保存流程优化（2026-11-01 晚）。** 修复「导入 Word/PDF 后保存失败」：slug 留空时根据标题自动生成（支持中文 slug），冲突自动加 -2/-3 后缀；导入成功自动填当天日期；保存成功显示可点击的「查看文章」链接并自动清空表单；错误提示红色高亮；编辑/删除接口 URL 兼容中文 slug。

# v1.7 分类/标签合并进文章页（2026-11-01）

- [x] **导航精简。** 导航现为：首页 / 文章 / 留言 / 关于；删除独立的分类页与标签页（/categories.html、/tags.html 下线，路由清单同步）。

- [x] **文章页组合筛选。** 文章列表页新增「标签」筛选行：分类一行 + 标签一行（带文章计数），两者可叠加过滤（如：前端开发 ∩ 交互设计）；点击已选标签可取消；筛选状态同步到 URL（?tag=、#分类），可分享/刷新保持。

- [x] **联动调整。** 文章详情页底部的标签链接改为跳转文章页并自动按该标签过滤；搜索与组合筛选可同时使用。

- [x] **补充：标签功能整体下线（2026-11-01 晚）。** 按用户要求移除标签体系：文章页只保留搜索 + 分类筛选；文章详情页去掉底部标签区块；后台移除「标签」选项卡与文章表单的标签输入。数据库中历史标签数据保留（不再展示），后台分类管理不受影响。

# v1.8 全面功能测试与代码审计（2026-11-01）

- [x] **自动化功能测试。** 60+ 项检查覆盖：11 个页面/静态资源路由、全部公开 API（文章/分类/标签/统计/设置/留言/订阅/搜索/过滤）、管理鉴权、文章与分类 CRUD、Word/PDF 导入（含坏输入）、请求体限制、路径边界，全部通过。

- [x] **审计修复（后端 serve.py）。** ① 分类 slug 路由正则 [a-z0-9-] 放宽为 [\w-]，修复中文 slug 分类无法更新/删除；② 日期校验从仅查格式升级为 strptime 真实日期校验（2026-02-30 等不再入库）；③ 订阅邮箱加 254 字符上限；④ 超大请求体返回 413 前先分块丢弃请求体，修复连接被 RST 导致客户端读不到错误响应；⑤ RSS 频道标题改为跟随站点设置。

- [x] **审计修复（前端）。** ① 修复后台选项卡切换遍历已删除 tab-tags 导致整个选项卡 JS 报错的严重 bug；② 补上保存失败红色提示（.is-error）缺失的 CSS；③ 清理 site.js 两段死代码（旧版静态卡片筛选、遗留阅读弹窗逻辑）；④ 搜索时同步清理 URL 中的分类 hash。

- [x] **数据清理。** 移除全部测试遗留（测试文章、XSS 测试留言、测试分类、测试订阅）。


## v1.10 安全加固（2026-11-01）
- [x] **安全响应头。** 所有响应统一注入 `X-Content-Type-Options: nosniff`、`X-Frame-Options: DENY`、`Referrer-Policy`、`Permissions-Policy` 和 CSP（允许 Google Fonts 与文章内外链图片）。
- [x] **接口限流。** 内存级滑动窗口：留言 / 订阅每 IP 每分钟 5 次，超限返回 429。
- [x] **管理令牌防暴力破解。** 同 IP 15 分钟内令牌错 5 次即临时锁定；正确令牌不受影响。
- [x] **隐藏服务器指纹。** Server 头不再暴露 Python / http.server 版本号。

## v1.11 渗透测试与安全审计（2026-11-01）
- [x] **修复存储型 XSS。** 新增 sanitize_html() 白名单清洗器，文章正文与关于页富文本入库前剥离 script/事件属性/javascript: 协议。
- [x] **修复畸形 JSON 崩溃。** read_json_body 校验必须为对象，非 dict 一律 400。
- [x] **修复 Host 头注入。** RSS 链接改用 BASE_URL 环境变量，不再信任请求 Host。
- [x] **错误信息泛化。** SQLite/解析异常不再回显客户端，全部转入审计日志。
- [x] **新增审计日志。** logs/audit.log 记录全部后台敏感操作与认证失败。
- [x] **后台令牌改 sessionStorage。** 关闭浏览器即失效。
- [x] **HSTS 条件开关 + 启动弱令牌警告。** ENABLE_HSTS=1 开启；默认令牌启动时告警。
- [x] **渗透测试通过项。** SQLi 免疫、路径穿越拦截、越权 401/锁定、上传白名单、SSRF/XXE 无攻击面、CSRF 天然免疫。
- 详细报告见《安全审计报告.md》。
- [x] **后台地址防扫描（2026-11-01）。** admin.html 改名为 /yy-AviuuP3r.html（secrets 随机生成），旧地址 404。⚠️ 令牌默认值 yy-admin-2026 在公开仓库源码可见，部署时必须设 ADMIN_TOKEN 环境变量。
- [x] **删除硬编码默认令牌（2026-11-01）。** 源码不再含任何默认令牌；未设 ADMIN_TOKEN 时首启自动生成强随机值存 .admin_token（已入 .gitignore）。旧令牌 yy-admin-2026 立即失效。

## v1.12 深度复查加固（2026-11-01 第二轮）
- [x] **畸形 Content-Length 头崩溃。** 畸形头按 0/400 处理，不再中断线程。
- [x] **入库字段长度上限。** 标题120/摘要300/正文30万字符/标签20个×50字/分类与设置字段全部封顶，防超大字段撑爆页面。
- [x] **docx 解压炸弹防护。** 解析前用 zipfile 预检解压后总量（>64MB 拒绝），实测 132KB→100MB 炸弹被拦截。
- [x] **限流桶内存防膨胀。** 超 4096 个 key 自动清理过期桶。
- [x] **后台脚本外置 + CSP 收紧。** 内联脚本抽到 admin.js，script-src 去掉 'unsafe-inline'。
- [x] **订阅邮箱枚举防护。** 已订阅与首次订阅返回一致文案。

---

# v2.0 架构升级（2026-11-02，FastAPI 模块化单体）

> 按升级指令文档 8 阶段串行执行；每阶段独立验收并打 tag（v2.0-phase1 … phase8）。

## Phase 1 骨架
- [x] app/（FastAPI + pydantic-settings 配置 + SQLite WAL/ATTACH 三库连接管理）
- [x] deploy/（nginx.conf、Dockerfile python:3.12-slim）+ docker-compose.yml（nginx:alpine + app，app 不暴露宿主机端口）
- [x] 验收：health OK / 静态 200 / 三库 WAL / 安全响应头齐全
- ⚠️ 偏差：本机沙箱禁用 WSL → Docker Desktop 无法启动，compose 验收延后至服务器执行（功能验收已用 uvicorn 等价完成）

## Phase 2 认证
- [x] users 表 + init_admin.py（bcrypt，密码仅环境变量）
- [x] JWT 双令牌（access 15min / refresh 7d）+ get_current_user + require_role
- [x] login/refresh/logout/me + 登录失败限流（修复：只统计失败尝试，成功登录不占额度）
- [x] 验收：双令牌 / 401 / 429 锁定 / 审计日志

## Phase 3 博客迁移
- [x] 文章/分类/留言/订阅/设置/RSS/Word-PDF 转换/详情页模板 全部迁移（行为镜像 v1.0）
- [x] sanitize_html 白名单清洗移植；管理接口全部 require_admin；X-Admin-Token 废弃（401）
- [x] 后台面板最小 JWT 化（登录框换账号密码，api() 自动带 Bearer + 401 静默续期）——前端仅此功能性改动，视觉未动
- [x] /api/stats、/rss.xml 兼容路由补齐
- [x] 验收：前端行为一致 / XSS 剥离 / 审计日志 / 转换接口（docx 23 字、php 400）

## Phase 4 统一标签
- [x] tags(name) + taggables(entity_type×entity_id)；v1 旧标签幂等迁移（含 FK 重建踩坑修复）
- [x] 校验：≤32 字、白名单正则拒绝 <>&"'、entity_type 白名单
- [x] 验收：打标→按类型查询返回关联文章；旧文章标签回显正常

## Phase 5 工作台
- [x] workspace.db：notes/todos/bookmarks（迁移脚本 schema 前缀修复：表曾误建到主库）
- [x] 全部 require_admin；富文本 sanitize；分页 limit≤100；书签 URL 仅 http/https
- [x] 验收：401/CRUD/XSS/伪协议拦截/limit 钳制

## Phase 6 音乐
- [x] music.db：tracks；流式上传（UUID 落盘、扩展白名单、MIME 签名、100MB 上限）
- [x] Range 流媒体：206 / Content-Range / Accept-Ranges / 256KB 分块；mutagen 时长解析
- [x] 验收：10.9MB 上传、php 400、假 wav 400、Range 206、无令牌 401
- ⚠️ 偏差：safeuploads 库 PyPI 不存在，以同等强度内置校验实现（文件名净化+白名单+签名）

## Phase 7 网盘
- [x] files 表（主库）；上传链：文件名净化（../ 直接 400）→ 扩展白名单 → MIME 签名 → ZIP 炸弹预检（256MB）→ 20MB 上限 → UUID 无扩展落盘
- [x] 下载 require_admin + Content-Disposition attachment + resolve/is_relative 路径防护
- [x] 验收：exe/php/假pdf/穿越文件名全 400；未登录下载 401；uploads/ 不在 Nginx 静态根

## Phase 8 收尾
- [x] legacy/ 冷备（serve.py + blog.db-pre-v2.db + README）；删除 app.config.ts/package.json/manus-routes.json
- [x] app/scripts/backup.py 三库 .backup（保留最近 42 份）
- [x] 全模块回归绿 + 审计报告增补（JWT/上传/Range 三节）
- [ ] Docker Compose 在服务器实测（本机 WSL 受限，待部署时执行）

## v2.0 新增安全约束落实情况
零硬编码密钥（.env.example + secrets 生成）· 全参数化 SQL · Pydantic 模型校验全部请求体 ·
CORS 白名单（无 *）· 全局安全响应头中间件 · 审计日志全覆盖（登录/增删改/上传/删除文件）

# v2.3 个人数字空间（2026-11-02，P0–P7 全量）

- [x] **P0 设计系统**：site.css token 层（亮暗双套）+ 玻璃组件库 + icons.svg sprite（36 图标）+ 环境光斑 + hands.js 帧率节流；tag `v2.2-p0`。
- [x] **P1 知识中心**：articles.kind（文章/技术笔记）、前台 kind 切换、后台标签管理 UI、启动迁移自愈；tag `v2.2-p1`。
- [x] **P2 项目中心**：projects/project_logs 表、公开项目页 `/projects.html` + 动态详情页 `/projects/{slug}.html`、后台项目管理（状态/进度/技术栈/可见性/开发日志）；tag `v2.3-p2`。
- [x] **P3 个人空间**：`/space.html` 单页应用（左侧图标栏 + hash 路由）：概览（问候/统计/今日待办/最近笔记/快速入口）、知识笔记（双栏编辑）、云盘、效率工具（番茄钟 localStorage+服务端双写 / JSON / 文本 / 网络信息）、音乐库、AI 助手；`/api/space/search` 六类聚合搜索；待办增强（due/priority）；tag `v2.3-p3`。
- [x] **P4 云盘增强**：files.is_starred、文件名搜索、收藏筛选、图片/文本在线预览；tag `v2.3-p4`。
- [x] **P5 音乐增强**：收藏（track_favorites）、最近播放（play_history，去重到曲目）、space 音乐面板收藏区/历史区/星标；tag `v2.3-p5`。
- [x] **P6 AI 中心**：ai_conversations/ai_messages、SSE 流式聊天（OpenAI 兼容上游，密钥仅服务端 env：AI_API_KEY/AI_BASE_URL/AI_MODEL）、限流 60s/10 次、审计埋点、前端 textContent 渲染；未配置密钥时 503 提示；tag `v2.3-p6`。
- [x] **P7 收尾**：审计日志在线查看（`/api/admin/audit` + 后台面板搜索/刷新）、遗留表 tags_legacy/article_tags 归档后 DROP（`python -m app.scripts.cleanup_legacy`，归档在 data/legacy-archive/）、89 项回归全绿、桌面/移动双端截图自查；tag `v2.3`。
- [ ] **待办（下一阶段）**：Docker Compose 服务器实测；site.css 残余硬编码色值清理；AI 知识库问答（RAG）；后台 admin 页内联样式迁移到外部 CSS。

# v2.4 Liquid Glass 全站视觉系统（2026-11-02）

- [x] **官方组件研究**：Aceternity UI LiquidGlass 源码（React/TSX）完整研读——Canvas SDF+Snell 位移贴图、feDisplacementMap×3 色散、backdrop-filter: url(#id)、三级降级、ResizeObserver 重建、filter id 防缓存。
- [x] **原生移植**：`public/liquid-glass.js`（零依赖，纯原生 JS），`data-liquid-glass` 属性驱动渐进增强，`data-lg-*` 参数（radius/bevel/scale/aberration/frost）。来源与许可注明于文件头。
- [x] **应用范围**：折射=全站顶栏/首页 hero 导航/个人空间侧栏+播放条/音乐播放条/搜索弹层/分段标签容器；磨砂=普通玻璃按钮/输入框/后台侧栏；不透明=reduced-transparency。
- [x] **分段标签**：kind/topic/project 三组筛选实现平滑移动的深色选中层（seg-pill），动态重渲染自愈。
- [x] **统一交互**：悬停/按下/焦点环/禁用全站一致；亮暗双主题 --lg-tint 变量。
- [x] **兼容性**：Chromium 折射实测通过；Safari/Firefox 磨砂降级（判定逻辑与官方一致）；prefers-reduced-transparency CSS 兜底；CSP img-src 放行 blob:。
- [x] **验证**：89 项回归全绿；桌面/移动/触摸截图与交互测试通过；零 console 报错。tag `v2.4-liquid-glass`。
- [ ] 待办：真实 Safari/Firefox 人工复验（无头环境只验证了判定分支）；折射元素数量可按需增减（改 data-liquid-glass 即可）。
