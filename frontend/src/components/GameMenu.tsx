// Game Menu Component - Start screen and menu options

interface GameMenuProps {
  onNewGame: (playerName: string) => void;
  onLoadGame: () => void;
  hasExistingGame: boolean;
  isLoading: boolean;
  error: string | null;
}

import { useState } from 'react';

export function GameMenu({
  onNewGame,
  onLoadGame,
  hasExistingGame,
  isLoading,
  error,
}: GameMenuProps) {
  const [playerName, setPlayerName] = useState('Adventurer');
  const [showNameInput, setShowNameInput] = useState(false);

  const handleNewGame = () => {
    if (showNameInput) {
      onNewGame(playerName || 'Adventurer');
    } else {
      setShowNameInput(true);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-dungeon-bg p-4">
      <div className="game-panel max-w-md w-full text-center">
        {/* Title */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-dungeon-accent mb-2">
            TILE-CRAWLER
          </h1>
          <p className="text-dungeon-muted">
            An LLM-Powered Dungeon Crawler
          </p>
        </div>

        {/* ASCII Art */}
        <pre className="tile-map text-sm mb-8 text-dungeon-muted">
{`    ▓▓▓▓▓▓▓▓▓▓▓
    ▓░░░░░░░░░▓
    ▓░░░@░░░░░▓
    ▓░░░░░░$░░▓
    ▓░░░☺░░░░░▓
    ▓░░░░░░░░░▓
    ▓▓▓▓▓ ▓▓▓▓▓`}
        </pre>

        {/* Error display */}
        {error && (
          <div className="mb-4 p-3 bg-dungeon-danger bg-opacity-20 border border-dungeon-danger rounded text-dungeon-danger text-sm">
            {error}
          </div>
        )}

        {/* Name input */}
        {showNameInput && (
          <div className="mb-4">
            <label className="block text-dungeon-muted text-sm mb-2">
              Enter your name:
            </label>
            <input
              type="text"
              value={playerName}
              onChange={(e) => setPlayerName(e.target.value)}
              placeholder="Adventurer"
              className="w-full bg-dungeon-bg border border-dungeon-border rounded px-4 py-2 text-dungeon-text text-center focus:outline-none focus:border-dungeon-accent"
              maxLength={20}
              autoFocus
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  handleNewGame();
                }
              }}
            />
          </div>
        )}

        {/* Menu buttons */}
        <div className="space-y-3">
          <button
            className="game-btn game-btn-primary w-full py-3 text-lg"
            onClick={handleNewGame}
            disabled={isLoading}
          >
            {isLoading ? (
              <span className="spinner" />
            ) : showNameInput ? (
              'Begin Adventure'
            ) : (
              'New Game'
            )}
          </button>

          {hasExistingGame && !showNameInput && (
            <button
              className="game-btn w-full py-3 text-lg"
              onClick={onLoadGame}
              disabled={isLoading}
            >
              {isLoading ? <span className="spinner" /> : 'Continue'}
            </button>
          )}

          {showNameInput && (
            <button
              className="game-btn w-full"
              onClick={() => setShowNameInput(false)}
              disabled={isLoading}
            >
              Back
            </button>
          )}
        </div>

        {/* Controls hint */}
        <div className="mt-8 pt-4 border-t border-dungeon-border text-xs text-dungeon-muted">
          <div className="mb-2">Controls:</div>
          <div>WASD / Arrows = Move</div>
          <div>Click items and NPCs to interact</div>
        </div>

        {/* Credits */}
        <div className="mt-4 text-xs text-dungeon-muted opacity-50">
          Powered by LLM Dungeon Master
        </div>
      </div>
    </div>
  );
}

export default GameMenu;
