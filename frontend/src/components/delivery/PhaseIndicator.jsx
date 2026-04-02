import React from 'react';
import { CheckCircle2, Circle, Loader2 } from 'lucide-react';

/**
 * Phase Indicator Component
 * Zeigt den aktuellen Delivery-Phase-Status an
 */

const PHASES = [
  { id: 'discovery', label: 'Discovery', emoji: '🔍' },
  { id: 'design', label: 'Solution Design', emoji: '🎨' },
  { id: 'planning', label: 'Planning', emoji: '📋' },
  { id: 'provisioning', label: 'Environment Setup', emoji: '⚙️' },
  { id: 'implementing', label: 'Implementation', emoji: '💻' },
  { id: 'reviewing', label: 'Code Review', emoji: '👀' },
  { id: 'testing', label: 'Testing', emoji: '🧪' },
  { id: 'debugging', label: 'Debugging', emoji: '🐛' },
  { id: 'ready_for_handover', label: 'Ready for Handover', emoji: '📦' },
  { id: 'completed', label: 'Completed', emoji: '🎉' }
];

const PhaseIndicator = ({ currentPhase = 'discovery', className = '' }) => {
  const currentIndex = PHASES.findIndex(p => p.id === currentPhase);

  return (
    <div className={`flex items-center gap-2 overflow-x-auto pb-2 ${className}`}>
      {PHASES.map((phase, index) => {
        const isActive = index === currentIndex;
        const isCompleted = index < currentIndex;
        const isFuture = index > currentIndex;

        return (
          <div
            key={phase.id}
            className={`flex items-center gap-2 px-3 py-2 rounded-lg border transition-all ${
              isActive
                ? 'bg-blue-500/10 border-blue-500 text-blue-400'
                : isCompleted
                ? 'bg-green-500/10 border-green-700 text-green-400'
                : 'bg-zinc-900 border-zinc-800 text-zinc-500'
            }`}
          >
            <span className="text-lg">{phase.emoji}</span>
            <span className="text-sm font-medium whitespace-nowrap">{phase.label}</span>
            {isActive && <Loader2 size={14} className="animate-spin ml-1" />}
            {isCompleted && <CheckCircle2 size={14} className="ml-1" />}
            {isFuture && <Circle size={14} className="ml-1 opacity-30" />}
          </div>
        );
      })}
    </div>
  );
};

export default PhaseIndicator;
