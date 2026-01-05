/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        'tileset': ['DungeonTiles', 'Courier New', 'monospace'],
        'game': ['Press Start 2P', 'Courier New', 'monospace'],
      },
      colors: {
        'dungeon': {
          'bg': '#0a0a0f',
          'panel': '#1a1a2e',
          'border': '#3d3d5c',
          'text': '#e0e0e0',
          'muted': '#8888aa',
          'accent': '#7b68ee',
          'danger': '#dc3545',
          'success': '#28a745',
          'warning': '#ffc107',
          'info': '#17a2b8',
        },
        'tile': {
          'wall': '#4a4a4a',
          'floor': '#2a2a2a',
          'player': '#00ff00',
          'enemy': '#ff4444',
          'npc': '#ffff00',
          'item': '#00ffff',
          'water': '#0066ff',
          'lava': '#ff6600',
        }
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'blink': 'blink 1s step-end infinite',
      },
      keyframes: {
        blink: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0' },
        }
      }
    },
  },
  plugins: [],
}
