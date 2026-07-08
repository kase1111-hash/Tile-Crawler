import { test, expect, type Page } from '@playwright/test';
import { freshGame } from './helpers';

/**
 * Walk rooms via the API until an enemy encounter starts.
 * Encounters are random, so this is bounded and the tests skip when
 * the dungeon stays quiet.
 */
async function enterCombat(page: Page): Promise<boolean> {
  for (let i = 0; i < 40; i++) {
    const state = await (await page.request.get('/api/game/state')).json();
    if (state.combat?.in_combat) return true;
    if (state.player.hp.startsWith('0/')) {
      await page.request.post('/api/game/new', { data: { player_name: 'E2E Fighter' } });
      continue;
    }
    const open = Object.entries(state.room.exits)
      .filter(([, isOpen]) => isOpen)
      .map(([dir]) => dir)
      .filter((dir) => ['north', 'south', 'east', 'west'].includes(dir));
    if (open.length === 0) return false;
    await page.request.post('/api/game/move', {
      data: { direction: open[i % open.length] },
    });
  }
  return false;
}

test.describe('Combat', () => {
  test.beforeEach(async ({ page }) => {
    await freshGame(page, 'E2E Fighter');
  });

  test('combat overlay appears with enemy info and actions', async ({ page }) => {
    test.skip(!(await enterCombat(page)), 'no enemy encountered within the walk budget');
    await page.reload();

    const overlay = page.locator('.combat-overlay');
    await expect(overlay).toBeVisible({ timeout: 15000 });
    await expect(overlay.locator('.combat-title')).toContainText('COMBAT');
    await expect(overlay.locator('.combat-turn')).toContainText(/Turn \d+/);
    await expect(overlay.locator('.combat-enemy')).not.toHaveText('');
    await expect(overlay.locator('.combat-hp')).toContainText(/\d+\/\d+/);
    await expect(overlay.locator('.enemy-bar')).toBeVisible();
    await expect(overlay.locator('.combat-player-hp')).toContainText(/\d+\/\d+/);
    await expect(overlay.locator('.action-btn').filter({ hasText: 'Attack' })).toBeVisible();
    await expect(overlay.locator('.action-btn').filter({ hasText: 'Flee' })).toBeVisible();
    await expect(overlay.locator('.action-btn').filter({ hasText: 'Item' })).toBeVisible();
  });

  test('inventory opens during combat and warns about the turn cost', async ({ page }) => {
    test.skip(!(await enterCombat(page)), 'no enemy encountered within the walk budget');
    await page.reload();
    await expect(page.locator('.combat-overlay')).toBeVisible({ timeout: 15000 });

    // Keypresses are dropped while a request is in flight
    await expect(page.locator('.loading-spinner')).not.toBeVisible();
    await page.keyboard.press('i');
    await expect(page.locator('.inventory-box')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('.inv-combat-warning')).toContainText('enemy');

    await page.keyboard.press('Escape');
    await expect(page.locator('.inventory-box')).not.toBeVisible();
  });

  test('A key attacks during combat', async ({ page }) => {
    test.skip(!(await enterCombat(page)), 'no enemy encountered within the walk budget');
    await page.reload();
    await expect(page.locator('.combat-overlay')).toBeVisible({ timeout: 15000 });

    const attackDone = page.waitForResponse(
      (resp) => resp.url().includes('/api/game/combat/attack') && resp.ok()
    );
    await page.keyboard.press('a');
    await attackDone;

    // Combat either continues (overlay + updated HP) or the enemy died
    await expect(page.locator('.dungeon-container')).toBeVisible();
  });

  test('F key attempts to flee during combat', async ({ page }) => {
    test.skip(!(await enterCombat(page)), 'no enemy encountered within the walk budget');
    await page.reload();
    await expect(page.locator('.combat-overlay')).toBeVisible({ timeout: 15000 });

    const fleeDone = page.waitForResponse(
      (resp) => resp.url().includes('/api/game/combat/flee') && resp.ok()
    );
    await page.keyboard.press('f');
    await fleeDone;

    await expect(page.locator('.dungeon-container')).toBeVisible();
  });
});
