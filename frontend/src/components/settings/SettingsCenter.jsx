import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Settings, ExternalLink, Check, X, Loader2, TestTube2 } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL || '';

const SettingsCenter = ({ isOpen, onClose }) => {
  const [providers, setProviders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedProvider, setSelectedProvider] = useState(null);
  const [testResults, setTestResults] = useState({});

  useEffect(() => {
    if (isOpen) {
      loadProviders();
    }
  }, [isOpen]);

  const loadProviders = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API}/api/v1/settings/providers`);
      setProviders(response.data);
    } catch (error) {
      console.error('Failed to load providers:', error);
    } finally {
      setLoading(false);
    }
  };

  const testConnection = async (providerId) => {
    setTestResults(prev => ({ ...prev, [providerId]: 'testing' }));
    try {
      const response = await axios.post(`${API}/api/v1/settings/providers/${providerId}/test`);
      setTestResults(prev => ({ 
        ...prev, 
        [providerId]: response.data.success ? 'success' : 'error' 
      }));
      setTimeout(() => {
        setTestResults(prev => ({ ...prev, [providerId]: null }));
      }, 3000);
    } catch (error) {
      setTestResults(prev => ({ ...prev, [providerId]: 'error' }));
      setTimeout(() => {
        setTestResults(prev => ({ ...prev, [providerId]: null }));
      }, 3000);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-[500] p-4" onClick={onClose}>
      <div 
        className="bg-zinc-900 border border-zinc-700 rounded-lg w-full max-w-6xl max-h-[90vh] shadow-2xl flex flex-col"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-6 border-b border-zinc-800 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-500/10 rounded-lg">
              <Settings size={24} className="text-blue-400" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-white">Settings Center</h2>
              <p className="text-sm text-zinc-400">Konfiguriere Provider und Systemeinstellungen</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-zinc-400 hover:text-white transition-colors"
          >
            <X size={24} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <Loader2 size={32} className="animate-spin text-zinc-500" />
            </div>
          ) : (
            <div className="space-y-6">
              {/* LLM Providers */}
              <section>
                <h3 className="text-lg font-semibold text-white mb-4">🤖 LLM Provider</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {providers.filter(p => p.category === 'llm').map(provider => (
                    <ProviderCard
                      key={provider.id}
                      provider={provider}
                      testStatus={testResults[provider.id]}
                      onTest={() => testConnection(provider.id)}
                    />
                  ))}
                </div>
              </section>

              {/* CI/CD Providers */}
              <section>
                <h3 className="text-lg font-semibold text-white mb-4">🔧 CI/CD & Integration</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {providers.filter(p => p.category === 'ci_cd').map(provider => (
                    <ProviderCard
                      key={provider.id}
                      provider={provider}
                      testStatus={testResults[provider.id]}
                      onTest={() => testConnection(provider.id)}
                    />
                  ))}
                </div>
              </section>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

const ProviderCard = ({ provider, testStatus, onTest }) => {
  const getStatusColor = () => {
    if (provider.configured) return 'text-emerald-400';
    return 'text-zinc-500';
  };

  const getStatusText = () => {
    if (provider.configured) return 'Configured';
    return 'Not configured';
  };

  return (
    <div className="bg-zinc-800 border border-zinc-700 rounded-lg p-4 hover:border-zinc-600 transition-colors">
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-2xl">{provider.icon_emoji}</span>
          <div>
            <h4 className="font-medium text-white">{provider.name}</h4>
            <p className="text-xs text-zinc-500">{provider.category}</p>
          </div>
        </div>
        <div className={`text-xs font-medium ${getStatusColor()}`}>
          {getStatusText()}
        </div>
      </div>

      {/* Description */}
      <p className="text-sm text-zinc-400 mb-4 line-clamp-2">{provider.description}</p>

      {/* Actions */}
      <div className="space-y-2">
        {/* Get API Key - Prominent Button */}
        <a
          href={provider.create_key_url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center justify-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-medium text-sm transition-colors w-full group"
        >
          <span>Get API Key</span>
          <ExternalLink size={16} className="group-hover:translate-x-0.5 transition-transform" />
        </a>

        {/* Docs & Test Buttons */}
        <div className="flex gap-2">
          <a
            href={provider.docs_url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex-1 flex items-center justify-center px-3 py-2 bg-zinc-700 hover:bg-zinc-600 text-zinc-300 rounded text-sm transition-colors"
          >
            Docs
          </a>
          <button
            onClick={onTest}
            disabled={testStatus === 'testing'}
            className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded text-sm transition-colors ${
              testStatus === 'success'
                ? 'bg-emerald-500/20 text-emerald-400'
                : testStatus === 'error'
                ? 'bg-red-500/20 text-red-400'
                : testStatus === 'testing'
                ? 'bg-zinc-700 text-zinc-400'
                : 'bg-zinc-700 hover:bg-zinc-600 text-zinc-300'
            }`}
          >
            {testStatus === 'testing' ? (
              <><Loader2 size={14} className="animate-spin" /> Testing</>
            ) : testStatus === 'success' ? (
              <><Check size={14} /> Success</>
            ) : testStatus === 'error' ? (
              <><X size={14} /> Error</>
            ) : (
              <><TestTube2 size={14} /> Test</>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default SettingsCenter;
