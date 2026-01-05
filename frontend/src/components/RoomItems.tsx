// Room Items Component - Shows items available in the current room

import type { RoomItem } from '../types/game';

interface RoomItemsProps {
  items: RoomItem[];
  onTakeItem: (itemId: string) => void;
  isLoading: boolean;
  className?: string;
}

export function RoomItems({ items, onTakeItem, isLoading, className = '' }: RoomItemsProps) {
  if (items.length === 0) {
    return null;
  }

  return (
    <div className={`game-panel ${className}`}>
      <h2 className="text-lg font-bold text-dungeon-info mb-3">
        Items Here
      </h2>

      <div className="space-y-2">
        {items.map((item, index) => (
          <div
            key={`${item.id}-${index}`}
            className="flex items-center justify-between bg-dungeon-bg p-2 rounded"
          >
            <div className="flex items-center gap-2">
              <span className="text-dungeon-info">$</span>
              <span>{item.name}</span>
              {item.quantity && item.quantity > 1 && (
                <span className="text-dungeon-muted text-sm">x{item.quantity}</span>
              )}
            </div>
            <button
              className="game-btn game-btn-primary text-sm py-1 px-3"
              onClick={() => onTakeItem(item.id)}
              disabled={isLoading}
            >
              Take
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

export default RoomItems;
