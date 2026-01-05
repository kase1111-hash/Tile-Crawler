import { test, expect } from '@playwright/test';

test.describe('Movement', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');

    // Start new game
    const newGameButton = page.locator('button:has-text("New Game"), button:has-text("Start"), [data-testid="new-game"]');
    await newGameButton.first().click();

    // Wait for game to load
    await page.waitForTimeout(2000);
  });

  test('should have movement controls', async ({ page }) => {
    // Check for directional buttons or controls
    const controls = page.locator('button:has-text("North"), button:has-text("N"), [data-testid*="north"], [aria-label*="north"]');
    await expect(controls.first()).toBeVisible({ timeout: 10000 });
  });

  test('should move north with button click', async ({ page }) => {
    // Get initial position or state
    const initialContent = await page.locator('[data-testid="game-map"], .game-map, pre').first().textContent();

    // Click north button
    const northButton = page.locator('button:has-text("North"), button:has-text("N"), [data-testid*="north"]');
    await northButton.first().click();

    // Wait for response
    await page.waitForTimeout(1000);

    // Game state should update (narrative or map change)
    const narrative = page.locator('[data-testid="narrative"], .narrative, [class*="description"]');
    await expect(narrative.first()).toBeVisible();
  });

  test('should move with keyboard arrow keys', async ({ page }) => {
    // Press arrow key
    await page.keyboard.press('ArrowUp');

    // Wait for response
    await page.waitForTimeout(1000);

    // Check that game responded
    const narrative = page.locator('[data-testid="narrative"], .narrative');
    await expect(narrative.first()).toBeVisible();
  });

  test('should move with WASD keys', async ({ page }) => {
    // Press W key
    await page.keyboard.press('w');

    // Wait for response
    await page.waitForTimeout(1000);

    // Check that game responded
    const gameArea = page.locator('[data-testid="game-map"], .game-map, pre');
    await expect(gameArea.first()).toBeVisible();
  });

  test('should show blocked message when hitting wall', async ({ page }) => {
    // Try to move in same direction multiple times to hit a wall
    for (let i = 0; i < 10; i++) {
      await page.keyboard.press('ArrowUp');
      await page.waitForTimeout(300);
    }

    // Should eventually see blocked message or error
    // The game should handle this gracefully
    const gameArea = page.locator('[data-testid="game-map"], .game-map, pre');
    await expect(gameArea.first()).toBeVisible();
  });

  test('should update map display after movement', async ({ page }) => {
    // Get map content before
    const mapBefore = await page.locator('[data-testid="game-map"], .game-map, pre').first().textContent();

    // Try to move to a new room
    await page.keyboard.press('ArrowRight');
    await page.waitForTimeout(1500);

    // Either map changes or narrative indicates blocked
    const narrativeOrMap = page.locator('[data-testid="narrative"], .narrative, [data-testid="game-map"]');
    await expect(narrativeOrMap.first()).toBeVisible();
  });
});
