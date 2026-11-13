# 课件复习发布验证 / Release validation

日期：2026-11-13（新加坡时间）。本记录只声明实际完成的检查。

## 本地结果

- 后端完整回归：**341 passed**，使用 PostgreSQL 17 + pgvector 的独立测试数据库。原有测试依赖的用户与保护文档由 `prepare_review_test_database.py` 创建为合成记录；没有复制真实课程资料。
- 新增 `backend/tests/test_review.py`：**14 项测试**。包括整页覆盖、顺序、摘录匹配、视觉来源、代码保真、无截断、扫描 PDF 原页渲染、PPTX 解析、错误输出失败、四则运算及舍入、所有权隔离、状态保存、活动任务上限、认证、演示系数、重试和总超时（部分用例在同一个测试中验证多个条件）。
- 前端 TypeScript 检查与 Vite 生产构建：通过。
- 新增前端源文件 ESLint：**0 errors / 0 warnings**。没有把旧项目所有文件的 lint 状态当作已验证结果。
- Playwright：**3 passed**，使用独立 Chrome 测试会话和合成课件，未操作用户现有浏览器标签。
- 人工查看实际桌面与 390px 窄屏截图；浏览器测试检查窄屏横向溢出。
- `git diff --check`：通过。

## 浏览器验收范围

桌面流程覆盖公式实际渲染、原始代码按文本显示、来源聚焦预览、原页打开/翻页/返回、复习进度、勘误确认、滑块读数、例题步骤、键盘搜索、速查与正文往返。

离线验收实际下载 HTML，检查字体为内嵌数据，关闭浏览器网络后以 `file://` 打开：公式、原页、速查、进度保存、线性演示均工作，重新加载能恢复本地进度，未发起 HTTP/HTTPS 请求。导出包含 KaTeX 许可。

窄屏流程覆盖目录展开/收起、原页弹窗、关闭和 English 切换。另一个回归用例给旧画布返回乱序的 `S7` / `S2` 来源和未知 `S99`，验证每张卡片按实际编号绑定，未知引用不会被分配其他页码。

UI 测试模拟 API，不能证明数据库或模型输出质量；相应行为由后端和真实服务检查分别覆盖。

## 实际 AI 与转换检查

使用已配置 DashScope Key，仅提交自制样例，无用户上传文件：

1. 文字总结：`qwen3.8-flash` 生成 1 个章节，覆盖样例页，包含 1 条速查；通过结构与摘录校验。
2. 图像读取：`qwen3-vl-plus` 读取自制关系式图片，识别出样例数字。
3. PPTX 完整流程：2 张合成幻灯片 → LibreOffice 转 PDF → 原页视觉读取 → 全文总结 → 来源/覆盖校验 → ready。实际输出：**2 页、1 节、2 条速查、1 条勘误候选**。命令为 `PYTHONPATH=. .venv/bin/python scripts/smoke_review.py --pptx --vision`。

这是功能连通性验证，不是所有学科、所有图表或全部输出的准确率评测。复算仅覆盖显式基本数字算式，视觉读取和推导仍可能出错。

## 发布边界

- 新增 GitHub Actions 执行后端独立测试库回归、前端构建和 Playwright。远程运行状态应以 GitHub Actions 页面为准。
- 首次远程运行发现旧 PDF 测试使用的 ReportLab 未声明为开发依赖；已补入 `.[dev]`，使全新环境也能安装完整测试依赖。
- 首次发布未重建 Docker 镜像；后续用户环境复测已重建前后端，实际确认 KaTeX、PDFium、PPTX 与 LibreOffice 可用。直接针对 Docker 的 5174 地址再次运行浏览器验收，3 项通过。
- 部署仍要求单 API worker 和持久上传卷；BackgroundTasks 不提供进程重启后的续跑。
- 默认合计 120 页、30 分钟总超时；离线原图合计上限 100 MB。
- 保留原项目构建的大主包提示；没有把性能优化或所有依赖安全问题列为本次已解决事项。

## English

Validated on 2026-11-13: 341 backend tests passed against an isolated PostgreSQL/pgvector database with synthetic legacy fixtures; frontend type checking/build passed; new frontend source files passed ESLint without warnings; three real-browser tests passed. Browser tests use mocked APIs and synthetic materials, covering desktop/mobile interactions, explicit citation-ID binding, actual KaTeX output and an offline HTML file with zero HTTP(S) requests.

Real-provider smoke tests used synthetic content only. Text summarization with `qwen3.8-flash` passed source validation. `qwen3-vl-plus` read a synthetic image. The complete two-slide PPTX pipeline (LibreOffice conversion, page rendering, visual reading, source-bound generation) finished ready with two pages, one section, two quick-reference entries and one correction candidate.

These are connectivity and regression checks, not a semantic accuracy benchmark. Docker images were rebuilt in a subsequent runtime check; all three browser tests also passed against the actual Docker frontend on port 5174. Single-worker persistence, restart recovery, page/time/export limits and other boundaries are documented in [Courseware Review](COURSEWARE_REVIEW.md). Remote CI status is reported by GitHub Actions itself.


## Docker 运行环境复测

发现旧容器映射了新前端源码，但镜像内保留旧依赖，导致 KaTeX 无法导入；后端镜像也缺少新增依赖。已重建应用镜像、补齐每个构建上下文的 `.dockerignore`、取消默认前端源码映射并统一到 Node 22，启动脚本增加复习模块与依赖检查。数据库容器和课程上传目录保留。

验收直接针对实际 Docker 页面：`PLAYWRIGHT_BASE_URL=http://127.0.0.1:5174 npm run test:e2e`。UI 测试的 API 仍为合成模拟接口，后端真实 AI 结果需单独核验。


复测最终结果：实际前端容器内生产构建通过；实际 Docker 前端的 3 项浏览器测试通过。旧 `qwen-turbo` 配置在实测中持续返回 `429 / limit_requests`，已将 Docker 默认值与后端统一为同一凭证下可用的 `qwen3.8-flash`，并保留环境变量覆盖。更正后，在 Docker 后端中完成合成 PPTX 的转换、逐页视觉读取和总结，返回 ready：2 页、1 节、1 条速查、1 条勘误候选。


## 状态提示与长课件修复

新增任务阶段、页数、耗时、自动恢复历史、失败停止提示及重新生成入口；重复提交复用活动任务。引用改用服务器分配的片段编号，复制真实原文，继续拒绝未知或跨页来源。新增清单分类。

本次专项验证：18 个后端复习测试通过；4 个浏览器验收通过，新增用例验证实际阶段切换、耗时、4/28 页显示、失败停止和重新生成。经用户明确授权，仅将当前课件前 4 页发送到配置的 DashScope 复测，77.2 秒完成并通过来源绑定，未发送余下课件页。

独立合成 PostgreSQL/pgvector 数据库中的完整回归结果：**345 passed**。
