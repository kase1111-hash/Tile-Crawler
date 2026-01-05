// Main App Component for Tile-Crawler - Fullscreen ASCII Map

import { useCallback, useEffect, useState } from 'react';
import { useGame } from './hooks/useGame';
import { GameMenu } from './components';

// Map dimensions for fullscreen rendering
const MAP_WIDTH = 80;
const MAP_HEIGHT = 24;

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
    clearDialogue,
  } = useGame();

  const [selectedItem, setSelectedItem] = useState<number>(0);
  const [showInventory, setShowInventory] = useState(false);

  // Keyboard controls
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (!gameState || isLoading) return;
      if (e.target instanceof HTMLInputElement) return;

      const inCombat = gameState.combat?.in_combat;
      const items = gameState.inventory;

      // Toggle inventory with 'i'
      if (e.key.toLowerCase() === 'i' && !inCombat && !dialogueData) {
        setShowInventory(prev => !prev);
        return;
      }

      // Escape closes overlays
      if (e.key === 'Escape') {
        if (showInventory) {
          setShowInventory(false);
          return;
        }
        if (dialogueData) {
          clearDialogue();
          return;
        }
      }

      // Dialogue controls
      if (dialogueData) {
        if (e.key.toLowerCase() === 'q') {
          clearDialogue();
        }
        return;
      }

      // Inventory navigation when open
      if (showInventory) {
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
        if (e.key.toLowerCase() === 'q') {
          setShowInventory(false);
          return;
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
    [gameState, isLoading, dialogueData, selectedItem, showInventory, move, attack, flee, rest, talk, takeItem, useItem, clearDialogue, saveGame]
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

  // Parse stat strings like "100/100" into [current, max]
  const parseStat = (stat: string): [number, number] => {
    const parts = stat.split('/');
    const current = parseInt(parts[0]) || 0;
    const max = parseInt(parts[1]) || 1;
    return [current, max];
  };

  const [hp, maxHp] = parseStat(gameState.player.hp);
  const [mana, maxMana] = parseStat(gameState.player.mana);

  // Create fullscreen map with room centered
  const renderFullscreenMap = () => {
    const roomMap = gameState.room.map;
    const roomHeight = roomMap.length;
    const roomWidth = roomMap[0]?.length || 0;

    // Calculate padding to center the room
    const padTop = Math.floor((MAP_HEIGHT - roomHeight) / 2);
    const padLeft = Math.floor((MAP_WIDTH - roomWidth) / 2);

    const lines: string[] = [];

    for (let y = 0; y < MAP_HEIGHT; y++) {
      let line = '';
      for (let x = 0; x < MAP_WIDTH; x++) {
        const roomY = y - padTop;
        const roomX = x - padLeft;

        if (roomY >= 0 && roomY < roomHeight && roomX >= 0 && roomX < roomWidth) {
          line += roomMap[roomY][roomX];
        } else {
          // Fill with darkness/void outside room
          line += ' ';
        }
      }
      lines.push(line);
    }

    return lines;
  };

  const fullMap = renderFullscreenMap();

  // Build HP/MP bars for status line
  const hpPct = Math.round((hp / maxHp) * 100);
  const mpPct = Math.round((mana / maxMana) * 100);
  const hpBar = '█'.repeat(Math.floor(hpPct / 10)) + '░'.repeat(10 - Math.floor(hpPct / 10));
  const mpBar = '█'.repeat(Math.floor(mpPct / 10)) + '░'.repeat(10 - Math.floor(mpPct / 10));

  // Build exit string
  const exitChars = [
    exits.north && 'N',
    exits.south && 'S',
    exits.east && 'E',
    exits.west && 'W',
    exits.up && '↑',
    exits.down && '↓'
  ].filter(Boolean).join('');

  return (
    <div className="fullscreen-container">
      {/* Fullscreen ASCII Map */}
      <div className="ascii-map">
        {fullMap.map((row, i) => (
          <div key={i} className="map-row">
            {row.split('').map((char, j) => (
              <span key={j} className={getTileClass(char)}>{char}</span>
            ))}
          </div>
        ))}
      </div>

      {/* Top HUD - Status Bar */}
      <div className="hud-top">
        <span className="text-green-400">{gameState.player.name}</span>
        <span className="text-dim"> Lv{gameState.player.level} </span>
        <span className="text-red-400">HP[{hpBar}]</span>
        <span className="text-blue-400"> MP[{mpBar}]</span>
        <span className="text-yellow-400"> ${gameState.gold}</span>
        <span className="text-dim"> ({gameState.position[0]},{gameState.position[1]})F{gameState.position[2]+1}</span>
        <span className="text-dim"> [{exitChars || '-'}]</span>
        {isLoading && <span className="text-yellow-400"> ◌</span>}
      </div>

      {/* Bottom HUD - Messages/Narrative */}
      <div className="hud-bottom">
        {error && <div className="text-red-400">&gt; {error}</div>}
        {narrative && <div className="text-dim">&gt; {narrative}</div>}
        {gameState.room.description && (
          <div className="text-dim">{gameState.room.description}</div>
        )}
        <div className="hud-controls">
          <span className="text-dim">[WASD]Move [I]Inventory [G]Get [T]Talk [R]Rest [Q]Save</span>
        </div>
      </div>

      {/* Combat Overlay */}
      {inCombat && gameState.combat && (
        <div className="overlay-panel combat-panel">
          <div className="panel-border">
            ╔══════════ COMBAT ══════════╗
          </div>
          <div className="panel-content">
            <div className="text-red-400">  {gameState.combat.enemy_name}</div>
            <div>  HP: {gameState.combat.enemy_hp}/{gameState.combat.enemy_max_hp}</div>
            <div className="mt-2">
              <div className="text-green-400">  [A] Attack</div>
              <div className="text-yellow-400">  [F] Flee</div>
            </div>
          </div>
          <div className="panel-border">
            ╚════════════════════════════╝
          </div>
        </div>
      )}

      {/* Dialogue Overlay */}
      {dialogueData && (
        <div className="overlay-panel dialogue-panel">
          <div className="panel-border">
            ╔══════════ {dialogueData.npc_name.toUpperCase()} ══════════╗
          </div>
          <div className="panel-content">
            <div className="text-dim">"{dialogueData.speech}"</div>
          </div>
          <div className="panel-border">
            ╚═══════════ [Q] Close ═══════════╝
          </div>
        </div>
      )}

      {/* Inventory Overlay */}
      {showInventory && (
        <div className="overlay-panel inventory-panel">
          <div className="panel-border">
            ╔═══════════ INVENTORY ═══════════╗
          </div>
          <div className="panel-content">
            {gameState.inventory.length === 0 ? (
              <div className="text-dim">  (empty)</div>
            ) : (
              gameState.inventory.map((item, i) => (
                <div key={item.id} className={i === selectedItem ? 'selected-item' : ''}>
                  {i === selectedItem ? ' ► ' : '   '}
                  <span className="text-cyan-400">{item.name}</span>
                  {item.quantity > 1 && <span className="text-dim"> x{item.quantity}</span>}
                </div>
              ))
            )}
            <div className="text-dim mt-2">  ↑↓:Select  U:Use  Q:Close</div>
          </div>
          <div className="panel-border">
            ╚════════════════════════════════╝
          </div>
        </div>
      )}

      {/* Room Items Indicator */}
      {!inCombat && !showInventory && gameState.room.items.length > 0 && (
        <div className="hud-items">
          <span className="text-cyan-400">Items here: </span>
          {gameState.room.items.map((item, i) => (
            <span key={item.id}>
              <span className="text-dim">[{i+1}]</span>
              <span className="text-cyan-400">{item.name} </span>
            </span>
          ))}
        </div>
      )}
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
    case '▓': case '╔': case '═': case '╗': case '║': case '╚': case '╝': case '╠': case '╣': case '╬': case '#': return 'tile-wall';
    case '░': case '.': return 'tile-floor';
    case '≈': return 'tile-water';
    case '~': return 'tile-lava';
    case '+': case '/': return 'tile-door';
    case '>': case '<': return 'tile-stairs';
    case '^': return 'tile-trap';
    case '◊': case '♨': return 'tile-chest';
    case ' ': return 'tile-void';
    default: return 'tile-floor';
  }
}

export default App;
