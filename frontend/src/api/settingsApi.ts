/**
 * Settings API - 前端调用封装
 * 后端接口：GET/PUT /api/settings，POST /api/settings/check
 */
const SETTINGS_API = '/api/settings'

interface SettingsDTO {
  id: number
  ai_provider_format?: string
  api_base_url?: string
  api_key_length: number
  minimax_api_key_length: number
  minimax_api_base?: string
  text_model?: string
  image_model?: string
  image_resolution?: string
  image_aspect_ratio?: string
  output_language?: string
  enable_text_reasoning: boolean
  text_thinking_budget: number
  enable_image_reasoning: boolean
  image_thinking_budget: number
  description_generation_mode?: string
  description_extra_fields?: string[]
  image_prompt_extra_fields?: string[]
  text_model_source?: string
  image_model_source?: string
  text_api_key_length: number
  text_api_base_url?: string
  image_api_key_length: number
  image_api_base_url?: string
  image_caption_api_key_length: number
  image_caption_api_base_url?: string
  created_at?: string
  updated_at?: string
}

export interface UpdateSettingsPayload {
  ai_provider_format?: string
  api_base_url?: string
  api_key?: string
  minimax_api_key?: string
  minimax_api_base?: string
  text_model?: string
  image_model?: string
  text_model_source?: string
  image_model_source?: string
  text_api_key?: string
  text_api_base_url?: string
  image_api_key?: string
  image_api_base_url?: string
  image_caption_api_key?: string
  image_caption_api_base_url?: string
  image_resolution?: string
  image_aspect_ratio?: string
  output_language?: string
  enable_text_reasoning?: boolean
  text_thinking_budget?: number
  enable_image_reasoning?: boolean
  image_thinking_budget?: number
  description_generation_mode?: string
  description_extra_fields?: string[]
  image_prompt_extra_fields?: string[]
}

export interface CheckConnectionPayload {
  api_key: string
  api_base_url?: string
  provider: string
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(path)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ message: res.statusText }))
    throw new Error(err.error || err.message || `HTTP ${res.status}`)
  }
  return res.json()
}

async function put<T>(path: string, data: unknown): Promise<T> {
  const res = await fetch(path, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ message: res.statusText }))
    throw new Error(err.error || err.message || `HTTP ${res.status}`)
  }
  return res.json()
}

async function post<T>(path: string, data: unknown): Promise<T> {
  const res = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ message: res.statusText }))
    throw new Error(err.error || err.message || `HTTP ${res.status}`)
  }
  return res.json()
}

export const settingsApi = {
  /** 获取当前设置 */
  getSettings(): Promise<{ success: true; data: SettingsDTO }> {
    return get(SETTINGS_API)
  },

  /** 更新设置 */
  updateSettings(payload: UpdateSettingsPayload): Promise<{ success: true; data: SettingsDTO }> {
    return put(SETTINGS_API, payload)
  },

  /** 验证 API Key 连通性 */
  checkConnection(payload: CheckConnectionPayload): Promise<{ success: true; data: { ok: boolean; message: string } }> {
    return post(`${SETTINGS_API}/check`, payload)
  },

  /** 重置所有设置回 .env 默认值 */
  resetSettings(): Promise<{ success: true; data: { message: string; settings: SettingsDTO } }> {
    return post(`${SETTINGS_API}/reset`, {})
  },
}