import { test, expect } from '@playwright/test';
import { startGame } from './helpers';

test.describe('Game Start', () => {
  test('should have the game title in the page', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle(/Tile-Crawler/i);
  });

  test('should reach a running game from a cold load', async ({ page }) => {
    await startGame(page);
    await expect(page.locator('.dungeon-container')).toBeVisible();
    await expect(page.locator('.view-3d')).toBeVisible();
  });

  test('should display player stats in the HUD', async ({ page }) => {
    await startGame(page);
    await expect(page.locator('.stat-bar-row', { hasText: 'HP' })).toBeVisible();
    await expect(page.locator('.stat-bar-row', { hasText: 'MP' })).toBeVisible();
    await expect(page.locator('.stat-level')).toContainText(/Level \d+/);
    await expect(page.locator('.stat-gold')).toContainText(/Gold: \d+/);
  });

  test('should display the exits panel', async ({ page }) => {
    await startGame(page);
    await expect(page.locator('.exits-block .block-title')).toHaveText('EXITS');
    await expect(page.locator('.exit-dir')).toHaveCount(4);
  });

  test('should display room description or narrative', async ({ page }) => {
    await startGame(page);
    const message = page.locator('.message-text');
    await expect(message).toBeVisible();
    await expect(message).not.toHaveText('');
  });

  test('should display the controls hint', async ({ page }) => {
    await startGame(page);
    await expect(page.locator('.controls-hint')).toContainText('[WASD] Move');
  });
});
