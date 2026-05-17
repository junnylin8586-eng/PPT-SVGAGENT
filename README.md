# PPT Agent - AI智能生成PPT系统

**将自然语言描述或结构化大纲，快速转换为专业级幻灯片，一键导出可编辑PPTX。**

[![GitHub stars](https://img.shields.io/github/stars/junnylin8586-eng/PPT-SVGAGENT)](https://github.com/junnylin8586-eng/PPT-SVGAGENT/stargazers)
[![License](https://img.shields.io/github/license/junnylin8586-eng/PPT-SVGAGENT)](https://github.com/junnylin8586-eng/PPT-SVGAGENT/blob/main/LICENSE)

---

## 功能特性

### 🧠 AI智能生成
- **主题分析** — 输入主题描述，AI自动分析并生成结构化PPT大纲
- **AI对话生成** — 通过对话方式描述需求，AI实时生成大纲内容
- **内容丰富度检测** — 自动评估每页内容的详细程度，智能选择主参考（大纲 or 详细描述）

### 🎨 统一设计系统
- **项目级设计简报** — 颜色/排版/图标风格跨页面统一，全片视觉协调
- **页面类型识别** — 自动识别封面/目录/章节/内容/结尾，注入对应设计规则
- **视觉元素质量** — 支持渐变/3D/水墨/扁平2.5D等多种图标风格

### 📋 高效编辑
- **大纲批量导入** — 粘贴"第X页：标题\n内容"格式，2秒完成所有页面创建
- **单页重生成** — 独立修改某一页的文案/描述，单独重新生成该页
- **大纲/详细描述编辑** — 双层内容结构，大纲决定页面主题，详细描述填充细节

### 📤 稳定导出
- **智能SVG净化** — 自动修复AI生成SVG中的格式问题（重复属性/裸&符/截断内容）
- **降级保护** — 个别页面SVG异常时自动跳过，其余页面正常导出
- **Native/Draft双模式** — 优先使用DrawingML原生形状（可编辑），异常时降级为图片

### 📁 多模板支持
- **17种内置模板** — 政府蓝/学术/金融/医疗/科技AI/深色高管等专业模板
- **模板预览** — 缩略图实时预览，无需猜测
- **一键切换** — 工作区随时更换模板，已生成页面同步更新

---

## 界面预览

| 首页 - 新建项目 | 工作区 - 生成进度 | 导出对话框 |
|:---:|:---:|:---:|
| ![首页](docs/images/home_page.png) | ![工作区](docs/images/workspace_page.png) | ![导出](docs/images/export_dialog.png) |

| AI对话生成大纲 | 模板选择器 | 单页编辑 |
|:---:|:---:|:---:|
| ![AI大纲](docs/images/ai_chat_outline.png) | ![模板](docs/images/template_selector.png) | ![页面编辑](docs/images/page_editor.png) |

---

## 快速开始

### 环境要求

| 组件 | 要求 | 说明 |
|------|------|------|
| Python | 3.11+ | 推荐使用 uv 管理 |
| Node.js | 18+ | 用于前端构建 |
| API Key | MiniMax / OpenAI 等 | AI生成必需 |

### 一键启动（推荐）

下载 release 包后双击运行：

```bash
# Windows
start.bat

# macOS / Linux
bash start.sh
```

### 手动启动

**后端**：
```bash
cd backend
cp .env.example .env          # 编辑 .env 填入你的 API Key
uv sync                      # 安装依赖
uv run python app.py          # 启动 (http://localhost:5201)
```

**前端**：
```bash
cd frontend
npm install                   # 安装依赖
npx vite --port 5200          # 启动 (http://localhost:5200)
```

---

## 使用流程

```
┌─────────────────────────────────────────────────────────┐
│  ① 创建项目    →    ② 生成大纲    →    ③ 选择模板        │
│                                                                 │
│  输入主题描述        AI对话/手动输入       17种专业模板          │
│  或粘贴结构化内容    实时生成预览          缩略图预览            │
└─────────────────────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────────────────────┐
│  ④ 批量生成    →    ⑤ 单页调整    →    ⑥ 导出PPTX         │
│                                                                 │
│  AI逐页生成          单页重生成/编辑       一键下载             │
│  实时进度条          修改大纲+描述         可编辑/可分享         │
└─────────────────────────────────────────────────────────┘
```

### 方式一：AI智能分析（输入主题描述）

1. 点击「新建项目」→ 输入项目名称和主题描述
2. 点击「AI 生成大纲」→ AI自动分析并生成结构化页面列表
3. 编辑大纲内容后，点击「开始生成」

### 方式二：结构化快速导入（跳过AI，秒级完成）

已有清晰的PPT内容结构？直接粘贴以下格式：

```
第1页：封面
标题：智慧城市数字化转型研究报告
副标题：基于新一代信息技术的城市治理创新实践

第2页：研究背景
标题：数字中国战略下的城市转型需求
要点：
- 政策驱动：数字中国建设全面提速
- 技术成熟：大模型、物联网、5G加速落地
- 民生需求：城市治理效率和居民体验双重提升
```

点击「确认所有页面」→ 直接点「开始生成」，**全程无需调用AI，2秒完成**。

---

## 技术架构

```
┌────────────────────────────────────────────────────────────┐
│                        前端 (React)                         │
│   首页 → 新建项目 → 工作区 → 生成/编辑 → 导出下载            │
└──────────────────┬─────────────────────────────────────────┘
                   │ Proxy :5200 → :5201
┌──────────────────▼─────────────────────────────────────────┐
│                      后端 (Flask)                            │
│                                                              │
│   controllers/  ← API 路由（生成/导出/模板/设置）             │
│   services/                                             │
│   ├── ai_generation_service    ← AI生成SVG                 │
│   ├── svg_export_service       ← SVG→PPTX导出              │
│   ├── page_content_planner     ← 内容规划/设计简报           │
│   ├── outline_generator        ← 大纲解析（"第X页"格式）     │
│   └── ai_providers/            ← 多AI提供商抽象层           │
│   models/                 ← SQLAlchemy ORM                 │
└──────────────────┬─────────────────────────────────────────┘
                   │
┌──────────────────▼─────────────────────────────────────────┐
│                 ppt_master_engine                            │
│   templates/layouts/  ← 17种设计模板（SVG+design_spec）       │
│   scripts/svg_to_pptx/ ← DrawingML转换引擎                   │
│   scripts/svg_finalize/← SVG后处理（图标嵌入/图片裁剪）        │
└─────────────────────────────────────────────────────────────┘
```

---

## 目录结构

```
ppt-agent/
├── backend/
│   ├── app.py                      # Flask 应用入口
│   ├── controllers/
│   │   ├── ppt_controller.py       # PPT API（生成/导出/模板）
│   │   ├── chat_controller.py       # AI对话/大纲生成
│   │   └── settings_controller.py   # 设置管理
│   ├── services/
│   │   ├── ai_generation_service.py    # SVG页面生成（含设计简报）
│   │   ├── svg_export_service.py       # PPTX导出（净化+降级）
│   │   ├── page_content_planner.py     # 内容优先级/页面类型检测
│   │   └── outline_generator.py        # "第X页"格式解析
│   ├── models/
│   │   ├── project.py              # 项目模型
│   │   └── page.py                 # 页面模型
│   └── ppt_master_engine/
│       ├── templates/layouts/      # 17种设计模板
│       └── scripts/
│           ├── svg_to_pptx/        # DrawingML转换器
│           └── svg_finalize/       # SVG后处理
├── frontend/src/
│   ├── components/
│   │   ├── home/NewProjectModal.tsx      # 新建项目（AI对话/大纲）
│   │   ├── workspace/
│   │   │   ├── PageEditorModal.tsx       # 单页编辑（大纲/详细描述）
│   │   │   ├── ExportDialog.tsx          # 导出下载
│   │   │   └── GenerationProgress.tsx    # 生成进度条
│   │   └── template/TemplateSelectorModal.tsx  # 模板选择
│   ├── pages/
│   │   ├── HomePage.tsx            # 首页
│   │   └── WorkspacePage.tsx       # 工作区
│   └── store/projectStore.ts       # 状态管理（Zustand）
├── docs/images/                    # 截图与示例
└── README.md
```

---

## 更新日志

### v0.7（2026-05-18）

**AI幻灯片生成质量三大改进**

- **内容优先级智能** — `page_content_planner.py`：自动比较大纲和详细描述的内容丰富度，选择更详细的一方作为主参考。告别"蓝底一行字"问题。
- **统一设计系统** — 整项目生成统一的设计简报（颜色/排版/图标风格），跨页面视觉一致。封面与结尾页风格对齐，章节页有区分但成系列。
- **页面类型感知** — 自动识别封面/目录/章节/内容/结尾，为每类页面注入对应设计规则和视觉质量要求。

**导出稳定性修复**

- **属性去重** — AI生成的SVG中重复的XML属性（如 `x="0" x="60"`）现在会被自动去重，避免DrawingML转换失败
- **降级保护** — 单个页面SVG异常时自动跳过并告知用户，其余页面正常导出，不再因为一个问题导致整次导出失败

### v0.6（2026-05-15）

- **AI对话生成大纲** — 输入主题后切换到对话模式，AI实时生成结构化大纲，可实时修改
- **自定义模板上传** — 支持将现有PPTX文件导入为自定义模板（Phase 4）
- **前端6项修复** — 工具栏布局/设置弹窗/样式一致性
- **大纲生成路径修复** — `/api/ppt/chat` → `/api/chat` 端点修正
- **模板缩略图** — 17种模板全部生成缩略图预览，无需猜测效果

### v0.5（2026-05）

- **完整生成流程** — 大纲→模板→批量生成→导出PPTX全链路贯通
- **SVG转DrawingML** — Path D原生形状模式，导出PPTX完全可编辑
- **多AI提供商** — MiniMax / OpenAI / Anthropic / Gemini / Qwen / DeepSeek

---

## 获取API Key

| 提供商 | 地址 | 说明 |
|--------|------|------|
| MiniMax（推荐） | https://www.minimax.chat/ | 国内访问快，支持TTS |
| OpenAI | https://platform.openai.com/ | GPT-4o/GPT-4 |
| Anthropic | https://console.anthropic.com/ | Claude 3.5/3.7 |
| Google Gemini | https://aistudio.google.com/ | Gemini 2.0 |

---

## 许可证

MIT License — 可免费商用，欢迎 Star ⭐

---

## 开发者

[GitHub](https://github.com/junnylin8586-eng/PPT-SVGAGENT) | [提交Issue](https://github.com/junnylin8586-eng/PPT-SVGAGENT/issues)