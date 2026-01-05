// Main App Component for Tile-Crawler

import { useCallback, useEffect } from 'react';
import { useGame } from './hooks/useGame';
import {
  GameMap,
  PlayerStats,
  Inventory,
  Controls,
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
  const hasNpcs = gameState.room.npcs.length > 0;
  const canRest =
    gameState.room.features.includes('campfire') ||
    gameState.room.features.includes('safe_room');

  return (
    <div className="min-h-screen bg-dungeon-bg p-4">
      {/* Header */}
      <header className="max-w-7xl mx-auto mb-4 flex justify-between items-center">
        <h1 className="text-2xl font-bold text-dungeon-accent">TILE-CRAWLER</h1>
        <div className="flex gap-2">
          <button
            className="game-btn text-sm"
            onClick={saveGame}
            disabled={isLoading}
          >
            Save
          </button>
          <button
            className="game-btn text-sm"
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
        <div className="max-w-7xl mx-auto mb-4">
          <div className="game-panel border-dungeon-danger bg-dungeon-danger bg-opacity-10 flex justify-between items-center">
            <span className="text-dungeon-danger">{error}</span>
            <button
              className="text-dungeon-muted hover:text-dungeon-text"
              onClick={clearError}
            >
              ✕
            </button>
          </div>
        </div>
      )}

      {/* Main game layout */}
      <main className="max-w-7xl mx-auto">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
          {/* Left sidebar - Player stats */}
          <aside className="lg:col-span-3 space-y-4">
            <PlayerStats stats={gameState.player} gold={gameState.gold} />

            {/* Position display */}
            <div className="game-panel text-sm">
              <div className="text-dungeon-muted mb-1">Location</div>
              <div className="flex justify-between">
                <span>Position:</span>
                <span>
                  ({gameState.position[0]}, {gameState.position[1]})
                </span>
              </div>
              <div className="flex justify-between">
                <span>Floor:</span>
                <span>{gameState.position[2] + 1}</span>
              </div>
              <div className="flex justify-between">
                <span>Biome:</span>
                <span className="capitalize">{gameState.room.biome}</span>
              </div>
            </div>

            {/* Game stats */}
            <div className="game-panel text-sm">
              <div className="text-dungeon-muted mb-2">Statistics</div>
              <div className="space-y-1">
                <div className="flex justify-between">
                  <span>Rooms explored:</span>
                  <span>{gameState.stats.rooms_explored}</span>
                </div>
                <div className="flex justify-between">
                  <span>Enemies defeated:</span>
                  <span>{gameState.stats.enemies_defeated}</span>
                </div>
                <div className="flex justify-between">
                  <span>Steps taken:</span>
                  <span>{gameState.stats.steps_taken}</span>
                </div>
                <div className="flex justify-between">
                  <span>Deaths:</span>
                  <span>{gameState.stats.deaths}</span>
                </div>
              </div>
            </div>
          </aside>

          {/* Center - Map and narrative */}
          <section className="lg:col-span-6 space-y-4">
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

            {/* Game map */}
            <GameMap map={gameState.room.map} />

            {/* Narrative text */}
            <Narrative
              text={narrative}
              recentEvents={gameState.narrative.recent_events}
            />

            {/* Room items */}
            {!inCombat && gameState.room.items.length > 0 && (
              <RoomItems
                items={gameState.room.items}
                onTakeItem={takeItem}
                isLoading={isLoading}
              />
            )}
          </section>

          {/* Right sidebar - Controls and inventory */}
          <aside className="lg:col-span-3 space-y-4">
            {/* Movement controls */}
            <Controls
              onMove={(dir: Direction) => move(dir)}
              onRest={rest}
              onTalk={() => talk()}
              exits={gameState.room.exits}
              hasNpcs={hasNpcs}
              canRest={canRest}
              inCombat={inCombat}
              isLoading={isLoading}
            />

            {/* Inventory */}
            <Inventory
              items={gameState.inventory}
              onUseItem={useItem}
              isLoading={isLoading}
            />
          </aside>
        </div>
      </main>

      {/* Loading overlay */}
      {isLoading && (
        <div className="fixed bottom-4 right-4">
          <div className="game-panel flex items-center gap-2">
            <span className="spinner" />
            <span className="text-sm text-dungeon-muted">Loading...</span>
          </div>
        </div>
      )}

      {/* Footer */}
      <footer className="max-w-7xl mx-auto mt-8 text-center text-xs text-dungeon-muted opacity-50">
        TILE-CRAWLER v0.1.0 - An LLM-Powered Dungeon Crawler
      </footer>
    </div>
  );
}

export default App;
