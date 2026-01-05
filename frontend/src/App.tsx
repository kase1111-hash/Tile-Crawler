// Main App Component for Tile-Crawler - TUI Style

import { useCallback, useEffect, useState } from 'react';
import { useGame } from './hooks/useGame';
import { GameMenu } from './components';
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

  const [selectedItem, setSelectedItem] = useState<number>(0);

  // Keyboard controls
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (!gameState || isLoading) return;
      if (e.target instanceof HTMLInputElement) return;

      const inCombat = gameState.combat?.in_combat;
      const items = gameState.inventory;

      // Dialogue controls
      if (dialogueData) {
        if (e.key === 'Escape' || e.key.toLowerCase() === 'q') {
          clearDialogue();
        }
        return;
      }

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

      // Inventory navigation
      if (e.key === 'ArrowUp' || e.key.toLowerCase() === 'k') {
        setSelectedItem(i => Math.max(0, i - 1));
        return;
      }
      if (e.key === 'ArrowDown' || e.key.toLowerCase() === 'j') {
        setSelectedItem(i => Math.min(items.length - 1, i + 1));
        return;
      }
      if (e.key === 'Enter' || e.key.toLowerCase() === 'u') {
        if (items[selectedItem]) {
          useItem(items[selectedItem].id);
        }
        return;
      }

      // Movement controls
      const exits = gameState.room.exits;
      switch (e.key.toLowerCase()) {
        case 'w':
          if (exits.north) move('north');
          break;
        case 's':
          if (exits.south) move('south');
          break;
        case 'a':
          if (exits.west) move('west');
          break;
        case 'd':
          if (exits.east) move('east');
          break;
        case '<':
          if (exits.up) move('up');
          break;
        case '>':
          if (exits.down) move('down');
          break;
        case 'r':
          rest();
          break;
        case 't':
          if (gameState.room.npcs.length > 0) talk();
          break;
        case 'g':
          // Take first item in room
          if (gameState.room.items.length > 0) {
            takeItem(gameState.room.items[0].id);
          }
          break;
        case 'q':
          saveGame();
          break;
      }

      // Number keys for taking items
      const num = parseInt(e.key);
      if (!isNaN(num) && num >= 1 && num <= 9) {
        const roomItems = gameState.room.items;
        if (roomItems[num - 1]) {
          takeItem(roomItems[num - 1].id);
        }
      }
    },
    [gameState, isLoading, dialogueData, selectedItem, move, attack, flee, rest, talk, takeItem, useItem, clearDialogue, saveGame]
  );

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  // Auto-save periodically
  useEffect(() => {
    if (!gameState) return;
    const interval = setInterval(() => saveGame(), 60000);
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
  const exits = gameState.room.exits;
  const exitStr = [
    exits.north && 'N',
    exits.south && 'S',
    exits.east && 'E',
    exits.west && 'W',
    exits.up && '↑',
    exits.down && '↓'
  ].filter(Boolean).join(' ');

  // Format HP/MP bars
  const hpPct = Math.round((gameState.player.hp / gameState.player.max_hp) * 100);
  const mpPct = Math.round((gameState.player.mana / gameState.player.max_mana) * 100);
  const xpPct = Math.round((gameState.player.xp / gameState.player.xp_to_level) * 100);

  const hpBar = '█'.repeat(Math.floor(hpPct / 5)) + '░'.repeat(20 - Math.floor(hpPct / 5));
  const mpBar = '█'.repeat(Math.floor(mpPct / 5)) + '░'.repeat(20 - Math.floor(mpPct / 5));
  const xpBar = '█'.repeat(Math.floor(xpPct / 5)) + '░'.repeat(20 - Math.floor(xpPct / 5));

  return (
    <div className="tui-container">
      {/* Top status bar */}
      <div className="tui-status">
        <span className="text-green-400">{gameState.player.name}</span>
        <span className="text-dungeon-muted"> │ </span>
        <span>Lv.{gameState.player.level}</span>
        <span className="text-dungeon-muted"> │ </span>
        <span className="text-red-400">HP:{gameState.player.hp}/{gameState.player.max_hp}</span>
        <span className="text-dungeon-muted"> │ </span>
        <span className="text-blue-400">MP:{gameState.player.mana}/{gameState.player.max_mana}</span>
        <span className="text-dungeon-muted"> │ </span>
        <span className="text-yellow-400">Gold:{gameState.gold}</span>
        <span className="text-dungeon-muted"> │ </span>
        <span className="text-dungeon-muted">({gameState.position[0]},{gameState.position[1]}) F{gameState.position[2]+1}</span>
        <span className="text-dungeon-muted"> │ </span>
        <span className="capitalize">{gameState.room.biome}</span>
        {isLoading && <span className="text-yellow-400 ml-4">◌ Loading...</span>}
      </div>

      {/* Main content area */}
      <div className="tui-main">
        {/* Left panel - Stats & Inventory */}
        <div className="tui-panel tui-left">
          <div className="tui-section">
            <div className="tui-header">═══ STATS ═══</div>
            <div><span className="text-red-400">HP </span><span className="text-red-500">[{hpBar}]</span> {hpPct}%</div>
            <div><span className="text-blue-400">MP </span><span className="text-blue-500">[{mpBar}]</span> {mpPct}%</div>
            <div><span className="text-purple-400">XP </span><span className="text-purple-500">[{xpBar}]</span> {xpPct}%</div>
            <div className="text-dungeon-muted mt-1">ATK:{gameState.player.attack} DEF:{gameState.player.defense}</div>
          </div>

          <div className="tui-section">
            <div className="tui-header">═══ INVENTORY ═══</div>
            {gameState.inventory.length === 0 ? (
              <div className="text-dungeon-muted">  (empty)</div>
            ) : (
              gameState.inventory.map((item, i) => (
                <div
                  key={item.id}
                  className={i === selectedItem ? 'tui-selected' : ''}
                >
                  {i === selectedItem ? '► ' : '  '}
                  <span className="text-cyan-400">{item.name}</span>
                  {item.quantity > 1 && <span className="text-dungeon-muted"> x{item.quantity}</span>}
                </div>
              ))
            )}
            <div className="text-dungeon-muted mt-1 text-xs">↑↓:select  u:use</div>
          </div>

          <div className="tui-section">
            <div className="tui-header">═══ ROOM ═══</div>
            <div>Exits: <span className="text-green-400">{exitStr || 'none'}</span></div>
            {gameState.room.npcs.length > 0 && (
              <div>NPCs: <span className="text-yellow-400">{gameState.room.npcs.join(', ')}</span></div>
            )}
            {gameState.room.features.length > 0 && (
              <div className="text-dungeon-muted">{gameState.room.features.map(f => f.replace('_', ' ')).join(', ')}</div>
            )}
          </div>
        </div>

        {/* Center - Map */}
        <div className="tui-panel tui-center">
          <div className="tui-map">
            {gameState.room.map.map((row, i) => (
              <div key={i} className="tui-map-row">
                {row.split('').map((char, j) => (
                  <span key={j} className={getTileClass(char)}>{char}</span>
                ))}
              </div>
            ))}
          </div>
        </div>

        {/* Right panel - Combat/Items/Dialogue */}
        <div className="tui-panel tui-right">
          {/* Combat */}
          {inCombat && gameState.combat && (
            <div className="tui-section">
              <div className="tui-header text-red-400">══ COMBAT ══</div>
              <div className="text-red-400">{gameState.combat.enemy_name}</div>
              <div>HP: {gameState.combat.enemy_hp}/{gameState.combat.enemy_max_hp}</div>
              <div className="mt-2">
                <div>[A] Attack</div>
                <div>[F] Flee</div>
              </div>
            </div>
          )}

          {/* Dialogue */}
          {dialogueData && (
            <div className="tui-section">
              <div className="tui-header text-yellow-400">══ DIALOGUE ══</div>
              <div className="text-yellow-400">{dialogueData.npc_name}:</div>
              <div className="text-dungeon-text mt-1">"{dialogueData.speech}"</div>
              <div className="text-dungeon-muted mt-2">[Q] Close</div>
            </div>
          )}

          {/* Room Items */}
          {!inCombat && gameState.room.items.length > 0 && (
            <div className="tui-section">
              <div className="tui-header">═══ ITEMS ═══</div>
              {gameState.room.items.map((item, i) => (
                <div key={item.id}>
                  <span className="text-dungeon-muted">[{i+1}]</span>
                  <span className="text-cyan-400"> {item.name}</span>
                </div>
              ))}
              <div className="text-dungeon-muted mt-1 text-xs">g:take  1-9:take #</div>
            </div>
          )}

          {/* Controls Help */}
          <div className="tui-section mt-auto">
            <div className="tui-header">═══ KEYS ═══</div>
            <div className="text-xs">
              <div>WASD: Move</div>
              <div>&lt;&gt;: Up/Down</div>
              <div>T: Talk  R: Rest</div>
              <div>G: Take  Q: Save</div>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom narrative */}
      <div className="tui-narrative">
        {error && <div className="text-red-400">! {error}</div>}
        <div>{narrative}</div>
        {gameState.narrative.recent_events.slice(-2).map((event, i) => (
          <div key={i} className="text-dungeon-muted">{event}</div>
        ))}
      </div>
    </div>
  );
}

// Tile coloring
function getTileClass(char: string): string {
  switch (char) {
    case '@': return 'tile-player';
    case '&': case 'Ω': return 'tile-enemy';
    case '☺': return 'tile-npc';
    case '$': case '■': case '□': return 'tile-item';
    case '▓': case '╔': case '═': case '╗': case '║': case '╚': case '╝': case '╠': case '╣': case '╬': return 'tile-wall';
    case '░': case '.': return 'tile-floor';
    case '≈': return 'tile-water';
    case '~': return 'tile-lava';
    case '+': case '/': return 'tile-door';
    case '>': case '<': return 'tile-stairs';
    case '^': return 'tile-trap';
    case '◊': case '♨': return 'tile-chest';
    default: return 'tile-floor';
  }
}

export default App;
