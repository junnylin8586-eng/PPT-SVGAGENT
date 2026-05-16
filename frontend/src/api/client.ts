/**
 * PPT Agent API Client - Phase 3
 */
const API_BASE = '/api/ppt'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ message: res.statusText }))
    throw new Error(err.error || err.message || `HTTP ${res.status}`)
  }
  return res.json()
}

// ============ Types ============

export interface Project {
  project_id: string
  id?: string
  name: string
  creation_type: 'idea' | 'outline' | 'description'
  idea_prompt?: string
  outline_text?: string
  description_text?: string
  extra_requirements?: string
  template_path?: string
  generation_mode: 'guide' | 'auto'
  image_aspect_ratio: '16:9' | '4:3'
  primary_color?: string
  font_family?: string
  layout_style?: string
  status: string
  created_at: string
  updated_at: string
  is_deleted: boolean
  pages?: Page[]
}

export interface Page {
  page_id: string
  project_id?: string
  order_index: number
  part?: string
  outline_content?: string
  description_content?: string
  svg_path?: string
  status: string
  created_at?: string
}

export interface LayoutTemplate {
  layout_id: string
  name: string
  category: string
  summary: string
  keywords: string[]
}

export interface ThemeOutline {
  page: number
  part: string
  outline_content: string
  page_instruction?: string
  key_points?: string[]
  layout_hint?: string
}

type UnsubscribeFn = () => void

class Observable<T> {
  constructor(
    subscribe: (observer: {
      next: (value: T) => void
      error: (err: Error) => void
      complete: () => void
    }) => { unsubscribe: () => void }
  ) {
    this._subscribe = subscribe
  }

  subscribe(observer: {
    next: (value: T) => void
    error?: (err: Error) => void
    complete?: () => void
  }): { unsubscribe: () => void } {
    const { unsubscribe } = this._subscribe({
      next: observer.next,
      error: observer.error || (() => {}),
      complete: observer.complete || (() => {}),
    })
    return { unsubscribe }
  }

  private _subscribe: (observer: {
    next: (value: T) => void
    error: (err: Error) => void
    complete: () => void
  }) => { unsubscribe: () => void }
}

// ============ API ============

export const api = {
  // Projects
  getProjects(): Promise<any> {
    return request('/projects')
  },

  createProject(payload: Partial<Project>): Promise<any> {
    return request('/projects', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  getProject(id: string): Promise<any> {
    return request(`/projects/${id}`)
  },

  updateProject(id: string, payload: Partial<Project>): Promise<any> {
    return request(`/projects/${id}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    })
  },

  deleteProject(id: string): Promise<any> {
    return request(`/projects/${id}`, { method: 'DELETE' })
  },

  // Pages
  getPages(projectId: string): Promise<any> {
    return request(`/projects/${projectId}/pages`)
  },

  createPages(projectId: string, outlines: any[]): Promise<any> {
    return request(`/projects/${projectId}/pages`, {
      method: 'POST',
      body: JSON.stringify({ outlines }),
    })
  },

  updatePage(projectId: string, pageId: string, payload: Partial<Page>): Promise<any> {
    return request(`/projects/${projectId}/pages/${pageId}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    })
  },

  getPageSvg(projectId: string, pageId: string): Promise<any> {
    return request(`/projects/${projectId}/pages/${pageId}/svg`)
  },

  // Generate
  generate(projectId: string, template?: string): Promise<any> {
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 600_000) // 10 min timeout
    return request(`/projects/${projectId}/generate`, {
      method: 'POST',
      body: JSON.stringify({ template: template || 'government_blue' }),
      signal: controller.signal,
    }).finally(() => clearTimeout(timeoutId))
  },

  // Generate single page
  generatePage(projectId: string, pageId: string, template?: string): Promise<any> {
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 300_000) // 5 min timeout
    return request(`/projects/${projectId}/pages/${pageId}/generate`, {
      method: 'POST',
      body: JSON.stringify({ template: template || 'government_blue' }),
      signal: controller.signal,
    }).finally(() => clearTimeout(timeoutId))
  },

  // Export
  exportPptx(projectId: string, pageIds?: string[]): Promise<any> {
    return request(`/projects/${projectId}/export`, {
      method: 'POST',
      body: JSON.stringify({ page_ids: pageIds }),
    })
  },

  // Templates
  getLayouts(): Promise<any> {
    return request('/templates/layouts')
  },

  // Theme Analysis (AI outline generation, SSE streaming)
  analyzeTheme(themeText: string): Observable<ThemeOutline> {
    return new Observable((subscriber) => {
      const controller = new AbortController()
      let buffer = ''

      fetch(`${API_BASE}/analyze-theme`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ theme_text: themeText }),
        signal: controller.signal,
      }).then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const reader = res.body?.getReader()
        const decoder = new TextDecoder()

        const processLines = (text: string) => {
          const lines = text.split('\n')
          buffer = lines.pop() || ''
          for (const line of lines) {
            if (!line.startsWith('data: ')) continue
            try {
              const raw = JSON.parse(line.slice(6))

              // Handle terminal events first
              if (raw.type === 'complete') {
                subscriber.complete()
                return
              }
              if (raw.type === 'error') {
                subscriber.error(new Error(raw.message || 'AI analysis failed'))
                return
              }

              // ONLY process outline events — ignore started/analyzing progress events
              if (raw.type !== 'outline') continue

              const data = raw.data || raw
              const event: ThemeOutline = {
                page: data.page ?? data.page_index ?? 0,
                part: data.part || data.section || '',
                outline_content: data.outline_content || data.content || data.text || '',
                page_instruction: data.page_instruction || data.instruction || '',
                key_points: data.key_points ?? [],
                layout_hint: data.layout_hint || '两栏',
              }
              subscriber.next(event)
            } catch {}
          }
        }

        const read = () => {
          reader?.read().then(({ done, value }) => {
            if (done) {
              if (buffer) processLines(buffer)
              subscriber.complete()
              return
            }
            buffer += decoder.decode(value, { stream: true })
            processLines(buffer)
            if (!controller.signal.aborted) read()
          })
        }
        read()
      }).catch((err) => {
        if (err.name !== 'AbortError') subscriber.error(err)
      })

      return { unsubscribe: () => controller.abort() }
    })
  },

  // Multi-turn chat to generate PPT outline (SSE streaming)
  generateOutline(messages: Array<{ role: string; content: string }>, isFinal = false): Observable<any> {
    return new Observable((subscriber) => {
      const controller = new AbortController()
      let buffer = ''

      fetch(`${API_BASE}/chat/generate-outline`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages, final: isFinal }),
        signal: controller.signal,
      }).then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const reader = res.body?.getReader()
        const decoder = new TextDecoder()

        const processLines = (text: string) => {
          const lines = text.split('\n')
          buffer = lines.pop() || ''
          for (const line of lines) {
            if (!line.startsWith('data: ')) continue
            try {
              const raw = JSON.parse(line.slice(6))

              if (raw.type === 'complete') {
                subscriber.next({ type: 'complete', outlines: raw.outlines || [], total: raw.total || 0 })
                subscriber.complete()
                return
              }
              if (raw.type === 'error') {
                subscriber.error(new Error(raw.message || 'AI generation failed'))
                return
              }
              if (raw.type === 'outline') {
                const data = raw.data || raw
                subscriber.next({
                  type: 'outline',
                  index: raw.index ?? 0,
                  data: {
                    page: data.page ?? raw.index ?? 0,
                    part: data.part || data.section || '',
                    outline_content: data.outline_content || data.content || data.text || '',
                    page_instruction: data.page_instruction || data.instruction || '',
                    key_points: data.key_points ?? [],
                    layout_hint: data.layout_hint || '两栏',
                  },
                })
              }
            } catch {}
          }
        }

        const read = () => {
          reader?.read().then(({ done, value }) => {
            if (done) {
              if (buffer) processLines(buffer)
              subscriber.complete()
              return
            }
            buffer += decoder.decode(value, { stream: true })
            processLines(buffer)
            if (!controller.signal.aborted) read()
          })
        }
        read()
      }).catch((err) => {
        if (err.name !== 'AbortError') subscriber.error(err)
      })

      return { unsubscribe: () => controller.abort() }
    })
  },

  // Files (raw)
  getFileUrl(filename: string): string {
    return `${API_BASE}/files/${filename}`
  },
}
