// Main App Component for Tile-Crawler - Fullscreen Pseudo-3D View

import { useCallback, useEffect, useState } from 'react';
import { useGame } from './hooks/useGame';
import { GameMenu } from './components';

// Generate pseudo-3D dungeon view
function render3DView(
  forward: boolean,
  left: boolean,
  right: boolean,
  width: number,
  height: number
): string[] {
  const lines: string[] = [];
  const midX = Math.floor(width / 2);
  const midY = Math.floor(height / 2);

  // Perspective parameters
  const horizonY = Math.floor(height * 0.4);
  const floorStart = horizonY + 1;

  // Characters
  const WALL = '▓';
  const FLOOR = '░';
  const CEIL = '·';
  const DARK = ' ';
  const PASSAGE = '▒';

  for (let y = 0; y < height; y++) {
    let line = '';

    for (let x = 0; x < width; x++) {
      const distFromMidX = Math.abs(x - midX);
      const distFromMidY = Math.abs(y - midY);

      // Calculate perspective walls
      const perspectiveRatio = y < horizonY
        ? (horizonY - y) / horizonY
        : (y - horizonY) / (height - horizonY);

      const wallWidth = Math.floor(width * 0.35 * (1 - perspectiveRatio * 0.7));
      const innerWallWidth = Math.floor(wallWidth * 0.6);

      const leftWallOuter = wallWidth;
      const leftWallInner = innerWallWidth;
      const rightWallOuter = width - wallWidth - 1;
      const rightWallInner = width - innerWallWidth - 1;

      // Ceiling zone (top portion)
      if (y < horizonY) {
        const ceilDepth = (horizonY - y) / horizonY;

        // Left wall
        if (x < leftWallOuter) {
          if (left && x > leftWallOuter * 0.3 && y > horizonY * 0.3) {
            line += PASSAGE;
          } else {
            line += WALL;
          }
        }
        // Right wall
        else if (x > rightWallOuter) {
          if (right && x < rightWallOuter + (width - rightWallOuter) * 0.7 && y > horizonY * 0.3) {
            line += PASSAGE;
          } else {
            line += WALL;
          }
        }
        // Ceiling
        else {
          if (forward) {
            // Show depth - passage ahead
            const centerDist = Math.abs(x - midX);
            const depthZone = Math.floor(horizonY * 0.5);
            if (y > depthZone && centerDist < wallWidth * 0.5) {
              line += DARK;
            } else {
              line += CEIL;
            }
          } else {
            // Dead end - wall ahead
            if (y > horizonY * 0.6) {
              line += WALL;
            } else {
              line += CEIL;
            }
          }
        }
      }
      // Horizon line
      else if (y === horizonY) {
        if (x < leftWallInner || x > rightWallInner) {
          line += WALL;
        } else if (forward) {
          line += DARK;
        } else {
          line += WALL;
        }
      }
      // Floor zone (bottom portion)
      else {
        const floorDepth = (y - horizonY) / (height - horizonY);

        // Left wall
        if (x < leftWallOuter) {
          if (left && x > leftWallOuter * 0.3 && y < height - (height - horizonY) * 0.3) {
            line += PASSAGE;
          } else {
            line += WALL;
          }
        }
        // Right wall
        else if (x > rightWallOuter) {
          if (right && x < rightWallOuter + (width - rightWallOuter) * 0.7 && y < height - (height - horizonY) * 0.3) {
            line += PASSAGE;
          } else {
            line += WALL;
          }
        }
        // Floor
        else {
          if (forward) {
            const centerDist = Math.abs(x - midX);
            const nearFloor = y > height - (height - horizonY) * 0.4;
            if (nearFloor) {
              // Close floor tiles
              const tileX = Math.floor(x / 4) % 2;
              const tileY = Math.floor((y - floorStart) / 2) % 2;
              line += (tileX === tileY) ? FLOOR : '·';
            } else if (centerDist < wallWidth * 0.5) {
              line += DARK;
            } else {
              line += FLOOR;
            }
          } else {
            // Dead end floor
            const tileX = Math.floor(x / 4) % 2;
            const tileY = Math.floor((y - floorStart) / 2) % 2;
            line += (tileX === tileY) ? FLOOR : '·';
          }
        }
      }
    }
    lines.push(line);
  }

  return lines;
}

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

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (!gameState || isLoading) return;
      if (e.target instanceof HTMLInputElement) return;

      const inCombat = gameState.combat?.in_combat;
      const items = gameState.inventory;
      const exits = gameState.room.exits;

      if (e.key === 'Escape' || (e.key.toLowerCase() === 'q' && (showInventory || dialogueData))) {
        if (showInventory) { setShowInventory(false); return; }
        if (dialogueData) { clearDialogue(); return; }
      }

      if (dialogueData) return;

      if (e.key.toLowerCase() === 'i' && !inCombat) {
        setShowInventory(prev => !prev);
        return;
      }

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

      if (inCombat) {
        if (e.key.toLowerCase() === 'a' || e.key === '1') attack();
        if (e.key.toLowerCase() === 'f' || e.key === '2') flee();
        return;
      }

      switch (e.key.toLowerCase()) {
        case 'w':
          if (exits[facing]) move(facing);
          break;
        case 's': {
          const opposite = { north: 'south', south: 'north', east: 'west', west: 'east' } as const;
          if (exits[opposite[facing]]) move(opposite[facing]);
          break;
        }
        case 'a': {
          const leftTurn = { north: 'west', west: 'south', south: 'east', east: 'north' } as const;
          setFacing(leftTurn[facing]);
          break;
        }
        case 'd': {
          const rightTurn = { north: 'east', east: 'south', south: 'west', west: 'north' } as const;
          setFacing(rightTurn[facing]);
          break;
        }
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
  const hpPct = Math.round((hp / maxHp) * 100);
  const mpPct = Math.round((mana / maxMana) * 100);

  const leftDir = { north: 'west', west: 'south', south: 'east', east: 'north' } as const;
  const rightDir = { north: 'east', east: 'south', south: 'west', west: 'north' } as const;
  const backDir = { north: 'south', south: 'north', east: 'west', west: 'east' } as const;

  const canGoForward = exits[facing];
  const canGoLeft = exits[leftDir[facing]];
  const canGoRight = exits[rightDir[facing]];
  const canGoBack = exits[backDir[facing]];

  // Render the 3D view
  const viewWidth = 80;
  const viewHeight = 24;
  const view3D = render3DView(canGoForward, canGoLeft, canGoRight, viewWidth, viewHeight);

  const compassFull = { north: 'NORTH', south: 'SOUTH', east: 'EAST', west: 'WEST' };
  const hpBar = '█'.repeat(Math.floor(hpPct / 10)) + '░'.repeat(10 - Math.floor(hpPct / 10));
  const mpBar = '█'.repeat(Math.floor(mpPct / 10)) + '░'.repeat(10 - Math.floor(mpPct / 10));

  return (
    <div className="dungeon-container">
      {/* 3D View */}
      <div className="view-3d">
        {view3D.map((line, i) => (
          <div key={i} className="view-line">{line}</div>
        ))}
      </div>

      {/* HUD Overlay */}
      <div className="hud">
        {/* Top bar */}
        <div className="hud-top">
          <div className="hud-compass">
            <span className="compass-arrow">◄</span>
            <span className="compass-dir">{compassFull[facing]}</span>
            <span className="compass-arrow">►</span>
          </div>
          <div className="hud-location">
            {gameState.room.biome} · Floor {gameState.position[2] + 1} · ({gameState.position[0]},{gameState.position[1]})
          </div>
        </div>

        {/* Left panel - Stats */}
        <div className="hud-left">
          <div className="stat-block">
            <div className="stat-name">{gameState.player.name}</div>
            <div className="stat-level">Level {gameState.player.level}</div>
            <div className="stat-bar-row">
              <span className="stat-label">HP</span>
              <span className="hp-bar">[{hpBar}]</span>
              <span className="stat-val">{hp}</span>
            </div>
            <div className="stat-bar-row">
              <span className="stat-label">MP</span>
              <span className="mp-bar">[{mpBar}]</span>
              <span className="stat-val">{mana}</span>
            </div>
            <div className="stat-gold">Gold: {gameState.gold}</div>
          </div>
        </div>

        {/* Right panel - Exits & Items */}
        <div className="hud-right">
          <div className="exits-block">
            <div className="block-title">EXITS</div>
            <div className={`exit-dir ${canGoForward ? 'exit-open' : 'exit-blocked'}`}>
              [W] {canGoForward ? '▶ Forward' : '▌ Blocked'}
            </div>
            <div className={`exit-dir ${canGoBack ? 'exit-open' : 'exit-blocked'}`}>
              [S] {canGoBack ? '◀ Back' : '▌ Blocked'}
            </div>
            <div className={`exit-dir ${canGoLeft ? 'exit-open' : 'exit-blocked'}`}>
              [A] {canGoLeft ? '◄ Left' : '▌ Wall'}
            </div>
            <div className={`exit-dir ${canGoRight ? 'exit-open' : 'exit-blocked'}`}>
              [D] {canGoRight ? '► Right' : '▌ Wall'}
            </div>
          </div>

          {gameState.room.items.length > 0 && (
            <div className="items-block">
              <div className="block-title">ITEMS</div>
              {gameState.room.items.slice(0, 3).map((item, i) => (
                <div key={item.id} className="item-entry">[{i + 1}] {item.name}</div>
              ))}
            </div>
          )}
        </div>

        {/* Bottom bar - Messages */}
        <div className="hud-bottom">
          <div className="message-text">
            {error && <span className="msg-error">{error}</span>}
            {!error && narrative && <span>{narrative}</span>}
            {!error && !narrative && gameState.room.description}
          </div>
          <div className="controls-hint">
            [WASD] Move · [I] Inventory · [G] Get · [T] Talk · [R] Rest · [Q] Save
          </div>
        </div>

        {/* Combat overlay */}
        {inCombat && gameState.combat && (
          <div className="combat-overlay">
            <div className="combat-box">
              <div className="combat-title">⚔ COMBAT ⚔</div>
              <div className="combat-enemy">{gameState.combat.enemy_name}</div>
              <div className="combat-hp">HP: {gameState.combat.enemy_hp}/{gameState.combat.enemy_max_hp}</div>
              <div className="combat-actions">
                <span className="action-btn">[A] Attack</span>
                <span className="action-btn">[F] Flee</span>
              </div>
            </div>
          </div>
        )}

        {/* NPCs in room */}
        {gameState.room.npcs.length > 0 && !inCombat && (
          <div className="npc-indicator">
            <span className="npc-icon">☺</span>
            <span>{gameState.room.npcs[0]} is here</span>
            <span className="npc-hint">[T] Talk</span>
          </div>
        )}
      </div>

      {/* Dialogue overlay */}
      {dialogueData && (
        <div className="overlay">
          <div className="dialogue-box">
            <div className="dlg-speaker">{dialogueData.npc_name}</div>
            <div className="dlg-text">"{dialogueData.speech}"</div>
            <div className="dlg-dismiss">[Q] Close</div>
          </div>
        </div>
      )}

      {/* Inventory overlay */}
      {showInventory && (
        <div className="overlay">
          <div className="inventory-box">
            <div className="inv-header">══════ INVENTORY ══════</div>
            <div className="inv-content">
              {gameState.inventory.length === 0 ? (
                <div className="inv-empty">(empty)</div>
              ) : (
                gameState.inventory.map((item, i) => (
                  <div key={item.id} className={`inv-item ${i === selectedItem ? 'selected' : ''}`}>
                    {i === selectedItem ? '► ' : '  '}{item.name}
                    {item.quantity > 1 && ` x${item.quantity}`}
                  </div>
                ))
              )}
            </div>
            <div className="inv-footer">↑↓ Select · [U] Use · [Q] Close</div>
          </div>
        </div>
      )}

      {isLoading && <div className="loading-spinner">◌</div>}
    </div>
  );
}

export default App;
