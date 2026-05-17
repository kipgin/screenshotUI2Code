import type { FileNode, GitCommit } from '@/types';

const API_BASE = '/api/v1';

export async function getFiles(sessionId: string, path: string = '.'): Promise<FileNode[]> {
  const res = await fetch(`${API_BASE}/workspace/${sessionId}/files?path=${encodeURIComponent(path)}`);
  if (!res.ok) throw new Error('Failed to get files');
  return res.json();
}

export async function getFile(sessionId: string, path: string): Promise<string> {
  const res = await fetch(`${API_BASE}/workspace/${sessionId}/file?path=${encodeURIComponent(path)}`);
  if (!res.ok) throw new Error('Failed to read file');
  const data = await res.json();
  return data.content;
}

export async function writeFile(sessionId: string, path: string, content: string): Promise<void> {
  const res = await fetch(`${API_BASE}/workspace/${sessionId}/file`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path, content }),
  });
  if (!res.ok) throw new Error('Failed to write file');
}

export async function createFolder(sessionId: string, path: string): Promise<void> {
  const res = await fetch(`${API_BASE}/workspace/${sessionId}/folder`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path }),
  });
  if (!res.ok) throw new Error('Failed to create folder');
}

export async function deleteFile(sessionId: string, path: string): Promise<void> {
  const res = await fetch(`${API_BASE}/workspace/${sessionId}/file?path=${encodeURIComponent(path)}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error('Failed to delete file');
}

export async function getGitStatus(sessionId: string): Promise<string> {
  const res = await fetch(`${API_BASE}/workspace/${sessionId}/git/status`);
  if (!res.ok) return '';
  const data = await res.json();
  return data.status || '';
}

export async function getGitLog(sessionId: string): Promise<GitCommit[]> {
  const res = await fetch(`${API_BASE}/workspace/${sessionId}/git/log`);
  if (!res.ok) return [];
  return res.json();
}

export async function checkoutGitCommit(sessionId: string, commitHash: string): Promise<void> {
  const res = await fetch(`${API_BASE}/workspace/${sessionId}/git/checkout`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ commit_hash: commitHash }),
  });
  if (!res.ok) throw new Error('Failed to checkout commit');
}
