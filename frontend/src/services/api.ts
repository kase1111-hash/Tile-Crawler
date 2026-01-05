// API service for Tile-Crawler backend

import type { ActionResponse, GameState, Direction } from '../types/game';

const API_BASE = '/api';

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;

  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new ApiError(response.status, error.detail || 'Request failed');
  }

  return response.json();
}

export const api = {
  // Health check
  async health(): Promise<{ status: string; llm_available: boolean; version: string }> {
    return request('/health');
  },

  // Game management
  async newGame(playerName: string = 'Adventurer'): Promise<ActionResponse> {
    return request('/game/new', {
      method: 'POST',
      body: JSON.stringify({ player_name: playerName }),
    });
  },

  async getState(): Promise<GameState> {
    return request('/game/state');
  },

  async saveGame(): Promise<{ success: boolean; message: string }> {
    return request('/game/save', { method: 'POST' });
  },

  async loadGame(): Promise<{ success: boolean; message: string; state: GameState }> {
    return request('/game/load', { method: 'POST' });
  },

  // Movement
  async move(direction: Direction): Promise<ActionResponse> {
    return request('/game/move', {
      method: 'POST',
      body: JSON.stringify({ direction }),
    });
  },

  // Combat
  async attack(): Promise<ActionResponse> {
    return request('/game/combat/attack', { method: 'POST' });
  },

  async flee(): Promise<ActionResponse> {
    return request('/game/combat/flee', { method: 'POST' });
  },

  // Inventory
  async takeItem(itemId: string): Promise<ActionResponse> {
    return request('/game/take', {
      method: 'POST',
      body: JSON.stringify({ item_id: itemId }),
    });
  },

  async useItem(itemId: string): Promise<ActionResponse> {
    return request('/game/use', {
      method: 'POST',
      body: JSON.stringify({ item_id: itemId }),
    });
  },

  async getInventory(): Promise<{ inventory: GameState['inventory']; gold: number }> {
    return request('/game/inventory');
  },

  // Interaction
  async talk(message: string = ''): Promise<ActionResponse> {
    return request('/game/talk', {
      method: 'POST',
      body: JSON.stringify({ message }),
    });
  },

  async rest(): Promise<ActionResponse> {
    return request('/game/rest', { method: 'POST' });
  },
};

export { ApiError };
