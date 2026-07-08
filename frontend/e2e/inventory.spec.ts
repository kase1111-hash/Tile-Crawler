import { test, expect } from '@playwright/test';
import { freshGame } from './helpers';

test.describe('Inventory', () => {
  test.beforeEach(async ({ page }) => {
    await freshGame(page);
  });

  test('I opens and Escape closes the inventory overlay', async ({ page }) => {
    await page.keyboard.press('i');
    const overlay = page.locator('.inventory-box');
    await expect(overlay).toBeVisible();
    await expect(overlay.locator('.inv-header')).toContainText('INVENTORY');

    await page.keyboard.press('Escape');
    await expect(overlay).not.toBeVisible();
  });

  test('shows starting items', async ({ page }) => {
    await page.keyboard.press('i');
    const items = page.locator('.inv-item');
    await expect(items.filter({ hasText: 'Torch' }).first()).toBeVisible();
    await expect(items.filter({ hasText: 'Healing Potion' }).first()).toBeVisible();
  });

  test('displays gold in the HUD', async ({ page }) => {
    await expect(page.locator('.stat-gold')).toContainText(/Gold: \d+/);
  });

  test('can select and use an item from the overlay', async ({ page }) => {
    await page.keyboard.press('i');
    await expect(page.locator('.inventory-box')).toBeVisible();

    // Move the selection down to the second item, then use it
    await page.keyboard.press('ArrowDown');
    const useDone = page.waitForResponse(
      (resp) => resp.url().includes('/api/game/use') && resp.ok()
    );
    await page.keyboard.press('Enter');
    await useDone;

    // The game must stay functional after using an item
    await expect(page.locator('.dungeon-container')).toBeVisible();
  });
});
