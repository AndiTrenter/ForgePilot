import React, { useState, useEffect, useRef } from 'react';
import { X, Copy, Play, Pause, Video, VideoOff, Loader2, Terminal, CheckCircle } from 'lucide-react';
import axios from 'axios';

const API = process.env.NODE_ENV === 'production' ? '/api' : `${process.env.REACT_APP_BACKEND_URL}/api`;

const DeployModal = ({ projectId, projectName, onClose }) => {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [sending, setSending] = useState(false);
  const [screenSharing, setScreenSharing] = useState(false);
  const [deployStatus, setDeployStatus] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  
  const messagesEndRef = useRef(null);
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const intervalRef = useRef(null);
  
  // Load deployment messages
  useEffect(() => {
    loadMessages();
    loadStatus();
    const interval = setInterval(() => {
      loadMessages();
      loadStatus();
    }, 3000);
    return () => clearInterval(interval);
  }, [projectId]);
  
  // Auto-scroll
  useEffect(() => {
    scrollToBottom();
  }, [messages]);
  
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };
  
  const loadMessages = async () => {
    try {
      const res = await axios.get(`${API}/projects/${projectId}/deploy/messages`);
      setMessages(res.data);
    } catch (e) {
      console.error('Failed to load messages:', e);
    }
  };
  
  const loadStatus = async () => {
    try {
      const res = await axios.get(`${API}/projects/${projectId}/deploy/status`);
      if (res.data.exists) {
        setDeployStatus(res.data);
      }
    } catch (e) {
      console.error('Failed to load status:', e);
    }
  };
  
  const sendMessage = async () => {
    if (!inputValue.trim() || sending) return;
    
    setSending(true);
    try {
      await axios.post(`${API}/projects/${projectId}/deploy/message`, {
        content: inputValue.trim()
      });
      setInputValue('');
      await loadMessages();
    } catch (e) {
      console.error('Failed to send message:', e);
      alert('Nachricht konnte nicht gesendet werden');
    } finally {
      setSending(false);
    }
  };
  
  const startScreenSharing = async () => {
    try {
      // Check if API is available
      if (!navigator.mediaDevices || !navigator.mediaDevices.getDisplayMedia) {
        alert('Screen-Sharing wird von diesem Browser nicht unterstützt. Bitte verwende Chrome, Edge oder Firefox.');
        return;
      }
      
      // Request screen capture
      const stream = await navigator.mediaDevices.getDisplayMedia({
        video: {
          displaySurface: 'monitor',
          cursor: 'always'
        },
        audio: false
      });
      
      streamRef.current = stream;
      
      // Show video preview (optional, can be hidden)
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.play();
      }
      
      setScreenSharing(true);
      
      // Start auto-capture every 5 seconds
      intervalRef.current = setInterval(() => {
        captureAndAnalyze();
      }, 5000);
      
      // Handle stream end
      stream.getVideoTracks()[0].addEventListener('ended', () => {
        stopScreenSharing();
      });
      
    } catch (e) {
      console.error('Screen sharing failed:', e);
      
      let errorMsg = 'Screen-Sharing konnte nicht gestartet werden.\n\n';
      
      if (e.name === 'NotAllowedError') {
        errorMsg += '❌ Berechtigung verweigert.\n\n' +
                   '💡 Lösung:\n' +
                   '1. Klicke erneut auf "Screen-Sharing starten"\n' +
                   '2. Wähle dein Browser-Fenster oder Bildschirm\n' +
                   '3. Klicke auf "Teilen"';
      } else if (e.name === 'NotSupportedError') {
        errorMsg += '❌ Dein Browser unterstützt kein Screen-Sharing.\n\n' +
                   '💡 Empfehlung: Verwende Chrome, Edge oder Firefox.';
      } else {
        errorMsg += `❌ Fehler: ${e.message}\n\n` +
                   '💡 Versuche es erneut oder lade Screenshots manuell hoch.';
      }
      
      alert(errorMsg);
    }
  };
  
  const stopScreenSharing = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    setScreenSharing(false);
  };
  
  const captureAndAnalyze = async () => {
    if (!streamRef.current || analyzing) return;
    
    setAnalyzing(true);
    
    try {
      // Get video track
      const video = videoRef.current;
      if (!video) return;
      
      // Create canvas and capture frame
      const canvas = canvasRef.current || document.createElement('canvas');
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      
      const ctx = canvas.getContext('2d');
      ctx.drawImage(video, 0, 0);
      
      // Convert to base64
      const base64 = canvas.toDataURL('image/png').split(',')[1];
      
      // Send to backend for analysis
      const res = await axios.post(`${API}/projects/${projectId}/deploy/analyze`, {
        screenshot: base64
      });
      
      // Reload messages to show new analysis
      await loadMessages();
      
    } catch (e) {
      console.error('Screenshot analysis failed:', e);
    } finally {
      setAnalyzing(false);
    }
  };
  
  const pauseDeployment = async () => {
    try {
      await axios.post(`${API}/projects/${projectId}/deploy/pause`);
      stopScreenSharing();
      await loadStatus();
    } catch (e) {
      console.error('Failed to pause:', e);
    }
  };
  
  const resumeDeployment = async () => {
    try {
      await axios.post(`${API}/projects/${projectId}/deploy/resume`);
      await loadStatus();
    } catch (e) {
      console.error('Failed to resume:', e);
    }
  };
  
  const completeDeployment = async () => {
    if (!confirm('Deployment als abgeschlossen markieren?')) return;
    
    try {
      await axios.post(`${API}/projects/${projectId}/deploy/complete`);
      stopScreenSharing();
      alert('Deployment abgeschlossen!');
      onClose();
    } catch (e) {
      console.error('Failed to complete:', e);
    }
  };
  
  const copyCommand = (command) => {
    navigator.clipboard.writeText(command);
    // TODO: Show toast notification
  };
  
  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-[200] p-4">
      <div className="bg-zinc-900 border border-zinc-700 rounded-lg w-full max-w-4xl h-[80vh] shadow-2xl flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-zinc-800 flex items-center justify-between shrink-0">
          <div>
            <h2 className="text-lg font-medium text-white flex items-center gap-2">
              <Terminal size={20} className="text-blue-400" />
              Deployment: {projectName}
            </h2>
            <p className="text-sm text-zinc-400 mt-1">
              Status: {deployStatus?.status || 'Laden...'}
              {screenSharing && (
                <span className="ml-2 text-emerald-400">
                  • Screen-Sharing aktiv {analyzing && '(Analysiere...)'}
                </span>
              )}
            </p>
          </div>
          <button onClick={onClose} className="text-zinc-400 hover:text-white">
            <X size={20} />
          </button>
        </div>
        
        {/* Controls */}
        <div className="p-3 border-b border-zinc-800 flex items-center gap-2 shrink-0 bg-zinc-950">
          {!screenSharing ? (
            <button
              onClick={startScreenSharing}
              className="flex items-center gap-2 px-3 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded text-sm font-medium"
            >
              <Video size={16} />
              Screen-Sharing starten
            </button>
          ) : (
            <button
              onClick={stopScreenSharing}
              className="flex items-center gap-2 px-3 py-2 bg-red-600 hover:bg-red-500 text-white rounded text-sm font-medium"
            >
              <VideoOff size={16} />
              Screen-Sharing stoppen
            </button>
          )}
          
          {deployStatus?.status === 'active' && (
            <button
              onClick={pauseDeployment}
              className="flex items-center gap-2 px-3 py-2 bg-amber-600 hover:bg-amber-500 text-white rounded text-sm"
            >
              <Pause size={16} />
              Pausieren
            </button>
          )}
          
          {deployStatus?.status === 'paused' && (
            <button
              onClick={resumeDeployment}
              className="flex items-center gap-2 px-3 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded text-sm"
            >
              <Play size={16} />
              Fortsetzen
            </button>
          )}
          
          <button
            onClick={completeDeployment}
            className="flex items-center gap-2 px-3 py-2 bg-zinc-700 hover:bg-zinc-600 text-white rounded text-sm ml-auto"
          >
            <CheckCircle size={16} />
            Abschließen
          </button>
        </div>
        
        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map((msg) => (
            <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[80%] rounded-lg p-3 ${
                msg.role === 'user' ? 'bg-blue-600 text-white' :
                msg.role === 'system' ? 'bg-zinc-800 text-zinc-300 border border-zinc-700' :
                'bg-zinc-800 text-white'
              }`}>
                {msg.role === 'assistant' && msg.screenshot_analyzed && (
                  <div className="text-xs text-emerald-400 mb-1">📸 Screenshot analysiert</div>
                )}
                <div className="text-sm whitespace-pre-wrap">{msg.content}</div>
                
                {/* Commands */}
                {msg.commands && msg.commands.length > 0 && (
                  <div className="mt-3 space-y-2">
                    {msg.commands.map((cmd, idx) => (
                      <div key={idx} className="bg-zinc-950 border border-zinc-700 rounded p-2 flex items-center justify-between gap-2">
                        <code className="text-emerald-400 text-xs font-mono flex-1">{cmd}</code>
                        <button
                          onClick={() => copyCommand(cmd)}
                          className="p-1.5 hover:bg-zinc-800 rounded text-zinc-400 hover:text-white"
                          title="Kopieren"
                        >
                          <Copy size={14} />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
                
                <div className="text-xs text-zinc-500 mt-2">
                  {new Date(msg.created_at).toLocaleTimeString('de-DE')}
                </div>
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>
        
        {/* Input */}
        <div className="p-4 border-t border-zinc-800 shrink-0">
          <div className="flex gap-2">
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage()}
              placeholder="Frage stellen oder Problem schildern..."
              className="flex-1 px-3 py-2 bg-zinc-800 border border-zinc-700 rounded text-white placeholder-zinc-500 focus:outline-none focus:border-blue-500"
              disabled={sending}
            />
            <button
              onClick={sendMessage}
              disabled={sending || !inputValue.trim()}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {sending ? <Loader2 size={16} className="animate-spin" /> : 'Senden'}
            </button>
          </div>
        </div>
      </div>
      
      {/* Hidden video and canvas for screen capture */}
      <video ref={videoRef} style={{ display: 'none' }} muted playsInline />
      <canvas ref={canvasRef} style={{ display: 'none' }} />
    </div>
  );
};

export default DeployModal;
