// Narrative Component - Displays story text and events

interface NarrativeProps {
  text: string;
  recentEvents?: string;
  className?: string;
}

export function Narrative({ text, recentEvents, className = '' }: NarrativeProps) {
  return (
    <div className={`game-panel ${className}`}>
      {/* Main narrative text */}
      <div className="mb-4">
        <div className="text-dungeon-accent text-sm mb-2 font-bold">
          ◆ Current
        </div>
        <p className="text-dungeon-text leading-relaxed">
          {text || 'The dungeon awaits...'}
        </p>
      </div>

      {/* Recent events log */}
      {recentEvents && (
        <div className="pt-4 border-t border-dungeon-border">
          <div className="text-dungeon-muted text-sm mb-2 font-bold">
            ◆ Recent Events
          </div>
          <div className="text-sm text-dungeon-muted space-y-1 max-h-32 overflow-y-auto">
            {recentEvents.split('\n').map((event, index) => (
              <div key={index} className="leading-relaxed">
                {event}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default Narrative;
