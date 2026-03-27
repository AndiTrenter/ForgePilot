import { useEffect, useCallback } from 'react';

// Keyboard shortcuts configuration
export const SHORTCUTS = {
  SAVE: { key: 's', ctrl: true, description: 'Speichern' },
  SAVE_ALL: { key: 's', ctrl: true, shift: true, description: 'Alle speichern' },
  NEW_FILE: { key: 'n', ctrl: true, description: 'Neue Datei' },
  TOGGLE_PREVIEW: { key: 'p', ctrl: true, description: 'Preview ein/aus' },
  TOGGLE_SIDEBAR: { key: 'b', ctrl: true, description: 'Sidebar ein/aus' },
  FOCUS_CHAT: { key: 'k', ctrl: true, description: 'Chat fokussieren' },
  SEND_MESSAGE: { key: 'Enter', ctrl: true, description: 'Nachricht senden' },
  REFRESH_PREVIEW: { key: 'r', ctrl: true, shift: true, description: 'Preview neu laden' },
  CLOSE_TAB: { key: 'w', ctrl: true, description: 'Tab schließen' },
  SETTINGS: { key: ',', ctrl: true, description: 'Einstellungen' },
};

// Hook for using keyboard shortcuts
export const useKeyboardShortcuts = (handlers) => {
  const handleKeyDown = useCallback((event) => {
    const { key, ctrlKey, metaKey, shiftKey } = event;
    const ctrl = ctrlKey || metaKey; // Support both Windows/Linux (Ctrl) and Mac (Cmd)
    
    // Check each shortcut
    for (const [action, shortcut] of Object.entries(SHORTCUTS)) {
      const matchesKey = key.toLowerCase() === shortcut.key.toLowerCase();
      const matchesCtrl = shortcut.ctrl ? ctrl : !ctrl;
      const matchesShift = shortcut.shift ? shiftKey : !shiftKey;
      
      if (matchesKey && matchesCtrl && matchesShift) {
        if (handlers[action]) {
          event.preventDefault();
          handlers[action]();
          return;
        }
      }
    }
  }, [handlers]);

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);
};

// Keyboard shortcuts help modal content
export const ShortcutsHelp = () => (
  <div className="space-y-2">
    <h3 className="text-sm font-semibold text-zinc-300 mb-3">Tastaturkürzel</h3>
    {Object.entries(SHORTCUTS).map(([action, shortcut]) => (
      <div key={action} className="flex items-center justify-between text-xs">
        <span className="text-zinc-400">{shortcut.description}</span>
        <kbd className="px-2 py-0.5 bg-zinc-800 border border-zinc-700 rounded text-zinc-300">
          {shortcut.ctrl && 'Ctrl+'}
          {shortcut.shift && 'Shift+'}
          {shortcut.key.toUpperCase()}
        </kbd>
      </div>
    ))}
  </div>
);
