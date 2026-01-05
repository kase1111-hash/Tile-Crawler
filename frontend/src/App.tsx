// Main App Component for Tile-Crawler - First Person ASCII View

import { useCallback, useEffect, useState } from 'react';
import { useGame } from './hooks/useGame';
import { GameMenu } from './components';

// First-person ASCII art for different views
const ASCII_VIEWS = {
  corridor: [
    "          ┌─────────────────────┐          ",
    "         ╱                       ╲         ",
    "        ╱   ┌───────────────┐     ╲        ",
    "       ╱   ╱                 ╲     ╲       ",
    "      ╱   ╱   ┌───────────┐   ╲     ╲      ",
    "     ╱   ╱   ╱             ╲   ╲     ╲     ",
    "    │   │   │   ▒▒▒▒▒▒▒▒▒   │   │     │    ",
    "    │   │   │   ▒▒▒▒▒▒▒▒▒   │   │     │    ",
    "    │   │   │   ▒▒▒▒▒▒▒▒▒   │   │     │    ",
    "────┴───┴───┴───────────────┴───┴─────┴────",
  ],
  wall: [
    "╔═══════════════════════════════════════════╗",
    "║▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓║",
    "║▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓║",
    "║▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓║",
    "║▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓║",
    "║▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓║",
    "║▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓║",
    "║▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓║",
    "║▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓║",
    "╚═══════════════════════════════════════════╝",
  ],
  doorway: [
    "▓▓▓▓▓▓▓▓▓▓▓┌─────────────────────┐▓▓▓▓▓▓▓▓▓▓▓",
    "▓▓▓▓▓▓▓▓▓▓▓│                     │▓▓▓▓▓▓▓▓▓▓▓",
    "▓▓▓▓▓▓▓▓▓▓▓│    ░░░░░░░░░░░░░    │▓▓▓▓▓▓▓▓▓▓▓",
    "▓▓▓▓▓▓▓▓▓▓▓│    ░░░░░░░░░░░░░    │▓▓▓▓▓▓▓▓▓▓▓",
    "▓▓▓▓▓▓▓▓▓▓▓│    ░░░░░░░░░░░░░    │▓▓▓▓▓▓▓▓▓▓▓",
    "▓▓▓▓▓▓▓▓▓▓▓│    ░░░░░░░░░░░░░    │▓▓▓▓▓▓▓▓▓▓▓",
    "▓▓▓▓▓▓▓▓▓▓▓│    ░░░░░░░░░░░░░    │▓▓▓▓▓▓▓▓▓▓▓",
    "▓▓▓▓▓▓▓▓▓▓▓│    ░░░░░░░░░░░░░    │▓▓▓▓▓▓▓▓▓▓▓",
    "▓▓▓▓▓▓▓▓▓▓▓│                     │▓▓▓▓▓▓▓▓▓▓▓",
    "───────────┴─────────────────────┴───────────",
  ],
  room: [
    "┌─────────────────────────────────────────────┐",
    "│  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │",
    "│  ░                                       ░  │",
    "│  ░                                       ░  │",
    "│  ░                                       ░  │",
    "│  ░                                       ░  │",
    "│  ░                                       ░  │",
    "│  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │",
    "│                                             │",
    "└─────────────────────────────────────────────┘",
  ],
};

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
  const [facing, setFacing] = useState<'north' | 'south' | 'east' | 'west'>('north');

  // Keyboard controls
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (!gameState || isLoading) return;
      if (e.target instanceof HTMLInputElement) return;

      const inCombat = gameState.combat?.in_combat;
      const items = gameState.inventory;
      const exits = gameState.room.exits;

      // Escape/Q closes overlays
      if (e.key === 'Escape' || (e.key.toLowerCase() === 'q' && (showInventory || dialogueData))) {
        if (showInventory) { setShowInventory(false); return; }
        if (dialogueData) { clearDialogue(); return; }
      }

      if (dialogueData) return;

      // Inventory toggle
      if (e.key.toLowerCase() === 'i' && !inCombat) {
        setShowInventory(prev => !prev);
        return;
      }

      // Inventory navigation
      if (showInventory) {
        if (e.key === 'ArrowUp' || e.key.toLowerCase() === 'k') {
          setSelectedItem(i => Math.max(0, i - 1));
        } else if (e.key === 'ArrowDown' || e.key.toLowerCase() === 'j') {
          setSelectedItem(i => Math.min(items.length - 1, i + 1));
        } else if (e.key === 'Enter' || e.key.toLowerCase() === 'u') {
          if (items[selectedItem]) useItem(items[selectedItem].id);
        }
        return;
      }

      // Combat controls
      if (inCombat) {
        if (e.key.toLowerCase() === 'a' || e.key === '1') attack();
        if (e.key.toLowerCase() === 'f' || e.key === '2') flee();
        return;
      }

      // First-person movement
      switch (e.key.toLowerCase()) {
        case 'w': // Move forward
          if (exits[facing]) move(facing);
          break;
        case 's': // Move backward (turn around and go back)
          const opposite = { north: 'south', south: 'north', east: 'west', west: 'east' } as const;
          if (exits[opposite[facing]]) move(opposite[facing]);
          break;
        case 'a': // Turn left
          const leftTurn = { north: 'west', west: 'south', south: 'east', east: 'north' } as const;
          setFacing(leftTurn[facing]);
          break;
        case 'd': // Turn right
          const rightTurn = { north: 'east', east: 'south', south: 'west', west: 'north' } as const;
          setFacing(rightTurn[facing]);
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
          if (gameState.room.items.length > 0) takeItem(gameState.room.items[0].id);
          break;
        case 'q':
          saveGame();
          break;
      }

      // Number keys for items
      const num = parseInt(e.key);
      if (!isNaN(num) && num >= 1 && num <= 9) {
        const roomItems = gameState.room.items;
        if (roomItems[num - 1]) takeItem(roomItems[num - 1].id);
      }
    },
    [gameState, isLoading, dialogueData, selectedItem, showInventory, facing, move, attack, flee, rest, talk, takeItem, useItem, clearDialogue, saveGame]
  );

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  useEffect(() => {
    if (!gameState) return;
    const interval = setInterval(() => saveGame(), 60000);
    return () => clearInterval(interval);
  }, [gameState, saveGame]);

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

  const parseStat = (stat: string): [number, number] => {
    const parts = stat.split('/');
    return [parseInt(parts[0]) || 0, parseInt(parts[1]) || 1];
  };

  const [hp, maxHp] = parseStat(gameState.player.hp);
  const [mana, maxMana] = parseStat(gameState.player.mana);

  // Determine what to show based on facing direction
  const canGoForward = exits[facing];
  const leftDir = { north: 'west', west: 'south', south: 'east', east: 'north' } as const;
  const rightDir = { north: 'east', east: 'south', south: 'west', west: 'north' } as const;
  const canGoLeft = exits[leftDir[facing]];
  const canGoRight = exits[rightDir[facing]];

  // Choose ASCII view based on what's ahead
  const getView = () => {
    if (canGoForward) return ASCII_VIEWS.doorway;
    return ASCII_VIEWS.wall;
  };

  const currentView = getView();

  // Compass directions
  const compassDir = { north: 'N', south: 'S', east: 'E', west: 'W' };

  return (
    <div className="fp-container">
      {/* Header */}
      <div className="fp-header">
        <span className="fp-title">TILE CRAWLER</span>
        <span className="fp-location">{gameState.room.biome} - Floor {gameState.position[2] + 1}</span>
      </div>

      {/* Main view area */}
      <div className="fp-main">
        {/* ASCII first-person view */}
        <div className="fp-view">
          <div className="fp-compass">
            Facing: {compassDir[facing]} {canGoLeft && `← ${leftDir[facing][0].toUpperCase()}`} {canGoRight && `${rightDir[facing][0].toUpperCase()} →`}
          </div>
          <div className="fp-scene">
            {currentView.map((line, i) => (
              <div key={i} className="fp-line">{line}</div>
            ))}
          </div>
          <div className="fp-forward">
            {canGoForward ? (
              <span className="exit-open">[W] A passage leads {facing}</span>
            ) : (
              <span className="exit-wall">A solid wall blocks the way</span>
            )}
          </div>
        </div>

        {/* Side panel */}
        <div className="fp-sidebar">
          <div className="fp-stats">
            <div className="stat-name">{gameState.player.name} Lv.{gameState.player.level}</div>
            <div className="stat-row">HP: <span className="hp-val">{hp}/{maxHp}</span></div>
            <div className="stat-row">MP: <span className="mp-val">{mana}/{maxMana}</span></div>
            <div className="stat-row">Gold: <span className="gold-val">{gameState.gold}</span></div>
          </div>

          <div className="fp-exits">
            <div className="exits-title">Exits:</div>
            {exits.north && <div className={facing === 'north' ? 'exit-facing' : ''}>North {facing === 'north' && '(ahead)'}</div>}
            {exits.south && <div className={facing === 'south' ? 'exit-facing' : ''}>South {facing === 'south' && '(ahead)'}</div>}
            {exits.east && <div className={facing === 'east' ? 'exit-facing' : ''}>East {facing === 'east' && '(ahead)'}</div>}
            {exits.west && <div className={facing === 'west' ? 'exit-facing' : ''}>West {facing === 'west' && '(ahead)'}</div>}
            {exits.up && <div>Up (&lt;)</div>}
            {exits.down && <div>Down (&gt;)</div>}
            {!exits.north && !exits.south && !exits.east && !exits.west && <div>None</div>}
          </div>

          {gameState.room.npcs.length > 0 && (
            <div className="fp-npcs">
              <div className="npc-title">Present:</div>
              {gameState.room.npcs.map(npc => <div key={npc} className="npc-name">{npc}</div>)}
            </div>
          )}

          {gameState.room.items.length > 0 && (
            <div className="fp-items">
              <div className="items-title">Items here:</div>
              {gameState.room.items.map((item, i) => (
                <div key={item.id} className="item-row">[{i + 1}] {item.name}</div>
              ))}
            </div>
          )}

          {inCombat && gameState.combat && (
            <div className="fp-combat">
              <div className="combat-title">⚔ COMBAT ⚔</div>
              <div className="combat-enemy">{gameState.combat.enemy_name}</div>
              <div className="combat-hp">HP: {gameState.combat.enemy_hp}/{gameState.combat.enemy_max_hp}</div>
              <div className="combat-act">[A]ttack [F]lee</div>
            </div>
          )}
        </div>
      </div>

      {/* Message area */}
      <div className="fp-messages">
        {error && <div className="msg-err">&gt; {error}</div>}
        {narrative && <div className="msg-narr">&gt; {narrative}</div>}
        {gameState.room.description && <div className="msg-desc">{gameState.room.description}</div>}
      </div>

      {/* Controls */}
      <div className="fp-controls">
        [W]Forward [S]Back [A]Turn Left [D]Turn Right | [I]Inventory [G]Get [T]Talk [R]Rest [Q]Save
      </div>

      {/* Overlays */}
      {dialogueData && (
        <div className="overlay">
          <div className="dlg-box">
            <div className="dlg-name">{dialogueData.npc_name}</div>
            <div className="dlg-text">"{dialogueData.speech}"</div>
            <div className="dlg-close">[Q] Close</div>
          </div>
        </div>
      )}

      {showInventory && (
        <div className="overlay">
          <div className="inv-box">
            <div className="inv-title">═══ INVENTORY ═══</div>
            {gameState.inventory.length === 0 ? (
              <div className="inv-empty">(empty)</div>
            ) : (
              gameState.inventory.map((item, i) => (
                <div key={item.id} className={`inv-row ${i === selectedItem ? 'selected' : ''}`}>
                  {i === selectedItem ? '► ' : '  '}{item.name}{item.quantity > 1 ? ` x${item.quantity}` : ''}
                </div>
              ))
            )}
            <div className="inv-help">↑↓:Select [U]se [Q]Close</div>
          </div>
        </div>
      )}

      {isLoading && <div className="loading">◌</div>}
    </div>
  );
}

export default App;
