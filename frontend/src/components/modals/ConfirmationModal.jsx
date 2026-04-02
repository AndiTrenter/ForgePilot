import React from 'react';

/**
 * Confirmation Modal Component
 * Wiederverwendbares Bestätigungsdialog-Modal
 */

const ConfirmationModal = ({ 
  isOpen, 
  onClose, 
  onConfirm, 
  title, 
  message, 
  confirmText = "Bestätigen", 
  confirmColor = "bg-red-600 hover:bg-red-500" 
}) => {
  if (!isOpen) return null;
  
  return (
    <div 
      className="fixed inset-0 bg-black/80 flex items-center justify-center z-[300] p-4"
      onClick={onClose}
    >
      <div 
        className="bg-zinc-900 border border-zinc-700 rounded-lg w-full max-w-md shadow-2xl"
        onClick={e => e.stopPropagation()}
      >
        <div className="p-4 border-b border-zinc-800">
          <h3 className="text-lg font-medium text-white">{title}</h3>
        </div>
        <div className="p-4">
          <p className="text-zinc-300">{message}</p>
        </div>
        <div className="p-4 border-t border-zinc-800 flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-white rounded transition-colors"
          >
            Abbrechen
          </button>
          <button
            onClick={() => {
              onConfirm();
              onClose();
            }}
            className={`px-4 py-2 text-white rounded transition-colors ${confirmColor}`}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ConfirmationModal;
