/**
 * Generate template thumbnail PNGs using pptxgenjs
 * Run: node generate_thumbnails.js
 */
const PptxGenJS = require('pptxgenjs')
const fs = require('fs')
const path = require('path')

const TEMPLATES = [
  {
    id: 'government_blue',
    name: '重点项目汇报',
    slides: [
      { bg: '#003371', accent: '#00875A', layout: 'hero', title: '重大项目\n汇报', subtitle: '2024年度总结' },
      { bg: '#003371', accent: '#005691', layout: 'content', title: '目录', items: ['01 项目背景', '02 实施进展', '03 成果展示', '04 未来规划'] },
      { bg: '#ffffff', accent: '#003371', layout: 'content', title: '项目背景', body: '重大项目实施情况汇报' },
    ]
  },
  {
    id: 'government_red',
    name: '政府汇报',
    slides: [
      { bg: '#8B0000', accent: '#FF6347', layout: 'hero', title: '工作汇报', subtitle: '政策解读与落实' },
      { bg: '#F5F5F5', accent: '#8B0000', layout: 'content', title: '目录', items: ['01 工作总结', '02 政策解读', '03 实施计划'] },
      { bg: '#ffffff', accent: '#8B0000', layout: 'content', title: '工作总结', body: '年度工作完成情况' },
    ]
  },
  {
    id: 'anthropic',
    name: 'AI科技发布',
    slides: [
      { bg: '#0F172A', accent: '#10B981', layout: 'hero', title: 'AI Product\nLaunch', subtitle: 'Next Generation' },
      { bg: '#0F172A', accent: '#6366F1', layout: 'content', title: 'Overview', items: ['01 Core Features', '02 Architecture', '03 Benchmarks'] },
      { bg: '#1E293B', accent: '#10B981', layout: 'content', title: 'Performance', body: 'Industry-leading results' },
    ]
  },
  {
    id: 'ai_ops',
    name: '电信AI运营架构',
    slides: [
      { bg: '#003371', accent: '#00875A', layout: 'hero', title: 'AI Ops\nArchitecture', subtitle: 'Intelligent Operations' },
      { bg: '#EBF5FF', accent: '#003371', layout: 'content', title: 'System Overview', items: ['01 Data Layer', '02 AI Engine', '03 Application'] },
      { bg: '#ffffff', accent: '#003371', layout: 'content', title: 'Data Flow', body: 'End-to-end pipeline' },
    ]
  },
  {
    id: 'google_style',
    name: '年度工作汇报',
    slides: [
      { bg: '#ffffff', accent: '#4285F4', layout: 'hero', title: 'Annual\nReport', subtitle: '2024 Key Metrics' },
      { bg: '#F8F9FA', accent: '#4285F4', layout: 'content', title: 'Highlights', items: ['Revenue Growth', 'User Acquisition', 'Product Launch'] },
      { bg: '#ffffff', accent: '#34A853', layout: 'content', title: 'Metrics', body: 'Data-driven insights' },
    ]
  },
  {
    id: 'academic_defense',
    name: '学术答辩',
    slides: [
      { bg: '#1A365D', accent: '#E2E8F0', layout: 'hero', title: 'Thesis\nDefense', subtitle: 'Academic Presentation' },
      { bg: '#F7FAFC', accent: '#1A365D', layout: 'content', title: 'Outline', items: ['01 Research Background', '02 Methodology', '03 Results', '04 Conclusion'] },
      { bg: '#ffffff', accent: '#1A365D', layout: 'content', title: 'Background', body: 'Research significance and objectives' },
    ]
  },
  {
    id: 'medical_university',
    name: '医学学术',
    slides: [
      { bg: '#002855', accent: '#00A99D', layout: 'hero', title: 'Medical\nResearch', subtitle: 'Clinical Study Report' },
      { bg: '#F0F9FF', accent: '#002855', layout: 'content', title: 'Study Design', items: ['01 Objectives', '02 Methods', '03 Results'] },
      { bg: '#ffffff', accent: '#002855', layout: 'content', title: 'Results', body: 'Key findings and analysis' },
    ]
  },
  {
    id: 'pixel_retro',
    name: '复古极客',
    slides: [
      { bg: '#1a1a2e', accent: '#00FF41', layout: 'hero', title: '8-BIT\nTECH', subtitle: 'Retro Computing' },
      { bg: '#16213e', accent: '#00FF41', layout: 'content', title: 'Topics', items: ['>> Algorithms', '>> Systems', '>> Code Review'] },
      { bg: '#0f3460', accent: '#e94560', layout: 'content', title: 'DEMO', body: 'Live coding session' },
    ]
  },
  {
    id: 'psychology_attachment',
    name: '心理培训',
    slides: [
      { bg: '#E8F5E9', accent: '#2E7D32', layout: 'hero', title: 'Psychology\nWorkshop', subtitle: 'Professional Development' },
      { bg: '#F1F8E9', accent: '#558B2F', layout: 'content', title: 'Agenda', items: ['01 Case Study', '02 Techniques', '03 Practice'] },
      { bg: '#ffffff', accent: '#2E7D32', layout: 'content', title: 'Case Analysis', body: 'Client assessment methods' },
    ]
  },
  {
    id: 'china_telecom_template',
    name: '政企数字化方案',
    slides: [
      { bg: '#003087', accent: '#00A9E0', layout: 'hero', title: 'Digital\nTransformation', subtitle: 'Enterprise Solutions' },
      { bg: '#EBF3FB', accent: '#003087', layout: 'content', title: 'Strategy', items: ['01 Current State', '02 Roadmap', '03 Outcomes'] },
      { bg: '#ffffff', accent: '#003087', layout: 'content', title: 'Implementation', body: 'Phased deployment plan' },
    ]
  },
]

const W = 800, H = 450 // 16:9

function hexToRgb(hex) {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return { r, g, b }
}

function renderSlide(pptx, slideData, bg, accent, layout, title, subtitle, items, body) {
  const slide = pptx.addSlide()
  slide.background = { color: bg }

  if (layout === 'hero') {
    // Title block at top
    const titleColor = bg === '#ffffff' || bg === '#F8F9FA' || bg === '#F7FAFC' || bg === '#F0F9FF' || bg === '#F1F8E9' || bg === '#E8F5E9'
      ? accent : '#FFFFFF'

    // Large title
    slide.addText(title, {
      x: 0.5, y: 1.2, w: W / 150 - 1, h: 1.8,
      fontSize: title.includes('\n') ? 44 : 40,
      bold: true, color: titleColor,
      fontFace: 'Arial', align: 'left',
    })

    // Subtitle
    if (subtitle) {
      slide.addText(subtitle, {
        x: 0.5, y: 3.1, w: W / 150 - 1, h: 0.5,
        fontSize: 18, color: layout === 'hero' && bg !== '#ffffff' ? '#AACCEE' : '#888888',
        fontFace: 'Arial', align: 'left',
      })
    }

    // Accent line
    slide.addShape(pptx.ShapeType.rect, {
      x: 0.5, y: 0.6, w: 0.8, h: 0.06,
      fill: { color: accent },
    })
  } else {
    // Content page
    const textColor = bg === '#ffffff' || bg === '#F8F9FA' || bg === '#F7FAFC' || bg === '#F0F9FF' || bg === '#F1F8E9' || bg === '#E8F5E9'
      ? accent : '#FFFFFF'

    // Title
    slide.addText(title, {
      x: 0.5, y: 0.4, w: W / 150 - 1, h: 0.7,
      fontSize: 24, bold: true, color: textColor,
      fontFace: 'Arial', align: 'left',
    })

    // Divider
    slide.addShape(pptx.ShapeType.rect, {
      x: 0.5, y: 1.1, w: 1.5, h: 0.04,
      fill: { color: accent },
    })

    if (items) {
      // Bullet list
      const bulletText = items.map((item, i) => ({
        text: item,
        options: { bullet: false, breakLine: i < items.length - 1, color: bg === '#ffffff' || bg === '#F8F9FA' ? '#333333' : '#DDDDDD' }
      }))
      slide.addText(bulletText, {
        x: 0.5, y: 1.4, w: W / 150 - 1, h: 3.2,
        fontSize: 16, fontFace: 'Arial', color: bg === '#ffffff' || bg === '#F8F9FA' ? '#333333' : '#DDDDDD',
        lineSpaceMult: 1.8,
      })
    }

    if (body) {
      slide.addText(body, {
        x: 0.5, y: 1.4, w: W / 150 - 1, h: 2,
        fontSize: 16, fontFace: 'Arial',
        color: bg === '#ffffff' || bg === '#F8F9FA' ? '#555555' : '#CCCCCC',
      })
    }
  }

  return slide
}

const outDir = path.join(__dirname, 'public', 'template_thumbs')
fs.mkdirSync(outDir, { recursive: true })

TEMPLATES.forEach(tmpl => {
  const pptx = new PptxGenJS()
  pptx.layout = 'LAYOUT_16x9'
  pptx.defineLayout({ name: 'Custom', width: 13.333, height: 7.5 })
  pptx.layout = 'Custom'

  const bg = tmpl.slides[0].bg
  const accent = tmpl.slides[0].accent
  const s = tmpl.slides[0]

  renderSlide(pptx, s, bg, accent, s.layout, s.title, s.subtitle, s.items, s.body)

  const outPath = path.join(outDir, `${tmpl.id}.png`)
  pptx.write('buffer').then(buf => {
    fs.writeFileSync(outPath, buf)
    console.log(`[OK] ${tmpl.id}.png`)
  }).catch(err => {
    console.error(`[FAIL] ${tmpl.id}: ${err.message}`)
  })
})