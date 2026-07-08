// Custom hook for game state management

import { useState, useCallback, useEffect, useRef } from 'react';
import { api } from '../services/api';
import type { GameState, ActionResponse, Direction, DialogueData } from '../types/game';

export interface DeathData {
  message: string;
  narrative: string;
}

interface UseGameReturn {
  // State
  gameState: GameState | null;
  isLoading: boolean;
  error: string | null;
  narrative: string;
  dialogueData: DialogueData | null;
  deathData: DeathData | null;

  // Actions
  newGame: (playerName?: string) => Promise<void>;
  loadGame: () => Promise<void>;
  saveGame: () => Promise<void>;
  move: (direction: Direction) => Promise<void>;
  attack: () => Promise<void>;
  flee: () => Promise<void>;
  takeItem: (itemId: string) => Promise<void>;
  useItem: (itemId: string) => Promise<void>;
  talk: (message?: string) => Promise<void>;
  rest: () => Promise<void>;
  clearError: () => void;
  clearDialogue: () => void;
  clearDeath: () => void;
}

export function useGame(): UseGameReturn {
  const [gameState, setGameState] = useState<GameState | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [narrative, setNarrative] = useState<string>('');
  const [dialogueData, setDialogueData] = useState<DialogueData | null>(null);
  const [deathData, setDeathData] = useState<DeathData | null>(null);
  const prefetchRef = useRef<AbortController | null>(null);

  // Prefetch adjacent rooms in background (silent, doesn't affect UI)
  const prefetchRooms = useCallback(() => {
    // Cancel any existing prefetch
    if (prefetchRef.current) {
      prefetchRef.current.abort();
    }
    prefetchRef.current = new AbortController();

    // Fire and forget - don't await, don't affect UI
    api.prefetch().catch(() => {
      // Silently ignore prefetch errors
    });
  }, []);

  // Helper to handle API responses
  const handleResponse = useCallback((response: ActionResponse, shouldPrefetch: boolean = false) => {
    if (response.narrative) {
      setNarrative(response.narrative);
    }
    if (response.state) {
      setGameState(response.state);
    }
    if (response.dialogue) {
      setDialogueData(response.dialogue);
    }
    if (response.defeat) {
      // Death gets its own overlay instead of the error bar
      setDeathData({ message: response.message, narrative: response.narrative });
    } else if (!response.success && response.message) {
      setError(response.message);
    }

    // Prefetch adjacent rooms in background if requested
    if (shouldPrefetch && response.success) {
      prefetchRooms();
    }
  }, [prefetchRooms]);

  // Wrap API calls with loading state
  const withLoading = useCallback(
    async <T>(fn: () => Promise<T>): Promise<T | null> => {
      setIsLoading(true);
      setError(null);
      try {
        const result = await fn();
        return result;
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An error occurred');
        return null;
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  // Game actions
  const newGame = useCallback(
    async (playerName: string = 'Adventurer') => {
      const response = await withLoading(() => api.newGame(playerName));
      if (response) {
        handleResponse(response, true); // Prefetch after new game
        setDialogueData(null);
      }
    },
    [withLoading, handleResponse]
  );

  const loadGame = useCallback(async () => {
    const response = await withLoading(() => api.loadGame());
    if (response && response.state) {
      setGameState(response.state);
      setNarrative('Game loaded. Your adventure continues...');
      prefetchRooms(); // Prefetch after load
    }
  }, [withLoading, prefetchRooms]);

  const saveGame = useCallback(async () => {
    const response = await withLoading(() => api.saveGame());
    if (response?.success) {
      setNarrative('Game saved successfully.');
    }
  }, [withLoading]);

  const move = useCallback(
    async (direction: Direction) => {
      const response = await withLoading(() => api.move(direction));
      if (response) {
        handleResponse(response, true); // Prefetch after move
        setDialogueData(null);
      }
    },
    [withLoading, handleResponse]
  );

  const attack = useCallback(async () => {
    const response = await withLoading(() => api.attack());
    if (response) {
      handleResponse(response);
    }
  }, [withLoading, handleResponse]);

  const flee = useCallback(async () => {
    const response = await withLoading(() => api.flee());
    if (response) {
      handleResponse(response, true); // Prefetch after flee (might be in new room)
    }
  }, [withLoading, handleResponse]);

  const takeItem = useCallback(
    async (itemId: string) => {
      const response = await withLoading(() => api.takeItem(itemId));
      if (response) {
        handleResponse(response);
      }
    },
    [withLoading, handleResponse]
  );

  const useItem = useCallback(
    async (itemId: string) => {
      const response = await withLoading(() => api.useItem(itemId));
      if (response) {
        handleResponse(response);
      }
    },
    [withLoading, handleResponse]
  );

  const talk = useCallback(
    async (message?: string) => {
      const response = await withLoading(() => api.talk(message || ''));
      if (response) {
        handleResponse(response);
      }
    },
    [withLoading, handleResponse]
  );

  const rest = useCallback(async () => {
    const response = await withLoading(() => api.rest());
    if (response) {
      handleResponse(response);
    }
  }, [withLoading, handleResponse]);

  const clearError = useCallback(() => setError(null), []);
  const clearDialogue = useCallback(() => setDialogueData(null), []);
  const clearDeath = useCallback(() => setDeathData(null), []);

  // Try to load existing game on mount
  useEffect(() => {
    const initGame = async () => {
      try {
        const state = await api.getState();
        if (state && state.player) {
          setGameState(state);
          setNarrative('Welcome back, adventurer...');
          prefetchRooms(); // Prefetch on initial load
        }
      } catch {
        // No existing game, that's fine
      }
    };
    initGame();
  }, [prefetchRooms]);

  return {
    gameState,
    isLoading,
    error,
    narrative,
    dialogueData,
    deathData,
    newGame,
    loadGame,
    saveGame,
    move,
    attack,
    flee,
    takeItem,
    useItem,
    talk,
    rest,
    clearError,
    clearDialogue,
    clearDeath,
  };
}
