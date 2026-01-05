// Combat Component - Combat UI and actions

import type { CombatState } from '../types/game';

interface CombatProps {
  combat: CombatState;
  onAttack: () => void;
  onFlee: () => void;
  isLoading: boolean;
  className?: string;
}

export function Combat({
  combat,
  onAttack,
  onFlee,
  isLoading,
  className = '',
}: CombatProps) {
  const healthPercentage = (combat.enemy_hp / combat.enemy_max_hp) * 100;

  // Determine enemy health color
  let healthColor = 'bg-red-500';
  if (healthPercentage > 60) {
    healthColor = 'bg-green-500';
  } else if (healthPercentage > 30) {
    healthColor = 'bg-yellow-500';
  }

  return (
    <div className={`game-panel border-2 border-dungeon-danger ${className}`}>
      <div className="text-center mb-4">
        <div className="text-dungeon-danger text-xl font-bold mb-2">
          ⚔️ COMBAT ⚔️
        </div>
        <div className="text-sm text-dungeon-muted">Turn {combat.turn}</div>
      </div>

      {/* Enemy info */}
      <div className="bg-dungeon-bg rounded-lg p-4 mb-4">
        <div className="flex justify-between items-center mb-2">
          <span className="text-lg font-bold text-dungeon-danger">
            {combat.enemy_name}
          </span>
          <span className="text-dungeon-muted text-sm">
            ATK: {combat.enemy_attack}
          </span>
        </div>

        {/* Enemy health bar */}
        <div className="mb-2">
          <div className="flex justify-between text-sm mb-1">
            <span className="text-dungeon-muted">HP</span>
            <span>
              {combat.enemy_hp}/{combat.enemy_max_hp}
            </span>
          </div>
          <div className="health-bar border border-dungeon-border">
            <div
              className={`health-bar-fill ${healthColor} transition-all duration-300`}
              style={{ width: `${healthPercentage}%` }}
            />
          </div>
        </div>

        {/* Enemy ASCII art placeholder */}
        <div className="text-center text-4xl my-4 text-dungeon-danger">
          {combat.enemy_name.toLowerCase().includes('dragon') ? '🐉' :
           combat.enemy_name.toLowerCase().includes('skeleton') ? '💀' :
           combat.enemy_name.toLowerCase().includes('goblin') ? '👺' :
           combat.enemy_name.toLowerCase().includes('spider') ? '🕷️' :
           combat.enemy_name.toLowerCase().includes('rat') ? '🐀' :
           combat.enemy_name.toLowerCase().includes('zombie') ? '🧟' :
           combat.enemy_name.toLowerCase().includes('vampire') ? '🧛' :
           combat.enemy_name.toLowerCase().includes('demon') ? '👿' :
           combat.enemy_name.toLowerCase().includes('slime') ? '🟢' :
           '👹'}
        </div>
      </div>

      {/* Combat actions */}
      <div className="grid grid-cols-2 gap-2">
        <button
          className="game-btn game-btn-danger py-3 text-lg"
          onClick={onAttack}
          disabled={isLoading}
        >
          {isLoading ? (
            <span className="spinner" />
          ) : (
            <>⚔️ Attack</>
          )}
        </button>
        <button
          className="game-btn py-3 text-lg"
          onClick={onFlee}
          disabled={isLoading}
        >
          {isLoading ? (
            <span className="spinner" />
          ) : (
            <>🏃 Flee</>
          )}
        </button>
      </div>

      {/* Combat tips */}
      <div className="mt-4 pt-4 border-t border-dungeon-border text-xs text-dungeon-muted text-center">
        Defeat the enemy or flee to continue exploring
      </div>
    </div>
  );
}

export default Combat;
