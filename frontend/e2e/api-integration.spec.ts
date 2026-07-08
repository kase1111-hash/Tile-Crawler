import { test, expect, type APIRequestContext } from '@playwright/test';

const API_URL = process.env.API_URL || 'http://localhost:8000';

const CARDINALS = ['north', 'south', 'east', 'west'];

async function getState(request: APIRequestContext) {
  const response = await request.get(`${API_URL}/api/game/state`);
  expect(response.ok()).toBeTruthy();
  return response.json();
}

/** Resolve any active combat so movement/attack expectations are deterministic. */
async function ensureNotInCombat(request: APIRequestContext) {
  for (let i = 0; i < 30; i++) {
    const state = await getState(request);
    if (state.player.hp.startsWith('0/')) {
      await request.post(`${API_URL}/api/game/new`, { data: { player_name: 'E2E Tester' } });
      continue;
    }
    if (!state.combat?.in_combat) return state;
    await request.post(`${API_URL}/api/game/combat/attack`);
  }
  throw new Error('could not resolve combat within 30 rounds');
}

test.describe('API Integration', () => {
  test('backend health check', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/health`);
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
    await request.post(`${API_URL}/api/game/new`, {
      data: { player_name: 'E2E Tester' }
    });

    const data = await getState(request);
    expect(data.player).toBeDefined();
    expect(data.room).toBeDefined();
    expect(data.inventory).toBeDefined();
    expect(data.position).toBeDefined();
  });

  test('movement follows the advertised exits', async ({ request }) => {
    await request.post(`${API_URL}/api/game/new`, {
      data: { player_name: 'E2E Tester' }
    });
    const state = await ensureNotInCombat(request);

    const open = CARDINALS.filter((d) => state.room.exits[d]);
    const closed = CARDINALS.filter((d) => !state.room.exits[d]);
    expect(open.length).toBeGreaterThan(0);

    // A closed direction is rejected with a structured error
    if (closed.length > 0) {
      const blocked = await request.post(`${API_URL}/api/game/move`, {
        data: { direction: closed[0] }
      });
      expect(blocked.status()).toBe(400);
      const err = await blocked.json();
      expect(err.error_type).toBe('NoExitError');
    }

    // An open direction succeeds
    const moved = await request.post(`${API_URL}/api/game/move`, {
      data: { direction: open[0] }
    });
    expect(moved.ok()).toBeTruthy();
    const data = await moved.json();
    expect(data.success).toBe(true);
    expect(data.state).toBeDefined();
  });

  test('inventory API', async ({ request }) => {
    await request.post(`${API_URL}/api/game/new`, {
      data: { player_name: 'E2E Tester' }
    });

    const response = await request.get(`${API_URL}/api/game/inventory`);
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data.inventory).toBeDefined();
    expect(Array.isArray(data.inventory)).toBe(true);
    expect(data.gold).toBeDefined();
  });

  test('attack outside combat is rejected with a structured error', async ({ request }) => {
    await request.post(`${API_URL}/api/game/new`, {
      data: { player_name: 'E2E Tester' }
    });
    await ensureNotInCombat(request);

    const response = await request.post(`${API_URL}/api/game/combat/attack`);
    expect(response.status()).toBe(400);

    const data = await response.json();
    expect(data.error_type).toBe('NotInCombatError');
    expect(data.detail).toBeDefined();
  });

  test('flee outside combat is rejected with a structured error', async ({ request }) => {
    await request.post(`${API_URL}/api/game/new`, {
      data: { player_name: 'E2E Tester' }
    });
    await ensureNotInCombat(request);

    const response = await request.post(`${API_URL}/api/game/combat/flee`);
    expect(response.status()).toBe(400);

    const data = await response.json();
    expect(data.error_type).toBeDefined();
    expect(data.detail).toBeDefined();
  });

  test('save and load game', async ({ request }) => {
    await request.post(`${API_URL}/api/game/new`, {
      data: { player_name: 'E2E Tester' }
    });

    // Move somewhere legal so the save has non-initial state
    const state = await ensureNotInCombat(request);
    const open = CARDINALS.filter((d) => state.room.exits[d]);
    if (open.length > 0) {
      await request.post(`${API_URL}/api/game/move`, { data: { direction: open[0] } });
    }

    const saveResponse = await request.post(`${API_URL}/api/game/save`);
    expect(saveResponse.ok()).toBeTruthy();

    const loadResponse = await request.post(`${API_URL}/api/game/load`);
    expect(loadResponse.ok()).toBeTruthy();

    const data = await loadResponse.json();
    expect(data.success).toBe(true);
    expect(data.state).toBeDefined();
  });

  test('use item API', async ({ request }) => {
    await request.post(`${API_URL}/api/game/new`, {
      data: { player_name: 'E2E Tester' }
    });

    // New games start with a healing potion
    const response = await request.post(`${API_URL}/api/game/use`, {
      data: { item_id: 'healing_potion' }
    });
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data.message).toBeDefined();
  });

  test('full API game flow', async ({ request }) => {
    // 1. Create new game
    const newGame = await request.post(`${API_URL}/api/game/new`, {
      data: { player_name: 'Full Flow Test' }
    });
    expect(newGame.ok()).toBeTruthy();
    const newGameData = await newGame.json();
    expect(newGameData.success).toBe(true);

    // 2. Walk through several rooms, always following the advertised exits
    for (let step = 0; step < 4; step++) {
      const state = await getState(request);
      if (state.combat?.in_combat) break;
      const open = CARDINALS.filter((d) => state.room.exits[d]);
      expect(open.length).toBeGreaterThan(0);
      const moveResp = await request.post(`${API_URL}/api/game/move`, {
        data: { direction: open[step % open.length] }
      });
      expect(moveResp.ok()).toBeTruthy();
    }

    // 3. Check inventory
    const inv = await request.get(`${API_URL}/api/game/inventory`);
    expect(inv.ok()).toBeTruthy();

    // 4. Get final state
    await getState(request);

    // 5. Save game
    const save = await request.post(`${API_URL}/api/game/save`);
    expect(save.ok()).toBeTruthy();
  });
});
