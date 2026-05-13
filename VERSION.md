# PPT-SVGAgent v0.5 商用手册

> 版本日期：2026-05-13
> 代码版本：`deb9432`（Git commit）
> 项目地址：https://github.com/junnylin8586-eng/PPT-SVGAGENT

---

## 一、产品概述

### 1.1 产品定位

PPT-SVGAgent 是一款基于 AI 的演示文稿智能生成平台，面向企业、机构和个人用户，提供从"主题描述"或"结构化大纲"到"专业级幻灯片"的全流程自动化生成能力。

### 1.2 核心能力

| 能力 | 说明 |
|------|------|
| AI 主题分析 | 输入自然语言主题描述，AI 自动规划幻灯片结构 |
| 结构化快速导入 | 粘贴"第X页"格式文本，秒级完成页面创建（无需 AI） |
| 多 AI 提供商 | 支持 MiniMax（主力）、OpenAI、Anthropic、Gemini、Qwen、DeepSeek |
| 20+ 专业模板 | 政府蓝、科技风、学术答辩等场景模板库 |
| SVG 高质量渲染 | 矢量格式输出，无限放大不失真 |
| PPTX 批量导出 | 一键生成可编辑 PowerPoint 文件 |

### 1.3 适用场景

- 企业年度汇报、战略规划汇报
- 政府/央企数字化转型方案汇报
- 学术答辩、论文演示
- 产品发布、商业提案
- 内部培训、教学课件

---

## 二、技术架构

### 2.1 系统架构图

```
┌─────────────────────────────────────────────────────────┐
│                      用户界面（Browser）                  │
│                   React + Vite + TypeScript             │
└────────────────────────────┬────────────────────────────┘
                             │ HTTP/REST + SSE
┌────────────────────────────┴────────────────────────────┐
│                    Flask 后端（:5031）                   │
│  ┌──────────────┐  ┌────────────┐  ┌───────────────┐  │
│  │ AI 大纲解析  │  │ AI 生成    │  │ SVG 渲染引擎  │  │
│  │（结构化切分）│  │（多提供商）│  │（ppt_master） │  │
│  └──────────────┘  └────────────┘  └───────────────┘  │
│  ┌──────────────┐  ┌────────────┐  ┌───────────────┐  │
│  │ 数据库模型    │  │ API 路由    │  │ PPTX 导出     │  │
│  │（SQLAlchemy） │  │（REST）    │  │               │  │
│  └──────────────┘  └────────────┘  └───────────────┘  │
└────────────────────────────┬────────────────────────────┘
                             │
                    ┌────────┴────────┐
                    │  MiniMax API    │
                    │ （或其他 AI）   │
                    └─────────────────┘
```

### 2.2 技术栈

**后端：**
- Python 3.10+ / Flask（Web 框架）
- SQLAlchemy（ORM）+ SQLite（数据库）
- ppt_master_engine（SVG 渲染引擎）
- MiniMax / OpenAI / Anthropic / Gemini（AI 提供商）

**前端：**
- React 18 + Vite + TypeScript
- Tailwind CSS + Lucide Icons
- Zustand（状态管理）
- React Router（路由）

### 2.3 目录结构

```
D:\AI\ppt-agent\
├── backend/
│   ├── app.py                          # 应用入口（Flask）
│   ├── controllers/
│   │   ├── ppt_controller.py           # PPT 相关 API（核心）
│   │   └── settings_controller.py     # 设置 API
│   ├── models/
│   │   ├── project.py                  # 项目数据模型
│   │   ├── page.py                      # 页面数据模型
│   │   └── settings.py                  # 配置数据模型
│   ├── services/
│   │   ├── outline_generator.py         # 大纲解析（"第X页"格式）
│   │   ├── theme_analysis_service.py    # AI 主题分析（SSE 流式）
│   │   ├── ai_generation_service.py     # SVG 生成（核心）
│   │   ├── svg_export_service.py        # PPTX 导出
│   │   └── ai_providers/                # 多 AI 提供商
│   └── ppt_master_engine/               # SVG 渲染引擎
│       └── templates/                   # 20+ 设计模板
├── frontend/
│   ├── src/
│   │   ├── api/client.ts               # API 客户端
│   │   ├── pages/
│   │   │   ├── HomePage.tsx            # 首页（项目列表）
│   │   │   └── WorkspacePage.tsx      # 工作区（核心页面）
│   │   └── components/
│   │       ├── home/NewProjectModal.tsx      # 新建项目
│   │       └── workspace/
│   │           ├── PageEditorModal.tsx        # 单页编辑
│   │           ├── OutlineEditorModal.tsx     # 大纲编辑
│   │           ├── GenerationProgress.tsx     # 生成进度
│   │           ├── ExportDialog.tsx           # 导出弹窗
│   │           └── StyleSettingsModal.tsx    # 样式设置
│   └── vite.config.ts                  # Vite 配置（含 API 代理）
├── docs/
│   └── images/                        # 示例幻灯片 SVG
├── .env.example                       # 环境变量模板
└── README.md
```

---

## 三、API 接口文档

### 3.1 项目管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/ppt/projects` | 获取所有项目列表 |
| POST | `/api/ppt/projects` | 创建新项目 |
| GET | `/api/ppt/projects/:id` | 获取项目详情 |
| PUT | `/api/ppt/projects/:id` | 更新项目 |
| DELETE | `/api/ppt/projects/:id` | 删除项目 |

### 3.2 页面管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/ppt/projects/:id/pages` | 获取所有页面 |
| POST | `/api/ppt/projects/:id/pages` | 批量创建/更新页面 |
| PUT | `/api/ppt/projects/:id/pages/:page_id` | 更新单页 |
| DELETE | `/api/ppt/projects/:id/pages/:page_id` | 删除单页 |

### 3.3 生成

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/ppt/projects/:id/generate` | 生成所有页面 SVG |
| POST | `/api/ppt/projects/:id/pages/:page_id/generate` | 生成单页 SVG |

### 3.4 导出

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/ppt/projects/:id/export` | 导出 PPTX |

### 3.5 主题分析

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/ppt/analyze-theme` | AI 分析主题（SSE 流式） |

---

## 四、安装与部署

### 4.1 环境要求

- Python 3.10+
- Node.js 18+
- MiniMax API Key

### 4.2 后端部署

```bash
cd D:\AI\ppt-agent\backend

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
copy .env.example .env
# 编辑 .env，填入 MINIMAX_API_KEY

# 启动
python app.py
# 后端地址：http://localhost:5031
```

### 4.3 前端部署

```bash
cd D:\AI\ppt-agent\frontend

# 安装依赖
npm install

# 开发模式启动
npx vite
# 前端地址：http://localhost:5200
```

### 4.4 生产部署建议

- 后端：使用 Gunicorn + Nginx 替代开发服务器
- 数据库：切换为 PostgreSQL（开发用 SQLite）
- 前端：执行 `npm run build` 构建静态文件，由 Nginx 提供服务
- HTTPS：务必启用 HTTPS（API Key 传输安全）

---

## 五、使用指南

### 5.1 新建项目（AI 分析模式）

1. 打开首页，点击「新建项目」
2. 输入项目名称
3. 输入主题描述（如：数字化转型汇报、智慧城市方案等）
4. 点击「AI 生成大纲」—— AI 自动分析并返回结构化页面列表
5. 可编辑大纲内容后，点击「开始生成」
6. 生成完成后，点击「导出」下载 PPTX 文件

### 5.2 快速导入（跳过 AI）

如果已有清晰的 PPT 内容结构，可以直接粘贴以下格式：

```
第1页：封面
标题：项目名称
副标题：副标题内容

第2页：章节名称
标题：本页标题
内容要点：
- 要点1
- 要点2
- 要点3

第3页：章节名称
...
```

粘贴后点击「确认所有页面」→ 所有页面一次性保存 → 直接点「开始生成」。

### 5.3 单页编辑

点击任意页面缩略图 → 进入单页编辑弹窗 → 修改大纲内容/详细描述 → 保存 → 单独生成该页或重新生成全部。

---

## 六、版本记录

### v0.5（2026-05-13）—— 当前版本

**代码版本：** `deb9432`

**新增功能：**
- ✅ AI 主题分析（SSE 流式返回）
- ✅ "第X页"格式快速导入（无需 AI，秒级完成）
- ✅ 统一确认保存（批量保存所有页面大纲）
- ✅ 多 AI 提供商支持（MiniMax / OpenAI / Anthropic / Gemini）
- ✅ 20+ 专业模板
- ✅ SVG 高质量渲染
- ✅ PPTX 批量导出

**Bug 修复：**
- 🐛 修复大纲解析"第X页"格式切分错误
- 🐛 修复 `analyze-theme` API 502 错误（`.env` 路径 + 变量名）
- 🐛 修复批量保存后页面缩略图不显示 ✅ 标记
- 🐛 修复 `ai_generation_service.py` 中 `page_outline` 未定义 bug

**已验证功能：**
- ✅ 15 页项目完整生成（智能体在电网中的实用化应用研究）
- ✅ 5 页通用示例生成（智慧城市数字化转型）
- ✅ 批量保存 + 统一确认按钮
- ✅ PPTX 导出功能
- ✅ 新建 + 编辑 + 删除页面

---

## 七、配置说明

### 7.1 环境变量（`.env`）

```bash
# MiniMax API（主要 AI 提供商）
MINIMAX_API_KEY=your-api-key-here
MINIMAX_CN_API_KEY=your-api-key-here

# 可选：其他 AI 提供商
# OPENAI_API_KEY=your-openai-key
# ANTHROPIC_API_KEY=your-anthropic-key
# GEMINI_API_KEY=your-gemini-key
```

### 7.2 数据库

- 开发环境：SQLite（`backend/` 目录下的数据库文件）
- 生产建议：PostgreSQL / MySQL

### 7.3 模板配置

可通过前端工作区右上角「模板」按钮切换，当前模板列表：

| 模板名 | 风格 | 适用场景 |
|--------|------|----------|
| `government_blue` | 深蓝政务风 | 政府/央企汇报 |
| `government_red` | 红金党政风 | 党建/红色主题 |
| `ai_ops` | 科技蓝黑 | AI/科技公司 |
| `academic_defense` | 学术蓝白 | 论文答辩/学术 |
| `google_style` | 简约多彩 | 互联网/创意 |
| `china_telecom_template` | 运营商蓝 | 通信/电信行业 |

---

## 八、已知限制

| 限制 | 说明 | 建议 |
|------|------|------|
| 网络要求 | 需能访问 MiniMax API（国内环境一般可达） | 如无法访问，可配置代理 |
| 页数限制 | 建议单项目不超过 50 页 | 大型汇报可拆分为多个项目 |
| 图片生成 | 当前版本 SVG 输出，PPTX 导出基于矢量 | 暂不支持真实图片插入（可手动在 PPTX 中添加） |

---

## 九、许可证

MIT License

## 十、联系方式

- GitHub：https://github.com/junnylin8586-eng/PPT-SVGAGENT
- 问题反馈：提交 GitHub Issue

---

*本文件由 PPT-SVGAgent 自动生成，最后更新：2026-05-13*