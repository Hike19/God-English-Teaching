import apiClient from './client'

export interface Subtitle {
  id: number
  index: number
  start_time: number
  end_time: number
  text: string
}

export interface Task {
  id: number
  source_type: 'upload' | 'url'
  source_path: string
  title: string
  status: 'processing' | 'done' | 'failed'
  audio_path: string | null
  error_msg: string | null
  created_at: string
  updated_at: string
  subtitles: Subtitle[]
}

export interface TaskCreateResponse {
  id: number
  status: string
}

export async function uploadFile(
  file: File,
  onProgress?: (pct: number) => void,
): Promise<TaskCreateResponse> {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await apiClient.post<TaskCreateResponse>('/tasks/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 300000,
    onUploadProgress: (e) => {
      if (e.total && onProgress) onProgress(Math.round((e.loaded / e.total) * 100))
    },
  })
  return data
}

export async function submitUrl(url: string): Promise<TaskCreateResponse> {
  const formData = new FormData()
  formData.append('url', url)
  const { data } = await apiClient.post<TaskCreateResponse>('/tasks/url', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function listTasks(): Promise<Task[]> {
  const { data } = await apiClient.get<Task[]>('/tasks')
  return data
}

export async function getTask(id: number): Promise<Task> {
  const { data } = await apiClient.get<Task>(`/tasks/${id}`)
  return data
}

export async function deleteTask(id: number): Promise<void> {
  await apiClient.delete(`/tasks/${id}`)
}

export function getAudioUrl(taskId: number): string {
  const token = localStorage.getItem('token')
  return `/api/tasks/${taskId}/audio?token=${token || ''}`
}
