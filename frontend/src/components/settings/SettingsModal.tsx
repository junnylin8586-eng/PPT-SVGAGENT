/**
 * SettingsModal - AI API Key & 模型配置
 * v0.6 Feature 1：用户可在界面上配置 LLM API Key 并验证连通性
 */
import { useState, useEffect } from 'react'
import { X, Eye, EyeOff, Check, AlertCircle, Loader, Settings, Key, Globe, Cpu } from 'lucide-react'
import { settingsApi, type UpdateSettingsPayload } from '@/api/settingsApi'

interface Props {
  open: boolean
  onClose: () => void
  onSaved?: () => void
}

interface SettingsState {
  ai_provider_format: string
  api_base_url: string
  api_key: string
  minimax_api_key: string
  minimax_api_base: string
  text_model: string
  image_model: string
  text_model_source: string
  image_model_source: string
  image_resolution: string
  image_aspect_ratio: string
  output_language: string
  enable_text_reasoning: boolean
  text_thinking_budget: number
  enable_image_reasoning: boolean
  image_thinking_budget: number
}

const PROVIDERS = [
  { value: 'minimax', label: 'MiniMax', baseDefault: 'https://api.minimax.chat/v1/' },
  { value: 'openai', label: 'OpenAI', baseDefault: 'https://api.openai.com/v1/' },
  { value: 'gemini', label: 'Google Gemini', baseDefault: 'https://generativelanguage.googleapis.com/v1beta/' },
  { value: 'deepseek', label: 'DeepSeek', baseDefault: 'https://api.deepseek.com/v1/' },
  { value: 'qwen', label: '阿里 Qwen', baseDefault: 'https://dashscope.aliyuncs.com/compatible-mode/v1/' },
  { value: 'kimi', label: 'Kimi (Moonshot)', baseDefault: 'https://api.moonshot.cn/v1/' },
]

const TEXT_MODEL_OPTIONS: Record<string, string[]> = {
  minimax: ['MiniMax-M2.7', 'MiniMax-M2', 'MiniMax-Text-01'],
  openai: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-3.5-turbo'],
  gemini: ['gemini-2.0-flash', 'gemini-1.5-pro', 'gemini-1.5-flash'],
  deepseek: ['deepseek-chat', 'deepseek-coder'],
  qwen: ['qwen-plus', 'qwen-max', 'qwen-turbo'],
  kimi: ['moonshot-v1-8k', 'moonshot-v1-32k', 'moonshot-v1-128k'],
}

const IMAGE_MODEL_OPTIONS: Record<string, string[]> = {
  minimax: ['image-01', 'image-01-mini'],
  openai: ['dall-e-3', 'dall-e-2'],
  gemini: ['imagen-3', 'imagen-2'],
  deepseek: [],
  qwen: ['wanx'],
  kimi: [],
}

const RESOLUTION_OPTIONS = ['1K', '2K', '4K']
const ASPECT_OPTIONS = ['16:9', '4:3', '1:1']
const LANGUAGE_OPTIONS = [
  { value: 'auto', label: '自动检测' },
  { value: 'zh', label: '中文' },
  { value: 'en', label: '英文' },
  { value: 'ja', label: '日文' },
]

const PROVIDER_ICONS: Record<string, string> = {
  minimax: '🤖',
  openai: '🔵',
  gemini: '🟡',
  deepseek: '🔴',
  qwen: '🟠',
  kimi: '🌙',
}

function maskKey(key: string, showLen = 6): string {
  if (!key) return ''
  if (key.length <= showLen + 4) return '*'.repeat(key.length)
  return key.slice(0, showLen) + '****' + key.slice(-4)
}

export default function SettingsModal({ open, onClose, onSaved }: Props) {
  const [settings, setSettings] = useState<SettingsState>({
    ai_provider_format: 'minimax',
    api_base_url: '',
    api_key: '',
    minimax_api_key: '',
    minimax_api_base: '',
    text_model: 'MiniMax-M2.7',
    image_model: 'image-01',
    text_model_source: '',
    image_model_source: '',
    image_resolution: '2K',
    image_aspect_ratio: '16:9',
    output_language: 'zh',
    enable_text_reasoning: false,
    text_thinking_budget: 1024,
    enable_image_reasoning: false,
    image_thinking_budget: 1024,
  })

  const [showKey, setShowKey] = useState(false)
  const [showMinimaxKey, setShowMinimaxKey] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<{ ok: boolean; message: string } | null>(null)
  const [error, setError] = useState('')
  const [activeTab, setActiveTab] = useState<'provider' | 'models' | 'generation'>('provider')

  // Load settings on open
  useEffect(() => {
    if (!open) return
    setLoading(true)
    setError('')
    setTestResult(null)
    settingsApi.getSettings().then(res => {
      const d = res.data
      setSettings({
        ai_provider_format: d.ai_provider_format || 'minimax',
        api_base_url: d.api_base_url || '',
        api_key: '', // never sent back (only written, not read back)
        minimax_api_key: '',
        minimax_api_base: d.minimax_api_base || '',
        text_model: d.text_model || 'MiniMax-M2.7',
        image_model: d.image_model || 'image-01',
        text_model_source: d.text_model_source || '',
        image_model_source: d.image_model_source || '',
        image_resolution: d.image_resolution || '2K',
        image_aspect_ratio: d.image_aspect_ratio || '16:9',
        output_language: d.output_language || 'zh',
        enable_text_reasoning: d.enable_text_reasoning ?? false,
        text_thinking_budget: d.text_thinking_budget ?? 1024,
        enable_image_reasoning: d.enable_image_reasoning ?? false,
        image_thinking_budget: d.image_thinking_budget ?? 1024,
      })
    }).catch(e => {
      setError('加载设置失败: ' + e.message)
    }).finally(() => setLoading(false))
  }, [open])

  const provider = PROVIDERS.find(p => p.value === settings.ai_provider_format) || PROVIDERS[0]

  const handleProviderChange = (val: string) => {
    const p = PROVIDERS.find(p => p.value === val) || PROVIDERS[0]
    setSettings(prev => ({
      ...prev,
      ai_provider_format: val,
      api_base_url: prev.api_base_url || p.baseDefault,
      text_model: TEXT_MODEL_OPTIONS[val]?.[0] || prev.text_model,
      image_model: IMAGE_MODEL_OPTIONS[val]?.[0] || prev.image_model,
    }))
    setTestResult(null)
  }

  const handleTestConnection = async () => {
    setTesting(true)
    setTestResult(null)
    setError('')
    try {
      const activeKey = settings.ai_provider_format === 'minimax'
        ? settings.minimax_api_key
        : settings.api_key
      const activeBase = settings.ai_provider_format === 'minimax'
        ? settings.minimax_api_base
        : settings.api_base_url

      if (!activeKey) {
        setError('请先填写 API Key')
        setTesting(false)
        return
      }

      const res = await settingsApi.checkConnection({
        api_key: activeKey,
        api_base_url: activeBase || provider.baseDefault,
        provider: settings.ai_provider_format,
      })
      setTestResult({ ok: true, message: res.data?.message || '连接成功！' })
    } catch (e: any) {
      setTestResult({ ok: false, message: e.message || '连接失败' })
    } finally {
      setTesting(false)
    }
  }

  const handleSave = async () => {
    setSaving(true)
    setError('')
    try {
      const payload: UpdateSettingsPayload = {
        ai_provider_format: settings.ai_provider_format,
        api_base_url: settings.api_base_url || undefined,
        minimax_api_base: settings.minimax_api_base || undefined,
        text_model: settings.text_model || undefined,
        image_model: settings.image_model || undefined,
        text_model_source: settings.text_model_source || undefined,
        image_model_source: settings.image_model_source || undefined,
        image_resolution: settings.image_resolution || undefined,
        image_aspect_ratio: settings.image_aspect_ratio || undefined,
        output_language: settings.output_language || undefined,
        enable_text_reasoning: settings.enable_text_reasoning,
        text_thinking_budget: settings.text_thinking_budget,
        enable_image_reasoning: settings.enable_image_reasoning,
        image_thinking_budget: settings.image_thinking_budget,
      }
      if (settings.api_key) payload.api_key = settings.api_key
      if (settings.minimax_api_key) payload.minimax_api_key = settings.minimax_api_key

      await settingsApi.updateSettings(payload)
      onSaved?.()
      onClose()
    } catch (e: any) {
      setError('保存失败: ' + e.message)
    } finally {
      setSaving(false)
    }
  }

  if (!open) return null

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box settings-modal-box" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Settings size={18} color="var(--color-primary)" />
            <span style={{ fontWeight: 600, fontSize: '15px' }}>AI 设置</span>
          </div>
          <button className="modal-close" onClick={onClose}><X size={18} /></button>
        </div>

        {/* Tabs */}
        <div className="settings-tabs">
          <button className={`settings-tab ${activeTab === 'provider' ? 'active' : ''}`} onClick={() => setActiveTab('provider')}>
            <Key size={14} /> API 配置
          </button>
          <button className={`settings-tab ${activeTab === 'models' ? 'active' : ''}`} onClick={() => setActiveTab('models')}>
            <Cpu size={14} /> 模型设置
          </button>
          <button className={`settings-tab ${activeTab === 'generation' ? 'active' : ''}`} onClick={() => setActiveTab('generation')}>
            <Settings size={14} /> 生成参数
          </button>
        </div>

        {loading ? (
          <div className="settings-loading">
            <Loader size={20} className="spin" />
            <span>加载中...</span>
          </div>
        ) : (
          <>
            <div className="modal-body" style={{ padding: '0 20px 16px' }}>
              {error && (
                <div className="settings-error">
                  <AlertCircle size={14} /> {error}
                </div>
              )}

              {/* === Tab: Provider === */}
              {activeTab === 'provider' && (
                <div className="settings-section">
                  <div className="settings-field">
                    <label>AI 提供商</label>
                    <div className="provider-grid">
                      {PROVIDERS.map(p => (
                        <button
                          key={p.value}
                          className={`provider-btn ${settings.ai_provider_format === p.value ? 'active' : ''}`}
                          onClick={() => handleProviderChange(p.value)}
                        >
                          <span className="provider-icon">{PROVIDER_ICONS[p.value]}</span>
                          <span className="provider-name">{p.label}</span>
                        </button>
                      ))}
                    </div>
                  </div>

                  {settings.ai_provider_format === 'minimax' ? (
                    <>
                      <div className="settings-field">
                        <label>MiniMax API Key</label>
                        <div className="input-group">
                          <input
                            type={showMinimaxKey ? 'text' : 'password'}
                            className="form-input"
                            placeholder="输入 MiniMax API Key"
                            value={settings.minimax_api_key}
                            onChange={e => { setSettings(prev => ({ ...prev, minimax_api_key: e.target.value })); setTestResult(null) }}
                            style={{ flex: 1 }}
                          />
                          <button className="input-icon-btn" onClick={() => setShowMinimaxKey(v => !v)}>
                            {showMinimaxKey ? <EyeOff size={15} /> : <Eye size={15} />}
                          </button>
                        </div>
                        <span className="field-hint">用于文本生成和图片生成，Key 会加密存储</span>
                      </div>
                      <div className="settings-field">
                        <label>MiniMax API 地址 <span className="field-optional">(可选)</span></label>
                        <input
                          type="text"
                          className="form-input"
                          placeholder="https://api.minimax.chat/v1/"
                          value={settings.minimax_api_base}
                          onChange={e => setSettings(prev => ({ ...prev, minimax_api_base: e.target.value }))}
                        />
                      </div>
                    </>
                  ) : (
                    <>
                      <div className="settings-field">
                        <label>{provider.label} API Key</label>
                        <div className="input-group">
                          <input
                            type={showKey ? 'text' : 'password'}
                            className="form-input"
                            placeholder={`输入 ${provider.label} API Key`}
                            value={settings.api_key}
                            onChange={e => { setSettings(prev => ({ ...prev, api_key: e.target.value })); setTestResult(null) }}
                            style={{ flex: 1 }}
                          />
                          <button className="input-icon-btn" onClick={() => setShowKey(v => !v)}>
                            {showKey ? <EyeOff size={15} /> : <Eye size={15} />}
                          </button>
                        </div>
                      </div>
                      <div className="settings-field">
                        <label>API Base URL <span className="field-optional">(可选)</span></label>
                        <input
                          type="text"
                          className="form-input"
                          placeholder={provider.baseDefault}
                          value={settings.api_base_url}
                          onChange={e => setSettings(prev => ({ ...prev, api_base_url: e.target.value }))}
                        />
                        <span className="field-hint">默认：{provider.baseDefault}</span>
                      </div>
                    </>
                  )}

                  {/* Test Connection */}
                  <div className="settings-field">
                    <label>连接测试</label>
                    <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                      <button
                        className="btn btn-outline"
                        onClick={handleTestConnection}
                        disabled={testing || (!settings.api_key && !settings.minimax_api_key)}
                      >
                        {testing ? <><Loader size={13} className="spin" /> 测试中...</> : '测试连接'}
                      </button>
                      {testResult && (
                        <div className={`test-result ${testResult.ok ? 'ok' : 'fail'}`}>
                          {testResult.ok ? <Check size={13} /> : <AlertCircle size={13} />}
                          {testResult.message}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* === Tab: Models === */}
              {activeTab === 'models' && (
                <div className="settings-section">
                  <div className="settings-field">
                    <label>文本生成模型</label>
                    <select
                      className="form-input"
                      value={settings.text_model}
                      onChange={e => setSettings(prev => ({ ...prev, text_model: e.target.value }))}
                    >
                      {(TEXT_MODEL_OPTIONS[settings.ai_provider_format] || []).map(m => (
                        <option key={m} value={m}>{m}</option>
                      ))}
                    </select>
                    {settings.text_model_source && (
                      <span className="field-hint">来源: {settings.text_model_source}</span>
                    )}
                  </div>
                  <div className="settings-field">
                    <label>图片生成模型</label>
                    <select
                      className="form-input"
                      value={settings.image_model}
                      onChange={e => setSettings(prev => ({ ...prev, image_model: e.target.value }))}
                    >
                      {(IMAGE_MODEL_OPTIONS[settings.ai_provider_format] || []).length === 0 ? (
                        <option value="">当前提供商不支持图片生成</option>
                      ) : (
                        (IMAGE_MODEL_OPTIONS[settings.ai_provider_format] || []).map(m => (
                          <option key={m} value={m}>{m}</option>
                        ))
                      )}
                    </select>
                  </div>
                  <div className="settings-field">
                    <label>输出语言</label>
                    <select
                      className="form-input"
                      value={settings.output_language}
                      onChange={e => setSettings(prev => ({ ...prev, output_language: e.target.value }))}
                    >
                      {LANGUAGE_OPTIONS.map(l => (
                        <option key={l.value} value={l.value}>{l.label}</option>
                      ))}
                    </select>
                  </div>
                </div>
              )}

              {/* === Tab: Generation === */}
              {activeTab === 'generation' && (
                <div className="settings-section">
                  <div className="settings-row">
                    <div className="settings-field">
                      <label>图片清晰度</label>
                      <select
                        className="form-input"
                        value={settings.image_resolution}
                        onChange={e => setSettings(prev => ({ ...prev, image_resolution: e.target.value }))}
                      >
                        {RESOLUTION_OPTIONS.map(r => <option key={r} value={r}>{r}</option>)}
                      </select>
                    </div>
                    <div className="settings-field">
                      <label>图片比例</label>
                      <select
                        className="form-input"
                        value={settings.image_aspect_ratio}
                        onChange={e => setSettings(prev => ({ ...prev, image_aspect_ratio: e.target.value }))}
                      >
                        {ASPECT_OPTIONS.map(a => <option key={a} value={a}>{a}</option>)}
                      </select>
                    </div>
                  </div>

                  <div className="settings-field" style={{ marginTop: '16px' }}>
                    <div className="settings-toggle-row">
                      <div>
                        <div className="toggle-label">文本推理模式</div>
                        <div className="toggle-desc">开启后模型会进行深度思考（消耗更多 token）</div>
                      </div>
                      <label className="toggle-switch">
                        <input
                          type="checkbox"
                          checked={settings.enable_text_reasoning}
                          onChange={e => setSettings(prev => ({ ...prev, enable_text_reasoning: e.target.checked }))}
                        />
                        <span className="toggle-slider" />
                      </label>
                    </div>
                    {settings.enable_text_reasoning && (
                      <div style={{ marginTop: '8px' }}>
                        <label style={{ fontSize: '12px', color: 'var(--text-muted)' }}>思考预算 (1-8192)</label>
                        <input
                          type="number"
                          className="form-input"
                          min={1}
                          max={8192}
                          value={settings.text_thinking_budget}
                          onChange={e => setSettings(prev => ({ ...prev, text_thinking_budget: parseInt(e.target.value) || 1024 }))}
                        />
                      </div>
                    )}
                  </div>

                  <div className="settings-field">
                    <div className="settings-toggle-row">
                      <div>
                        <div className="toggle-label">图片推理模式</div>
                        <div className="toggle-desc">开启后图片模型会进行深度思考</div>
                      </div>
                      <label className="toggle-switch">
                        <input
                          type="checkbox"
                          checked={settings.enable_image_reasoning}
                          onChange={e => setSettings(prev => ({ ...prev, enable_image_reasoning: e.target.checked }))}
                        />
                        <span className="toggle-slider" />
                      </label>
                    </div>
                    {settings.enable_image_reasoning && (
                      <div style={{ marginTop: '8px' }}>
                        <label style={{ fontSize: '12px', color: 'var(--text-muted)' }}>思考预算 (1-8192)</label>
                        <input
                          type="number"
                          className="form-input"
                          min={1}
                          max={8192}
                          value={settings.image_thinking_budget}
                          onChange={e => setSettings(prev => ({ ...prev, image_thinking_budget: parseInt(e.target.value) || 1024 }))}
                        />
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </>
        )}

        {/* Footer */}
        {!loading && (
          <div className="modal-footer">
            <button className="btn btn-outline" onClick={onClose}>取消</button>
            <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
              {saving ? <><Loader size={13} className="spin" /> 保存中...</> : '保存设置'}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}