// REST API Client

const API_BASE = '/api/v1';

export interface SessionData {
  session_id: string;
  framework: string;
  workspace: string;
  message_count: number;
  token_count: number;
}

export async function uploadScreenshot(
  file: File,
  framework: string = 'html/css',
  enableParallel: boolean = false
): Promise<Response> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('framework', framework);
  formData.append('enable_parallel', String(enableParallel));

  // Note: the backend uses SSE for this response, so we return the raw Response
  // so the caller can read the stream.
  return fetch(`${API_BASE}/design/upload`, {
    method: 'POST',
    body: formData,
  });
}

export async function submitFeedback(session_id: string, feedback: string): Promise<Response> {
  const formData = new FormData();
  formData.append('session_id', session_id);
  formData.append('feedback', feedback);

  return fetch(`${API_BASE}/design/feedback`, {
    method: 'POST',
    body: formData,
  });
}

export async function getSession(session_id: string): Promise<SessionData> {
  const res = await fetch(`${API_BASE}/design/session/${session_id}`);
  if (!res.ok) throw new Error('Session not found');
  return res.json();
}
