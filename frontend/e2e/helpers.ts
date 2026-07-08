import { expect, type Page } from '@playwright/test';

/**
 * Start a brand-new game via the API, then load the page.
 * The app auto-resumes the backend session on mount, so this lands
 * directly in the HUD with a fresh, deterministic game state.
 */
export async function freshGame(page: Page, playerName = 'E2E Hero'): Promise<void> {
  const resp = await page.request.post('/api/game/new', {
    data: { player_name: playerName },
  });
  expect(resp.ok()).toBeTruthy();
  await page.goto('/');
  await expect(page.locator('.dungeon-container')).toBeVisible({ timeout: 15000 });
}

/**
 * Load the page and get into a running game whichever way the app offers:
 * the menu shows only when the backend has no session yet, otherwise the
 * HUD loads directly.
 */
export async function startGame(page: Page): Promise<void> {
  await page.goto('/');
  const hud = page.locator('.dungeon-container');
  const newGameButton = page.getByRole('button', { name: 'New Game' });
  await expect(hud.or(newGameButton).first()).toBeVisible({ timeout: 15000 });
  if (await newGameButton.isVisible()) {
    await newGameButton.click();
    await page.getByRole('button', { name: 'Begin Adventure' }).click();
  }
  await expect(hud).toBeVisible({ timeout: 15000 });
}

/** Exit rows in the HUD, keyed by the key that uses them. Order matches App.tsx. */
export async function getExitLabels(page: Page): Promise<{ w: string; s: string; a: string; d: string }> {
  const rows = page.locator('.exit-dir');
  await expect(rows).toHaveCount(4);
  const [w, s, a, d] = await rows.allTextContents();
  return { w, s, a, d };
}

/**
 * Turn (A key) until the forward exit is open, then return true.
 * Every room has at least one cardinal exit, so four turns always suffice.
 */
export async function faceOpenExit(page: Page): Promise<boolean> {
  for (let i = 0; i < 4; i++) {
    const { w } = await getExitLabels(page);
    if (w.includes('Forward')) return true;
    await page.keyboard.press('a');
  }
  return false;
}

/** Current "(x,y)" coordinate text from the HUD location line. */
export async function getLocationText(page: Page): Promise<string> {
  return (await page.locator('.hud-location').textContent()) ?? '';
}
