// Game Map Component - Renders the tile-based dungeon map

import { useMemo } from 'react';

interface GameMapProps {
  map: string[];
  className?: string;
}

// Map characters to CSS classes for coloring
const getTileClass = (char: string): string => {
  switch (char) {
    case '@':
      return 'tile-player';
    case '&':
    case 'Ω':
      return 'tile-enemy';
    case '☺':
      return 'tile-npc';
    case '$':
    case '■':
    case '□':
      return 'tile-item';
    case '▓':
    case '╔':
    case '═':
    case '╗':
    case '║':
    case '╚':
    case '╝':
    case '╠':
    case '╣':
    case '╬':
      return 'tile-wall';
    case '░':
    case '.':
      return 'tile-floor';
    case '≈':
      return 'tile-water';
    case '~':
      return 'tile-lava';
    case '+':
    case '/':
      return 'tile-door';
    case '>':
    case '<':
      return 'tile-stairs';
    case '^':
      return 'tile-trap';
    case '◊':
    case '♨':
      return 'tile-chest';
    default:
      return 'tile-floor';
  }
};

export function GameMap({ map, className = '' }: GameMapProps) {
  // Process the map to add color spans
  const coloredMap = useMemo(() => {
    return map.map((row, rowIndex) => (
      <div key={rowIndex} className="flex">
        {row.split('').map((char, charIndex) => (
          <span key={charIndex} className={getTileClass(char)}>
            {char}
          </span>
        ))}
      </div>
    ));
  }, [map]);

  if (!map || map.length === 0) {
    return (
      <div className={`game-panel ${className}`}>
        <div className="text-dungeon-muted text-center py-8">
          No map data available
        </div>
      </div>
    );
  }

  return (
    <div className={`game-panel ${className}`}>
      <div className="tile-map text-xl md:text-2xl lg:text-3xl flex flex-col items-center">
        {coloredMap}
      </div>
    </div>
  );
}

export default GameMap;
