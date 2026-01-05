// Inventory Component - Displays and manages player inventory

import { useState } from 'react';
import type { InventoryItem } from '../types/game';

interface InventoryProps {
  items: InventoryItem[];
  onUseItem: (itemId: string) => void;
  isLoading: boolean;
  className?: string;
}

const categoryIcons: Record<string, string> = {
  weapon: '⚔️',
  armor: '🛡️',
  consumable: '🧪',
  scroll: '📜',
  tool: '🔧',
  key_item: '🔑',
  treasure: '💎',
  material: '🪨',
  misc: '📦',
};

const categoryOrder = [
  'weapon',
  'armor',
  'consumable',
  'scroll',
  'tool',
  'key_item',
  'treasure',
  'material',
  'misc',
];

export function Inventory({ items, onUseItem, isLoading, className = '' }: InventoryProps) {
  const [selectedItem, setSelectedItem] = useState<string | null>(null);

  // Group items by category
  const groupedItems = items.reduce((acc, item) => {
    const category = item.category || 'misc';
    if (!acc[category]) {
      acc[category] = [];
    }
    acc[category].push(item);
    return acc;
  }, {} as Record<string, InventoryItem[]>);

  // Sort categories
  const sortedCategories = Object.keys(groupedItems).sort(
    (a, b) => categoryOrder.indexOf(a) - categoryOrder.indexOf(b)
  );

  const handleItemClick = (itemId: string) => {
    setSelectedItem(selectedItem === itemId ? null : itemId);
  };

  const handleUseItem = (itemId: string) => {
    onUseItem(itemId);
    setSelectedItem(null);
  };

  if (items.length === 0) {
    return (
      <div className={`game-panel ${className}`}>
        <h2 className="text-lg font-bold text-dungeon-accent mb-4">Inventory</h2>
        <div className="text-dungeon-muted text-center py-4">
          Your inventory is empty
        </div>
      </div>
    );
  }

  return (
    <div className={`game-panel ${className}`}>
      <h2 className="text-lg font-bold text-dungeon-accent mb-4">
        Inventory ({items.length})
      </h2>

      <div className="space-y-4 max-h-64 overflow-y-auto">
        {sortedCategories.map((category) => (
          <div key={category}>
            <div className="text-sm text-dungeon-muted mb-2 flex items-center gap-1">
              <span>{categoryIcons[category] || '📦'}</span>
              <span className="capitalize">{category.replace('_', ' ')}</span>
            </div>

            <div className="space-y-1">
              {groupedItems[category].map((item) => (
                <div
                  key={item.id}
                  className={`
                    p-2 rounded cursor-pointer transition-colors
                    ${selectedItem === item.id
                      ? 'bg-dungeon-accent bg-opacity-30 border border-dungeon-accent'
                      : 'bg-dungeon-bg hover:bg-dungeon-border'
                    }
                  `}
                  onClick={() => handleItemClick(item.id)}
                >
                  <div className="flex justify-between items-center">
                    <span className={item.equipped ? 'text-dungeon-success' : ''}>
                      {item.name}
                      {item.equipped && ' [E]'}
                    </span>
                    {item.quantity > 1 && (
                      <span className="text-dungeon-muted text-sm">
                        x{item.quantity}
                      </span>
                    )}
                  </div>

                  {selectedItem === item.id && (
                    <div className="mt-2 pt-2 border-t border-dungeon-border">
                      <p className="text-sm text-dungeon-muted mb-2">
                        {item.description || 'No description'}
                      </p>
                      {(item.category === 'consumable' || item.category === 'scroll') && (
                        <button
                          className="game-btn game-btn-primary text-sm w-full"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleUseItem(item.id);
                          }}
                          disabled={isLoading}
                        >
                          {isLoading ? 'Using...' : 'Use'}
                        </button>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default Inventory;
