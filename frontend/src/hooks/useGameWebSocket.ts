// Custom hook for WebSocket-based game state management

import { useState, useCallback, useEffect, useRef } from 'react';
import { GameWebSocket, createGameWebSocket, generatePlayerId } from '../services/websocket';
import { getAudioEngine } from '../services/audioEngine';
import type { GameState, Direction, DialogueData, AudioBatch } from '../types/game';

interface UseGameWebSocketReturn {
  // State
  gameState: GameState | null;
  isConnected: boolean;
  isLoading: boolean;
  error: string | null;
  narrative: string;
  dialogueData: DialogueData | null;

  // Connection
  connect: () => void;
  disconnect: () => void;

  // Actions
  newGame: (playerName?: string) => void;
  move: (direction: Direction) => void;
  attack: () => void;
  flee: () => void;
  takeItem: (itemId: string) => void;
  useItem: (itemId: string) => void;
  talk: (message?: string) => void;
  rest: () => void;
  clearError: () => void;
  clearDialogue: () => void;
}

interface UseGameWebSocketOptions {
  autoConnect?: boolean;
  playerId?: string;
}

export function useGameWebSocket(options: UseGameWebSocketOptions = {}): UseGameWebSocketReturn {
  const { autoConnect = true, playerId: customPlayerId } = options;

  const [gameState, setGameState] = useState<GameState | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [narrative, setNarrative] = useState<string>('');
  const [dialogueData, setDialogueData] = useState<DialogueData | null>(null);

  const wsRef = useRef<GameWebSocket | null>(null);
  const audioEngine = useRef(getAudioEngine());
  const playerIdRef = useRef<string>(customPlayerId || '');

  // Initialize player ID
  useEffect(() => {
    if (!playerIdRef.current) {
      // Try to get from localStorage or generate new
      const storedId = localStorage.getItem('tile-crawler-player-id');
      if (storedId) {
        playerIdRef.current = storedId;
      } else {
        playerIdRef.current = generatePlayerId();
        localStorage.setItem('tile-crawler-player-id', playerIdRef.current);
      }
    }
  }, []);

  // Play audio from response
  const playAudio = useCallback(async (audio: AudioBatch | undefined) => {
    if (!audio) return;

    try {
      await audioEngine.current.playBatch(audio);
    } catch (err) {
      console.warn('Audio playback failed:', err);
    }
  }, []);

  // Handle state updates from WebSocket
  const handleStateUpdate = useCallback(
    (state: GameState, narrativeText?: string, audio?: AudioBatch, dialogue?: DialogueData) => {
      setGameState(state);
      setIsLoading(false);

      if (narrativeText) {
        setNarrative(narrativeText);
      }

      if (dialogue) {
        setDialogueData(dialogue);
      }

      if (audio) {
        playAudio(audio);
      }
    },
    [playAudio]
  );

  // Handle errors from WebSocket
  const handleError = useCallback((message: string) => {
    setError(message);
    setIsLoading(false);
  }, []);

  // Handle connection events
  const handleConnect = useCallback(() => {
    setIsConnected(true);
    setError(null);
  }, []);

  const handleDisconnect = useCallback(() => {
    setIsConnected(false);
  }, []);

  // Connect to WebSocket
  const connect = useCallback(() => {
    if (wsRef.current?.isConnected) {
      return;
    }

    wsRef.current = createGameWebSocket(playerIdRef.current, {
      onStateUpdate: handleStateUpdate,
      onError: handleError,
      onConnect: handleConnect,
      onDisconnect: handleDisconnect,
      autoReconnect: true,
    });

    wsRef.current.connect();
  }, [handleStateUpdate, handleError, handleConnect, handleDisconnect]);

  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    wsRef.current?.disconnect();
    wsRef.current = null;
  }, []);

  // Auto-connect on mount if enabled
  useEffect(() => {
    if (autoConnect && playerIdRef.current) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [autoConnect, connect, disconnect]);

  // Game actions
  const newGame = useCallback((playerName?: string) => {
    setIsLoading(true);
    setDialogueData(null);
    wsRef.current?.newGame(playerName);
  }, []);

  const move = useCallback((direction: Direction) => {
    setIsLoading(true);
    setDialogueData(null);
    wsRef.current?.move(direction);
  }, []);

  const attack = useCallback(() => {
    setIsLoading(true);
    wsRef.current?.attack();
  }, []);

  const flee = useCallback(() => {
    setIsLoading(true);
    wsRef.current?.flee();
  }, []);

  const takeItem = useCallback((itemId: string) => {
    setIsLoading(true);
    wsRef.current?.takeItem(itemId);
  }, []);

  const useItem = useCallback((itemId: string) => {
    setIsLoading(true);
    wsRef.current?.useItem(itemId);
  }, []);

  const talk = useCallback((message?: string) => {
    setIsLoading(true);
    wsRef.current?.talk(message);
  }, []);

  const rest = useCallback(() => {
    setIsLoading(true);
    wsRef.current?.rest();
  }, []);

  const clearError = useCallback(() => setError(null), []);
  const clearDialogue = useCallback(() => setDialogueData(null), []);

  return {
    gameState,
    isConnected,
    isLoading,
    error,
    narrative,
    dialogueData,
    connect,
    disconnect,
    newGame,
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
