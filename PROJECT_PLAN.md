# PPT Agent 项目执行计划

> 文档版本：v1.0
> 创建日期：2026-05-09
> 负责人：PPT Agent 开发组
> 状态：规划完成，待启动

---

## 一、项目概述

### 1.1 项目定位

**PPT Agent** — 基于 AI 的原生可编辑 PPT 生成与编辑工具。

- 通过自然语言输入，自动生成完整 PPT
- 所有元素（背景/图形/文字）均可独立选中、编辑
- 支持模板复用、批量编辑、多次修改
- 支持多种在线模型（MiniMax / OpenAI / Gemini 等）

### 1.2 核心价值

| 特性 | 说明 |
|------|------|
| **原生可编辑** | 导出的每个元素都是 DrawingML 形状，可点击修改 |
| **矢量优先** | SVG → DrawingML 精确映射，禁止光栅化 |
| **模板驱动** | 17 套内置模板 + 支持上传 PPTX 生成自定义模板 |
| **三轨生成** | 全自动 / 引导式 / 编辑式，灵活适配不同场景 |
| **质量门控** | 每页生成后立即检查，有错误不过关，保证导出稳定性 |

### 1.3 技术选型

| 模块 | 技术 |
|------|------|
| **前端框架** | React 18 + TypeScript + Vite |
| **样式方案** | Tailwind CSS + CSS 变量（蓝色商务主题） |
| **状态管理** | Zustand |
| **矢量渲染** | 原生 SVG / Fabric.js |
| **后端框架** | Flask + SQLAlchemy（沿用 banana-slides） |
| **PPT 引擎** | python-pptx + ppt-master SVG→DrawingML |
| **AI 通信** | WebSocket（流式生成进度）+ REST API |
| **多模型路由** | MiniMax-M2.7（测试）/ 用户 key（正式） |

---

## 二、源项目资产盘点（banana-slides）

### 2.1 可直接复用

| 资产 | 路径 | 复用说明 |
|------|------|---------|
| Flask 后端骨架 | `backend/app.py` | 应用工厂 + CORS + 路由注册 |
| SQLAlchemy 模型 | `backend/models/` | Project / Page / Task 模型 |
| 数据库实例 | `backend/instance/database.db` | SQLite WAL 模式配置 |
| 文件服务 | `backend/services/file_service.py` | 项目文件 / 导出文件管理 |
| AI 服务管理 | `backend/services/ai_service_manager.py` | MiniMax API 调用封装 |
| 任务管理器 | `backend/services/task_manager.py` | 异步任务队列 + 轮询机制 |
| 环境配置 | `.env.example` | API Key 等配置项参考 |

### 2.2 可参考（需适配）

| 资产 | 路径 | 参考点 |
|------|------|--------|
| 导出服务 | `backend/services/export_service.py` | 三路导出架构（Path A/B/C），已废弃但架构思路可参考 |
| 样式提取 | `backend/services/style_extractor.py` | 颜色/字体提取逻辑 |
| 模板分析 | `backend/services/template_analyzer.py` | PPTX 模板解析思路 |
| 前端工具函数 | `frontend/src/utils/` | 工具函数（normalizeErrorMessage / debounce / i18n）|
| Toast/Modal 组件 | `frontend/src/components/shared/Toast.tsx` 等 | UI 基础组件 |
| AI 提炼输入框 | `frontend/src/components/shared/AiRefineInput.tsx` | AI 辅助输入交互 |
| 国际化方案 | `frontend/src/locales/` | i18n 框架 |

### 2.3 不再使用（废弃）

| 资产 | 原因 |
|------|------|
| `backend/services/image_editability/` | AI 图片生成模块，文字乱码问题无解 |
| `frontend/src/components/preview/SlideCard.tsx` | 依赖 AI 图片 |
| `frontend/src/components/preview/SlidePreviewCanvas.tsx` | 依赖 AI 图片叠加 |
| `frontend/src/components/shared/MaterialGeneratorModal.tsx` | AI 素材生成（图片） |
| `frontend/src/components/shared/MaterialSelector.tsx` | 素材选择器（图片素材） |
| `backend/controllers/export_controller.py` | 旧导出控制器（三路导出）|
| `backend/services/pdf_service.py` | PDF 解析（作为备选保留）|

---

## 三、PPT Master 引擎集成

### 3.1 引擎位置

```
上游仓库：d:\temp\ppt-master-github\
集成路径：D:\AI\ppt-agent\backend\ppt_master_engine\
          指向 d:\temp\ppt-master-github\skills\ppt-master\
```

### 3.2 核心模块映射

| 功能 | 模块路径 | 用途 |
|------|---------|------|
| SVG 质量检查 | `scripts/svg_quality_checker.py` | 每页生成后门控检查 |
| 错误修复指引 | `scripts/error_helper.py` | 人性化错误提示 |
| SVG 后处理 | `scripts/finalize_svg.py` | 图标嵌入/图片对齐/圆角转Path |
| **SVG→DrawingML** | `scripts/svg_to_pptx/` | **核心**：矢量转 PPTX |
| 项目管理 | `scripts/project_manager.py` | 模板管理 / 格式验证 |
| 图片生成 | `scripts/image_gen.py` | AI SVG 图形生成（替代原有图片生成）|
| 动画/旁白 | `scripts/pptx_animations.py` | v2.6.0 新增能力 |
| 模板库 | `templates/layouts/` | **17 套内置模板** |

### 3.3 模板库（17 套）

| 模板 | 主色 | 适用场景 |
|------|------|---------|
| `government_blue` | #0050B3 | 政务蓝，国企汇报 |
| `government_red` | #8B0000 | 政务红，党政活动 |
| `google_style` | #4285F4 | 科技蓝，年度汇报 |
| `anthropic` | #D97757 | AI 技术分享 |
| `academic_defense` | #003366 | 学术答辩 |
| `ai_ops` | #C00000 | 电信 AI 运维 |
| `china_telecom_template` | #C00000 | 中国电信方案 |
| `中国电建_常规` | #00418D | 电建常规汇报 |
| `中国电建_现代` | #00418D | 电建现代风格 |
| `中汽研_商务` | #003366 | 中汽研商务 |
| `中汽研_常规` | #004098 | 中汽研常规 |
| `中汽研_现代` | #001529 | 中汽研现代 |
| `招商银行` | #C8152D | 招行品牌 |
| `medical_university` | #0066B3 | 医学院风格 |
| `psychology_attachment` | #2E5C8E | 心理培训 |
| `pixel_retro` | #0D1117 | 像素复古风 |
| `重庆大学` | #006BB7 | 学术模板 |

---

## 四、产品设计规范

### 4.1 设计系统

#### 颜色

```css
:root {
  /* 主色 */
  --color-primary:      #003371;   /* 藏蓝 */
  --color-primary-light:#005691;   /* 蓝 */
  --color-primary-dark: #002050;   /* 深藏蓝 */

  /* 强调色 */
  --color-accent-green: #00875A;   /* 成功/确认 */
  --color-accent-orange:#E07B39;   /* 警告/重点 */

  /* 背景 */
  --color-bg:          #FFFFFF;   /* 主背景 */
  --color-surface:     #F4F7FA;   /* 卡片/面板背景 */
  --color-border:     #E5E7EB;   /* 边框 */

  /* 文字 */
  --color-text-primary:  #333333;  /* 主文字 */
  --color-text-secondary:#666666;  /* 次要文字 */
  --color-text-muted:    #999999;  /* 辅助文字 */
  --color-text-inverse:  #FFFFFF;  /* 反色文字 */

  /* 状态 */
  --color-danger:  #DC2626;
  --color-success: #16A34A;
  --color-warning: #D97706;
}
```

#### 字体

| 用途 | 字体 |
|------|------|
| 中文正文 | Noto Sans SC |
| 英文正文 | Inter |
| 代码/等宽 | JetBrains Mono |

#### 圆角

| 元素 | 圆角 |
|------|------|
| 按钮 | 6px |
| 卡片 | 8px |
| 模态框 | 12px |
| 缩略图 | 4px |

#### 阴影

```css
--shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
--shadow-md: 0 2px 8px rgba(0,0,0,0.06);
--shadow-lg: 0 4px 16px rgba(0,0,0,0.10);
```

### 4.2 页面结构

#### 首页（项目列表）

```
┌─────────────────────────────────────────────────────────────┐
│  [Logo] PPT Agent              [模板库] [历史] [⚙ 设置]   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   [+ 新建项目]                                              │
│                                                             │
│   最近项目                                                  │
│   ┌────────────┐ ┌────────────┐ ┌────────────┐            │
│   │  缩略图    │ │  缩略图    │ │  缩略图    │            │
│   │  项目名    │ │  项目名    │ │  项目名    │            │
│   │  日期/页数 │ │  日期/页数 │ │  日期/页数 │            │
│   └────────────┘ └────────────┘ └────────────┘            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 工作台

```
┌─────────────────────────────────────────────────────────────┐
│  ← 返回   项目名称              [保存] [预览] [导出]       │
├────────────┬──────────────────────────────┬─────────────────┤
│            │                              │                 │
│  左侧面板  │       主工作区               │  右侧属性面板   │
│  (240px)  │       (弹性)                 │  (280px)       │
│            │                              │                 │
│  ▼ 大纲   │  ┌──┐ ┌──┐ ┌──┐ ┌──┐     │  选中元素属性   │
│    第1页  │  │01│ │02│ │03│ │04│ ... │  ─────────────  │
│    第2页  │  └──┘ └──┘ └──┘ └──┘     │  填充  边框    │
│    第3页  │                              │  字体  颜色    │
│            │  ┌──────────────────────┐  │  位置  尺寸    │
│  ▼ 素材   │  │                      │  │                 │
│    装饰   │  │    当前页大预览        │  │  ─────────────  │
│    图标   │  │   （SVG矢量渲染）      │  │  [应用到多页]  │
│    背景   │  │                      │  │                 │
│            │  └──────────────────────┘  │                 │
│  ▼ 历史   │                              │                 │
│    v3 10:30│  [ + 添加页面 ]            │                 │
│    v2 09:15│                            │                 │
└────────────┴──────────────────────────────┴─────────────────┘
┌─────────────────────────────────────────────────────────────┐
│  生成模式: [全自动] [引导式] [编辑式]   [模板▼] [模型▼]  │
│  [生成PPT ▶]                                  [导出PPTX ↓] │
└─────────────────────────────────────────────────────────────┘
```

### 4.3 模板选择器

```
┌─────────────────────────────────────────────────────────────┐
│                    选择模板                                   │
├─────────────────────────────────────────────────────────────┤
│  [🔍 搜索模板...]                                           │
│  分类：[全部] [国企政务] [科技] [学术] [品牌] [杂志风]       │
│                                                             │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐             │
│  │  预览图    │ │  预览图    │ │  预览图    │             │
│  │government_ │ │google_style│ │ 招商银行   │             │
│  │  blue      │ │            │ │            │             │
│  │ #0050B3   │ │ #4285F4   │ │ #C8152D   │             │
│  └────────────┘ └────────────┘ └────────────┘             │
│                                                             │
│                              [取消]          [确认选择]      │
└─────────────────────────────────────────────────────────────┘
```

---

## 五、三轨生成流程

### 5.1 轨道 A — 全自动（无人工介入）

```
用户输入主题
    ↓
系统理解主题 → 生成大纲 → 选择模板 → 逐页生成 SVG
    ↓
质量门控（每页检查）
    ↓
finalize_svg → Path D 导出
    ↓
交付可编辑 PPTX
```

### 5.2 轨道 B — 引导式（用户确认大纲 + 风格）

```
用户输入主题
    ↓
系统生成大纲 → 呈现给用户 [确认/修改]
    ↓
系统推荐模板 + 八大确认（画布/页数/受众/风格/配色/图标/字体/图片）
    ↓
用户确认
    ↓
逐页生成 SVG（串行）
    ↓
质量门控 → Path D 导出
    ↓
交付
```

### 5.3 轨道 C — 编辑式（针对已有 PPT）

```
打开已有 PPT（或从历史选择）
    ↓
用户选择页面 + 输入编辑指令（自然语言）
    ↓
影响分析（哪些页需要重生成）
    ↓
重生成受影响页面
    ↓
质量门控 → 重新导出
    ↓
交付（可对比历史版本）
```

---

## 六、后端接口设计

### 6.1 新接口（`/api/ppt/*`）

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/ppt/projects` | 新建项目 |
| `GET` | `/api/ppt/projects` | 项目列表 |
| `GET` | `/api/ppt/projects/{id}` | 项目详情 |
| `PUT` | `/api/ppt/projects/{id}` | 更新项目 |
| `DELETE` | `/api/ppt/projects/{id}` | 删除项目 |
| `POST` | `/api/ppt/projects/{id}/pages` | 添加页面 |
| `PUT` | `/api/ppt/projects/{id}/pages/{page_id}` | 更新页面大纲/描述 |
| `DELETE` | `/api/ppt/projects/{id}/pages/{page_id}` | 删除页面 |
| `POST` | `/api/ppt/projects/{id}/generate` | **触发生成**（WebSocket 流式）|
| `GET` | `/api/ppt/projects/{id}/pages/{page_id}/svg` | 获取 SVG |
| `PUT` | `/api/ppt/projects/{id}/pages/{page_id}/elements` | 更新页面元素 |
| `POST` | `/api/ppt/projects/{id}/export` | 导出 PPTX |
| `POST` | `/api/ppt/templates/upload` | 上传自定义模板 |
| `GET` | `/api/ppt/templates` | 模板列表 |
| `GET` | `/api/ppt/templates/layouts` | 17 套内置模板 |

### 6.2 生成 WebSocket 事件

```typescript
// 客户端 → 服务端
{ type: 'start', payload: { project_id, page_ids?, mode, model } }

// 服务端 → 客户端
{ type: 'progress', payload: { page_id: 'p1', status: 'generating', message: '正在生成第3页...' } }
{ type: 'progress', payload: { page_id: 'p1', status: 'quality_check', message: '质量检查中...' } }
{ type: 'page_done', payload: { page_id: 'p1', svg_path: '/files/xxx.svg' } }
{ type: 'error', payload: { page_id: 'p2', error: 'SVG contains forbidden <style> element' } }
{ type: 'complete', payload: { export_url: '/files/xxx.pptx' } }
```

---

## 七、实施计划

### Phase 1：后端框架搭建
**时间**：1-2 天
**内容**：
- [ ] 创建 `D:\AI\ppt-agent\` 项目目录
- [ ] 引入 banana-slides 后端骨架（app.py / models / services）
- [ ] 建立 `backend/ppt_master_engine/` 链接到 ppt-master
- [ ] 改造数据库模型（Project / Page 支持新字段）
- [ ] 实现 `/api/ppt/*` REST 接口
- [ ] 实现 WebSocket 生成流
- [ ] 验证 ppt-master 引擎可在后端环境运行

### Phase 2：前端项目框架
**时间**：1 天
**内容**：
- [ ] 初始化 React + TypeScript + Vite 项目
- [ ] 配置 Tailwind CSS + 设计系统变量
- [ ] 基础布局组件（Header / Sidebar / MainContent）
- [ ] 路由配置（Home / Workspace / TemplateGallery）
- [ ] Zustand 状态管理框架
- [ ] API 客户端封装

### Phase 3：首页（项目列表）
**时间**：1 天
**内容**：
- [ ] 项目卡片组件
- [ ] 新建项目弹窗
- [ ] 项目列表 API 对接
- [ ] 模板库入口

### Phase 4：模板选择器
**时间**：1 天
**内容**：
- [ ] 模板卡片组件（缩略图 + 标签）
- [ ] 分类筛选
- [ ] 搜索功能
- [ ] 模板预览弹窗
- [ ] 模板上传 API（create-template 工作流）

### Phase 5：工作台（核心）
**时间**：2-3 天
**内容**：
- [ ] 页面缩略图画布（SVG 渲染）
- [ ] 左侧大纲面板（拖拽排序）
- [ ] 右侧属性面板（SVG 元素属性编辑）
- [ ] 素材库面板（装饰/图标/背景）
- [ ] 历史版本面板
- [ ] 页面 CRUD（添加/删除/复制/移动）

### Phase 6：生成流程
**时间**：1-2 天
**内容**：
- [ ] 底部工具栏（三轨切换 / 模型选择）
- [ ] WebSocket 流式生成（实时进度）
- [ ] 错误展示 + 修复指引
- [ ] 生成历史记录

### Phase 7：导出 + 动画旁白
**时间**：1 天
**内容**：
- [ ] Path D 导出（svg_quality_checker → finalize_svg → drawingml_converter → pptx_builder）
- [ ] 导出进度
- [ ] 可选：pptx_animations（页间转场 + 元素入场动画）
- [ ] 可选：pptx_narration（语音旁白 + 音色复刻）

### Phase 8：联调 + 优化
**时间**：1-2 天
**内容**：
- [ ] 前后端全流程联调
- [ ] spec_lock 每页重读验证
- [ ] 长 PPT（20+ 页）压力测试
- [ ] 用户 key 输入 + 多模型路由

---

## 八、里程碑

| 里程碑 | 完成标准 |
|--------|---------|
| **M1 后端闭环** | 输入主题 → 后端生成 SVG → 导出 PPTX（无前端）|
| **M2 前端基本盘** | 首页 + 模板选择 + 工作台缩略图（静态）|
| **M3 生成闭环** | 前端触发生成 → WebSocket 进度 → PPTX 交付 |
| **M4 完整三轨** | 全自动/引导式/编辑式全部可用 |
| **M5 模板系统** | 17 套内置 + 自定义模板上传 |
| **M6 v2.6.0 能力** | 动画 + 旁白（可选功能）|

---

## 九、风险与对策

| 风险 | 影响 | 对策 |
|------|------|------|
| SVG 生成质量不稳定 | 导出后格式错误 | svg_quality_checker 每页门控 + error_helper 修复指引 |
| 长 PPT 上下文漂移 | 颜色/字体逐页偏移 | spec_lock 每页重读机制 |
| AI 理解用户意图偏差 | 生成内容不符合预期 | 引导式轨道 B 先确认大纲 |
| 用户 key 安全存储 | API Key 泄露 | 仅存入会话环境变量，不写盘 |
| PPT 文字乱码 | AI 图片含乱码文字 | 已废弃 AI 图片，文字全走 SVG `<text>` 元素 |

---

## 十、文件结构

```
D:\AI\ppt-agent\
├── backend/
│   ├── app.py                    # Flask 应用入口
│   ├── config.py                 # 配置
│   ├── models/                   # SQLAlchemy 模型（复用 banana）
│   │   ├── project.py
│   │   ├── page.py
│   │   └── ...
│   ├── controllers/
│   │   └── ppt_controller.py     # 新：/api/ppt/* 接口
│   ├── services/
│   │   ├── ai_service_manager.py # 复用 banana（扩展多模型）
│   │   ├── file_service.py       # 复用 banana
│   │   ├── task_manager.py       # 复用 banana（改造流式）
│   │   ├── svg_export_service.py  # 新：Path D 导出
│   │   └── svg_generation_service.py  # 新：SVG 生成编排
│   ├── ppt_master_engine/        # 链接 → d:\temp\ppt-master-github\skills\ppt-master\
│   └── instance/
│       └── database.db
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── layout/          # Header / Sidebar / MainContent
│   │   │   ├── home/             # ProjectCard / NewProjectModal
│   │   │   ├── workspace/        # SlideCanvas / ElementPanel / PropertyPanel
│   │   │   ├── template/         # TemplateCard / TemplateGallery
│   │   │   └── shared/           # Button / Modal / Toast 等基础组件
│   │   ├── pages/
│   │   │   ├── Home.tsx
│   │   │   ├── Workspace.tsx
│   │   │   └── TemplateGallery.tsx
│   │   ├── store/               # Zustand store
│   │   ├── api/                 # API 客户端
│   │   ├── hooks/               # 自定义 hooks
│   │   └── styles/              # CSS 变量 / Tailwind 配置
│   ├── index.html
│   └── vite.config.ts
├── PROJECT_PLAN.md              # 本文档
└── README.md
```
