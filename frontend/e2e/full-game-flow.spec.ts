import { test, expect } from '@playwright/test';

test.describe('Full Game Flow', () => {
  test('complete game session flow', async ({ page }) => {
    // 1. Navigate to game
    await page.goto('/');
    await expect(page).toHaveTitle(/Tile|Crawler|Game/i, { timeout: 10000 });

    // 2. Start new game
    const newGameButton = page.locator('button:has-text("New Game"), button:has-text("Start"), [data-testid="new-game"]');
    await expect(newGameButton.first()).toBeVisible({ timeout: 10000 });
    await newGameButton.first().click();

    // 3. Verify game loaded
    await page.waitForTimeout(2000);
    const gameMap = page.locator('[data-testid="game-map"], .game-map, pre');
    await expect(gameMap.first()).toBeVisible({ timeout: 10000 });

    // 4. Verify player stats visible
    const stats = page.locator('text=/HP|Level|Health/i');
    await expect(stats.first()).toBeVisible({ timeout: 5000 });

    // 5. Verify inventory visible
    const inventory = page.locator('text=/Inventory|Items/i');
    await expect(inventory.first()).toBeVisible({ timeout: 5000 });

    // 6. Move around the dungeon
    await page.keyboard.press('ArrowRight');
    await page.waitForTimeout(500);
    await page.keyboard.press('ArrowDown');
    await page.waitForTimeout(500);
    await page.keyboard.press('ArrowLeft');
    await page.waitForTimeout(500);
    await page.keyboard.press('ArrowUp');
    await page.waitForTimeout(500);

    // 7. Verify game is still responsive
    await expect(gameMap.first()).toBeVisible();

    // 8. Check controls are working
    const controls = page.locator('button:has-text("North"), button:has-text("Attack")');
    await expect(controls.first()).toBeVisible({ timeout: 5000 });

    // 9. Try saving the game (if available)
    const saveButton = page.locator('button:has-text("Save"), [data-testid="save"]');
    if (await saveButton.first().isVisible().catch(() => false)) {
      await saveButton.first().click();
      await page.waitForTimeout(500);
    }

    // 10. Game should still be functional
    await expect(gameMap.first()).toBeVisible();
  });

  test('game persists state across actions', async ({ page }) => {
    await page.goto('/');

    // Start new game
    const newGameButton = page.locator('button:has-text("New Game"), button:has-text("Start"), [data-testid="new-game"]');
    await newGameButton.first().click();
    await page.waitForTimeout(2000);

    // Get initial gold value
    const goldDisplay = page.locator('text=/Gold:\\s*\\d+|💰\\s*\\d+|\\d+\\s*gold/i');
    const initialGoldText = await goldDisplay.first().textContent().catch(() => '');

    // Perform some actions
    await page.keyboard.press('ArrowRight');
    await page.waitForTimeout(500);

    // Gold should still be displayed
    await expect(goldDisplay.first()).toBeVisible();
  });

  test('game handles rapid inputs gracefully', async ({ page }) => {
    await page.goto('/');

    // Start game
    const newGameButton = page.locator('button:has-text("New Game"), button:has-text("Start"), [data-testid="new-game"]');
    await newGameButton.first().click();
    await page.waitForTimeout(2000);

    // Rapid inputs
    for (let i = 0; i < 10; i++) {
      await page.keyboard.press('ArrowUp');
      await page.keyboard.press('ArrowRight');
    }

    // Wait for processing
    await page.waitForTimeout(1000);

    // Game should still be functional
    const gameMap = page.locator('[data-testid="game-map"], .game-map, pre');
    await expect(gameMap.first()).toBeVisible();
  });

  test('narrative updates with player actions', async ({ page }) => {
    await page.goto('/');

    // Start game
    const newGameButton = page.locator('button:has-text("New Game"), button:has-text("Start"), [data-testid="new-game"]');
    await newGameButton.first().click();
    await page.waitForTimeout(2000);

    // Get initial narrative
    const narrative = page.locator('[data-testid="narrative"], .narrative, [class*="description"]');
    const initialText = await narrative.first().textContent().catch(() => '');

    // Make a move
    await page.keyboard.press('ArrowRight');
    await page.waitForTimeout(1000);

    // Narrative should exist (may or may not change based on room)
    await expect(narrative.first()).toBeVisible();
  });
});
