// Main App Component for Tile-Crawler

import { useCallback, useEffect } from 'react';
import { useGame } from './hooks/useGame';
import {
  GameMap,
  PlayerStats,
  Inventory,
  Combat,
  Narrative,
  RoomItems,
  Dialogue,
  GameMenu,
} from './components';
import type { Direction } from './types/game';

function App() {
  const {
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
  } = useGame();

  // Keyboard controls
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (!gameState || isLoading) return;

      // Don't process if in dialogue or typing
      if (dialogueData || e.target instanceof HTMLInputElement) return;

      const inCombat = gameState.combat?.in_combat;

      // Combat controls
      if (inCombat) {
        switch (e.key.toLowerCase()) {
          case 'a':
          case '1':
            attack();
            break;
          case 'f':
          case '2':
            flee();
            break;
        }
        return;
      }

      // Movement controls
      const exits = gameState.room.exits;
      switch (e.key.toLowerCase()) {
        case 'w':
        case 'arrowup':
          if (exits.north) move('north');
          break;
        case 's':
        case 'arrowdown':
          if (exits.south) move('south');
          break;
        case 'a':
        case 'arrowleft':
          if (exits.west) move('west');
          break;
        case 'd':
        case 'arrowright':
          if (exits.east) move('east');
          break;
        case 'r':
          rest();
          break;
        case 't':
          if (gameState.room.npcs.length > 0) talk();
          break;
        case 'escape':
          if (dialogueData) clearDialogue();
          break;
      }
    },
    [gameState, isLoading, dialogueData, move, attack, flee, rest, talk, clearDialogue]
  );

  // Set up keyboard listener
  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  // Auto-save periodically
  useEffect(() => {
    if (!gameState) return;

    const interval = setInterval(() => {
      saveGame();
    }, 60000); // Save every minute

    return () => clearInterval(interval);
  }, [gameState, saveGame]);

  // Show menu if no game state
  if (!gameState) {
    return (
      <GameMenu
        onNewGame={newGame}
        onLoadGame={loadGame}
        hasExistingGame={false}
        isLoading={isLoading}
        error={error}
      />
    );
  }

  const inCombat = gameState.combat?.in_combat ?? false;

  return (
    <div className="min-h-screen bg-dungeon-bg p-2 flex flex-col">
      {/* Header */}
      <header className="flex justify-between items-center mb-2 px-2">
        <h1 className="text-xl font-bold text-dungeon-accent">TILE-CRAWLER</h1>
        <div className="flex gap-2">
          <button
            className="game-btn text-sm py-1"
            onClick={saveGame}
            disabled={isLoading}
          >
            Save
          </button>
          <button
            className="game-btn text-sm py-1"
            onClick={() => {
              if (confirm('Start a new game? Current progress will be lost.')) {
                newGame();
              }
            }}
            disabled={isLoading}
          >
            New Game
          </button>
        </div>
      </header>

      {/* Error notification */}
      {error && (
        <div className="mb-2 px-2">
          <div className="game-panel border-dungeon-danger bg-dungeon-danger bg-opacity-10 flex justify-between items-center py-2">
            <span className="text-dungeon-danger text-sm">{error}</span>
            <button
              className="text-dungeon-muted hover:text-dungeon-text"
              onClick={clearError}
            >
              ✕
            </button>
          </div>
        </div>
      )}

      {/* Main game layout - 3 columns */}
      <main className="flex-1 flex gap-2 px-2 min-h-0">
        {/* Left sidebar - Inventory and Stats */}
        <aside className="w-64 flex-shrink-0 flex flex-col gap-2 overflow-y-auto">
          <PlayerStats stats={gameState.player} gold={gameState.gold} />

          {/* Inventory */}
          <Inventory
            items={gameState.inventory}
            onUseItem={useItem}
            isLoading={isLoading}
          />

          {/* Position display */}
          <div className="game-panel text-xs py-2">
            <div className="text-dungeon-muted mb-1">Location</div>
            <div className="grid grid-cols-2 gap-x-2">
              <span>Position:</span>
              <span>({gameState.position[0]}, {gameState.position[1]})</span>
              <span>Floor:</span>
              <span>{gameState.position[2] + 1}</span>
              <span>Biome:</span>
              <span className="capitalize">{gameState.room.biome}</span>
            </div>
          </div>

          {/* Game stats */}
          <div className="game-panel text-xs py-2">
            <div className="text-dungeon-muted mb-1">Statistics</div>
            <div className="grid grid-cols-2 gap-x-2">
              <span>Explored:</span>
              <span>{gameState.stats.rooms_explored}</span>
              <span>Defeated:</span>
              <span>{gameState.stats.enemies_defeated}</span>
              <span>Steps:</span>
              <span>{gameState.stats.steps_taken}</span>
              <span>Deaths:</span>
              <span>{gameState.stats.deaths}</span>
            </div>
          </div>
        </aside>

        {/* Center - Map (larger) */}
        <section className="flex-1 flex flex-col gap-2 min-w-0">
          {/* Combat UI (shown when in combat) */}
          {inCombat && gameState.combat && (
            <Combat
              combat={gameState.combat}
              onAttack={attack}
              onFlee={flee}
              isLoading={isLoading}
            />
          )}

          {/* Dialogue UI (shown when talking to NPC) */}
          {dialogueData && (
            <Dialogue
              dialogue={dialogueData}
              onRespond={talk}
              onClose={clearDialogue}
              isLoading={isLoading}
            />
          )}

          {/* Game map - now larger */}
          <GameMap map={gameState.room.map} className="flex-1" />

          {/* Room items */}
          {!inCombat && gameState.room.items.length > 0 && (
            <RoomItems
              items={gameState.room.items}
              onTakeItem={takeItem}
              isLoading={isLoading}
            />
          )}
        </section>

        {/* Right sidebar - Room info */}
        <aside className="w-48 flex-shrink-0 flex flex-col gap-2 overflow-y-auto">
          {/* Exits */}
          <div className="game-panel text-sm py-2">
            <div className="text-dungeon-muted mb-2">Exits</div>
            <div className="grid grid-cols-3 gap-1 text-center">
              <div></div>
              <button
                className={`px-2 py-1 rounded text-xs ${gameState.room.exits.north ? 'bg-dungeon-accent text-white cursor-pointer hover:bg-opacity-80' : 'bg-dungeon-panel text-dungeon-muted opacity-30'}`}
                onClick={() => gameState.room.exits.north && move('north')}
                disabled={!gameState.room.exits.north || isLoading}
              >
                N
              </button>
              <div></div>
              <button
                className={`px-2 py-1 rounded text-xs ${gameState.room.exits.west ? 'bg-dungeon-accent text-white cursor-pointer hover:bg-opacity-80' : 'bg-dungeon-panel text-dungeon-muted opacity-30'}`}
                onClick={() => gameState.room.exits.west && move('west')}
                disabled={!gameState.room.exits.west || isLoading}
              >
                W
              </button>
              <div className="text-dungeon-muted">+</div>
              <button
                className={`px-2 py-1 rounded text-xs ${gameState.room.exits.east ? 'bg-dungeon-accent text-white cursor-pointer hover:bg-opacity-80' : 'bg-dungeon-panel text-dungeon-muted opacity-30'}`}
                onClick={() => gameState.room.exits.east && move('east')}
                disabled={!gameState.room.exits.east || isLoading}
              >
                E
              </button>
              <div></div>
              <button
                className={`px-2 py-1 rounded text-xs ${gameState.room.exits.south ? 'bg-dungeon-accent text-white cursor-pointer hover:bg-opacity-80' : 'bg-dungeon-panel text-dungeon-muted opacity-30'}`}
                onClick={() => gameState.room.exits.south && move('south')}
                disabled={!gameState.room.exits.south || isLoading}
              >
                S
              </button>
              <div></div>
            </div>
            {(gameState.room.exits.up || gameState.room.exits.down) && (
              <div className="flex gap-2 mt-2 justify-center">
                {gameState.room.exits.up && (
                  <button
                    className="px-2 py-1 rounded text-xs bg-dungeon-accent text-white hover:bg-opacity-80"
                    onClick={() => move('up')}
                    disabled={isLoading}
                  >
                    ↑ Up
                  </button>
                )}
                {gameState.room.exits.down && (
                  <button
                    className="px-2 py-1 rounded text-xs bg-dungeon-accent text-white hover:bg-opacity-80"
                    onClick={() => move('down')}
                    disabled={isLoading}
                  >
                    ↓ Down
                  </button>
                )}
              </div>
            )}
          </div>

          {/* NPCs in room */}
          {gameState.room.npcs.length > 0 && (
            <div className="game-panel text-sm py-2">
              <div className="text-dungeon-muted mb-1">NPCs</div>
              {gameState.room.npcs.map((npc, i) => (
                <button
                  key={i}
                  className="w-full text-left px-2 py-1 rounded text-xs bg-dungeon-panel hover:bg-dungeon-accent text-yellow-400"
                  onClick={() => talk()}
                  disabled={isLoading}
                >
                  {npc}
                </button>
              ))}
            </div>
          )}

          {/* Room features */}
          {gameState.room.features.length > 0 && (
            <div className="game-panel text-xs py-2">
              <div className="text-dungeon-muted mb-1">Features</div>
              <div className="space-y-1">
                {gameState.room.features.map((f, i) => (
                  <div key={i} className="capitalize text-dungeon-text">{f.replace('_', ' ')}</div>
                ))}
              </div>
            </div>
          )}
        </aside>
      </main>

      {/* Bottom - Narrative text (full width) */}
      <div className="mt-2 px-2">
        <Narrative
          text={narrative}
          recentEvents={gameState.narrative.recent_events}
        />
      </div>

      {/* Loading indicator */}
      {isLoading && (
        <div className="fixed bottom-4 right-4">
          <div className="game-panel flex items-center gap-2 py-2 px-3">
            <span className="spinner w-4 h-4" />
            <span className="text-xs text-dungeon-muted">Loading...</span>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
