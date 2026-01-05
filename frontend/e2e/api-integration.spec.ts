import { test, expect } from '@playwright/test';

const API_URL = process.env.API_URL || 'http://localhost:8000';

test.describe('API Integration', () => {
  test('backend health check', async ({ request }) => {
    const response = await request.get(`${API_URL}/health`);
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data.status).toBe('healthy');
  });

  test('create new game via API', async ({ request }) => {
    const response = await request.post(`${API_URL}/api/game/new`, {
      data: { player_name: 'E2E Tester' }
    });
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data.success).toBe(true);
    expect(data.state).toBeDefined();
    expect(data.state.player).toBeDefined();
    expect(data.state.room).toBeDefined();
  });

  test('get game state via API', async ({ request }) => {
    // First start a new game
    await request.post(`${API_URL}/api/game/new`, {
      data: { player_name: 'E2E Tester' }
    });

    // Then get state
    const response = await request.get(`${API_URL}/api/game/state`);
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data.player).toBeDefined();
    expect(data.room).toBeDefined();
    expect(data.inventory).toBeDefined();
    expect(data.position).toBeDefined();
  });

  test('movement via API', async ({ request }) => {
    // Start new game
    await request.post(`${API_URL}/api/game/new`, {
      data: { player_name: 'E2E Tester' }
    });

    // Try to move
    const response = await request.post(`${API_URL}/api/game/move`, {
      data: { direction: 'north' }
    });
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data.message).toBeDefined();
    expect(data.state).toBeDefined();
  });

  test('API returns audio intents', async ({ request }) => {
    // Start new game
    const newGameResponse = await request.post(`${API_URL}/api/game/new`, {
      data: { player_name: 'E2E Tester' }
    });
    expect(newGameResponse.ok()).toBeTruthy();

    const data = await newGameResponse.json();

    // Check audio intent is present
    expect(data.audio).toBeDefined();
    expect(data.audio.primary).toBeDefined();
    expect(data.audio.primary.onomatopoeia).toBeDefined();
    expect(data.audio.primary.event_type).toBeDefined();
  });

  test('inventory API', async ({ request }) => {
    // Start new game
    await request.post(`${API_URL}/api/game/new`, {
      data: { player_name: 'E2E Tester' }
    });

    // Get inventory
    const response = await request.get(`${API_URL}/api/game/inventory`);
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data.inventory).toBeDefined();
    expect(Array.isArray(data.inventory)).toBe(true);
    expect(data.gold).toBeDefined();
  });

  test('attack API when not in combat', async ({ request }) => {
    // Start new game
    await request.post(`${API_URL}/api/game/new`, {
      data: { player_name: 'E2E Tester' }
    });

    // Try to attack (should respond gracefully)
    const response = await request.post(`${API_URL}/api/game/combat/attack`);
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data.message).toBeDefined();
  });

  test('flee API when not in combat', async ({ request }) => {
    // Start new game
    await request.post(`${API_URL}/api/game/new`, {
      data: { player_name: 'E2E Tester' }
    });

    // Try to flee (should respond gracefully)
    const response = await request.post(`${API_URL}/api/game/combat/flee`);
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data.message).toBeDefined();
  });

  test('save and load game', async ({ request }) => {
    // Start new game
    await request.post(`${API_URL}/api/game/new`, {
      data: { player_name: 'E2E Tester' }
    });

    // Move to change state
    await request.post(`${API_URL}/api/game/move`, {
      data: { direction: 'east' }
    });

    // Save game
    const saveResponse = await request.post(`${API_URL}/api/game/save`);
    expect(saveResponse.ok()).toBeTruthy();

    // Load game
    const loadResponse = await request.post(`${API_URL}/api/game/load`);
    expect(loadResponse.ok()).toBeTruthy();

    const data = await loadResponse.json();
    expect(data.success).toBe(true);
    expect(data.state).toBeDefined();
  });

  test('use item API', async ({ request }) => {
    // Start new game
    await request.post(`${API_URL}/api/game/new`, {
      data: { player_name: 'E2E Tester' }
    });

    // Try to use a healing potion
    const response = await request.post(`${API_URL}/api/game/use`, {
      data: { item_id: 'healing_potion' }
    });
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data.message).toBeDefined();
    // May succeed or fail depending on if player has the item
  });

  test('full API game flow', async ({ request }) => {
    // 1. Create new game
    const newGame = await request.post(`${API_URL}/api/game/new`, {
      data: { player_name: 'Full Flow Test' }
    });
    expect(newGame.ok()).toBeTruthy();
    const newGameData = await newGame.json();
    expect(newGameData.success).toBe(true);

    // 2. Get initial state
    const state1 = await request.get(`${API_URL}/api/game/state`);
    expect(state1.ok()).toBeTruthy();

    // 3. Move around
    const directions = ['north', 'east', 'south', 'west'];
    for (const dir of directions) {
      const moveResp = await request.post(`${API_URL}/api/game/move`, {
        data: { direction: dir }
      });
      expect(moveResp.ok()).toBeTruthy();
    }

    // 4. Check inventory
    const inv = await request.get(`${API_URL}/api/game/inventory`);
    expect(inv.ok()).toBeTruthy();

    // 5. Get final state
    const finalState = await request.get(`${API_URL}/api/game/state`);
    expect(finalState.ok()).toBeTruthy();

    // 6. Save game
    const save = await request.post(`${API_URL}/api/game/save`);
    expect(save.ok()).toBeTruthy();
  });
});
