// Custom hook for game state management

import { useState, useCallback, useEffect } from 'react';
import { api } from '../services/api';
import type { GameState, ActionResponse, Direction, DialogueData } from '../types/game';

interface UseGameReturn {
  // State
  gameState: GameState | null;
  isLoading: boolean;
  error: string | null;
  narrative: string;
  dialogueData: DialogueData | null;

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
}

export function useGame(): UseGameReturn {
  const [gameState, setGameState] = useState<GameState | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [narrative, setNarrative] = useState<string>('');
  const [dialogueData, setDialogueData] = useState<DialogueData | null>(null);

  // Helper to handle API responses
  const handleResponse = useCallback((response: ActionResponse) => {
    if (response.narrative) {
      setNarrative(response.narrative);
    }
    if (response.state) {
      setGameState(response.state);
    }
    if (response.dialogue) {
      setDialogueData(response.dialogue);
    }
    if (!response.success && response.message) {
      setError(response.message);
    }
  }, []);

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
        handleResponse(response);
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
    }
  }, [withLoading]);

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
        handleResponse(response);
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
      handleResponse(response);
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

  // Try to load existing game on mount
  useEffect(() => {
    const initGame = async () => {
      try {
        const state = await api.getState();
        if (state && state.player) {
          setGameState(state);
          setNarrative('Welcome back, adventurer...');
        }
      } catch {
        // No existing game, that's fine
      }
    };
    initGame();
  }, []);

  return {
    gameState,
    isLoading,
    error,
    narrative,
    dialogueData,
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
  };
}
