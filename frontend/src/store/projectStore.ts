/**
 * Project Store - 管理项目列表和当前项目状态
 */
import { create } from 'zustand'
import { api } from '@/api/client'
import type { Project } from '@/api/client'

interface ProjectState {
  projects: Project[]
  currentProject: Project | null
  loading: boolean
  error: string | null

  fetchProjects: () => Promise<void>
  createProject: (payload: Partial<Project>) => Promise<Project>
  setCurrentProject: (p: Project | null) => void
  deleteProject: (id: string) => Promise<void>
  updateProject: (id: string, payload: Partial<Project>) => Promise<void>
}

export const useProjectStore = create<ProjectState>((set, get) => ({
  projects: [],
  currentProject: null,
  loading: false,
  error: null,

  fetchProjects: async () => {
    set({ loading: true, error: null })
    try {
      const res = await api.getProjects()
      set({ projects: res.data || [], loading: false })
    } catch (e: any) {
      set({ error: e.message, loading: false })
    }
  },

  createProject: async (payload) => {
    const res = await api.createProject(payload)
    const project = res.data
    set(s => ({ projects: [project, ...s.projects] }))
    return project
  },

  setCurrentProject: (p) => set({ currentProject: p }),

  deleteProject: async (id) => {
    // Optimistic delete — remove from UI immediately
    set(s => ({
      projects: s.projects.filter(p => p.project_id !== id),
      currentProject: s.currentProject?.project_id === id ? null : s.currentProject,
    }))
    // Retry up to 3 times for SQLite locked errors
    for (let attempt = 0; attempt < 3; attempt++) {
      try {
        await api.deleteProject(id)
        return
      } catch (e: any) {
        if (attempt === 2 || !e?.message?.includes('database is locked')) {
          // Restore list on final failure so UI is consistent
          await get().fetchProjects()
          throw e
        }
        await new Promise(r => setTimeout(r, 200 * (attempt + 1)))
      }
    }
  },

  updateProject: async (id, payload) => {
    // Silent skip for status-only polling updates — don't hit DB
    const statusOnly = Object.keys(payload).length === 1 && 'status' in payload
    if (statusOnly) {
      set(s => ({
        projects: s.projects.map(p => p.project_id === id ? { ...p, ...payload } : p),
        currentProject: s.currentProject?.project_id === id ? { ...s.currentProject, ...payload } : s.currentProject,
      }))
      return
    }
    // Retry up to 3 times for SQLite locked errors
    for (let attempt = 0; attempt < 3; attempt++) {
      try {
        const res = await api.updateProject(id, payload)
        const updated = res.data
        set(s => ({
          projects: s.projects.map(p => p.project_id === id ? updated : p),
          currentProject: s.currentProject?.project_id === id ? updated : s.currentProject,
        }))
        return
      } catch (e: any) {
        if (attempt === 2 || !e?.message?.includes('database is locked')) throw e
        await new Promise(r => setTimeout(r, 200 * (attempt + 1)))
      }
    }
  },
}))
