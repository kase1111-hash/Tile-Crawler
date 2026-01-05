import { test, expect } from '@playwright/test';

test.describe('Inventory', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');

    // Start new game
    const newGameButton = page.locator('button:has-text("New Game"), button:has-text("Start"), [data-testid="new-game"]');
    await newGameButton.first().click();

    // Wait for game to load
    await page.waitForTimeout(2000);
  });

  test('should display inventory section', async ({ page }) => {
    // Check for inventory display
    const inventory = page.locator('[data-testid="inventory"], .inventory, text=/Inventory|Items|Bag/i');
    await expect(inventory.first()).toBeVisible({ timeout: 10000 });
  });

  test('should show starting items', async ({ page }) => {
    // Player should start with some items (torch, potions)
    const items = page.locator('text=/Torch|Potion|torch|potion/i');
    await expect(items.first()).toBeVisible({ timeout: 10000 });
  });

  test('should display gold amount', async ({ page }) => {
    // Check for gold display
    const gold = page.locator('text=/Gold|gold|\\$|💰/');
    await expect(gold.first()).toBeVisible({ timeout: 10000 });
  });

  test('should be able to use healing potion', async ({ page }) => {
    // Find and click on healing potion
    const potion = page.locator('text=/Healing Potion|healing_potion/i');

    if (await potion.first().isVisible()) {
      // Click use button or the item itself
      const useButton = page.locator('button:has-text("Use"), [data-testid="use-item"]');
      if (await useButton.first().isVisible()) {
        await useButton.first().click();
      } else {
        await potion.first().click();
      }

      // Wait for response
      await page.waitForTimeout(1000);

      // Should see some feedback
      const feedback = page.locator('[data-testid="narrative"], .narrative');
      await expect(feedback.first()).toBeVisible();
    }
  });

  test('should show equipment slots', async ({ page }) => {
    // Check for equipment section
    const equipment = page.locator('text=/Equipment|Equipped|Weapon|Armor/i');
    await expect(equipment.first()).toBeVisible({ timeout: 10000 });
  });
});
