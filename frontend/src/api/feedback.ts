import apiClient from './client'

export interface FeedbackResponse {
  id: number
  user_id: number | null
  content: string
  created_at: string
}

export async function submitFeedback(content: string): Promise<FeedbackResponse> {
  const { data } = await apiClient.post<FeedbackResponse>('/feedback', { content })
  return data
}
