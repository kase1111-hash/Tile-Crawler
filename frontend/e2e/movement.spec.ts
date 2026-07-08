import { test, expect } from '@playwright/test';
import { freshGame, faceOpenExit, getExitLabels, getLocationText } from './helpers';

test.describe('Movement', () => {
  test.beforeEach(async ({ page }) => {
    await freshGame(page);
  });

  test('compass starts facing north', async ({ page }) => {
    await expect(page.locator('.compass-dir')).toHaveText('NORTH');
  });

  test('A and D turn the player without moving', async ({ page }) => {
    const location = await getLocationText(page);

    await page.keyboard.press('a');
    await expect(page.locator('.compass-dir')).toHaveText('WEST');

    await page.keyboard.press('d');
    await page.keyboard.press('d');
    await expect(page.locator('.compass-dir')).toHaveText('EAST');

    // Turning is client-side only; position must not change
    expect(await getLocationText(page)).toBe(location);
  });

  test('W moves forward through an open exit', async ({ page }) => {
    expect(await faceOpenExit(page)).toBe(true);
    const before = await getLocationText(page);

    const moveDone = page.waitForResponse(
      (resp) => resp.url().includes('/api/game/move') && resp.ok()
    );
    await page.keyboard.press('w');
    await moveDone;

    await expect(page.locator('.hud-location')).not.toHaveText(before);
  });

  test('W against a blocked exit does not move', async ({ page }) => {
    // Find a facing whose forward exit is blocked (skip if the room opens everywhere)
    let blocked = false;
    for (let i = 0; i < 4; i++) {
      const { w } = await getExitLabels(page);
      if (w.includes('Blocked')) {
        blocked = true;
        break;
      }
      await page.keyboard.press('a');
    }
    test.skip(!blocked, 'room has all four exits open');

    const before = await getLocationText(page);
    await page.keyboard.press('w');
    // The app suppresses the request entirely for a blocked direction
    await page.waitForTimeout(500);
    expect(await getLocationText(page)).toBe(before);
  });

  test('exits panel matches movement outcome across several rooms', async ({ page }) => {
    for (let step = 0; step < 3; step++) {
      // Combat can start when entering a room; movement is locked then
      if (await page.locator('.combat-overlay').isVisible()) break;
      expect(await faceOpenExit(page)).toBe(true);
      const before = await getLocationText(page);

      const moveDone = page.waitForResponse(
        (resp) => resp.url().includes('/api/game/move') && resp.ok()
      );
      await page.keyboard.press('w');
      await moveDone;

      await expect(page.locator('.hud-location')).not.toHaveText(before);
    }
  });
});
