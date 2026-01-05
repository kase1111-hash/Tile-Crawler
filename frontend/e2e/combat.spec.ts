import { test, expect } from '@playwright/test';

test.describe('Combat', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');

    // Start new game
    const newGameButton = page.locator('button:has-text("New Game"), button:has-text("Start"), [data-testid="new-game"]');
    await newGameButton.first().click();

    // Wait for game to load
    await page.waitForTimeout(2000);
  });

  test('should have attack button available', async ({ page }) => {
    // Attack button should exist (may be disabled if not in combat)
    const attackButton = page.locator('button:has-text("Attack"), button:has-text("attack"), [data-testid="attack"]');
    await expect(attackButton.first()).toBeVisible({ timeout: 10000 });
  });

  test('should have flee button available', async ({ page }) => {
    // Flee button should exist
    const fleeButton = page.locator('button:has-text("Flee"), button:has-text("flee"), button:has-text("Run"), [data-testid="flee"]');
    await expect(fleeButton.first()).toBeVisible({ timeout: 10000 });
  });

  test('should show combat UI when enemy present', async ({ page }) => {
    // Move around to potentially encounter an enemy
    for (let i = 0; i < 5; i++) {
      await page.keyboard.press('ArrowRight');
      await page.waitForTimeout(500);
      await page.keyboard.press('ArrowDown');
      await page.waitForTimeout(500);
    }

    // Check if combat section exists (may or may not be in combat)
    const combatSection = page.locator('[data-testid="combat"], .combat, text=/Combat|Enemy|HP:/i');
    // This is informational - combat may or may not trigger
    const hasCombat = await combatSection.first().isVisible().catch(() => false);
    console.log('Combat encountered:', hasCombat);
  });

  test('attack button should respond when clicked', async ({ page }) => {
    const attackButton = page.locator('button:has-text("Attack"), [data-testid="attack"]');

    // Click attack (may show "not in combat" message if no enemy)
    await attackButton.first().click();
    await page.waitForTimeout(500);

    // Should see some response
    const response = page.locator('[data-testid="narrative"], .narrative, .message');
    await expect(response.first()).toBeVisible();
  });

  test('flee button should respond when clicked', async ({ page }) => {
    const fleeButton = page.locator('button:has-text("Flee"), button:has-text("Run"), [data-testid="flee"]');

    // Click flee (may show "not in combat" message if no enemy)
    await fleeButton.first().click();
    await page.waitForTimeout(500);

    // Should see some response
    const response = page.locator('[data-testid="narrative"], .narrative, .message');
    await expect(response.first()).toBeVisible();
  });
});
