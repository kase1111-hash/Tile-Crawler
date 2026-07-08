import { test, expect } from '@playwright/test';
import { freshGame, faceOpenExit, getLocationText } from './helpers';

test.describe('Full Game Flow', () => {
  test('complete game session flow', async ({ page }) => {
    // 1. Fresh game loads into the HUD
    await freshGame(page, 'Full Flow Test');
    await expect(page).toHaveTitle(/Tile-Crawler/i);
    await expect(page.locator('.stat-name')).toHaveText('Full Flow Test');

    // 2. Stats are rendered
    await expect(page.locator('.stat-bar-row', { hasText: 'HP' })).toBeVisible();
    await expect(page.locator('.stat-gold')).toContainText(/Gold: \d+/);

    // 3. Move through an open exit
    if (!(await page.locator('.combat-overlay').isVisible())) {
      expect(await faceOpenExit(page)).toBe(true);
      const before = await getLocationText(page);
      const moveDone = page.waitForResponse(
        (resp) => resp.url().includes('/api/game/move') && resp.ok()
      );
      await page.keyboard.press('w');
      await moveDone;
      await expect(page.locator('.hud-location')).not.toHaveText(before);
    }

    // 4. Inventory opens and closes (outside combat)
    if (!(await page.locator('.combat-overlay').isVisible())) {
      await page.keyboard.press('i');
      await expect(page.locator('.inventory-box')).toBeVisible();
      await page.keyboard.press('Escape');
      await expect(page.locator('.inventory-box')).not.toBeVisible();
    }

    // 5. Save with Q (combat mode only listens for attack/flee keys)
    if (!(await page.locator('.combat-overlay').isVisible())) {
      await expect(page.locator('.loading-spinner')).not.toBeVisible();
      const saveDone = page.waitForResponse(
        (resp) => resp.url().includes('/api/game/save') && resp.ok()
      );
      await page.keyboard.press('q');
      await saveDone;
      await expect(page.locator('.message-text')).toContainText('Game saved');
    }

    // 6. Game is still functional
    await expect(page.locator('.dungeon-container')).toBeVisible();
  });

  test('game state survives a page reload', async ({ page }) => {
    await freshGame(page, 'Reload Test');
    const location = await getLocationText(page);

    await page.reload();
    await expect(page.locator('.dungeon-container')).toBeVisible({ timeout: 15000 });
    await expect(page.locator('.stat-name')).toHaveText('Reload Test');
    expect(await getLocationText(page)).toBe(location);
  });

  test('game handles rapid inputs gracefully', async ({ page }) => {
    await freshGame(page);

    for (let i = 0; i < 10; i++) {
      await page.keyboard.press('a');
      await page.keyboard.press('w');
    }
    await page.waitForTimeout(1000);

    await expect(page.locator('.dungeon-container')).toBeVisible();
    await expect(page.locator('.compass-dir')).toHaveText(/NORTH|SOUTH|EAST|WEST/);
  });

  test('resting updates the narrative', async ({ page }) => {
    await freshGame(page);
    test.skip(await page.locator('.combat-overlay').isVisible(), 'combat started in the first room');

    const restDone = page.waitForResponse(
      (resp) => resp.url().includes('/api/game/rest') && resp.ok()
    );
    await page.keyboard.press('r');
    await restDone;

    await expect(page.locator('.message-text')).not.toHaveText('');
  });
});
