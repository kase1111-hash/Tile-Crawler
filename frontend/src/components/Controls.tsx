// Controls Component - Movement and action buttons

import type { Direction } from '../types/game';

interface ControlsProps {
  onMove: (direction: Direction) => void;
  onRest: () => void;
  onTalk: () => void;
  exits: Record<string, boolean>;
  hasNpcs: boolean;
  canRest: boolean;
  inCombat: boolean;
  isLoading: boolean;
  className?: string;
}

export function Controls({
  onMove,
  onRest,
  onTalk,
  exits,
  hasNpcs,
  canRest,
  inCombat,
  isLoading,
  className = '',
}: ControlsProps) {
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (isLoading || inCombat) return;

    switch (e.key.toLowerCase()) {
      case 'w':
      case 'arrowup':
        if (exits.north) onMove('north');
        break;
      case 's':
      case 'arrowdown':
        if (exits.south) onMove('south');
        break;
      case 'a':
      case 'arrowleft':
        if (exits.west) onMove('west');
        break;
      case 'd':
      case 'arrowright':
        if (exits.east) onMove('east');
        break;
      case 'r':
        if (canRest) onRest();
        break;
      case 't':
        if (hasNpcs) onTalk();
        break;
    }
  };

  return (
    <div
      className={`game-panel ${className}`}
      tabIndex={0}
      onKeyDown={handleKeyDown}
    >
      <h2 className="text-lg font-bold text-dungeon-accent mb-4">Controls</h2>

      {/* Movement pad */}
      <div className="grid grid-cols-3 gap-2 mb-4">
        <div /> {/* Empty cell */}
        <button
          className="game-btn"
          onClick={() => onMove('north')}
          disabled={!exits.north || isLoading || inCombat}
          title="Move North (W)"
        >
          ↑ N
        </button>
        <div /> {/* Empty cell */}

        <button
          className="game-btn"
          onClick={() => onMove('west')}
          disabled={!exits.west || isLoading || inCombat}
          title="Move West (A)"
        >
          ← W
        </button>
        <div className="flex items-center justify-center text-dungeon-muted">
          ◆
        </div>
        <button
          className="game-btn"
          onClick={() => onMove('east')}
          disabled={!exits.east || isLoading || inCombat}
          title="Move East (D)"
        >
          E →
        </button>

        <div /> {/* Empty cell */}
        <button
          className="game-btn"
          onClick={() => onMove('south')}
          disabled={!exits.south || isLoading || inCombat}
          title="Move South (S)"
        >
          ↓ S
        </button>
        <div /> {/* Empty cell */}
      </div>

      {/* Vertical movement */}
      {(exits.up || exits.down) && (
        <div className="flex gap-2 mb-4">
          {exits.up && (
            <button
              className="game-btn flex-1"
              onClick={() => onMove('up')}
              disabled={isLoading || inCombat}
              title="Go Up"
            >
              ⬆ Up
            </button>
          )}
          {exits.down && (
            <button
              className="game-btn flex-1"
              onClick={() => onMove('down')}
              disabled={isLoading || inCombat}
              title="Go Down"
            >
              ⬇ Down
            </button>
          )}
        </div>
      )}

      {/* Action buttons */}
      <div className="space-y-2">
        {hasNpcs && (
          <button
            className="game-btn w-full"
            onClick={onTalk}
            disabled={isLoading || inCombat}
            title="Talk (T)"
          >
            💬 Talk
          </button>
        )}

        {canRest && (
          <button
            className="game-btn game-btn-success w-full"
            onClick={onRest}
            disabled={isLoading || inCombat}
            title="Rest (R)"
          >
            🔥 Rest
          </button>
        )}
      </div>

      {/* Keyboard hints */}
      <div className="mt-4 pt-4 border-t border-dungeon-border text-xs text-dungeon-muted">
        <div className="mb-1">Keyboard:</div>
        <div>WASD / Arrows = Move</div>
        {hasNpcs && <div>T = Talk</div>}
        {canRest && <div>R = Rest</div>}
      </div>
    </div>
  );
}

export default Controls;
