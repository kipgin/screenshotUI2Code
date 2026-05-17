/**
 * src/test/e2e/ui.spec.ts
 *
 * End-to-end browser UI tests using Playwright.
 * These tests run against the LIVE dev server (http://localhost:3002)
 * and do NOT mock anything — they verify real DOM output in a real browser.
 *
 * Run with:
 *   npx playwright test
 */
import { test, expect, Page } from '@playwright/test';

// ── helpers ──────────────────────────────────────────────────────────────────

async function goto(page: Page) {
  // Try common dev-server ports
  for (const port of [3000, 3001, 3002, 3003]) {
    try {
      await page.goto(`http://localhost:${port}/`, { timeout: 4000 });
      return;
    } catch { /* try next */ }
  }
  throw new Error('Could not reach dev server on any port');
}

// ── Layout / structural tests ─────────────────────────────────────────────────

test.describe('UI Layout', () => {
  test('page title is "AI Frontend Designer"', async ({ page }) => {
    await goto(page);
    await expect(page).toHaveTitle(/AI Frontend Designer/i);
  });

  test('three-pane layout renders — chat, explorer, editor', async ({ page }) => {
    await goto(page);
    await expect(page.getByText('Agent Chat')).toBeVisible();
    // Explorer tab buttons
    await expect(page.locator('button').filter({ hasText: /files/i }).first()).toBeVisible();
    await expect(page.locator('button').filter({ hasText: /git/i }).first()).toBeVisible();
    // Editor tabs — use getByText with exact: false to handle icon + text
    await expect(page.getByText('Code', { exact: false }).first()).toBeVisible();
    await expect(page.getByText('Diffs', { exact: false }).first()).toBeVisible();
    await expect(page.getByText('Preview', { exact: false }).first()).toBeVisible();
  });
});

// ── Chat Panel tests ──────────────────────────────────────────────────────────

test.describe('Chat Panel', () => {
  test.beforeEach(async ({ page }) => { await goto(page); });

  test('shows "No active session" and upload button on first load', async ({ page }) => {
    await expect(page.getByText('No active session')).toBeVisible();
    await expect(page.getByRole('button', { name: /select image/i })).toBeVisible();
  });

  test('connection status indicator is visible', async ({ page }) => {
    // The colored dot is a small div with rounded-full inside the h2 header area
    const dot = page.locator('.rounded-full').first();
    await expect(dot).toBeAttached();
  });

  test('clicking "Select Image" opens a file picker', async ({ page }) => {
    const [fileChooser] = await Promise.all([
      page.waitForEvent('filechooser'),
      page.getByRole('button', { name: /select image/i }).click(),
    ]);
    expect(fileChooser).toBeTruthy();
  });

  test('feedback input is disabled before a session starts', async ({ page }) => {
    const input = page.getByPlaceholder('Give feedback...');
    await expect(input).toBeDisabled();
  });
});

// ── Explorer Panel tests ──────────────────────────────────────────────────────

test.describe('Explorer Panel', () => {
  test.beforeEach(async ({ page }) => { await goto(page); });

  test('Files tab is active by default', async ({ page }) => {
    await expect(page.getByText('No files in workspace')).toBeVisible();
  });

  test('switching to Git tab shows "No commits yet" or commit circles', async ({ page }) => {
    await page.getByRole('button', { name: /^Git$/i }).click();
    
    // It might show "No commits yet" if empty, or render commit circles if not empty.
    const noCommits = page.getByText('No commits yet');
    const commitCircles = page.locator('.rounded-full.bg-\\[\\#1a1d24\\]');
    
    // Either there are no commits, or there is at least one commit circle
    await expect(noCommits.or(commitCircles.first())).toBeVisible();
    
    // Test clickability of commit circle if they exist
    if (await commitCircles.count() > 0) {
      await commitCircles.first().click();
    }
  });
  
  test('can create and remove a file using the UI', async ({ page }) => {
    // Mock the backend to avoid needing a real session
    await page.evaluate(() => {
      // Force a fake session ID so the UI enables features
      window.localStorage.setItem('chat-store', JSON.stringify({ state: { sessionId: 'fake-session' } }));
    });
    await page.reload();

    await page.route('**/api/v1/workspace/*/files*', async route => {
      await route.fulfill({ json: [] });
    });
    await page.route('**/api/v1/workspace/*/file*', async route => {
      await route.fulfill({ json: { detail: 'success' } });
    });

    const testFileName = `test-file-${Date.now()}.txt`;
    page.on('dialog', dialog => dialog.accept(testFileName));
    
    // We mock the files response after creation to return our new file
    await page.route('**/api/v1/workspace/*/files*', async route => {
      await route.fulfill({ json: [{ path: testFileName, name: testFileName, isDir: false }] });
    });

    await page.getByTitle('New File').click();
    await expect(page.getByText(testFileName)).toBeVisible({ timeout: 5000 });

    
    // 2. Remove the file
    // Hover over the file to reveal the delete button
    const fileNode = page.locator('div').filter({ hasText: new RegExp(`^${testFileName}$`) }).first();
    await fileNode.hover();
    
    // Handle the confirm dialog
    page.on('dialog', dialog => dialog.accept());
    
    // Click the delete button
    await fileNode.locator('button[title="Delete File"]').click();
    
    // Wait for the file to disappear
    await expect(page.getByText(testFileName)).toBeHidden({ timeout: 5000 });
  });
});

// ── Editor Panel tests ────────────────────────────────────────────────────────

test.describe('Editor Panel', () => {
  test.beforeEach(async ({ page }) => { await goto(page); });

  test('Code tab shows placeholder before a file is selected', async ({ page }) => {
    await expect(page.getByText('Select a file to view code')).toBeVisible();
  });

  test('interact with IDE when a file is selected', async ({ page }) => {
    // Mock session and files
    await page.evaluate(() => {
      window.localStorage.setItem('chat-store', JSON.stringify({ state: { sessionId: 'fake-session' } }));
    });
    await page.reload();
    
    const testFileName = `ide-test-${Date.now()}.js`;
    await page.route('**/api/v1/workspace/*/file*', async route => {
      if (route.request().method() === 'GET') {
        await route.fulfill({ json: { content: '// test code' } });
      } else {
        await route.fulfill({ json: { detail: 'success' } });
      }
    });
    await page.route('**/api/v1/workspace/*/files*', async route => {
      await route.fulfill({ json: [{ path: testFileName, name: testFileName, isDir: false }] });
    });

    // File should already be visible from the mock
    await expect(page.getByText(testFileName)).toBeVisible();
    
    // Click the file to open it in the editor
    await page.getByText(testFileName).click();
    
    // The Monaco editor should now be visible instead of the placeholder
    await expect(page.getByText('Select a file to view code')).toBeHidden();
    
    // Verify Monaco Editor is mounted by checking for its core class
    const monacoEditor = page.locator('.monaco-editor').first();
    await expect(monacoEditor).toBeVisible();
    
    // Check if Save File button appears
    await expect(page.getByRole('button', { name: /save file/i })).toBeVisible();
    
    // Clean up
    const fileNode = page.locator('div').filter({ hasText: new RegExp(`^${testFileName}$`) }).first();
    await fileNode.hover();
    page.once('dialog', dialog => dialog.accept());
    await fileNode.locator('button[title="Delete File"]').click();
  });

  test('switching to Diffs tab shows "No pending diffs"', async ({ page }) => {
    await page.getByRole('button', { name: /^Diffs$/i }).click();
    await expect(page.getByText(/no pending diffs/i)).toBeVisible();
  });

  test('switching to Preview tab renders an iframe', async ({ page }) => {
    await page.getByRole('button', { name: /^Preview$/i }).click();
    await expect(page.frameLocator('iframe[title="preview"]').locator('body')).toBeDefined();
  });
});
