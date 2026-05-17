/**
 * i18n - Lightweight internationalization utility
 * v0.6: Foundation layer for future multi-language support
 * 
 * Usage:
 *   import { t, setLocale, getLocale } from '@/i18n'
 *   t('common.create')  // → "创建新项目" or "Create Project"
 */

const locales: Record<string, Record<string, string>> = {
  zh: {
    // Common
    'common.create': '创建新项目',
    'common.cancel': '取消',
    'common.save': '保存',
    'common.delete': '删除',
    'common.confirm': '确认',
    'common.close': '关闭',
    'common.loading': '加载中...',
    'common.export': '导出',
    'common.download': '下载',
    'common.search': '搜索',
    'common.reset': '重置',
    'common.ok': '确定',

    // Home
    'home.title': 'AI 智能 PPT 生成',
    'home.subtitle': '输入想法，AI 自动生成专业演示文稿 · 支持矢量可编辑导出',
    'home.createBtn': '创建新项目',
    'home.recentProjects': '最近项目',
    'home.aiGenerated': 'AI 生成',

    // Project creation
    'project.stepName': '第 1 步：项目信息',
    'project.projectName': '项目名称',
    'project.namePlaceholder': '输入项目名称',
    'project.themeDesc': '主题描述',
    'project.descPlaceholder': '描述你想做的 PPT 主题、目的和关键内容...',
    'project.chatMode': '对话模式',
    'project.autoMode': '自动模式',
    'project.generateOutline': 'AI 生成大纲',
    'project.nextTemplate': '下一步：选模板',
    'project.fillAll': '请填写完整信息',
    'project.fillName': '请输入项目名称',
    'project.fillTheme': '请输入主题描述或生成大纲',

    // Generation
    'gen.generating': '生成中...',
    'gen.completed': '已完成',
    'gen.failed': '失败',
    'gen.pending': '待生成',
    'gen.skipped': '已跳过',
    'gen.regenerate': '重新生成',
    'gen.startGen': '开始生成',
    'gen.retrying': '重试中...',

    // Export
    'export.title': '导出 PPTX',
    'export.selectPages': '选择要导出的页面',
    'export.collecting': '正在收集 SVG 文件...',
    'export.converting': '正在转换 {count} 页...',
    'export.success': '导出成功！',
    'export.successMsg': '{count} 页已转换为 PPTX',
    'export.noPages': '没有可导出的页面',
    'export.download': '下载文件',

    // Settings
    'settings.title': 'AI 设置',
    'settings.apiConfig': 'API 配置',
    'settings.modelSettings': '模型设置',
    'settings.genParams': '生成参数',
    'settings.testConnection': '测试连接',
    'settings.saveSettings': '保存设置',
    'settings.resetDefault': '重置为默认',
    'settings.resetConfirm': '确定要重置所有设置为 .env 默认值吗？所有自定义配置将被清除。',

    // Status
    'status.COMPLETED': '已完成',
    'status.GENERATING': '生成中',
    'status.DRAFT': '草稿',
    'status.GENERATED': '已生成',
    'status.FAILED': '失败',
    'status.PENDING': '待生成',
  },

  en: {
    'common.create': 'Create Project',
    'common.cancel': 'Cancel',
    'common.save': 'Save',
    'common.delete': 'Delete',
    'common.confirm': 'Confirm',
    'common.close': 'Close',
    'common.loading': 'Loading...',
    'common.export': 'Export',
    'common.download': 'Download',
    'common.search': 'Search',
    'common.reset': 'Reset',
    'common.ok': 'OK',

    'home.title': 'AI PPT Generator',
    'home.subtitle': 'Describe your idea, AI generates professional presentations · Vector editable export',
    'home.createBtn': 'Create Project',
    'home.recentProjects': 'Recent Projects',
    'home.aiGenerated': 'AI Generated',

    'project.stepName': 'Step 1: Project Info',
    'project.projectName': 'Project Name',
    'project.namePlaceholder': 'Enter project name',
    'project.themeDesc': 'Theme Description',
    'project.descPlaceholder': 'Describe your PPT theme, purpose, and key content...',
    'project.chatMode': 'Chat Mode',
    'project.autoMode': 'Auto Mode',
    'project.generateOutline': 'Generate Outline',
    'project.nextTemplate': 'Next: Select Template',
    'project.fillAll': 'Please fill in all fields',
    'project.fillName': 'Please enter project name',
    'project.fillTheme': 'Please enter theme description or generate outline',

    'gen.generating': 'Generating...',
    'gen.completed': 'Completed',
    'gen.failed': 'Failed',
    'gen.pending': 'Pending',
    'gen.skipped': 'Skipped',
    'gen.regenerate': 'Regenerate',
    'gen.startGen': 'Start Generation',
    'gen.retrying': 'Retrying...',

    'export.title': 'Export PPTX',
    'export.selectPages': 'Select pages to export',
    'export.collecting': 'Collecting SVG files...',
    'export.converting': 'Converting {count} pages...',
    'export.success': 'Export successful!',
    'export.successMsg': '{count} pages converted to PPTX',
    'export.noPages': 'No pages to export',
    'export.download': 'Download File',

    'settings.title': 'AI Settings',
    'settings.apiConfig': 'API Config',
    'settings.modelSettings': 'Model Settings',
    'settings.genParams': 'Generation Params',
    'settings.testConnection': 'Test Connection',
    'settings.saveSettings': 'Save Settings',
    'settings.resetDefault': 'Reset to Default',
    'settings.resetConfirm': 'Reset all settings to .env defaults? All custom config will be cleared.',

    'status.COMPLETED': 'Completed',
    'status.GENERATING': 'Generating',
    'status.DRAFT': 'Draft',
    'status.GENERATED': 'Generated',
    'status.FAILED': 'Failed',
    'status.PENDING': 'Pending',
  },
}

let currentLocale = 'zh'

export function setLocale(locale: string) {
  if (locales[locale]) {
    currentLocale = locale
  }
}

export function getLocale(): string {
  return currentLocale
}

/**
 * Translate a key to the current locale.
 * Supports simple variable substitution: t('export.converting', { count: 16 })
 */
export function t(key: string, vars?: Record<string, string | number>): string {
  const dict = locales[currentLocale]
  let text = dict?.[key] || locales['zh']?.[key] || key
  if (vars) {
    for (const [k, v] of Object.entries(vars)) {
      text = text.replace(`{${k}}`, String(v))
    }
  }
  return text
}

export default { t, setLocale, getLocale, locales }
