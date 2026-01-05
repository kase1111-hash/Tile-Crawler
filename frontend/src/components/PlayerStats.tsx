// Player Stats Component - Displays player health, mana, level, etc.

import type { PlayerStats as PlayerStatsType } from '../types/game';

interface PlayerStatsProps {
  stats: PlayerStatsType;
  gold: number;
  className?: string;
}

interface StatBarProps {
  label: string;
  current: number;
  max: number;
  colorClass: string;
}

function StatBar({ label, current, max, colorClass }: StatBarProps) {
  const percentage = max > 0 ? (current / max) * 100 : 0;

  return (
    <div className="mb-2">
      <div className="flex justify-between text-sm mb-1">
        <span className="text-dungeon-muted">{label}</span>
        <span>
          {current}/{max}
        </span>
      </div>
      <div className="health-bar border border-dungeon-border">
        <div
          className={`health-bar-fill ${colorClass}`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}

function parseStatValue(value: string): { current: number; max: number } {
  const parts = value.split('/');
  return {
    current: parseInt(parts[0]) || 0,
    max: parseInt(parts[1]) || parseInt(parts[0]) || 0,
  };
}

export function PlayerStats({ stats, gold, className = '' }: PlayerStatsProps) {
  const hp = parseStatValue(stats.hp);
  const mana = parseStatValue(stats.mana);
  const xp = parseStatValue(stats.xp);

  return (
    <div className={`game-panel ${className}`}>
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-bold text-dungeon-accent">{stats.name}</h2>
        <span className="text-dungeon-muted">Lv. {stats.level}</span>
      </div>

      <StatBar label="HP" current={hp.current} max={hp.max} colorClass="health-bar-hp" />
      <StatBar label="MP" current={mana.current} max={mana.max} colorClass="health-bar-mana" />
      <StatBar label="XP" current={xp.current} max={xp.max} colorClass="health-bar-xp" />

      <div className="grid grid-cols-2 gap-2 mt-4 text-sm">
        <div className="flex justify-between">
          <span className="text-dungeon-muted">ATK:</span>
          <span className="text-dungeon-danger">{stats.attack}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-dungeon-muted">DEF:</span>
          <span className="text-dungeon-info">{stats.defense}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-dungeon-muted">SPD:</span>
          <span className="text-dungeon-success">{stats.speed}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-dungeon-muted">MAG:</span>
          <span className="text-dungeon-accent">{stats.magic}</span>
        </div>
      </div>

      <div className="mt-4 pt-4 border-t border-dungeon-border">
        <div className="flex justify-between items-center">
          <span className="text-dungeon-muted">Gold:</span>
          <span className="text-yellow-400 font-bold">{gold} G</span>
        </div>
      </div>

      {stats.status_effects.length > 0 && (
        <div className="mt-4 pt-4 border-t border-dungeon-border">
          <div className="text-dungeon-muted text-sm mb-2">Status:</div>
          <div className="flex flex-wrap gap-1">
            {stats.status_effects.map((effect, index) => (
              <span
                key={index}
                className="px-2 py-1 text-xs bg-dungeon-accent bg-opacity-30 rounded"
              >
                {effect}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default PlayerStats;
