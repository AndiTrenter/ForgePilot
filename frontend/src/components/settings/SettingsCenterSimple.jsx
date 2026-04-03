import React, { useState, useEffect } from 'react';
import { X } from 'lucide-react';

/**
 * SUPER SIMPLE Settings Center - GARANTIERT FUNKTIONIEREND
 */
const SettingsCenterSimple = ({ isOpen, onClose }) => {
  const [providers, setProviders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isOpen) {
      console.log('🔍 SettingsCenter: Loading providers...');
      loadProviders();
    }
  }, [isOpen]);

  const loadProviders = async () => {
    try {
      setLoading(true);
      setError(null);
      
      console.log('📡 Fetching: /api/v1/settings/providers');
      const response = await fetch('/api/v1/settings/providers');
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      
      const data = await response.json();
      console.log('✅ Providers loaded:', data);
      console.log('📊 Provider count:', data.length);
      
      setProviders(data);
      setLoading(false);
    } catch (err) {
      console.error('❌ Load error:', err);
      setError(err.message);
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  console.log('🎨 Rendering with providers:', providers);

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-[500] p-4" onClick={onClose}>
      <div 
        className="bg-zinc-900 border border-zinc-700 rounded-lg w-full max-w-6xl max-h-[90vh] shadow-2xl flex flex-col"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-6 border-b border-zinc-800 flex items-center justify-between shrink-0">
          <h2 className="text-2xl font-bold text-white">Settings Center (Simple)</h2>
          <button onClick={onClose} className="text-zinc-400 hover:text-white">
            <X size={24} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {/* Debug Info */}
          <div className="mb-4 p-4 bg-zinc-800 rounded border border-zinc-700 text-xs font-mono">
            <div>Loading: {loading ? 'true' : 'false'}</div>
            <div>Error: {error || 'null'}</div>
            <div>Providers count: {providers.length}</div>
            <div>Providers: {JSON.stringify(providers.map(p => p.id))}</div>
          </div>

          {loading && (
            <div className="text-center text-zinc-400 py-12">
              Loading...
            </div>
          )}

          {error && (
            <div className="text-center text-red-400 py-12">
              Error: {error}
            </div>
          )}

          {!loading && !error && providers.length === 0 && (
            <div className="text-center text-zinc-400 py-12">
              Keine Provider gefunden
            </div>
          )}

          {!loading && !error && providers.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {providers.map(provider => (
                <div 
                  key={provider.id}
                  className="bg-zinc-800 border border-zinc-700 rounded-lg p-4"
                >
                  <div className="text-2xl mb-2">{provider.icon_emoji || '🔧'}</div>
                  <h3 className="text-white font-semibold mb-1">{provider.name}</h3>
                  <p className="text-xs text-zinc-500 mb-2">{provider.category}</p>
                  <p className="text-sm text-zinc-400 mb-3">{provider.description}</p>
                  
                  <a
                    href={provider.create_key_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block w-full px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded text-center text-sm"
                  >
                    Get API Key →
                  </a>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default SettingsCenterSimple;
