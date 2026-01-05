// WebSocket service for real-time game updates

import type { GameState, Direction, DialogueData, AudioBatch } from '../types/game';

// Message types from server
export interface WebSocketMessage {
  type: 'connected' | 'game_update' | 'error' | 'ping';
  message?: string;
  state?: GameState;
  event?: string;
  timestamp?: string;
  data?: {
    state: GameState;
    narrative?: string;
    audio?: AudioBatch;
    combat?: Record<string, unknown>;
    dialogue?: DialogueData;
  };
}

// Action messages to server
export type WebSocketAction =
  | { action: 'move'; direction: Direction }
  | { action: 'attack' }
  | { action: 'flee' }
  | { action: 'take'; item_id: string }
  | { action: 'use'; item_id: string }
  | { action: 'talk'; message?: string }
  | { action: 'rest' }
  | { action: 'new_game'; player_name?: string }
  | { type: 'pong' };

export interface WebSocketOptions {
  onStateUpdate?: (state: GameState, narrative?: string, audio?: AudioBatch, dialogue?: DialogueData) => void;
  onError?: (message: string) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  autoReconnect?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}

class GameWebSocket {
  private ws: WebSocket | null = null;
  private playerId: string;
  private options: WebSocketOptions;
  private reconnectAttempts = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private pingTimer: ReturnType<typeof setInterval> | null = null;
  private isConnecting = false;

  constructor(playerId: string, options: WebSocketOptions = {}) {
    this.playerId = playerId;
    this.options = {
      autoReconnect: true,
      reconnectInterval: 3000,
      maxReconnectAttempts: 5,
      ...options,
    };
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  connect(): void {
    if (this.isConnecting || this.isConnected) {
      return;
    }

    this.isConnecting = true;

    // Determine WebSocket URL based on current location
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/ws/${this.playerId}`;

    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        this.isConnecting = false;
        this.reconnectAttempts = 0;
        this.startPingTimer();
        this.options.onConnect?.();
      };

      this.ws.onclose = () => {
        this.isConnecting = false;
        this.stopPingTimer();
        this.options.onDisconnect?.();

        if (this.options.autoReconnect && this.reconnectAttempts < (this.options.maxReconnectAttempts || 5)) {
          this.scheduleReconnect();
        }
      };

      this.ws.onerror = () => {
        this.isConnecting = false;
        this.options.onError?.('WebSocket connection error');
      };

      this.ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          this.handleMessage(message);
        } catch {
          console.error('Failed to parse WebSocket message');
        }
      };
    } catch (error) {
      this.isConnecting = false;
      this.options.onError?.(`Failed to connect: ${error}`);
    }
  }

  disconnect(): void {
    this.options.autoReconnect = false;
    this.stopPingTimer();
    this.cancelReconnect();

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  private handleMessage(message: WebSocketMessage): void {
    switch (message.type) {
      case 'connected':
        if (message.state) {
          this.options.onStateUpdate?.(message.state);
        }
        break;

      case 'game_update':
        if (message.data?.state) {
          this.options.onStateUpdate?.(
            message.data.state,
            message.data.narrative,
            message.data.audio,
            message.data.dialogue
          );
        }
        break;

      case 'error':
        this.options.onError?.(message.message || 'Unknown error');
        break;

      case 'ping':
        this.sendPong();
        break;
    }
  }

  private sendPong(): void {
    this.send({ type: 'pong' });
  }

  private startPingTimer(): void {
    // Send ping every 30 seconds to keep connection alive
    this.pingTimer = setInterval(() => {
      if (this.isConnected) {
        // Server will send pings, we just respond with pongs
      }
    }, 30000);
  }

  private stopPingTimer(): void {
    if (this.pingTimer) {
      clearInterval(this.pingTimer);
      this.pingTimer = null;
    }
  }

  private scheduleReconnect(): void {
    this.cancelReconnect();
    this.reconnectAttempts++;

    const delay = this.options.reconnectInterval || 3000;
    this.reconnectTimer = setTimeout(() => {
      this.connect();
    }, delay);
  }

  private cancelReconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  send(action: WebSocketAction): boolean {
    if (!this.isConnected) {
      this.options.onError?.('Not connected');
      return false;
    }

    try {
      this.ws!.send(JSON.stringify(action));
      return true;
    } catch {
      this.options.onError?.('Failed to send message');
      return false;
    }
  }

  // Game actions
  move(direction: Direction): boolean {
    return this.send({ action: 'move', direction });
  }

  attack(): boolean {
    return this.send({ action: 'attack' });
  }

  flee(): boolean {
    return this.send({ action: 'flee' });
  }

  takeItem(itemId: string): boolean {
    return this.send({ action: 'take', item_id: itemId });
  }

  useItem(itemId: string): boolean {
    return this.send({ action: 'use', item_id: itemId });
  }

  talk(message?: string): boolean {
    return this.send({ action: 'talk', message });
  }

  rest(): boolean {
    return this.send({ action: 'rest' });
  }

  newGame(playerName?: string): boolean {
    return this.send({ action: 'new_game', player_name: playerName });
  }
}

// Factory function to create WebSocket connection
export function createGameWebSocket(playerId: string, options?: WebSocketOptions): GameWebSocket {
  return new GameWebSocket(playerId, options);
}

// Generate a unique player ID
export function generatePlayerId(): string {
  return `player_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

export { GameWebSocket };
