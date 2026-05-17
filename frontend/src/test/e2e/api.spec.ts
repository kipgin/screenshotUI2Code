/**
 * src/test/e2e/api.spec.ts
 *
 * Real HTTP integration tests for the backend API.
 * These tests hit the LIVE backend running on http://localhost:8001 — no mocks.
 *
 * Prerequisites:
 *   - Backend running: uvicorn main:app --port 8001  (cd backend)
 *   - AI model server running on port 8000
 *
 * Run with:
 *   npx playwright test src/test/e2e/api.spec.ts
 */
import { test, expect, type Page } from '@playwright/test';

const BACKEND = 'http://localhost:8001/api/v1';

async function goto(page: Page) {
  for (const port of [3000, 3001, 3002, 3003]) {
    try {
      await page.goto(`http://localhost:${port}/`, { timeout: 4000 });
      return;
    } catch { /* try next */ }
  }
  throw new Error('Could not reach dev server on any port');
}

// ── Health check ──────────────────────────────────────────────────────────────

test.describe('Backend Health', () => {
  test('GET /health returns 200 and healthy status', async ({ request }) => {
    const res = await request.get(`${BACKEND}/health`);
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body).toHaveProperty('status');
    expect(body.status).toMatch(/ok|healthy/i);
  });
});

// ── Session upload ────────────────────────────────────────────────────────────

test.describe('Design – POST /design/upload', () => {
  test('uploading a PNG returns an SSE 200 with text/event-stream content-type', async ({ page }) => {
    await goto(page); // navigate so we share the same origin as the backend proxy
    // We use page.evaluate so we can read only the first chunk of the SSE stream
    // without waiting for the infinite stream to close.
    const result = await page.evaluate(async () => {
      const pngB64 = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==';
      const byteStr = atob(pngB64);
      const buf = new Uint8Array(byteStr.length);
      for (let i = 0; i < byteStr.length; i++) buf[i] = byteStr.charCodeAt(i);
      const blob = new Blob([buf], { type: 'image/png' });

      const fd = new FormData();
      fd.append('file', blob, 'test.png');
      fd.append('framework', 'html/css');
      fd.append('enable_parallel', 'false');

      const res = await fetch('/api/v1/design/upload', { method: 'POST', body: fd });
      const status = res.status;
      const ct = res.headers.get('content-type') ?? '';

      // Read first line of the SSE stream then abort
      const reader = res.body!.getReader();
      const { value } = await reader.read();
      reader.cancel();
      const firstChunk = new TextDecoder().decode(value ?? new Uint8Array());

      return { status, ct, firstChunk };
    });

    expect(result.status).toBe(200);
    expect(result.ct).toMatch(/event-stream/i);
    // The first SSE chunk contains a session_id or token event
    expect(result.firstChunk.length).toBeGreaterThan(0);
  });

  test('upload without a file returns 422 Unprocessable Entity', async ({ request }) => {
    const res = await request.post(`${BACKEND}/design/upload`, {
      form: { framework: 'html/css' },
    });
    expect(res.status()).toBe(422);
  });
});

// ── Session metadata ──────────────────────────────────────────────────────────

test.describe('Design – GET /design/session/:id', () => {
  test('getting a non-existent session returns 404', async ({ request }) => {
    const res = await request.get(`${BACKEND}/design/session/does-not-exist-xyz`);
    expect(res.status()).toBe(404);
    const body = await res.json();
    expect(body).toHaveProperty('detail');
  });
});

// ── Workspace routes ──────────────────────────────────────────────────────────

test.describe('Workspace – /workspace/:id/*', () => {
  test('requesting files for an unknown session returns 404', async ({ request }) => {
    const res = await request.get(`${BACKEND}/workspace/unknown-session/files?path=.`);
    expect(res.status()).toBe(404);
  });

  test('requesting git log for an unknown session returns 404', async ({ request }) => {
    const res = await request.get(`${BACKEND}/workspace/unknown-session/git/log`);
    expect(res.status()).toBe(404);
  });
});

// ── Feedback (multi-turn) ─────────────────────────────────────────────────────

test.describe('Design – POST /design/feedback', () => {
  test('submitting feedback without a valid session returns 404', async ({ request }) => {
    const formData = new URLSearchParams({
      session_id: 'ghost-session-xyz',
      feedback: 'Make it blue',
    });
    const res = await request.post(`${BACKEND}/design/feedback`, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      data: formData.toString(),
    });
    expect(res.status()).toBe(404);
    const body = await res.json();
    expect(body.detail).toMatch(/session not found/i);
  });
});
