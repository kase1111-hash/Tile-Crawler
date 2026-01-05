// Dialogue Component - NPC conversation interface

import { useState } from 'react';
import type { DialogueData } from '../types/game';

interface DialogueProps {
  dialogue: DialogueData;
  onRespond: (message: string) => void;
  onClose: () => void;
  isLoading: boolean;
  className?: string;
}

export function Dialogue({
  dialogue,
  onRespond,
  onClose,
  isLoading,
  className = '',
}: DialogueProps) {
  const [response, setResponse] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (response.trim()) {
      onRespond(response.trim());
      setResponse('');
    }
  };

  const quickResponses = [
    'Hello',
    'Tell me more',
    'What do you know?',
    'Goodbye',
  ];

  return (
    <div className={`game-panel border-2 border-dungeon-warning ${className}`}>
      <div className="flex justify-between items-center mb-4">
        <div className="flex items-center gap-2">
          <span className="text-2xl">☺</span>
          <span className="text-lg font-bold text-dungeon-warning">
            {dialogue.npc_name}
          </span>
        </div>
        <button
          className="text-dungeon-muted hover:text-dungeon-text"
          onClick={onClose}
          title="Close dialogue"
        >
          ✕
        </button>
      </div>

      {/* NPC Speech */}
      <div className="bg-dungeon-bg rounded-lg p-4 mb-4">
        <p className="text-dungeon-text leading-relaxed italic">
          "{dialogue.speech}"
        </p>
        {dialogue.mood && dialogue.mood !== 'neutral' && (
          <div className="text-sm text-dungeon-muted mt-2">
            *{dialogue.mood}*
          </div>
        )}
      </div>

      {/* Hints */}
      {dialogue.hints && dialogue.hints.length > 0 && (
        <div className="mb-4 text-sm">
          <div className="text-dungeon-muted mb-1">Hints:</div>
          <ul className="list-disc list-inside text-dungeon-info">
            {dialogue.hints.map((hint, index) => (
              <li key={index}>{hint}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Trade available indicator */}
      {dialogue.trade_available && (
        <div className="mb-4 p-2 bg-dungeon-success bg-opacity-20 rounded text-sm text-dungeon-success">
          💰 This NPC has items to trade
        </div>
      )}

      {/* Quick responses */}
      <div className="flex flex-wrap gap-2 mb-4">
        {quickResponses.map((resp) => (
          <button
            key={resp}
            className="game-btn text-sm py-1"
            onClick={() => onRespond(resp)}
            disabled={isLoading}
          >
            {resp}
          </button>
        ))}
      </div>

      {/* Custom response input */}
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={response}
          onChange={(e) => setResponse(e.target.value)}
          placeholder="Say something..."
          className="flex-1 bg-dungeon-bg border border-dungeon-border rounded px-3 py-2 text-dungeon-text placeholder-dungeon-muted focus:outline-none focus:border-dungeon-accent"
          disabled={isLoading}
        />
        <button
          type="submit"
          className="game-btn game-btn-primary"
          disabled={isLoading || !response.trim()}
        >
          {isLoading ? <span className="spinner" /> : 'Send'}
        </button>
      </form>
    </div>
  );
}

export default Dialogue;
