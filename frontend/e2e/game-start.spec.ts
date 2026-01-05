import { test, expect } from '@playwright/test';

test.describe('Game Start', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should display the game title', async ({ page }) => {
    // Check for game title or header
    await expect(page.locator('text=Tile-Crawler')).toBeVisible({ timeout: 10000 });
  });

  test('should show new game button or menu', async ({ page }) => {
    // Look for new game option
    const newGameButton = page.locator('button:has-text("New Game"), button:has-text("Start"), [data-testid="new-game"]');
    await expect(newGameButton.first()).toBeVisible({ timeout: 10000 });
  });

  test('should start a new game', async ({ page }) => {
    // Click new game
    const newGameButton = page.locator('button:has-text("New Game"), button:has-text("Start"), [data-testid="new-game"]');
    await newGameButton.first().click();

    // Wait for game to load - should see map or game content
    await expect(page.locator('[data-testid="game-map"], .game-map, pre')).toBeVisible({ timeout: 15000 });
  });

  test('should display player stats after starting', async ({ page }) => {
    // Start new game
    const newGameButton = page.locator('button:has-text("New Game"), button:has-text("Start"), [data-testid="new-game"]');
    await newGameButton.first().click();

    // Wait for game to load
    await page.waitForTimeout(2000);

    // Check for player stats - HP, Level, etc.
    const statsArea = page.locator('text=/HP|Health|Level/i');
    await expect(statsArea.first()).toBeVisible({ timeout: 10000 });
  });

  test('should display room description', async ({ page }) => {
    // Start new game
    const newGameButton = page.locator('button:has-text("New Game"), button:has-text("Start"), [data-testid="new-game"]');
    await newGameButton.first().click();

    // Wait for game content
    await page.waitForTimeout(2000);

    // Should have some narrative/description text
    const narrative = page.locator('[data-testid="narrative"], .narrative, [class*="description"]');
    await expect(narrative.first()).toBeVisible({ timeout: 10000 });
  });
});
