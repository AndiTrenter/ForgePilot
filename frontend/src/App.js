import React, { useState, useEffect, useRef } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, useNavigate, useParams } from "react-router-dom";
import axios from "axios";
import SettingsCenter from "./components/settings/SettingsCenter";
import { 
  Send, Loader2, GitBranch, FolderGit2, Play, RefreshCw, 
  Home, Settings, ChevronRight, FileCode, Terminal, 
  CheckCircle2, Zap, Bug, Eye, X, Code, ListTodo,
  Folder, File, ChevronDown, Save, LayoutPanelLeft, GitCommit,
  Check, Circle, ArrowRight, Lock, Globe, Upload, Search,
  ExternalLink, Mic, MicOff, Square, PanelRightClose, PanelRightOpen,
  Maximize2, Minimize2, Rocket, Paperclip, Image as ImageIcon,
  Trash2, Download, Archive, ArchiveRestore, MonitorPlay, CloudDownload
} from "lucide-react";
import DeployModal from "./DeployModal";
import Prism from 'prismjs';
import 'prismjs/themes/prism-tomorrow.css';
import 'prismjs/components/prism-javascript';
import 'prismjs/components/prism-css';
import 'prismjs/components/prism-markup';
import 'prismjs/components/prism-python';
import 'prismjs/components/prism-json';

// API Base URL - uses relative path for production (nginx proxy)
// In development, REACT_APP_BACKEND_URL can override
const getApiBase = () => {
  const envUrl = process.env.REACT_APP_BACKEND_URL;
  if (process.env.NODE_ENV === 'production') return '/api';
  if (envUrl) return `${envUrl}/api`;
  return '/api';
};
const API = getApiBase();
// For preview URLs - use relative path in production (nginx proxies to backend)
// The preview URL from API is like "/api/projects/{id}/preview/index.html"
// In production, this works directly. In dev, we need the full backend URL.
const getPreviewBase = () => {
  if (process.env.NODE_ENV === 'production') return '';
  return process.env.REACT_APP_BACKEND_URL || '';
};
const PREVIEW_BASE = getPreviewBase();

// ============== API Functions ==============
const api = {
  getProjects: (includeArchived = false) => axios.get(`${API}/projects`, { params: { include_archived: includeArchived } }),
  createProject: (data) => axios.post(`${API}/projects`, data),
  getProject: (id) => axios.get(`${API}/projects/${id}`),
  deleteProject: (id) => axios.delete(`${API}/projects/${id}`),
  downloadProject: (id) => axios.get(`${API}/projects/${id}/download`, { responseType: 'blob' }),
  archiveProject: (id) => axios.post(`${API}/projects/${id}/archive`),
  unarchiveProject: (id) => axios.post(`${API}/projects/${id}/unarchive`),
  getArchivedProjects: () => axios.get(`${API}/projects/archived/list`),
  getMessages: (projectId) => axios.get(`${API}/projects/${projectId}/messages`),
  getAgents: (projectId) => axios.get(`${API}/projects/${projectId}/agents`),
  getLogs: (projectId) => axios.get(`${API}/projects/${projectId}/logs`),
  getRoadmap: (projectId) => axios.get(`${API}/projects/${projectId}/roadmap`),
  getFiles: (projectId, path = "") => axios.get(`${API}/projects/${projectId}/files`, { params: { path } }),
  saveFile: (projectId, path, content) => axios.put(`${API}/projects/${projectId}/files`, { path, content }),
  importGitHub: (data) => axios.post(`${API}/github/import`, data),
  commitGitHub: (data) => axios.post(`${API}/github/commit`, data),
  getGitHubRepos: () => axios.get(`${API}/github/repos`),
  getGitHubBranches: (repo) => axios.get(`${API}/github/branches`, { params: { repo } }),
  getPreviewInfo: (projectId) => axios.get(`${API}/projects/${projectId}/preview-info`),
  pushToGitHub: (projectId) => axios.post(`${API}/projects/${projectId}/push`),
};

// ============== Tooltip Component ==============

const Tooltip = ({ children, text, position = "bottom" }) => {
  const [show, setShow] = useState(false);
  const timeoutRef = useRef(null);
  
  const handleMouseEnter = () => {
    timeoutRef.current = setTimeout(() => setShow(true), 2000); // 2 seconds delay
  };
  
  const handleMouseLeave = () => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    setShow(false);
  };
  
  const handleClick = () => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    setShow(false);
  };

  const positionClasses = {
    top: "bottom-full left-1/2 -translate-x-1/2 mb-2",
    bottom: "top-full left-1/2 -translate-x-1/2 mt-2",
    left: "right-full top-1/2 -translate-y-1/2 mr-2",
    right: "left-full top-1/2 -translate-y-1/2 ml-2",
  };

  return (
    <div 
      className="relative inline-flex"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onClick={handleClick}
    >
      {children}
      {show && (
        <div className={`absolute z-[100] ${positionClasses[position]} animate-fade-in`}>
          <div className="bg-zinc-800 border border-zinc-700 text-zinc-200 text-xs px-3 py-2 rounded-lg shadow-xl max-w-xs whitespace-normal">
            {text}
          </div>
        </div>
      )}
    </div>
  );
};

// ============== Simple Components ==============

const Logo = () => (
  <div className="font-mono font-bold text-lg tracking-tight flex items-center gap-2">
    <div className="w-7 h-7 bg-gradient-to-br from-blue-500 via-purple-500 to-pink-500 rounded-lg flex items-center justify-center shadow-lg shadow-purple-500/30">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" className="text-white">
        <path d="M12 2L2 7L12 12L22 7L12 2Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        <path d="M2 17L12 22L22 17" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        <path d="M2 12L12 17L22 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
    </div>
    <span className="bg-gradient-to-r from-white to-zinc-300 bg-clip-text text-transparent flex items-center gap-2">
      ForgePilot
      <span className="text-[10px] text-zinc-500 font-normal">v3.0.3</span>
    </span>
  </div>
);

// ============== Agent Activity Feed Component ==============

const AgentActivityItem = ({ activity }) => {
  const agentColors = {
    orchestrator: "text-purple-400 border-purple-500/30 bg-purple-500/10",
    planner: "text-blue-400 border-blue-500/30 bg-blue-500/10",
    coder: "text-emerald-400 border-emerald-500/30 bg-emerald-500/10",
    reviewer: "text-amber-400 border-amber-500/30 bg-amber-500/10",
    tester: "text-cyan-400 border-cyan-500/30 bg-cyan-500/10",
    debugger: "text-rose-400 border-rose-500/30 bg-rose-500/10",
    git: "text-orange-400 border-orange-500/30 bg-orange-500/10",
  };
  
  const agentIcons = {
    orchestrator: Zap,
    planner: ListTodo,
    coder: Code,
    reviewer: Eye,
    tester: CheckCircle2,
    debugger: Bug,
    git: GitBranch,
  };
  
  const Icon = agentIcons[activity.agent] || Zap;
  const colorClass = agentColors[activity.agent] || "text-zinc-400 border-zinc-500/30 bg-zinc-500/10";
  
  const getActionIcon = () => {
    switch(activity.action) {
      case 'file_created': return <File size={10} className="text-emerald-400" />;
      case 'file_modified': return <FileCode size={10} className="text-amber-400" />;
      case 'file_deleted': return <X size={10} className="text-rose-400" />;
      case 'test_started': return <Play size={10} className="text-cyan-400" />;
      case 'test_passed': return <CheckCircle2 size={10} className="text-emerald-400" />;
      case 'test_failed': return <Bug size={10} className="text-rose-400" />;
      case 'error_found': return <Bug size={10} className="text-rose-400" />;
      case 'error_fixed': return <CheckCircle2 size={10} className="text-emerald-400" />;
      case 'handoff': return <ArrowRight size={10} className="text-blue-400" />;
      case 'thinking': return <Loader2 size={10} className="animate-spin text-purple-400" />;
      case 'searching': return <Search size={10} className="text-blue-400" />;
      case 'complete': return <Check size={10} className="text-emerald-400" />;
      default: return <Circle size={10} />;
    }
  };
  
  return (
    <div className={`flex items-start gap-2 p-2 rounded-md border ${colorClass} animate-fade-in`}>
      <div className="flex items-center gap-1.5 shrink-0">
        <Icon size={12} />
        <span className="text-xs font-medium capitalize">{activity.agent}</span>
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5">
          {getActionIcon()}
          <span className="text-xs text-zinc-300">{activity.message}</span>
        </div>
        {activity.details && (
          <p className="text-xs text-zinc-500 mt-0.5 truncate">{activity.details}</p>
        )}
      </div>
      <span className="text-xs text-zinc-600 shrink-0">{activity.time}</span>
    </div>
  );
};

// ============== Project Summary Component ==============

const ProjectSummary = ({ previewInfo, onPush, isPushing, onDeploy, isDeploying }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  
  if (!previewInfo?.ready_for_push) return null;
  
  return (
    <div className="p-3 bg-gradient-to-r from-emerald-500/10 to-blue-500/10 border border-emerald-500/30 rounded-lg">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <CheckCircle2 size={20} className="text-emerald-400" />
          <div>
            <h3 className="text-sm font-semibold text-emerald-300">Projekt fertig!</h3>
            <p className="text-xs text-zinc-400">{previewInfo.pending_commit_message}</p>
            <p className="text-[11px] text-zinc-500 mt-0.5 italic">
              💡 Du kannst im Chat weitere Änderungen anfragen — FP startet dann eine neue Iteration.
            </p>
          </div>
        </div>
        
        <div className="flex items-center gap-2 shrink-0">
          <button 
            onClick={onPush}
            disabled={isPushing}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium rounded transition-colors disabled:opacity-50"
          >
            {isPushing ? <Loader2 size={14} className="animate-spin" /> : <Upload size={14} />}
            GitHub pushen
          </button>
          <button 
            onClick={onDeploy}
            disabled={isDeploying}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded transition-colors disabled:opacity-50"
          >
            {isDeploying ? <Loader2 size={14} className="animate-spin" /> : <Rocket size={14} />}
            Deploy
          </button>
          {previewInfo.tested_features?.length > 0 && (
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="p-1.5 hover:bg-zinc-800 rounded text-zinc-400 hover:text-white"
              title={isExpanded ? "Features ausblenden" : "Getestete Features anzeigen"}
            >
              {isExpanded ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
            </button>
          )}
        </div>
      </div>
      
      {/* Expanded Features */}
      {isExpanded && previewInfo.tested_features?.length > 0 && (
        <div className="mt-3 pt-3 border-t border-zinc-700">
          <p className="text-xs text-zinc-500 mb-1.5">Getestete Features:</p>
          <div className="flex flex-wrap gap-1.5">
            {previewInfo.tested_features.map((feature, i) => (
              <span key={i} className="px-2 py-0.5 bg-zinc-800 border border-zinc-700 text-zinc-300 text-xs rounded-full flex items-center gap-1">
                <Check size={10} className="text-emerald-400" />
                {feature}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

const AgentStatusPill = ({ agent, isProjectComplete, allAgents }) => {
  // Bestimme den tatsächlichen Status basierend auf Logik
  const getActualStatus = () => {
    // Wenn Projekt komplett: Alle grün
    if (isProjectComplete) {
      return 'completed';
    }
    
    // Orchestrator bleibt "running" solange IRGENDEIN anderer Agent läuft
    if (agent.agent_type === 'orchestrator' && allAgents) {
      const anyAgentRunning = allAgents.some(a => 
        a.agent_type !== 'orchestrator' && a.status === 'running'
      );
      if (anyAgentRunning) {
        return 'running';
      }
      // Wenn alle anderen completed → Orchestrator auch completed
      const allOthersCompleted = allAgents
        .filter(a => a.agent_type !== 'orchestrator')
        .every(a => a.status === 'completed');
      if (allOthersCompleted) {
        return 'completed';
      }
    }
    
    return agent.status;
  };
  
  const actualStatus = getActualStatus();
  
  const statusColors = {
    idle: "bg-blue-500",  // Blau: noch nichts getan
    running: "bg-red-500 animate-pulse",  // Rot pulsierend: arbeitet
    completed: "bg-emerald-500",  // Grün: fertig
    error: "bg-rose-500",
  };
  
  const agentDescriptions = {
    orchestrator: "Koordiniert alle Agenten und den Entwicklungsprozess",
    planner: "Plant die Architektur und erstellt die Roadmap",
    coder: "Schreibt und generiert den Code",
    reviewer: "Überprüft den Code auf Qualität und Best Practices",
    tester: "Führt Tests durch und validiert die Funktionalität",
    debugger: "Analysiert Fehler und schlägt Lösungen vor",
    git: "Verwaltet Versionskontrolle und GitHub-Operationen",
  };
  
  const icons = {
    orchestrator: Zap,
    planner: ListTodo,
    coder: Code,
    reviewer: Eye,
    tester: CheckCircle2,
    debugger: Bug,
    git: GitBranch,
  };
  const Icon = icons[agent.agent_type] || Zap;
  
  const statusText = {
    idle: "Bereit",
    running: agent.current_task || "Arbeitet...",
    completed: "Abgeschlossen",
    error: "Fehler",
  };

  return (
    <Tooltip text={agentDescriptions[agent.agent_type] || agent.agent_type} position="bottom">
      <div className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-full ${statusColors[actualStatus]} text-white text-xs font-medium transition-all cursor-pointer`}>
        <div className={`w-1.5 h-1.5 rounded-full bg-white ${actualStatus === 'running' ? 'animate-pulse' : ''}`} />
        <Icon size={14} />
        <span className="capitalize">{agent.agent_type === 'orchestrator' ? 'Orchestrator' : agent.agent_type}</span>
      </div>
    </Tooltip>
  );
};

const FileTreeView = ({ items, onSelect, selectedPath }) => {
  const [openFolders, setOpenFolders] = useState(new Set());
  
  if (!items || items.length === 0) return null;
  
  const flattenTree = (nodes, depth = 0, parentOpen = true) => {
    const result = [];
    for (const node of nodes) {
      if (!parentOpen) continue;
      result.push({ ...node, depth });
      if (node.type === "directory" && node.children && openFolders.has(node.path)) {
        result.push(...flattenTree(node.children, depth + 1, true));
      }
    }
    return result;
  };
  
  const flatItems = flattenTree(items);
  
  const toggleFolder = (path) => {
    setOpenFolders(prev => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  };
  
  return (
    <div>
      {flatItems.map((item) => {
        const isFolder = item.type === "directory";
        const isSelected = selectedPath === item.path;
        const isOpen = openFolders.has(item.path);
        
        return (
          <div
            key={item.path}
            className={`flex items-center gap-1 py-1 px-2 cursor-pointer rounded text-sm transition-colors ${
              isSelected ? "bg-zinc-800 text-white" : "text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-200"
            }`}
            style={{ paddingLeft: `${item.depth * 12 + 8}px` }}
            onClick={() => isFolder ? toggleFolder(item.path) : onSelect(item.path)}
          >
            {isFolder ? (
              <React.Fragment>
                <ChevronRight size={12} className={`transition-transform ${isOpen ? "rotate-90" : ""}`} />
                <Folder size={14} className="text-zinc-400" />
              </React.Fragment>
            ) : (
              <File size={14} className="text-zinc-400 ml-3" />
            )}
            <span className="truncate">{item.name}</span>
          </div>
        );
      })}
    </div>
  );
};

const SyntaxEditor = ({ content, onChange, language = "javascript", readOnly = false }) => {
  const textareaRef = useRef(null);
  const highlightRef = useRef(null);
  
  const getLanguage = (lang) => {
    const map = { js: 'javascript', jsx: 'javascript', ts: 'javascript', tsx: 'javascript', py: 'python', html: 'markup', css: 'css', json: 'json' };
    return map[lang] || lang || 'javascript';
  };

  const highlighted = React.useMemo(() => {
    try {
      const lang = getLanguage(language);
      if (Prism.languages[lang]) {
        return Prism.highlight(content || '', Prism.languages[lang], lang);
      }
    } catch (e) {}
    return content;
  }, [content, language]);

  const handleScroll = (e) => {
    if (highlightRef.current) {
      highlightRef.current.scrollTop = e.target.scrollTop;
      highlightRef.current.scrollLeft = e.target.scrollLeft;
    }
  };

  return (
    <div className="relative h-full w-full bg-zinc-950 font-mono text-sm overflow-hidden">
      <pre 
        ref={highlightRef}
        className="absolute inset-0 p-4 overflow-auto pointer-events-none m-0 whitespace-pre text-left"
        style={{ color: 'transparent' }}
        aria-hidden="true"
      >
        <code dangerouslySetInnerHTML={{ __html: highlighted }} className="text-zinc-200" />
      </pre>
      <textarea
        ref={textareaRef}
        value={content}
        onChange={(e) => onChange(e.target.value)}
        onScroll={handleScroll}
        readOnly={readOnly}
        className="absolute inset-0 w-full h-full bg-transparent text-transparent caret-white p-4 resize-none focus:outline-none leading-relaxed whitespace-pre text-left"
        spellCheck={false}
        data-testid="code-editor-textarea"
      />
    </div>
  );
};

const ChatMessage = ({ message }) => {
  const isUser = message.role === "user";
  
  const formatContent = (content) => {
    if (!content) return null;
    
    const parts = content.split(/(```[\s\S]*?```)/g);
    return parts.map((part, index) => {
      if (part.startsWith('```')) {
        const lines = part.slice(3, -3).split('\n');
        const language = lines[0] || 'javascript';
        const code = lines.slice(1).join('\n');
        
        let highlighted = code;
        try {
          const lang = language === 'html' ? 'markup' : language;
          if (Prism.languages[lang]) {
            highlighted = Prism.highlight(code, Prism.languages[lang], lang);
          }
        } catch (e) {}
        
        return (
          <div key={index} className="my-3 rounded-lg overflow-hidden border border-zinc-800">
            {language && (
              <div className="bg-zinc-800 px-3 py-1 text-xs text-zinc-400 border-b border-zinc-700">
                {language}
              </div>
            )}
            <pre className="bg-zinc-900 p-3 overflow-x-auto m-0">
              <code className="text-sm font-mono" dangerouslySetInnerHTML={{ __html: highlighted }} />
            </pre>
          </div>
        );
      }
      return <span key={index} className="whitespace-pre-wrap">{part}</span>;
    });
  };
  
  const icons = { orchestrator: Zap, planner: ListTodo, coder: Code };
  const AgentIcon = icons[message.agent_type] || Zap;
  
  return (
    <div className={`chat-message animate-fade-in flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div className={`max-w-[90%] ${isUser ? "bg-zinc-800 border border-zinc-700 text-zinc-100 p-4 rounded-xl rounded-tr-sm" : "text-zinc-300 p-0"}`}>
        {!isUser && (
          <div className="flex items-center gap-2 mb-2 text-xs text-zinc-500">
            <AgentIcon size={12} />
            <span className="capitalize">{message.agent_type || "Orchestrator"}</span>
            {message.files_created?.length > 0 && <span className="text-emerald-400 ml-2">+{message.files_created.length} Dateien</span>}
          </div>
        )}
        <div className="markdown-content">{formatContent(message.content)}</div>
      </div>
    </div>
  );
};

const LogEntry = ({ log, onClick }) => {
  const levelColors = { 
    info: "text-zinc-400 border-zinc-700", 
    success: "text-emerald-400 border-emerald-500/30", 
    warning: "text-amber-400 border-amber-500/30", 
    error: "text-rose-400 border-rose-500/30" 
  };
  const levelIcons = { info: "ℹ️", success: "✓", warning: "⚠", error: "✕" };
  
  const agentIcons = {
    orchestrator: "⚡",
    planner: "📋",
    coder: "💻",
    reviewer: "👁️",
    tester: "🧪",
    debugger: "🐛",
    git: "📦",
    system: "⚙️"
  };
  
  const icon = agentIcons[log.source] || levelIcons[log.level] || "○";
  const color = levelColors[log.level] || "text-zinc-400 border-zinc-700";
  
  // Truncate message if too long
  const displayMessage = log.message?.length > 60 
    ? log.message.substring(0, 60) + "..." 
    : log.message;

  return (
    <button
      onClick={() => onClick && onClick(log)}
      className={`w-full text-left flex gap-2 text-xs ${color} px-2 py-1.5 rounded border bg-zinc-900/30 hover:bg-zinc-800/50 transition-colors cursor-pointer group`}
      title="Klicken für Details"
    >
      <span className="text-zinc-600 shrink-0">{new Date(log.timestamp).toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>
      <span className="shrink-0">{icon}</span>
      <span className="text-zinc-500 shrink-0 font-medium">[{log.source}]</span>
      <span className="break-all flex-1 group-hover:text-white transition-colors">{displayMessage}</span>
      {log.message?.length > 60 && (
        <ChevronRight size={12} className="shrink-0 text-zinc-600 group-hover:text-zinc-400 transition-colors mt-0.5" />
      )}
    </button>
  );
};

// ============== LOG DETAIL MODAL ==============

const LogDetailModal = ({ log, onClose }) => {
  if (!log) return null;
  
  const levelColors = {
    info: "bg-blue-500/10 border-blue-500/30 text-blue-300",
    success: "bg-emerald-500/10 border-emerald-500/30 text-emerald-300",
    warning: "bg-amber-500/10 border-amber-500/30 text-amber-300",
    error: "bg-rose-500/10 border-rose-500/30 text-rose-300"
  };
  
  const agentIcons = {
    orchestrator: "⚡",
    planner: "📋",
    coder: "💻",
    reviewer: "👁️",
    tester: "🧪",
    debugger: "🐛",
    git: "📦",
    system: "⚙️"
  };
  
  const icon = agentIcons[log.source] || "📌";
  const bgColor = levelColors[log.level] || "bg-zinc-800 border-zinc-700 text-zinc-300";
  
  return (
    <div 
      className="fixed inset-0 bg-black/80 flex items-center justify-center z-[300] p-4"
      onClick={onClose}
    >
      <div 
        className="bg-zinc-900 border border-zinc-700 rounded-lg w-full max-w-2xl shadow-2xl max-h-[80vh] overflow-hidden flex flex-col"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-4 border-b border-zinc-800 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <span className="text-2xl">{icon}</span>
            <div>
              <h3 className="text-lg font-medium text-white capitalize">
                {log.source || 'System'} Log
              </h3>
              <p className="text-xs text-zinc-500">
                {new Date(log.timestamp).toLocaleString('de-DE')}
              </p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="text-zinc-400 hover:text-white transition-colors"
          >
            <X size={20} />
          </button>
        </div>
        
        {/* Content */}
        <div className="p-4 overflow-y-auto flex-1">
          {/* Log Level Badge */}
          <div className="mb-4">
            <span className={`px-3 py-1.5 rounded-full text-xs font-medium border ${bgColor}`}>
              {log.level.toUpperCase()}
            </span>
          </div>
          
          {/* Message */}
          <div className="mb-4">
            <h4 className="text-sm font-semibold text-zinc-400 mb-2">Nachricht:</h4>
            <div className="bg-zinc-950 border border-zinc-800 rounded p-3 text-sm text-zinc-200 whitespace-pre-wrap break-words">
              {log.message}
            </div>
          </div>
          
          {/* Additional Details */}
          {log.details && (
            <div className="mb-4">
              <h4 className="text-sm font-semibold text-zinc-400 mb-2">Details:</h4>
              <div className="bg-zinc-950 border border-zinc-800 rounded p-3 text-sm text-zinc-300 whitespace-pre-wrap break-words font-mono">
                {typeof log.details === 'string' ? log.details : JSON.stringify(log.details, null, 2)}
              </div>
            </div>
          )}
          
          {/* Metadata */}
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="bg-zinc-950 border border-zinc-800 rounded p-2">
              <span className="text-zinc-500">Quelle:</span>
              <span className="text-zinc-300 ml-2 font-medium">{log.source}</span>
            </div>
            <div className="bg-zinc-950 border border-zinc-800 rounded p-2">
              <span className="text-zinc-500">Level:</span>
              <span className="text-zinc-300 ml-2 font-medium">{log.level}</span>
            </div>
            <div className="bg-zinc-950 border border-zinc-800 rounded p-2 col-span-2">
              <span className="text-zinc-500">Timestamp:</span>
              <span className="text-zinc-300 ml-2 font-mono">
                {new Date(log.timestamp).toISOString()}
              </span>
            </div>
          </div>
        </div>
        
        {/* Footer */}
        <div className="p-4 border-t border-zinc-800 flex justify-end shrink-0">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-white rounded transition-colors"
          >
            Schließen
          </button>
        </div>
      </div>
    </div>
  );
};

// ============== CONFIRMATION MODAL ==============

const ConfirmationModal = ({ isOpen, onClose, onConfirm, title, message, confirmText = "Bestätigen", confirmColor = "bg-red-600 hover:bg-red-500" }) => {
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

// ============== LIVE TERMINAL MODAL ==============

const LiveTerminalModal = ({ isOpen, onClose, title = "Update Console" }) => {
  const [logs, setLogs] = useState([]);
  const [isRunning, setIsRunning] = useState(false);
  const [isDone, setIsDone] = useState(false);
  const terminalRef = useRef(null);
  const eventSourceRef = useRef(null);

  useEffect(() => {
    if (isOpen && !isRunning && !isDone) {
      startUpdate();
    }
    
    return () => {
      // Cleanup: close event source when modal closes
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, [isOpen]);

  useEffect(() => {
    // Auto-scroll to bottom when new logs appear
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [logs]);

  const startUpdate = () => {
    setIsRunning(true);
    setLogs([]);
    
    // Create EventSource for Server-Sent Events
    const eventSource = new EventSource(`${getApiBase()}/update/execute-live`);
    eventSourceRef.current = eventSource;

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        if (data.type === 'done') {
          setIsRunning(false);
          setIsDone(true);
          eventSource.close();
        } else {
          setLogs(prev => [...prev, data]);
        }
      } catch (e) {
        console.error('Failed to parse SSE data:', e);
      }
    };

    eventSource.onerror = (error) => {
      console.error('EventSource error:', error);
      setLogs(prev => [...prev, { type: 'error', message: 'Verbindung zum Server unterbrochen' }]);
      setIsRunning(false);
      setIsDone(true);
      eventSource.close();
    };
  };

  const getLogColor = (type) => {
    switch (type) {
      case 'error': return 'text-red-400';
      case 'success': return 'text-emerald-400';
      case 'info': return 'text-blue-400';
      default: return 'text-zinc-300';
    }
  };

  if (!isOpen) return null;

  return (
    <div 
      className="fixed inset-0 bg-black/90 flex items-center justify-center z-[400] p-4"
      onClick={(e) => {
        if (isDone) onClose();
      }}
    >
      <div 
        className="bg-zinc-950 border border-zinc-700 rounded-lg w-full max-w-4xl h-[80vh] shadow-2xl flex flex-col"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-4 border-b border-zinc-800 flex items-center justify-between shrink-0 bg-zinc-900">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-zinc-800 rounded">
              <Terminal size={20} className="text-emerald-400" />
            </div>
            <div>
              <h3 className="text-lg font-medium text-white">{title}</h3>
              <p className="text-xs text-zinc-500">Live Output</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {isRunning && (
              <div className="flex items-center gap-2 px-3 py-1 bg-emerald-500/10 border border-emerald-500/30 rounded text-emerald-400 text-sm">
                <Loader2 size={14} className="animate-spin" />
                <span>Läuft...</span>
              </div>
            )}
            {isDone && (
              <button
                onClick={onClose}
                className="text-zinc-400 hover:text-white transition-colors"
              >
                <X size={20} />
              </button>
            )}
          </div>
        </div>
        
        {/* Terminal Content */}
        <div 
          ref={terminalRef}
          className="flex-1 overflow-y-auto p-4 font-mono text-sm bg-black"
        >
          {logs.length === 0 && isRunning && (
            <div className="flex items-center gap-2 text-zinc-500">
              <Loader2 size={16} className="animate-spin" />
              <span>Initialisiere Update...</span>
            </div>
          )}
          {logs.map((log, index) => (
            <div key={index} className={`mb-1 ${getLogColor(log.type)}`}>
              {log.message}
            </div>
          ))}
        </div>
        
        {/* Footer */}
        <div className="p-4 border-t border-zinc-800 flex justify-between items-center shrink-0 bg-zinc-900">
          <div className="text-xs text-zinc-500">
            {isRunning && "Update wird ausgeführt..."}
            {isDone && "Update abgeschlossen - Sie können dieses Fenster schließen"}
          </div>
          {isDone && (
            <button
              onClick={onClose}
              className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-white rounded transition-colors"
            >
              Schließen
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

// ============== ROADMAP VIEW ==============

const RoadmapView = ({ items }) => {
  const statusIcons = {
    pending: <Circle size={14} className="text-zinc-500" />,
    in_progress: <ArrowRight size={14} className="text-blue-400" />,
    completed: <Check size={14} className="text-emerald-400" />,
  };
  
  if (!items?.length) {
    return (
      <div className="text-center py-8 text-zinc-500">
        <ListTodo size={32} className="mx-auto mb-2 opacity-50" />
        <p>Noch keine Roadmap erstellt</p>
      </div>
    );
  }
  
  return (
    <div className="space-y-3">
      {items.map((item, index) => (
        <div key={item.id} className={`p-3 rounded-lg border ${
          item.status === 'completed' ? 'bg-emerald-500/5 border-emerald-500/20' :
          item.status === 'in_progress' ? 'bg-blue-500/5 border-blue-500/20' :
          'bg-zinc-900 border-zinc-800'
        }`}>
          <div className="flex items-start gap-3">
            <div className="mt-0.5">{statusIcons[item.status]}</div>
            <div>
              <h4 className="font-medium text-zinc-200">{item.title}</h4>
              <p className="text-sm text-zinc-400 mt-1">{item.description}</p>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

// ============== Update Banner Component ==============

const UpdateBanner = ({ updateStatus, onCheckUpdate, onInstallUpdate, onDismiss }) => {
  const [showDetails, setShowDetails] = useState(false);
  const [showTerminal, setShowTerminal] = useState(false);
  
  if (!updateStatus?.update_available) return null;
  
  return (
    <>
      <div className="fixed top-0 left-0 right-0 z-50 bg-gradient-to-r from-blue-600 to-purple-600 text-white px-4 py-2 shadow-lg animate-fade-in">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-1.5 bg-white/20 rounded-full">
              <RefreshCw size={16} />
            </div>
            <div>
              <span className="font-medium">Update verfügbar: Version {updateStatus.latest_version}</span>
              <span className="text-white/70 text-sm ml-2">(aktuell: {updateStatus.installed_version})</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button 
              onClick={() => setShowDetails(true)} 
              className="px-3 py-1 text-sm bg-white/20 hover:bg-white/30 rounded-md transition-colors"
            >
              Details
            </button>
            <button 
              onClick={() => setShowTerminal(true)} 
              className="flex items-center gap-2 px-3 py-1 text-sm bg-white text-blue-600 hover:bg-blue-50 rounded-md font-medium transition-colors"
            >
              <MonitorPlay size={14} />
              Jetzt updaten
            </button>
            <button 
              onClick={onDismiss} 
              className="p-1 hover:bg-white/20 rounded-md transition-colors"
            >
              <X size={16} />
            </button>
          </div>
        </div>
        
        {/* Details Modal */}
        {showDetails && (
          <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4" onClick={() => setShowDetails(false)}>
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg w-full max-w-md shadow-2xl" onClick={e => e.stopPropagation()}>
              <div className="p-4 border-b border-zinc-800 flex items-center justify-between">
                <h3 className="text-lg font-medium text-white">Update Details</h3>
                <button onClick={() => setShowDetails(false)} className="text-zinc-400 hover:text-white"><X size={20} /></button>
              </div>
              <div className="p-4 space-y-4">
                <div className="flex justify-between text-sm">
                  <span className="text-zinc-400">Installiert:</span>
                  <span className="text-white font-mono">{updateStatus.installed_version}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-zinc-400">Verfügbar:</span>
                  <span className="text-emerald-400 font-mono">{updateStatus.latest_version}</span>
                </div>
                {updateStatus.last_checked_at && (
                  <div className="flex justify-between text-sm">
                    <span className="text-zinc-400">Geprüft:</span>
                    <span className="text-zinc-300">{new Date(updateStatus.last_checked_at).toLocaleString('de-DE')}</span>
                  </div>
                )}
                {updateStatus.release_notes && (
                  <div className="mt-4">
                    <h4 className="text-sm font-medium text-zinc-300 mb-2">Release Notes:</h4>
                    <div className="text-xs text-zinc-400 bg-zinc-800 p-3 rounded-md max-h-48 overflow-auto whitespace-pre-wrap">
                      {updateStatus.release_notes}
                    </div>
                  </div>
                )}
              </div>
              <div className="p-4 border-t border-zinc-800 flex justify-end gap-2">
                <button onClick={() => setShowDetails(false)} className="px-4 py-2 text-zinc-400 hover:text-white">
                  Später
                </button>
                <button onClick={() => { setShowDetails(false); setShowTerminal(true); }} className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-md font-medium">
                  <MonitorPlay size={14} />
                  Update installieren
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
      
      {/* Live Terminal Modal */}
      <LiveTerminalModal
        isOpen={showTerminal}
        onClose={() => setShowTerminal(false)}
        title="ForgePilot Update"
      />
    </>
  );
};

// ============== Settings Modal Component ==============

const SettingsModal = ({ isOpen, onClose, onRefreshLLMStatus }) => {
  const [activeTab, setActiveTab] = useState('api');
  const [settings, setSettings] = useState({ 
    openai_api_key_set: false,
    openai_api_key_preview: '',
    openai_from_env: false,
    github_token_set: false,
    github_token_preview: '',
    github_from_env: false,
    ollama_url: 'http://localhost:11434',
    ollama_model: 'llama3',
    llm_provider: 'auto',
    ollama_available: false,
    ollama_models: []
  });
  const [llmStatus, setLLMStatus] = useState(null);
  const [openaiKey, setOpenaiKey] = useState('');
  const [githubToken, setGithubToken] = useState('');
  const [ollamaUrl, setOllamaUrl] = useState('');
  const [ollamaModel, setOllamaModel] = useState('');
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [message, setMessage] = useState(null);
  const [updateStatus, setUpdateStatus] = useState(null);
  const [checkingUpdate, setCheckingUpdate] = useState(false);

  const [showUpdateInstructions, setShowUpdateInstructions] = useState(false);
  const [updateCommand, setUpdateCommand] = useState('');
  const [updateResponse, setUpdateResponse] = useState(null);

  const installUpdate = async () => {
    try {
      const res = await axios.post(`${API}/update/execute`);
      
      // Show command and response
      if (res.data.command) {
        setUpdateCommand(res.data.command);
      }
      setUpdateResponse(res.data);
      setShowUpdateInstructions(true);
      
      // Show success/error message
      if (res.data.success) {
        setMessage({ 
          type: 'success', 
          text: res.data.message || 'Update wird ausgeführt...' 
        });
      } else {
        setMessage({ 
          type: 'error', 
          text: res.data.message || 'Update fehlgeschlagen' 
        });
      }
    } catch (e) {
      const errorData = e.response?.data;
      const errorMsg = errorData?.detail || e.message;
      
      setMessage({ type: 'error', text: 'Fehler: ' + errorMsg });
      
      // If command is included in error, show it
      if (errorData?.command) {
        setUpdateCommand(errorData.command);
        setShowUpdateInstructions(true);
      }
    }
  };

  const rollbackUpdate = async () => {
    try {
      const res = await axios.post(`${API}/update/rollback`);
      setShowUpdateInstructions(true);
    } catch (e) {
      setMessage({ type: 'error', text: 'Fehler: ' + (e.response?.data?.detail || e.message) });
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadSettings();
      loadLLMStatus();
      loadUpdateStatus();
    }
  }, [isOpen]);

  const loadSettings = async () => {
    try {
      const res = await axios.get(`${API}/settings`);
      setSettings(res.data);
      setOllamaUrl(res.data.ollama_url || 'http://localhost:11434');
      setOllamaModel(res.data.ollama_model || 'llama3');
    } catch (e) {
      console.error('Failed to load settings:', e);
      setMessage({ type: 'error', text: 'Einstellungen konnten nicht geladen werden' });
    }
  };

  const loadLLMStatus = async () => {
    try {
      const res = await axios.get(`${API}/llm/status`);
      setLLMStatus(res.data);
      // Update settings with fresh Ollama models
      setSettings(prev => ({
        ...prev,
        ollama_available: res.data.ollama_available,
        ollama_models: res.data.ollama_models || []
      }));
    } catch (e) {
      console.error('Failed to load LLM status:', e);
    }
  };

  const loadUpdateStatus = async () => {
    try {
      const res = await axios.get(`${API}/update/status`);
      setUpdateStatus(res.data);
    } catch (e) {
      console.error('Failed to load update status:', e.message);
      setUpdateStatus(prev => ({
        ...prev,
        installed_version: prev?.installed_version || 'Unbekannt',
        latest_version: prev?.latest_version || '-',
        update_available: false
      }));
    }
  };

  const checkForUpdates = async () => {
    setCheckingUpdate(true);
    setMessage(null);
    try {
      const res = await axios.post(`${API}/update/check`);
      setUpdateStatus(res.data);
      if (res.data.update_available) {
        setMessage({ type: 'success', text: `Update verfügbar: ${res.data.latest_version}` });
      } else {
        setMessage({ type: 'success', text: `Keine Updates verfügbar (Version ${res.data.installed_version})` });
      }
    } catch (e) {
      console.error('Update check failed:', e.message);
      try {
        const versionRes = await axios.get(`${API}/version`);
        setUpdateStatus(prev => ({
          ...prev,
          installed_version: versionRes.data.version,
          latest_version: '-',
          update_available: false
        }));
        setMessage({ type: 'error', text: `Konnte GitHub nicht erreichen (Version ${versionRes.data.version})` });
      } catch (e2) {
        setMessage({ type: 'error', text: 'Backend nicht erreichbar' });
      }
    }
    setCheckingUpdate(false);
  };

  const saveOpenAIKey = async () => {
    if (!openaiKey.trim()) return;
    setSaving(true);
    setMessage(null);
    try {
      const res = await axios.put(`${API}/settings`, { openai_api_key: openaiKey });
      setSettings(prev => ({ 
        ...prev, 
        openai_api_key_set: true,
        openai_api_key_preview: res.data.openai_api_key_preview 
      }));
      setOpenaiKey('');
      setMessage({ type: 'success', text: 'OpenAI API Key gespeichert!' });
      await loadSettings(); // Reload to get preview
    } catch (e) {
      setMessage({ type: 'error', text: 'Fehler beim Speichern: ' + (e.response?.data?.detail || e.message) });
    }
    setSaving(false);
  };

  const saveGitHubToken = async () => {
    if (!githubToken.trim()) return;
    setSaving(true);
    setMessage(null);
    try {
      const res = await axios.put(`${API}/settings`, { github_token: githubToken });
      setSettings(prev => ({ 
        ...prev, 
        github_token_set: true,
        github_token_preview: res.data.github_token_preview 
      }));
      setGithubToken('');
      setMessage({ type: 'success', text: 'GitHub Token gespeichert!' });
      await loadSettings(); // Reload to get preview
    } catch (e) {
      setMessage({ type: 'error', text: 'Fehler beim Speichern: ' + (e.response?.data?.detail || e.message) });
    }
    setSaving(false);
  };

  const saveOllamaUrl = async () => {
    setSaving(true);
    setMessage(null);
    try {
      const res = await axios.put(`${API}/settings`, { 
        ollama_url: ollamaUrl,
        ollama_model: ollamaModel
      });
      setSettings(prev => ({ 
        ...prev, 
        ollama_url: ollamaUrl,
        ollama_model: ollamaModel,
        ollama_available: res.data.ollama_available,
        ollama_models: res.data.ollama_models || []
      }));
      if (res.data.ollama_available) {
        setMessage({ type: 'success', text: `Ollama gespeichert - ${res.data.ollama_models?.length || 0} Modelle gefunden` });
      } else {
        setMessage({ type: 'warning', text: 'Ollama URL gespeichert, aber nicht erreichbar' });
      }
      await loadLLMStatus();
    } catch (e) {
      setMessage({ type: 'error', text: 'Fehler beim Speichern' });
    }
    setSaving(false);
  };

  const saveLLMSettings = async (provider) => {
    setSaving(true);
    setMessage(null);
    try {
      const res = await axios.put(`${API}/settings`, { 
        llm_provider: provider,
        ollama_url: ollamaUrl,
        ollama_model: ollamaModel
      });
      setSettings(prev => ({ ...prev, llm_provider: provider }));
      await loadLLMStatus();
      setMessage({ type: 'success', text: `LLM Provider auf "${provider}" gesetzt` });
      if (onRefreshLLMStatus) onRefreshLLMStatus();
    } catch (e) {
      setMessage({ type: 'error', text: 'Fehler beim Speichern' });
    }
    setSaving(false);
  };

  const testOllamaConnection = async () => {
    setTesting(true);
    setMessage(null);
    try {
      const res = await axios.post(`${API}/llm/test-ollama?url=${encodeURIComponent(ollamaUrl)}`);
      if (res.data.success) {
        setSettings(prev => ({
          ...prev,
          ollama_available: true,
          ollama_models: res.data.models || []
        }));
        setMessage({ type: 'success', text: res.data.message });
        // If models found, select first one if none selected
        if (res.data.models?.length > 0 && !ollamaModel) {
          setOllamaModel(res.data.models[0]);
        }
      } else {
        setSettings(prev => ({ ...prev, ollama_available: false, ollama_models: [] }));
        setMessage({ type: 'error', text: res.data.message });
      }
    } catch (e) {
      setSettings(prev => ({ ...prev, ollama_available: false, ollama_models: [] }));
      setMessage({ type: 'error', text: 'Verbindungstest fehlgeschlagen: ' + e.message });
    }
    setTesting(false);
  };

  const refreshOllamaStatus = async () => {
    setSaving(true);
    try {
      const res = await axios.post(`${API}/llm/refresh`);
      setLLMStatus(res.data);
      setSettings(prev => ({ 
        ...prev, 
        ollama_available: res.data.ollama_available,
        ollama_models: res.data.ollama_models || []
      }));
      if (res.data.ollama_available) {
        setMessage({ type: 'success', text: `Ollama verbunden: ${res.data.ollama_models?.length || 0} Modelle gefunden` });
      } else {
        setMessage({ type: 'error', text: 'Ollama nicht erreichbar' });
      }
    } catch (e) {
      setMessage({ type: 'error', text: 'Fehler beim Verbinden zu Ollama' });
    }
    setSaving(false);
  };

  const deleteOpenAIKey = async () => {
    if (!window.confirm('OpenAI API Key wirklich löschen?')) return;
    try {
      await axios.delete(`${API}/settings/openai-key`);
      setSettings(prev => ({ ...prev, openai_api_key_set: false }));
      setMessage({ type: 'success', text: 'OpenAI API Key gelöscht' });
    } catch (e) {
      setMessage({ type: 'error', text: 'Fehler beim Löschen' });
    }
  };

  const deleteGitHubToken = async () => {
    if (!window.confirm('GitHub Token wirklich löschen?')) return;
    try {
      await axios.delete(`${API}/settings/github-token`);
      setSettings(prev => ({ ...prev, github_token_set: false }));
      setMessage({ type: 'success', text: 'GitHub Token gelöscht' });
    } catch (e) {
      setMessage({ type: 'error', text: 'Fehler beim Löschen' });
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4" data-testid="settings-modal">
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg w-full max-w-lg shadow-2xl max-h-[90vh] flex flex-col">
        <div className="flex items-center justify-between p-4 border-b border-zinc-800 shrink-0">
          <div className="flex items-center gap-2">
            <Settings size={20} />
            <h2 className="text-lg font-medium">Einstellungen</h2>
          </div>
          <button onClick={onClose} className="p-1 text-zinc-400 hover:text-white"><X size={20} /></button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-zinc-800 shrink-0">
          {[
            { id: 'api', label: 'API Keys', icon: Lock },
            { id: 'llm', label: 'LLM', icon: Zap },
            { id: 'updates', label: 'Updates', icon: RefreshCw },
            { id: 'shortcuts', label: 'Tastatur', icon: Terminal },
          ].map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={`flex-1 flex items-center justify-center gap-2 px-3 py-3 text-sm font-medium transition-colors ${
                activeTab === id ? 'text-white border-b-2 border-white bg-zinc-800/50' : 'text-zinc-400 hover:text-white'
              }`}
            >
              <Icon size={14} />
              {label}
            </button>
          ))}
        </div>

        {/* Env Notice */}
        {(settings.openai_from_env || settings.github_from_env) && activeTab === 'api' && (
          <div className="mx-4 mt-4 p-3 bg-blue-500/10 border border-blue-500/30 rounded-lg text-sm text-blue-300">
            <strong>Hinweis:</strong> Einige Keys werden aus .env geladen (siehe Labels).
          </div>
        )}

        {/* Message */}
        {message && (
          <div className={`mx-4 mt-4 p-3 rounded-lg text-sm ${
            message.type === 'success' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30' : 
            message.type === 'warning' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/30' :
            'bg-rose-500/10 text-rose-400 border border-rose-500/30'
          }`}>
            {message.text}
          </div>
        )}

        <div className="p-4 space-y-6 overflow-y-auto flex-1">
          {/* API Keys Tab */}
          {activeTab === 'api' && (
            <div className="space-y-6">
              {/* OpenAI API Key */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-sm font-semibold text-zinc-300">OpenAI API Key</h3>
                  {settings.openai_api_key_set && (
                    <span className="px-2 py-0.5 bg-emerald-500/20 text-emerald-400 text-xs rounded-full flex items-center gap-1">
                      <Check size={10} /> {settings.openai_from_env ? 'Aus .env' : 'In DB gespeichert'}
                    </span>
                  )}
                </div>
                {/* Show current key preview */}
                {settings.openai_api_key_set && settings.openai_api_key_preview && (
                  <div className="mb-2 p-2 bg-zinc-800 rounded border border-zinc-700">
                    <span className="text-xs text-zinc-500">Aktueller Key: </span>
                    <span className="text-sm font-mono text-zinc-300">{settings.openai_api_key_preview}</span>
                  </div>
                )}
                <p className="text-xs text-zinc-500 mb-3">
                  Erforderlich für KI-Funktionen. Erstelle deinen Key unter{' '}
                  <a href="https://platform.openai.com/api-keys" target="_blank" rel="noreferrer" className="text-blue-400 hover:underline">
                    platform.openai.com/api-keys
                  </a>
                </p>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={openaiKey}
                    onChange={(e) => setOpenaiKey(e.target.value)}
                    placeholder={settings.openai_api_key_set ? 'Neuen Key eingeben zum Ersetzen...' : 'sk-proj-...'}
                    className="flex-1 bg-zinc-800 border border-zinc-700 rounded-md px-3 py-2 text-sm focus:outline-none focus:border-zinc-500 font-mono"
                  />
                  <button
                    onClick={saveOpenAIKey}
                    disabled={!openaiKey.trim() || saving}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-zinc-700 disabled:text-zinc-500 text-white rounded-md text-sm font-medium transition-colors"
                  >
                    {saving ? <Loader2 size={14} className="animate-spin" /> : 'Speichern'}
                  </button>
                </div>
                {settings.openai_api_key_set && !settings.openai_from_env && (
                  <button onClick={deleteOpenAIKey} className="mt-2 text-xs text-rose-400 hover:text-rose-300">
                    Key löschen
                  </button>
                )}
              </div>

              {/* GitHub Token */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-sm font-semibold text-zinc-300">GitHub Token</h3>
                  {settings.github_token_set && (
                    <span className="px-2 py-0.5 bg-emerald-500/20 text-emerald-400 text-xs rounded-full flex items-center gap-1">
                      <Check size={10} /> {settings.github_from_env ? 'Aus .env' : 'In DB gespeichert'}
                    </span>
                  )}
                </div>
                {/* Show current token preview */}
                {settings.github_token_set && settings.github_token_preview && (
                  <div className="mb-2 p-2 bg-zinc-800 rounded border border-zinc-700">
                    <span className="text-xs text-zinc-500">Aktueller Token: </span>
                    <span className="text-sm font-mono text-zinc-300">{settings.github_token_preview}</span>
                  </div>
                )}
                <p className="text-xs text-zinc-500 mb-3">
                  Optional für GitHub Import/Push. Erstelle unter{' '}
                  <a href="https://github.com/settings/tokens" target="_blank" rel="noreferrer" className="text-blue-400 hover:underline">
                    github.com/settings/tokens
                  </a>
                </p>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={githubToken}
                    onChange={(e) => setGithubToken(e.target.value)}
                    placeholder={settings.github_token_set ? 'Neuen Token eingeben zum Ersetzen...' : 'github_pat_...'}
                    className="flex-1 bg-zinc-800 border border-zinc-700 rounded-md px-3 py-2 text-sm focus:outline-none focus:border-zinc-500 font-mono"
                  />
                  <button
                    onClick={saveGitHubToken}
                    disabled={!githubToken.trim() || saving}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-zinc-700 disabled:text-zinc-500 text-white rounded-md text-sm font-medium transition-colors"
                  >
                    {saving ? <Loader2 size={14} className="animate-spin" /> : 'Speichern'}
                  </button>
                </div>
                {settings.github_token_set && !settings.github_from_env && (
                  <button onClick={deleteGitHubToken} className="mt-2 text-xs text-rose-400 hover:text-rose-300">
                    Token löschen
                  </button>
                )}
              </div>
            </div>
          )}

          {/* LLM Tab */}
          {activeTab === 'llm' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-zinc-300">LLM Provider</h3>
                {llmStatus && (
                  <span className={`px-2 py-0.5 text-xs rounded-full ${
                    llmStatus.active_provider === 'ollama' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-blue-500/20 text-blue-400'
                  }`}>
                    Aktiv: {llmStatus.active_provider}
                  </span>
                )}
              </div>
              
              <div className="space-y-3">
                {/* Auto Mode */}
                <div 
                  onClick={() => saveLLMSettings('auto')}
                  className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                    settings.llm_provider === 'auto' ? 'bg-purple-500/10 border-purple-500/50' : 'bg-zinc-800/50 border-zinc-700 hover:border-zinc-600'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Zap size={16} className={settings.llm_provider === 'auto' ? 'text-purple-400' : 'text-zinc-500'} />
                      <span className="font-medium">Auto</span>
                      <span className="text-xs text-zinc-500">(Empfohlen)</span>
                    </div>
                    {settings.llm_provider === 'auto' && <Check size={16} className="text-purple-400" />}
                  </div>
                  <p className="text-xs text-zinc-500 mt-1">Nutzt Ollama wenn verfügbar, sonst OpenAI</p>
                </div>

                {/* OpenAI */}
                <div 
                  onClick={() => saveLLMSettings('openai')}
                  className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                    settings.llm_provider === 'openai' ? 'bg-blue-500/10 border-blue-500/50' : 'bg-zinc-800/50 border-zinc-700 hover:border-zinc-600'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Globe size={16} className={settings.llm_provider === 'openai' ? 'text-blue-400' : 'text-zinc-500'} />
                      <span className="font-medium">OpenAI GPT-4o</span>
                      {settings.openai_api_key_set ? (
                        <span className="px-1.5 py-0.5 text-xs bg-emerald-500/20 text-emerald-400 rounded">Key vorhanden</span>
                      ) : (
                        <span className="px-1.5 py-0.5 text-xs bg-rose-500/20 text-rose-400 rounded">Kein Key</span>
                      )}
                    </div>
                    {settings.llm_provider === 'openai' && <Check size={16} className="text-blue-400" />}
                  </div>
                  <p className="text-xs text-zinc-500 mt-1">Cloud-basiert, beste Qualität</p>
                </div>
                
                {/* Ollama */}
                <div 
                  onClick={() => settings.ollama_available && saveLLMSettings('ollama')}
                  className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                    !settings.ollama_available ? 'opacity-60' : ''
                  } ${
                    settings.llm_provider === 'ollama' && settings.ollama_available ? 'bg-emerald-500/10 border-emerald-500/50' : 'bg-zinc-800/50 border-zinc-700 hover:border-zinc-600'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Terminal size={16} className={settings.llm_provider === 'ollama' ? 'text-emerald-400' : 'text-zinc-500'} />
                      <span className="font-medium">Ollama (Lokal)</span>
                      {settings.ollama_available ? (
                        <span className="px-1.5 py-0.5 text-xs bg-emerald-500/20 text-emerald-400 rounded">Verbunden</span>
                      ) : (
                        <span className="px-1.5 py-0.5 text-xs bg-zinc-700 text-zinc-400 rounded">Nicht erreichbar</span>
                      )}
                    </div>
                    {settings.llm_provider === 'ollama' && settings.ollama_available && <Check size={16} className="text-emerald-400" />}
                  </div>
                  <p className="text-xs text-zinc-500 mt-1">
                    {settings.ollama_available 
                      ? `Modelle: ${settings.ollama_models?.join(', ') || 'Keine gefunden'}`
                      : 'Lokale KI ohne Cloud-Anbindung'
                    }
                  </p>
                </div>
              </div>

              {/* Ollama Settings */}
              <div className="mt-4 p-3 bg-zinc-800/50 rounded-lg border border-zinc-700">
                <h4 className="text-sm font-medium text-zinc-300 mb-3">Ollama Konfiguration</h4>
                <div className="space-y-3">
                  <div>
                    <label className="text-xs text-zinc-400 block mb-1">Ollama URL</label>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={ollamaUrl}
                        onChange={(e) => setOllamaUrl(e.target.value)}
                        placeholder="http://192.168.1.140:11434"
                        className="flex-1 bg-zinc-700 border border-zinc-600 rounded px-2 py-1.5 text-sm focus:outline-none focus:border-zinc-500 font-mono"
                      />
                      <button
                        onClick={testOllamaConnection}
                        disabled={testing}
                        className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded text-sm transition-colors flex items-center gap-1"
                      >
                        {testing ? <Loader2 size={12} className="animate-spin" /> : <RefreshCw size={12} />}
                        Test
                      </button>
                      <button
                        onClick={saveOllamaUrl}
                        disabled={saving}
                        className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded text-sm transition-colors"
                      >
                        {saving ? <Loader2 size={12} className="animate-spin" /> : 'Speichern'}
                      </button>
                    </div>
                    <p className="text-xs text-zinc-500 mt-1">
                      Auf Unraid: Die IP deines Servers, z.B. http://192.168.1.140:11434
                    </p>
                  </div>
                  <div>
                    <label className="text-xs text-zinc-400 block mb-1">
                      Modell {settings.ollama_models?.length > 0 && <span className="text-emerald-400">({settings.ollama_models.length} verfügbar)</span>}
                    </label>
                    <select
                      value={ollamaModel}
                      onChange={(e) => setOllamaModel(e.target.value)}
                      className="w-full bg-zinc-700 border border-zinc-600 rounded px-2 py-1.5 text-sm focus:outline-none focus:border-zinc-500"
                    >
                      {settings.ollama_models?.length > 0 ? (
                        settings.ollama_models.map(m => <option key={m} value={m}>{m}</option>)
                      ) : (
                        <>
                          <option value={ollamaModel}>{ollamaModel} (manuell)</option>
                          <option value="llama3">llama3</option>
                          <option value="llama3.2">llama3.2</option>
                          <option value="mistral">mistral</option>
                          <option value="codellama">codellama</option>
                          <option value="deepseek-coder">deepseek-coder</option>
                        </>
                      )}
                    </select>
                  </div>
                  {/* Connection Status */}
                  <div className="flex items-center gap-2 text-xs">
                    <div className={`w-2 h-2 rounded-full ${settings.ollama_available ? 'bg-emerald-400' : 'bg-rose-400'}`} />
                    <span className={settings.ollama_available ? 'text-emerald-400' : 'text-rose-400'}>
                      {settings.ollama_available ? 'Verbunden' : 'Nicht verbunden'}
                    </span>
                    <span className="text-zinc-500">• {ollamaUrl}</span>
                  </div>
                </div>
              </div>

              {/* Auto Fallback Info */}
              {llmStatus?.auto_fallback_active && (
                <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg text-sm text-amber-300">
                  <strong>Auto-Fallback aktiv:</strong> Ollama nicht erreichbar, nutze OpenAI
                </div>
              )}
            </div>
          )}

          {/* Updates Tab */}
          {activeTab === 'updates' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-zinc-300">Version & Updates</h3>
                <button 
                  onClick={checkForUpdates}
                  disabled={checkingUpdate}
                  className="flex items-center gap-1 px-3 py-1.5 bg-zinc-700 hover:bg-zinc-600 text-white rounded text-sm transition-colors"
                >
                  {checkingUpdate ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
                  Prüfen
                </button>
              </div>

              <div className="p-4 bg-zinc-800/50 rounded-lg border border-zinc-700 space-y-3">
                <div className="flex justify-between">
                  <span className="text-zinc-400">Installierte Version:</span>
                  <span className="font-mono text-white">{updateStatus?.installed_version || '...'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-400">Neueste Version:</span>
                  <span className={`font-mono ${updateStatus?.update_available ? 'text-emerald-400' : 'text-white'}`}>
                    {updateStatus?.latest_version || '...'}
                  </span>
                </div>
                {updateStatus?.last_checked_at && (
                  <div className="flex justify-between text-sm">
                    <span className="text-zinc-500">Zuletzt geprüft:</span>
                    <span className="text-zinc-400">{new Date(updateStatus.last_checked_at).toLocaleString('de-DE')}</span>
                  </div>
                )}
                {updateStatus?.previous_version && (
                  <div className="flex justify-between text-sm">
                    <span className="text-zinc-500">Vorherige Version:</span>
                    <span className="text-zinc-400">{updateStatus.previous_version}</span>
                  </div>
                )}
              </div>

              {updateStatus?.update_available && (
                <div className="p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <RefreshCw size={16} className="text-emerald-400" />
                    <span className="font-medium text-emerald-300">Update verfügbar!</span>
                  </div>
                  {updateStatus.release_notes && (
                    <p className="text-sm text-zinc-400 mb-3">{updateStatus.release_notes.substring(0, 200)}</p>
                  )}
                  <div className="flex gap-2">
                    <button 
                      onClick={installUpdate}
                      className="flex-1 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded font-medium text-sm transition-colors"
                    >
                      Update installieren
                    </button>
                  </div>
                </div>
              )}

              {updateStatus?.previous_version && (
                <button 
                  onClick={rollbackUpdate}
                  className="w-full px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded text-sm transition-colors"
                >
                  Rollback zu {updateStatus.previous_version}
                </button>
              )}

              {/* Update Instructions Modal */}
              {showUpdateInstructions && (
                <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-[60] p-4" onClick={() => setShowUpdateInstructions(false)}>
                  <div className="bg-zinc-900 border border-zinc-700 rounded-lg w-full max-w-2xl shadow-2xl" onClick={e => e.stopPropagation()}>
                    <div className="p-4 border-b border-zinc-800 flex items-center justify-between">
                      <h3 className="text-lg font-medium text-white flex items-center gap-2">
                        <RefreshCw size={20} className="text-emerald-400" />
                        Update auf {updateResponse?.target_version || updateStatus?.latest_version}
                      </h3>
                      <button onClick={() => setShowUpdateInstructions(false)} className="text-zinc-400 hover:text-white">
                        <X size={20} />
                      </button>
                    </div>
                    <div className="p-4 space-y-4">
                      {/* Status Message */}
                      {updateResponse?.message && (
                        <div className={`p-3 rounded-lg border ${updateResponse.success ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300' : 'bg-amber-500/10 border-amber-500/30 text-amber-300'}`}>
                          {updateResponse.message}
                        </div>
                      )}
                      
                      {/* Command to execute */}
                      {updateCommand && (
                        <div className="bg-zinc-950 rounded-lg p-4 border border-amber-500/30">
                          <div className="flex items-center gap-2 mb-3">
                            <Terminal size={16} className="text-amber-400" />
                            <span className="text-sm font-medium text-amber-400">Befehl zum Ausführen (als Root):</span>
                          </div>
                          <div className="bg-black/50 rounded p-3 mb-3">
                            <code className="text-emerald-400 font-mono text-sm whitespace-pre-wrap break-all">
                              {updateCommand}
                            </code>
                          </div>
                          <button
                            onClick={() => {
                              navigator.clipboard.writeText(updateCommand);
                              setMessage({ type: 'success', text: 'Befehl in Zwischenablage kopiert!' });
                            }}
                            className="w-full px-3 py-2 bg-zinc-800 hover:bg-zinc-700 text-white rounded text-sm flex items-center justify-center gap-2"
                          >
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                              <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                            </svg>
                            In Zwischenablage kopieren
                          </button>
                        </div>
                      )}
                      
                      {/* Update Details */}
                      {updateResponse && (
                        <div className="space-y-2 text-sm">
                          {updateResponse.script_path && (
                            <div className="flex justify-between text-zinc-400">
                              <span>Script-Pfad:</span>
                              <span className="font-mono text-zinc-300">{updateResponse.script_path}</span>
                            </div>
                          )}
                          {updateResponse.working_directory && (
                            <div className="flex justify-between text-zinc-400">
                              <span>Arbeitsverzeichnis:</span>
                              <span className="font-mono text-zinc-300">{updateResponse.working_directory}</span>
                            </div>
                          )}
                          {updateResponse.pid && (
                            <div className="flex justify-between text-zinc-400">
                              <span>Prozess-ID (PID):</span>
                              <span className="font-mono text-emerald-400">{updateResponse.pid}</span>
                            </div>
                          )}
                        </div>
                      )}
                      
                      {/* Alternative: Original Instructions */}
                      {!updateCommand && (
                        <>
                          <p className="text-sm text-zinc-300">
                            Führe <strong>einen</strong> der folgenden Befehle auf deinem Unraid Server aus:
                          </p>
                          
                          {/* Option 1: Update Script */}
                          <div className="bg-zinc-950 rounded-lg p-4">
                            <div className="flex items-center gap-2 mb-2">
                              <span className="px-2 py-0.5 bg-emerald-500/20 text-emerald-400 text-xs rounded">Empfohlen</span>
                              <span className="text-sm font-medium text-white">Update Script</span>
                            </div>
                            <code className="text-emerald-400 font-mono text-sm">cd /mnt/user/appdata/forgepilot && sudo bash update.sh</code>
                            <p className="text-xs text-zinc-500 mt-2">Das Script macht alles automatisch: Pull, Stop, Remove, Start</p>
                          </div>
                        </>
                      )}
                      
                      <div className="flex gap-2 mt-4">
                        <button
                          onClick={() => {
                            setShowUpdateInstructions(false);
                            window.location.reload();
                          }}
                          className="flex-1 px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-white rounded"
                        >
                          Seite neu laden
                        </button>
                        <button
                          onClick={() => setShowUpdateInstructions(false)}
                          className="flex-1 px-4 py-2 bg-zinc-700 hover:bg-zinc-600 text-white rounded"
                        >
                          Schließen
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              <div className="text-xs text-zinc-500 mt-4">
                <p>ForgePilot prüft automatisch auf Updates.</p>
                <p>Updates können über die UI oder per Docker installiert werden.</p>
              </div>
              
              {/* Debug Info */}
              <div className="mt-4 p-3 bg-zinc-800/30 rounded-lg border border-zinc-700/50">
                <h4 className="text-xs font-medium text-zinc-400 mb-2">Debug Info</h4>
                <div className="text-xs text-zinc-500 font-mono space-y-1">
                  <p>API: {API}</p>
                  <button 
                    onClick={async () => {
                      try {
                        const res = await axios.get(`${API}/version`);
                        setMessage({ type: 'success', text: `Backend erreichbar: ${JSON.stringify(res.data)}` });
                      } catch (e) {
                        setMessage({ type: 'error', text: `Backend Fehler: ${e.message}` });
                      }
                    }}
                    className="px-2 py-1 bg-zinc-700 hover:bg-zinc-600 rounded text-zinc-300"
                  >
                    API Test
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Shortcuts Tab */}
          {activeTab === 'shortcuts' && (
            <div>
              <h3 className="text-sm font-semibold text-zinc-300 mb-3">Tastaturkürzel</h3>
              <div className="space-y-2 text-xs">
                {[
                  { keys: 'Ctrl+S', desc: 'Datei speichern' },
                  { keys: 'Ctrl+Shift+S', desc: 'Alle Dateien speichern' },
                  { keys: 'Ctrl+P', desc: 'Preview ein/aus' },
                  { keys: 'Ctrl+B', desc: 'Datei-Explorer ein/aus' },
                  { keys: 'Ctrl+K', desc: 'Chat fokussieren' },
                  { keys: 'Ctrl+W', desc: 'Tab schließen' },
                  { keys: 'Ctrl+Shift+R', desc: 'Preview neu laden' },
                  { keys: 'Ctrl+,', desc: 'Einstellungen öffnen' },
                ].map(({ keys, desc }) => (
                  <div key={keys} className="flex items-center justify-between p-2 bg-zinc-800/50 rounded">
                    <span className="text-zinc-400">{desc}</span>
                    <kbd className="px-2 py-0.5 bg-zinc-700 border border-zinc-600 rounded text-zinc-300 font-mono">{keys}</kbd>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
        
        <div className="flex items-center justify-end gap-3 p-4 border-t border-zinc-800 shrink-0">
          <button onClick={onClose} className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-white rounded-md">Schließen</button>
        </div>
      </div>
    </div>
  );
};

// ============== Start Screen ==============

const StartScreen = () => {
  const navigate = useNavigate();
  const [prompt, setPrompt] = useState("");
  const [projectType, setProjectType] = useState("fullstack");
  const [isLoading, setIsLoading] = useState(false);
  const [recentProjects, setRecentProjects] = useState([]);
  const [archivedProjects, setArchivedProjects] = useState([]);
  const [showArchived, setShowArchived] = useState(false);
  const [showGitHubModal, setShowGitHubModal] = useState(false);
  const [showTemplates, setShowTemplates] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [showSettingsCenter, setShowSettingsCenter] = useState(false); // NEW: Settings Center v2
  const [showTerminal, setShowTerminal] = useState(false); // NEW: Update Terminal
  const [ollamaStatus, setOllamaStatus] = useState({ available: false });
  const [useOllama, setUseOllama] = useState(false);
  const [confirmModal, setConfirmModal] = useState({ isOpen: false, projectId: null, action: null });
  
  const toggleOllama = async () => {
    try {
      await axios.put(`${API}/settings`, { use_ollama: !useOllama });
      setUseOllama(!useOllama);
    } catch (e) {
      console.error('Failed to toggle Ollama');
    }
  };

  const loadProjects = async () => {
    try {
      const [activeRes, archivedRes] = await Promise.all([
        api.getProjects(false),
        api.getArchivedProjects()
      ]);
      setRecentProjects(activeRes.data.slice(0, 12));
      setArchivedProjects(archivedRes.data || []);
    } catch (e) {
      console.error('Failed to load projects:', e);
    }
  };

  useEffect(() => {
    loadProjects();
  }, []);

  const handleDeleteProject = async (projectId) => {
    try {
      await api.deleteProject(projectId);
      await loadProjects();
    } catch (e) {
      console.error('Failed to delete project:', e);
      alert('Fehler beim Löschen des Projekts');
    }
  };

  const handleDownloadProject = async (projectId, projectName) => {
    try {
      const response = await api.downloadProject(projectId);
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${projectName || projectId}.zip`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      console.error('Failed to download project:', e);
      alert('Fehler beim Download des Projekts');
    }
  };

  const handleArchiveProject = async (projectId) => {
    try {
      await api.archiveProject(projectId);
      await loadProjects();
    } catch (e) {
      console.error('Failed to archive project:', e);
      alert('Fehler beim Archivieren des Projekts');
    }
  };

  const handleUnarchiveProject = async (projectId) => {
    try {
      await api.unarchiveProject(projectId);
      await loadProjects();
    } catch (e) {
      console.error('Failed to unarchive project:', e);
      alert('Fehler beim Entarchivieren des Projekts');
    }
  };

  const openConfirmModal = (projectId, action) => {
    setConfirmModal({ isOpen: true, projectId, action });
  };

  const closeConfirmModal = () => {
    setConfirmModal({ isOpen: false, projectId: null, action: null });
  };

  const handleConfirmAction = () => {
    const { projectId, action } = confirmModal;
    if (action === 'delete') {
      handleDeleteProject(projectId);
    } else if (action === 'archive') {
      handleArchiveProject(projectId);
    }
  };

  const handleSubmit = async () => {
    if (!prompt.trim()) return;
    setIsLoading(true);
    try {
      const res = await api.createProject({
        name: prompt.split('\n')[0].substring(0, 50) || "Neues Projekt",
        description: prompt,
        project_type: projectType,
      });
      navigate(`/workspace/${res.data.id}`);
    } catch (e) {
      setIsLoading(false);
    }
  };

  const handleTemplateSelect = async (template) => {
    setIsLoading(true);
    try {
      const res = await api.createProject({
        name: `${template.name} Projekt`,
        description: `${template.prompt} ${template.description}`,
        project_type: template.id,
        template_files: template.files,
      });
      navigate(`/workspace/${res.data.id}`);
    } catch (e) {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) handleSubmit();
  };

  const projectTypes = [
    { id: "fullstack", label: "Full Stack App", icon: Terminal, desc: "Komplette Web-App mit Frontend und Backend" },
    { id: "mobile", label: "Mobile App", icon: FileCode, desc: "Mobile-optimierte Web-Anwendung" },
    { id: "landing", label: "Landing Page", icon: Eye, desc: "Einzelseite für Marketing oder Produkte" },
  ];

  // Project templates
  const templates = [
    { id: "react", name: "React App", icon: "⚛️", color: "from-cyan-500 to-blue-500", desc: "Moderne React-Anwendung" },
    { id: "vue", name: "Vue.js App", icon: "💚", color: "from-emerald-500 to-green-500", desc: "Reaktive Vue.js 3 App" },
    { id: "node", name: "Node.js API", icon: "🟢", color: "from-green-500 to-lime-500", desc: "Express.js REST API" },
    { id: "python", name: "Python FastAPI", icon: "🐍", color: "from-yellow-500 to-amber-500", desc: "FastAPI mit Pydantic" },
    { id: "landing", name: "Landing Page", icon: "🚀", color: "from-purple-500 to-pink-500", desc: "Marketing-Landingpage" },
    { id: "dashboard", name: "Dashboard", icon: "📊", color: "from-blue-500 to-indigo-500", desc: "Admin mit Charts" },
  ];

  return (
    <div className="min-h-screen bg-zinc-950 flex flex-col">
      <nav className="h-14 border-b border-zinc-800 bg-zinc-950/80 backdrop-blur-xl flex items-center justify-between px-6 sticky top-0 z-50">
        <Logo />
        <div className="flex items-center gap-4">
          <Tooltip text="Starte mit einem vorgefertigten Template" position="bottom">
            <button onClick={() => setShowTemplates(!showTemplates)} className={`flex items-center gap-2 px-3 py-1.5 text-sm rounded-md transition-colors ${showTemplates ? 'bg-zinc-800 text-white' : 'text-zinc-400 hover:text-white hover:bg-zinc-800/50'}`} data-testid="templates-btn">
              <ListTodo size={16} />
              <span>Templates</span>
            </button>
          </Tooltip>
          <Tooltip text="Importiere ein bestehendes Projekt von GitHub" position="bottom">
            <button onClick={() => setShowGitHubModal(true)} className="flex items-center gap-2 px-3 py-1.5 text-sm text-zinc-400 hover:text-white hover:bg-zinc-800/50 rounded-md transition-colors" data-testid="github-import-btn">
              <FolderGit2 size={16} />
              <span>GitHub Import</span>
            </button>
          </Tooltip>
          <Tooltip text="Einstellungen und Konfiguration" position="bottom">
            <button onClick={() => setShowSettingsCenter(true)} className="p-2 text-zinc-400 hover:text-white hover:bg-zinc-800/50 rounded-md transition-colors" data-testid="start-settings-btn">
              <Settings size={18} />
            </button>
          </Tooltip>
          
          <Tooltip text="ForgePilot Update (Unraid)" position="bottom">
            <button onClick={() => setShowTerminal(true)} className="p-2 text-zinc-400 hover:text-white hover:bg-zinc-800/50 rounded-md transition-colors" data-testid="update-btn">
              <CloudDownload size={18} />
            </button>
          </Tooltip>
        </div>
      </nav>

      <main className="flex-1 flex flex-col items-center justify-center p-6 sm:p-12 md:p-24">
        <div className="max-w-3xl w-full flex flex-col items-center space-y-12">
          <div className="text-center space-y-4">
            <h1 className="text-4xl sm:text-5xl font-medium tracking-tighter text-zinc-50">Was möchtest du bauen?</h1>
            <p className="text-lg text-zinc-500">Beschreibe dein Projekt. ForgePilot recherchiert Best Practices, plant und entwickelt es für dich.</p>
          </div>

          {/* Templates Section */}
          {showTemplates && (
            <div className="w-full animate-fade-in">
              <h3 className="text-sm font-semibold uppercase tracking-widest text-zinc-500 mb-4">Schnellstart Templates</h3>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {templates.map((template) => (
                  <button
                    key={template.id}
                    onClick={() => handleTemplateSelect(template)}
                    disabled={isLoading}
                    className="p-4 bg-zinc-900 border border-zinc-800 rounded-lg text-left hover:border-zinc-600 hover:bg-zinc-800/50 transition-all group disabled:opacity-50"
                    data-testid={`template-${template.id}`}
                  >
                    <div className={`w-10 h-10 rounded-lg bg-gradient-to-br ${template.color} flex items-center justify-center text-xl mb-3`}>
                      {template.icon}
                    </div>
                    <p className="font-medium text-zinc-200">{template.name}</p>
                    <p className="text-xs text-zinc-500 mt-1">{template.desc}</p>
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="flex items-center gap-2 p-1 bg-zinc-900 rounded-lg border border-zinc-800">
            {projectTypes.map(({ id, label, icon: Icon, desc }) => (
              <Tooltip key={id} text={desc} position="bottom">
                <button onClick={() => setProjectType(id)} className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all ${projectType === id ? "bg-zinc-800 text-white" : "text-zinc-400 hover:text-zinc-200"}`} data-testid={`project-type-${id}`}>
                  <Icon size={16} />{label}
                </button>
              </Tooltip>
            ))}
          </div>

          <div className="w-full bg-zinc-900 border border-zinc-800 rounded-lg shadow-2xl overflow-hidden focus-within:border-zinc-600 transition-colors" data-testid="prompt-container">
            <textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} onKeyDown={handleKeyDown} placeholder="Beschreibe dein Projekt in natürlicher Sprache...

Beispiel: Erstelle eine moderne Todo-App mit dunklem Design. Die App soll Todos hinzufügen, bearbeiten und löschen können. Nutze moderne CSS-Techniken wie Grid und Animationen." className="w-full min-h-[200px] bg-transparent p-6 text-lg placeholder:text-zinc-600 focus:outline-none" data-testid="main-prompt-input" />
            <div className="flex items-center justify-between p-4 border-t border-zinc-800 bg-zinc-900/50">
              <span className="text-xs text-zinc-500">⌘ + Enter zum Starten</span>
              <Tooltip text="Startet die KI-gestützte Entwicklung" position="top">
                <button onClick={handleSubmit} disabled={!prompt.trim() || isLoading} className="flex items-center gap-2 bg-white text-black hover:bg-zinc-200 font-medium px-5 py-2.5 rounded-md transition-all disabled:opacity-50 disabled:cursor-not-allowed" data-testid="submit-prompt-btn">
                  {isLoading ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
                  <span>Projekt starten</span>
                </button>
              </Tooltip>
            </div>
          </div>

          {(recentProjects.length > 0 || archivedProjects.length > 0 || showArchived) && (
            <div className="w-full space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold uppercase tracking-widest text-zinc-500">
                  {showArchived ? `Archivierte Projekte (${archivedProjects.length})` : `Aktuelle Projekte (${recentProjects.length})`}
                </h3>
                <button
                  onClick={() => setShowArchived(!showArchived)}
                  className="flex items-center gap-2 px-3 py-1.5 text-sm text-zinc-400 hover:text-white hover:bg-zinc-800/50 rounded-md transition-colors"
                  data-testid="toggle-archive-btn"
                >
                  {showArchived ? (
                    <>
                      <Home size={14} />
                      <span>Aktive Projekte</span>
                    </>
                  ) : (
                    <>
                      <Archive size={14} />
                      <span>Archiv ({archivedProjects.length})</span>
                    </>
                  )}
                </button>
              </div>

              {showArchived && archivedProjects.length === 0 ? (
                <div className="w-full flex flex-col items-center justify-center py-16 px-6 bg-zinc-900/50 border border-dashed border-zinc-800 rounded-lg text-center">
                  <Archive size={32} className="text-zinc-600 mb-3" />
                  <p className="text-zinc-300 font-medium mb-1">Keine archivierten Projekte</p>
                  <p className="text-sm text-zinc-500 mb-5">Du hast noch nichts archiviert. Archivierte Projekte erscheinen hier.</p>
                  <button
                    onClick={() => setShowArchived(false)}
                    className="flex items-center gap-2 px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 rounded-md transition-colors"
                    data-testid="back-to-active-btn"
                  >
                    <Home size={14} />
                    <span>Zurück zu aktiven Projekten</span>
                  </button>
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                  {(showArchived ? archivedProjects : recentProjects).map((project) => (
                  <div key={project.id} className="group relative flex items-center gap-3 p-4 bg-zinc-900 border border-zinc-800 rounded-lg hover:border-zinc-700 hover:bg-zinc-800/50 transition-all" data-testid={`project-${project.id}`}>
                    <button 
                      onClick={() => navigate(`/workspace/${project.id}`)} 
                      className="flex items-center gap-3 flex-1 min-w-0 text-left"
                    >
                      <div className="w-10 h-10 bg-zinc-800 rounded-md flex items-center justify-center text-zinc-400 group-hover:text-white transition-colors shrink-0">
                        <FileCode size={20} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-zinc-200 truncate">{project.name}</p>
                        <p className="text-xs text-zinc-500">{project.project_type}</p>
                      </div>
                    </button>
                    
                    {/* Action Buttons */}
                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                      <Tooltip text="Projekt herunterladen" position="top">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDownloadProject(project.id, project.name);
                          }}
                          className="p-1.5 text-zinc-500 hover:text-blue-400 hover:bg-zinc-800 rounded transition-colors"
                          data-testid={`download-project-${project.id}`}
                        >
                          <Download size={16} />
                        </button>
                      </Tooltip>
                      
                      {showArchived ? (
                        <Tooltip text="Projekt entarchivieren" position="top">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleUnarchiveProject(project.id);
                            }}
                            className="p-1.5 text-zinc-500 hover:text-emerald-400 hover:bg-zinc-800 rounded transition-colors"
                            data-testid={`unarchive-project-${project.id}`}
                          >
                            <ArchiveRestore size={16} />
                          </button>
                        </Tooltip>
                      ) : (
                        <Tooltip text="Projekt archivieren" position="top">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              openConfirmModal(project.id, 'archive');
                            }}
                            className="p-1.5 text-zinc-500 hover:text-amber-400 hover:bg-zinc-800 rounded transition-colors"
                            data-testid={`archive-project-${project.id}`}
                          >
                            <Archive size={16} />
                          </button>
                        </Tooltip>
                      )}
                      
                      <Tooltip text="Projekt löschen" position="top">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            openConfirmModal(project.id, 'delete');
                          }}
                          className="p-1.5 text-zinc-500 hover:text-red-400 hover:bg-zinc-800 rounded transition-colors"
                          data-testid={`delete-project-${project.id}`}
                        >
                          <Trash2 size={16} />
                        </button>
                      </Tooltip>
                    </div>
                  </div>
                ))}
                </div>
              )}
            </div>
          )}
        </div>
      </main>

      {/* GitHub Import Modal */}
      {showGitHubModal && <GitHubImportModal onClose={() => setShowGitHubModal(false)} onImport={(p) => { setShowGitHubModal(false); navigate(`/workspace/${p.id}`); }} />}
      
      {/* Settings Modal (Legacy) */}
      {showSettings && (
        <SettingsModal 
          isOpen={showSettings} 
          onClose={() => setShowSettings(false)}
        />
      )}

      {/* Settings Center v2 (NEW MODULAR SYSTEM) */}
      <SettingsCenter
        isOpen={showSettingsCenter}
        onClose={() => setShowSettingsCenter(false)}
      />

      {/* Live Terminal Modal (Update) */}
      <LiveTerminalModal
        isOpen={showTerminal}
        onClose={() => setShowTerminal(false)}
        title="ForgePilot Update (Unraid)"
      />
      
      {/* Confirmation Modal */}
      <ConfirmationModal
        isOpen={confirmModal.isOpen}
        onClose={closeConfirmModal}
        onConfirm={handleConfirmAction}
        title={confirmModal.action === 'delete' ? 'Projekt löschen' : 'Projekt archivieren'}
        message={
          confirmModal.action === 'delete'
            ? 'Möchten Sie dieses Projekt wirklich löschen? Alle Dateien und Daten werden unwiderruflich gelöscht.'
            : 'Möchten Sie dieses Projekt archivieren? Es wird aus der aktiven Projektliste entfernt, bleibt aber verfügbar.'
        }
        confirmText={confirmModal.action === 'delete' ? 'Löschen' : 'Archivieren'}
        confirmColor={confirmModal.action === 'delete' ? 'bg-red-600 hover:bg-red-500' : 'bg-amber-600 hover:bg-amber-500'}
      />
    </div>
  );
};

// ============== GitHub Import Modal ==============

const GitHubImportModal = ({ onClose, onImport }) => {
  const [repos, setRepos] = useState([]);
  const [branches, setBranches] = useState([]);
  const [selectedRepo, setSelectedRepo] = useState(null);
  const [selectedBranch, setSelectedBranch] = useState("");
  const [isLoadingRepos, setIsLoadingRepos] = useState(true);
  const [isLoadingBranches, setIsLoadingBranches] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const [error, setError] = useState("");
  const [manualUrl, setManualUrl] = useState("");
  const [useManualUrl, setUseManualUrl] = useState(false);

  useEffect(() => { loadRepos(); }, []);

  const loadRepos = async () => {
    setIsLoadingRepos(true);
    try {
      const res = await api.getGitHubRepos();
      setRepos(res.data.repos || []);
    } catch (e) {
      setError("Repos konnten nicht geladen werden");
    } finally {
      setIsLoadingRepos(false);
    }
  };

  const loadBranches = async (repoFullName) => {
    setIsLoadingBranches(true);
    setBranches([]);
    try {
      const res = await api.getGitHubBranches(repoFullName);
      setBranches(res.data.branches || []);
      const repo = repos.find(r => r.full_name === repoFullName);
      if (repo) setSelectedBranch(repo.default_branch);
    } catch (e) {
      setError("Branches konnten nicht geladen werden");
    } finally {
      setIsLoadingBranches(false);
    }
  };

  const handleRepoSelect = (repoFullName) => {
    const repo = repos.find(r => r.full_name === repoFullName);
    setSelectedRepo(repo);
    setSelectedBranch("");
    if (repo) loadBranches(repo.full_name);
  };

  const handleImport = async () => {
    const url = useManualUrl ? manualUrl : selectedRepo?.url;
    const branch = useManualUrl ? "main" : selectedBranch;
    if (!url) return;
    setIsImporting(true);
    setError("");
    try {
      const res = await api.importGitHub({ repo_url: url, branch });
      onImport(res.data);
    } catch (e) {
      setError(e.response?.data?.detail || "Import fehlgeschlagen");
      setIsImporting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4" data-testid="github-import-modal">
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg w-full max-w-lg shadow-2xl">
        <div className="flex items-center justify-between p-4 border-b border-zinc-800">
          <div className="flex items-center gap-2">
            <FolderGit2 size={20} />
            <h2 className="text-lg font-medium">Von GitHub importieren</h2>
          </div>
          <button onClick={onClose} className="p-1 text-zinc-400 hover:text-white"><X size={20} /></button>
        </div>
        
        <div className="p-4 space-y-4">
          <div className="flex gap-2">
            <Tooltip text="Zeigt alle deine GitHub Repositories zur Auswahl" position="bottom">
              <button onClick={() => setUseManualUrl(false)} className={`flex-1 py-2 rounded-md text-sm font-medium transition-colors ${!useManualUrl ? 'bg-zinc-800 text-white' : 'text-zinc-400 hover:text-zinc-200'}`}>Meine Repos</button>
            </Tooltip>
            <Tooltip text="Gib eine beliebige GitHub URL manuell ein" position="bottom">
              <button onClick={() => setUseManualUrl(true)} className={`flex-1 py-2 rounded-md text-sm font-medium transition-colors ${useManualUrl ? 'bg-zinc-800 text-white' : 'text-zinc-400 hover:text-zinc-200'}`}>URL eingeben</button>
            </Tooltip>
          </div>

          {useManualUrl ? (
            <div>
              <label className="block text-sm font-medium text-zinc-400 mb-2">Repository URL</label>
              <input type="text" value={manualUrl} onChange={(e) => setManualUrl(e.target.value)} placeholder="https://github.com/user/repo" className="w-full bg-zinc-800 border border-zinc-700 text-white px-3 py-2.5 rounded-md focus:outline-none focus:border-zinc-500 placeholder:text-zinc-600" data-testid="github-repo-url-input" />
            </div>
          ) : (
            <React.Fragment>
              <div>
                <label className="block text-sm font-medium text-zinc-400 mb-2">Repository auswählen</label>
                {isLoadingRepos ? (
                  <div className="flex items-center gap-2 text-zinc-500 py-2"><Loader2 size={16} className="animate-spin" /><span>Lade Repositories...</span></div>
                ) : (
                  <div className="relative">
                    <select value={selectedRepo?.full_name || ""} onChange={(e) => handleRepoSelect(e.target.value)} className="w-full bg-zinc-800 border border-zinc-700 text-white px-3 py-2.5 rounded-md focus:outline-none focus:border-zinc-500 appearance-none cursor-pointer" data-testid="github-repo-select">
                      <option value="">-- Repository wählen --</option>
                      {repos.map((repo) => (<option key={repo.full_name} value={repo.full_name}>{repo.private ? "🔒 " : "🌐 "}{repo.full_name}</option>))}
                    </select>
                    <ChevronDown size={16} className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-400 pointer-events-none" />
                  </div>
                )}
              </div>

              {selectedRepo && (
                <div className="p-3 bg-zinc-800/50 rounded-md border border-zinc-700">
                  <div className="flex items-center gap-2 text-sm">
                    {selectedRepo.private ? <Lock size={14} className="text-amber-400" /> : <Globe size={14} className="text-emerald-400" />}
                    <span className="font-medium text-zinc-200">{selectedRepo.name}</span>
                    <span className="text-zinc-500">({selectedRepo.private ? "privat" : "öffentlich"})</span>
                  </div>
                  {selectedRepo.description && <p className="text-xs text-zinc-400 mt-1">{selectedRepo.description}</p>}
                </div>
              )}

              {selectedRepo && (
                <div>
                  <label className="block text-sm font-medium text-zinc-400 mb-2">Branch auswählen</label>
                  {isLoadingBranches ? (
                    <div className="flex items-center gap-2 text-zinc-500 py-2"><Loader2 size={16} className="animate-spin" /><span>Lade Branches...</span></div>
                  ) : (
                    <div className="relative">
                      <select value={selectedBranch} onChange={(e) => setSelectedBranch(e.target.value)} className="w-full bg-zinc-800 border border-zinc-700 text-white px-3 py-2.5 rounded-md focus:outline-none focus:border-zinc-500 appearance-none cursor-pointer" data-testid="github-branch-select">
                        <option value="">-- Branch wählen --</option>
                        {branches.map((branch) => (<option key={branch} value={branch}>{branch}</option>))}
                      </select>
                      <ChevronDown size={16} className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-400 pointer-events-none" />
                    </div>
                  )}
                </div>
              )}
            </React.Fragment>
          )}
          
          {error && <div className="p-3 bg-rose-500/10 border border-rose-500/20 rounded-md text-rose-400 text-sm">{error}</div>}
        </div>
        
        <div className="flex items-center justify-end gap-3 p-4 border-t border-zinc-800">
          <button onClick={onClose} className="px-4 py-2 text-zinc-400 hover:text-white">Abbrechen</button>
          <Tooltip text="Klont das Repository in einen neuen Workspace" position="top">
            <button onClick={handleImport} disabled={(useManualUrl ? !manualUrl.trim() : (!selectedRepo || !selectedBranch)) || isImporting} className="flex items-center gap-2 bg-white text-black hover:bg-zinc-200 font-medium px-4 py-2 rounded-md disabled:opacity-50" data-testid="github-import-confirm-btn">
              {isImporting ? <Loader2 size={16} className="animate-spin" /> : <GitBranch size={16} />}
              Importieren
            </button>
          </Tooltip>
        </div>
      </div>
    </div>
  );
};

// ============== Workspace ==============

const Workspace = () => {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const [project, setProject] = useState(null);
  const [messages, setMessages] = useState([]);
  const [agents, setAgents] = useState([]);
  const [logs, setLogs] = useState([]);
  const [roadmap, setRoadmap] = useState([]);
  const [fileTree, setFileTree] = useState([]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [activeTab, setActiveTab] = useState("preview");
  // Multi-tab editor state
  const [openTabs, setOpenTabs] = useState([]);
  const [activeFileTab, setActiveFileTab] = useState(null);
  const [fileContents, setFileContents] = useState({});
  const [dirtyFiles, setDirtyFiles] = useState(new Set());
  const [showFileExplorer, setShowFileExplorer] = useState(true);
  const [previewInfo, setPreviewInfo] = useState(null);
  const [isPushing, setIsPushing] = useState(false);
  // Ollama settings
  const [showSettings, setShowSettings] = useState(false);
  const [ollamaStatus, setOllamaStatus] = useState({ available: false, models: [] });
  const [useOllama, setUseOllama] = useState(false);
  // Autonomous agent progress
  const [agentProgress, setAgentProgress] = useState({ iteration: 0, maxIterations: 20, currentTool: null, isAutonomous: false });
  // Agent Activity Feed - detaillierte Anzeige was gerade passiert
  const [agentActivities, setAgentActivities] = useState([]);
  // Right Panel (Preview) visibility
  const [showRightPanel, setShowRightPanel] = useState(true);
  // Update Banner State
  const [updateStatus, setUpdateStatus] = useState(null);
  const [showUpdateBanner, setShowUpdateBanner] = useState(true);
  const [showUpdateInstructions, setShowUpdateInstructions] = useState(false);
  const [isUpdating, setIsUpdating] = useState(false);
  const [updateMessage, setUpdateMessage] = useState(null);
  // Deploy Modal State
  const [showDeployModal, setShowDeployModal] = useState(false);
  const [isDeploying, setIsDeploying] = useState(false);
  // File Upload State
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const fileInputRef = useRef(null);
  // Log Detail State
  const [selectedLog, setSelectedLog] = useState(null);
  // Voice Input State
  const [isListening, setIsListening] = useState(false);
  const [speechSupported, setSpeechSupported] = useState(false);
  const recognitionRef = useRef(null);
  const chatContainerRef = useRef(null);
  const activityContainerRef = useRef(null);
  const pollingRef = useRef(null);
  const iframeRef = useRef(null);

  // Initialize Speech Recognition
  useEffect(() => {
    // Check for updates on mount
    const checkUpdates = async () => {
      try {
        const res = await axios.post(`${API}/update/check`);
        if (res.data.update_available) {
          setUpdateStatus(res.data);
        }
      } catch (e) {
        console.log('Update check skipped');
      }
    };
    checkUpdates();
    
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      setSpeechSupported(true);
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.lang = 'de-DE';
      
      recognition.onresult = (event) => {
        let finalTranscript = '';
        let interimTranscript = '';
        
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const transcript = event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            finalTranscript += transcript;
          } else {
            interimTranscript += transcript;
          }
        }
        
        if (finalTranscript) {
          setInputValue(prev => prev + finalTranscript);
        } else if (interimTranscript) {
          // Show interim results in a temporary way
          setInputValue(prev => {
            const base = prev.replace(/\[...\]$/, '');
            return base + interimTranscript;
          });
        }
      };
      
      recognition.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        setIsListening(false);
      };
      
      recognition.onend = () => {
        setIsListening(false);
      };
      
      recognitionRef.current = recognition;
    }
  }, []);

  const toggleVoiceInput = () => {
    if (!recognitionRef.current) return;
    
    if (isListening) {
      recognitionRef.current.stop();
      setIsListening(false);
    } else {
      recognitionRef.current.start();
      setIsListening(true);
    }
  };

  const handleInstallUpdate = async () => {
    setIsUpdating(true);
    setUpdateMessage({ type: 'info', text: 'Update wird gestartet...' });
    
    try {
      const res = await axios.post(`${API}/update/install`);
      
      if (res.data.triggered) {
        // Auto-Update wurde erfolgreich getriggert
        setUpdateMessage({ 
          type: 'success', 
          text: 'Update läuft! Die Anwendung wird in ca. 30 Sekunden neu gestartet. Bitte warten...' 
        });
        
        // Seite nach 35 Sekunden neu laden
        setTimeout(() => {
          window.location.reload();
        }, 35000);
      } else {
        // Fallback: Zeige manuelle Anweisungen
        setUpdateMessage({ 
          type: 'warning', 
          text: 'Automatisches Update nicht verfügbar. Bitte manuell ausführen.' 
        });
        setShowUpdateInstructions(true);
      }
    } catch (error) {
      console.error('Update-Fehler:', error);
      setUpdateMessage({ 
        type: 'error', 
        text: 'Fehler beim Starten des Updates: ' + (error.response?.data?.detail || error.message) 
      });
      // Bei Fehler trotzdem Anweisungen zeigen
      setShowUpdateInstructions(true);
    } finally {
      setIsUpdating(false);
    }
  };

  const startDeployment = async () => {
    setIsDeploying(true);
    try {
      const res = await axios.post(`${API}/projects/${projectId}/deploy/start`);
      if (res.data.success) {
        setShowDeployModal(true);
      }
    } catch (error) {
      console.error('Deploy start failed:', error);
      alert('Deployment konnte nicht gestartet werden: ' + (error.response?.data?.detail || error.message));
    } finally {
      setIsDeploying(false);
    }
  };

  const handleFileUpload = (e) => {
    const files = Array.from(e.target.files);
    const newFiles = [];
    
    files.forEach(file => {
      // Only allow images and text files
      if (file.type.startsWith('image/') || file.type.startsWith('text/')) {
        const reader = new FileReader();
        reader.onload = (event) => {
          newFiles.push({
            name: file.name,
            type: file.type,
            size: file.size,
            data: event.target.result,
            preview: file.type.startsWith('image/') ? event.target.result : null
          });
          
          if (newFiles.length === files.length) {
            setUploadedFiles(prev => [...prev, ...newFiles]);
          }
        };
        reader.readAsDataURL(file);
      }
    });
  };

  const removeFile = (index) => {
    setUploadedFiles(prev => prev.filter((_, i) => i !== index));
  };

  // Keyboard Shortcuts
  useEffect(() => {
    const handleKeyDown = (e) => {
      const ctrl = e.ctrlKey || e.metaKey;
      const shift = e.shiftKey;
      const key = e.key.toLowerCase();

      // Ctrl+S - Save current file
      if (ctrl && key === 's' && !shift) {
        e.preventDefault();
        if (activeFileTab && dirtyFiles.has(activeFileTab)) {
          saveFile(activeFileTab);
        }
        return;
      }

      // Ctrl+Shift+S - Save all files
      if (ctrl && shift && key === 's') {
        e.preventDefault();
        saveAllFiles();
        return;
      }

      // Ctrl+P - Toggle preview panel
      if (ctrl && key === 'p') {
        e.preventDefault();
        setShowRightPanel(prev => !prev);
        return;
      }

      // Ctrl+B - Toggle file explorer
      if (ctrl && key === 'b') {
        e.preventDefault();
        setShowFileExplorer(prev => !prev);
        return;
      }

      // Ctrl+K - Focus chat input
      if (ctrl && key === 'k') {
        e.preventDefault();
        document.querySelector('[data-testid="chat-input"]')?.focus();
        return;
      }

      // Ctrl+Shift+R - Refresh preview
      if (ctrl && shift && key === 'r') {
        e.preventDefault();
        refreshPreview();
        return;
      }

      // Ctrl+W - Close current tab
      if (ctrl && key === 'w' && activeFileTab) {
        e.preventDefault();
        closeTab(activeFileTab);
        return;
      }

      // Ctrl+, - Open settings
      if (ctrl && key === ',') {
        e.preventDefault();
        setShowSettings(true);
        return;
      }

      // Ctrl+Enter - Send message (when chat focused)
      if (ctrl && e.key === 'Enter' && document.activeElement?.getAttribute('data-testid') === 'chat-input') {
        e.preventDefault();
        if (inputValue.trim() && !isLoading) {
          sendMessage(inputValue);
        }
        return;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [activeFileTab, dirtyFiles, inputValue, isLoading]);

  // Add activity to feed
  const addActivity = (agent, action, message, details = null) => {
    const now = new Date();
    const time = now.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    setAgentActivities(prev => [...prev.slice(-50), { id: Date.now(), agent, action, message, details, time }]);
    // Auto-scroll activity feed
    setTimeout(() => {
      if (activityContainerRef.current) {
        activityContainerRef.current.scrollTop = activityContainerRef.current.scrollHeight;
      }
    }, 100);
  };

  useEffect(() => {
    loadProjectData();
    checkOllamaStatus();
    pollingRef.current = setInterval(refreshData, 5000);
    return () => { if (pollingRef.current) clearInterval(pollingRef.current); };
  }, [projectId]);

  const checkOllamaStatus = async () => {
    try {
      const res = await axios.get(`${API}/ollama/status`);
      setOllamaStatus(res.data);
    } catch (e) {
      setOllamaStatus({ available: false, models: [] });
    }
  };

  const toggleOllama = async () => {
    try {
      if (!useOllama) {
        await axios.post(`${API}/ollama/enable`);
        setUseOllama(true);
      } else {
        setUseOllama(false);
      }
    } catch (e) {}
  };

  const loadProjectData = async () => {
    try {
      const [projectRes, messagesRes, agentsRes, logsRes, roadmapRes, filesRes, previewRes] = await Promise.all([
        api.getProject(projectId),
        api.getMessages(projectId),
        api.getAgents(projectId),
        api.getLogs(projectId),
        api.getRoadmap(projectId),
        api.getFiles(projectId),
        api.getPreviewInfo(projectId).catch(() => ({ data: null })),
      ]);
      setProject(projectRes.data);
      setMessages(messagesRes.data);
      setAgents(agentsRes.data);
      setLogs(logsRes.data);
      setRoadmap(roadmapRes.data);
      setFileTree(filesRes.data.tree || []);
      setPreviewInfo(previewRes.data);
      
      if (messagesRes.data.length === 0 && projectRes.data.description) {
        sendMessage(projectRes.data.description);
      }
    } catch (e) {
      navigate("/");
    }
  };

  const refreshData = async () => {
    try {
      const [agentsRes, logsRes, filesRes, roadmapRes, previewRes] = await Promise.all([
        api.getAgents(projectId),
        api.getLogs(projectId),
        api.getFiles(projectId),
        api.getRoadmap(projectId),
        api.getPreviewInfo(projectId).catch(() => ({ data: null })),
      ]);
      setAgents(agentsRes.data);
      setLogs(logsRes.data);
      setFileTree(filesRes.data.tree || []);
      setRoadmap(roadmapRes.data);
      setPreviewInfo(previewRes.data);
    } catch (e) {}
  };

  const loadFile = async (path) => {
    try {
      const res = await api.getFiles(projectId, path);
      if (res.data.type === "file") {
        // Add to open tabs if not already open
        if (!openTabs.includes(path)) {
          setOpenTabs(prev => [...prev, path]);
        }
        setFileContents(prev => ({ ...prev, [path]: res.data.content }));
        setActiveFileTab(path);
        setActiveTab("editor");
      }
    } catch (e) {}
  };

  const closeTab = (path, e) => {
    e?.stopPropagation();
    setOpenTabs(prev => prev.filter(p => p !== path));
    setFileContents(prev => {
      const newContents = { ...prev };
      delete newContents[path];
      return newContents;
    });
    setDirtyFiles(prev => {
      const newDirty = new Set(prev);
      newDirty.delete(path);
      return newDirty;
    });
    // Switch to another tab or close editor
    if (activeFileTab === path) {
      const remaining = openTabs.filter(p => p !== path);
      setActiveFileTab(remaining.length > 0 ? remaining[remaining.length - 1] : null);
    }
  };

  const saveFile = async (path = activeFileTab) => {
    if (!path || !dirtyFiles.has(path)) return;
    try {
      await api.saveFile(projectId, path, fileContents[path]);
      setDirtyFiles(prev => {
        const newDirty = new Set(prev);
        newDirty.delete(path);
        return newDirty;
      });
      refreshData();
      refreshPreview();
    } catch (e) {}
  };

  const saveAllFiles = async () => {
    for (const path of dirtyFiles) {
      await saveFile(path);
    }
  };

  const updateFileContent = (path, content) => {
    setFileContents(prev => ({ ...prev, [path]: content }));
    setDirtyFiles(prev => new Set(prev).add(path));
  };

  const refreshPreview = () => {
    if (iframeRef.current) {
      iframeRef.current.src = iframeRef.current.src;
    }
  };

  const getFileLanguage = (path) => path?.split('.').pop()?.toLowerCase() || '';

  const handlePush = async () => {
    if (!previewInfo?.ready_for_push) {
      alert("Das Projekt muss zuerst vom Agent als bereit markiert werden.");
      return;
    }
    
    setIsPushing(true);
    try {
      await api.pushToGitHub(projectId);
      alert("Erfolgreich zu GitHub gepusht!");
      refreshData();
    } catch (e) {
      alert("Push fehlgeschlagen: " + (e.response?.data?.detail || e.message));
    } finally {
      setIsPushing(false);
    }
  };

  const sendMessage = async (content) => {
    if (!content?.trim()) return;
    
    const userMessage = { id: Date.now().toString(), role: "user", content: content.trim(), created_at: new Date().toISOString() };
    setMessages(prev => [...prev, userMessage]);
    setInputValue("");
    setIsLoading(true);
    setAgentProgress({ iteration: 0, maxIterations: 20, currentTool: null, isAutonomous: true });
    setAgentActivities([]); // Clear previous activities
    
    addActivity('orchestrator', 'thinking', 'Starte autonome Entwicklung...', 'Analysiere Anfrage');

    try {
      const response = await fetch(`${API}/projects/${projectId}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_id: projectId, content: content.trim() }),
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let aiContent = "";
      let aiMessageId = Date.now().toString() + "_ai";
      let filesCreated = [];
      
      setMessages(prev => [...prev, { id: aiMessageId, role: "assistant", content: "", created_at: new Date().toISOString(), agent_type: "orchestrator" }]);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        const text = decoder.decode(value);
        const lines = text.split('\n');
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              if (data.content) {
                aiContent += data.content;
                setMessages(prev => prev.map(msg => msg.id === aiMessageId ? { ...msg, content: aiContent } : msg));
              }
              if (data.iteration) {
                setAgentProgress(prev => ({ ...prev, iteration: data.iteration }));
              }
              // Handle tool calls with detailed activity display
              if (data.tool) {
                setAgentProgress(prev => ({ ...prev, currentTool: data.tool }));
                const toolMessages = {
                  'create_file': { agent: 'coder', action: 'file_created', msg: 'Erstellt Datei' },
                  'modify_file': { agent: 'coder', action: 'file_modified', msg: 'Bearbeitet Datei' },
                  'read_file': { agent: 'coder', action: 'thinking', msg: 'Liest Datei' },
                  'delete_file': { agent: 'coder', action: 'file_deleted', msg: 'Löscht Datei' },
                  'list_files': { agent: 'coder', action: 'thinking', msg: 'Analysiert Projektstruktur' },
                  'run_command': { agent: 'tester', action: 'test_started', msg: 'Führt Befehl aus' },
                  'create_roadmap': { agent: 'planner', action: 'thinking', msg: 'Erstellt Roadmap-Punkt' },
                  'update_roadmap_status': { agent: 'planner', action: 'thinking', msg: 'Aktualisiert Roadmap' },
                  'web_search': { agent: 'planner', action: 'searching', msg: 'Recherchiert Best Practices' },
                  'test_code': { agent: 'tester', action: 'test_started', msg: 'Testet Code' },
                  'debug_error': { agent: 'debugger', action: 'error_found', msg: 'Analysiert Fehler' },
                  'ask_user': { agent: 'orchestrator', action: 'thinking', msg: 'Hat eine Frage' },
                  'mark_complete': { agent: 'orchestrator', action: 'complete', msg: 'Projekt fertiggestellt' },
                };
                const toolInfo = toolMessages[data.tool] || { agent: 'coder', action: 'thinking', msg: data.tool };
                const details = data.args ? Object.entries(data.args).map(([k, v]) => `${k}: ${v}`).join(', ') : null;
                addActivity(toolInfo.agent, toolInfo.action, toolInfo.msg, details);
              }
              // Handle tool results
              if (data.tool_result) {
                const isError = data.tool_result.includes('✗') || data.tool_result.toLowerCase().includes('fehler');
                const isSuccess = data.tool_result.includes('✓') || data.tool_result.includes('✅');
                if (isError) {
                  addActivity('debugger', 'error_found', 'Fehler gefunden', data.tool_result.substring(0, 100));
                  addActivity('debugger', 'thinking', 'Analysiert Problem...', 'Suche nach Lösung');
                } else if (isSuccess) {
                  addActivity('coder', 'test_passed', 'Erfolgreich', data.tool_result.substring(0, 80));
                }
              }
              if (data.agent) {
                setAgents(prev => prev.map(a => a.agent_type === data.agent ? { ...a, status: data.status } : a));
                if (data.status === 'running') {
                  addActivity(data.agent, 'thinking', `${data.agent} übernimmt...`, null);
                }
              }
              if (data.autonomous !== undefined) {
                setAgentProgress(prev => ({ ...prev, isAutonomous: data.autonomous }));
                if (data.autonomous) {
                  addActivity('orchestrator', 'thinking', 'Arbeitet autonom weiter...', null);
                }
              }
              if (data.ask_user) {
                setAgentProgress(prev => ({ ...prev, isAutonomous: false, currentTool: "ask_user" }));
                addActivity('orchestrator', 'handoff', 'Wartet auf Benutzer-Eingabe', 'Agent hat eine Frage');
                
                // CRITICAL: Add question as AI message in chat!
                const questionText = data.question || data.content || 'Agent hat eine Frage';
                setMessages(prev => [
                  ...prev,
                  {
                    id: Date.now(),
                    role: 'assistant',
                    content: `❓ **FRAGE VOM AGENT:**\n\n${questionText}\n\n_Bitte beantworten Sie die Frage im Chat-Feld._`,
                    timestamp: new Date().toISOString()
                  }
                ]);
                
                // Scroll to bottom to show question
                setTimeout(() => {
                  const chatContainer = document.querySelector('.overflow-y-auto');
                  if (chatContainer) {
                    chatContainer.scrollTop = chatContainer.scrollHeight;
                  }
                }, 100);
              }
              if (data.complete) {
                setAgentProgress(prev => ({ ...prev, isAutonomous: false, currentTool: "complete" }));
                addActivity('orchestrator', 'complete', 'Projekt fertiggestellt!', 'Bereit für GitHub Push');
              }
              if (data.done) {
                filesCreated = data.files_created || [];
                if (filesCreated.length > 0) {
                  setMessages(prev => prev.map(msg => msg.id === aiMessageId ? { ...msg, files_created: filesCreated } : msg));
                  addActivity('coder', 'file_created', `${filesCreated.length} Datei(en) erstellt`, filesCreated.join(', '));
                }
                addActivity('orchestrator', 'complete', 'Iteration abgeschlossen', `${data.iterations || 0} Schritte`);
                setAgentProgress({ iteration: 0, maxIterations: 20, currentTool: null, isAutonomous: false });
                refreshData();
                refreshPreview();
              }
              // Handle warning
              if (data.warning) {
                addActivity('orchestrator', 'error_found', 'Warnung', data.warning);
              }
              // Handle errors
              if (data.error) {
                addActivity('debugger', 'error_found', 'Fehler aufgetreten', data.error);
              }
            } catch (e) {}
          }
        }
      }
    } catch (e) {
      console.error("Chat error:", e);
      addActivity('orchestrator', 'error_found', 'Verbindungsfehler', e.message);
    } finally {
      setIsLoading(false);
      setAgentProgress({ iteration: 0, maxIterations: 20, currentTool: null, isAutonomous: false });
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(inputValue);
    }
  };

  const scrollToBottom = () => {
    if (chatContainerRef.current) chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
  };

  if (!project) {
    return <div className="min-h-screen bg-zinc-950 flex items-center justify-center"><Loader2 size={32} className="animate-spin text-zinc-500" /></div>;
  }

  return (
    <div className="workspace-container bg-zinc-950">
      {/* Update Banner */}
      {updateStatus?.update_available && showUpdateBanner && (
        <div className="fixed top-0 left-0 right-0 z-[100] bg-gradient-to-r from-blue-600 to-purple-600 text-white px-4 py-2 shadow-lg">
          <div className="max-w-7xl mx-auto flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-1.5 bg-white/20 rounded-full">
                <RefreshCw size={16} className={isUpdating ? 'animate-spin' : ''} />
              </div>
              <div>
                <span className="font-medium">Update verfügbar: Version {updateStatus.latest_version}</span>
                <span className="text-white/70 text-sm ml-2">(aktuell: {updateStatus.installed_version})</span>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {updateMessage && (
                <span className="text-sm px-3 py-1 bg-white/20 rounded-md">
                  {updateMessage.text}
                </span>
              )}
              <button 
                onClick={handleInstallUpdate}
                disabled={isUpdating}
                className="px-3 py-1 text-sm bg-white text-blue-600 hover:bg-blue-50 rounded-md font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {isUpdating && <Loader2 size={14} className="animate-spin" />}
                {isUpdating ? 'Update läuft...' : 'Jetzt updaten'}
              </button>
              {!isUpdating && (
                <button 
                  onClick={() => setShowUpdateBanner(false)} 
                  className="p-1 hover:bg-white/20 rounded-md transition-colors"
                >
                  <X size={16} />
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Update Instructions Modal */}
      {showUpdateInstructions && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-[110] p-4" onClick={() => !isUpdating && setShowUpdateInstructions(false)}>
          <div className="bg-zinc-900 border border-zinc-700 rounded-lg w-full max-w-lg shadow-2xl" onClick={e => e.stopPropagation()}>
            <div className="p-4 border-b border-zinc-800 flex items-center justify-between">
              <h3 className="text-lg font-medium text-white flex items-center gap-2">
                <RefreshCw size={20} className={`text-emerald-400 ${isUpdating ? 'animate-spin' : ''}`} />
                Update auf {updateStatus?.latest_version}
              </h3>
              {!isUpdating && (
                <button onClick={() => setShowUpdateInstructions(false)} className="text-zinc-400 hover:text-white">
                  <X size={20} />
                </button>
              )}
            </div>
            <div className="p-4 space-y-4">
              {/* Status-Nachricht */}
              {updateMessage && (
                <div className={`p-3 rounded-lg text-sm ${
                  updateMessage.type === 'success' ? 'bg-emerald-500/10 border border-emerald-500/30 text-emerald-300' :
                  updateMessage.type === 'error' ? 'bg-rose-500/10 border border-rose-500/30 text-rose-300' :
                  updateMessage.type === 'warning' ? 'bg-amber-500/10 border border-amber-500/30 text-amber-300' :
                  'bg-blue-500/10 border border-blue-500/30 text-blue-300'
                }`}>
                  {updateMessage.text}
                </div>
              )}

              {/* Automatisches Update (empfohlen) */}
              {!isUpdating && (
                <div className="bg-zinc-950 rounded-lg p-4 border-2 border-emerald-500/30">
                  <div className="flex items-center gap-2 mb-3">
                    <span className="px-2 py-0.5 bg-emerald-500/20 text-emerald-400 text-xs rounded font-medium">🚀 Empfohlen</span>
                    <span className="text-sm font-medium text-white">Automatisches Update</span>
                  </div>
                  <p className="text-xs text-zinc-400 mb-3">
                    Klicke auf den Button, um das Update automatisch durchzuführen. 
                    Die Anwendung wird in ca. 30 Sekunden neu gestartet.
                  </p>
                  <button
                    onClick={handleInstallUpdate}
                    disabled={isUpdating}
                    className="w-full px-4 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded font-medium flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
                  >
                    <RefreshCw size={16} />
                    Automatisches Update starten
                  </button>
                </div>
              )}

              {/* Manuelle Optionen */}
              <div className="space-y-3">
                <p className="text-sm text-zinc-400">
                  <strong>Alternative:</strong> Manuell auf dem Unraid Server:
                </p>
                
                {/* Option 1: Update Script */}
                <div className="bg-zinc-950 rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-sm font-medium text-white">Update Script</span>
                  </div>
                  <code className="text-emerald-400 font-mono text-sm">bash /app/forgepilot/update.sh</code>
                  <p className="text-xs text-zinc-500 mt-2">Das Script macht alles automatisch: Pull, Stop, Remove, Start</p>
                </div>
                
                {/* Option 2: Manuell */}
                <div className="bg-zinc-950 rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-sm font-medium text-zinc-400">Oder manuell:</span>
                  </div>
                  <div className="font-mono text-sm space-y-1">
                    <div className="text-zinc-400">cd /app/forgepilot</div>
                    <div className="text-emerald-400">docker-compose -f /app/forgepilot/docker-compose.unraid.yml pull</div>
                    <div className="text-emerald-400">docker-compose -f /app/forgepilot/docker-compose.unraid.yml down</div>
                    <div className="text-emerald-400">docker-compose -f /app/forgepilot/docker-compose.unraid.yml up -d</div>
                  </div>
                </div>
                
                <button
                  onClick={() => {
                    navigator.clipboard.writeText('bash /app/forgepilot/update.sh');
                  }}
                  className="w-full px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-white rounded flex items-center justify-center gap-2"
                >
                  <Terminal size={16} />
                  Script-Befehl kopieren
                </button>
              </div>
            </div>
            <div className="p-4 border-t border-zinc-800 flex justify-end">
              {!isUpdating && (
                <button onClick={() => setShowUpdateInstructions(false)} className="px-4 py-2 bg-zinc-700 hover:bg-zinc-600 text-white rounded">
                  Schließen
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Navigation */}
      <nav className="h-14 border-b border-zinc-800 bg-zinc-950/80 backdrop-blur-xl flex items-center justify-between px-4 shrink-0 z-50">
        <div className="flex items-center gap-4">
          <Tooltip text="Zurück zur Startseite" position="bottom">
            <button onClick={() => navigate("/")} className="p-2 text-zinc-400 hover:text-white hover:bg-zinc-800/50 rounded-md" data-testid="home-btn"><Home size={18} /></button>
          </Tooltip>
          <div className="h-6 w-px bg-zinc-800" />
          <Logo />
          <div className="h-6 w-px bg-zinc-800" />
          <span className="text-sm text-zinc-400 max-w-[200px] truncate">{project.name}</span>
        </div>
        <div className="flex items-center gap-2">
          {/* Autonomous Progress Indicator */}
          {agentProgress.isAutonomous && (
            <div className="flex items-center gap-2 px-3 py-1.5 bg-blue-500/10 border border-blue-500/30 rounded-md animate-pulse">
              <Loader2 size={14} className="animate-spin text-blue-400" />
              <span className="text-xs text-blue-300">
                Autonom: {agentProgress.iteration}/{agentProgress.maxIterations}
                {agentProgress.currentTool && ` • ${agentProgress.currentTool}`}
              </span>
            </div>
          )}
          {project.github_url && (
            <Tooltip text={previewInfo?.ready_for_push ? `Bereit für Push: "${previewInfo.pending_commit_message}"` : "Änderungen zu GitHub pushen (Agent muss zuerst als bereit markieren)"} position="bottom">
              <button 
                onClick={handlePush}
                disabled={!previewInfo?.ready_for_push || isPushing}
                className={`flex items-center gap-2 px-3 py-1.5 text-sm rounded-md transition-colors ${
                  previewInfo?.ready_for_push 
                    ? "bg-emerald-600 hover:bg-emerald-500 text-white" 
                    : "text-zinc-400 hover:text-white hover:bg-zinc-800/50"
                }`}
                data-testid="push-btn"
              >
                {isPushing ? <Loader2 size={14} className="animate-spin" /> : <Upload size={14} />}
                {previewInfo?.ready_for_push ? "Jetzt pushen" : "Push"}
              </button>
            </Tooltip>
          )}
          <Tooltip text="Zeigt/versteckt den Datei-Explorer links" position="bottom">
            <button onClick={() => setShowFileExplorer(!showFileExplorer)} className={`p-2 rounded-md ${showFileExplorer ? 'bg-zinc-800 text-white' : 'text-zinc-400 hover:text-white hover:bg-zinc-800/50'}`} data-testid="toggle-file-explorer-btn"><LayoutPanelLeft size={18} /></button>
          </Tooltip>
          <Tooltip text={showRightPanel ? "Preview-Panel schließen" : "Preview-Panel öffnen"} position="bottom">
            <button 
              onClick={() => setShowRightPanel(!showRightPanel)} 
              className={`p-2 rounded-md ${showRightPanel ? 'bg-zinc-800 text-white' : 'text-zinc-400 hover:text-white hover:bg-zinc-800/50'}`} 
              data-testid="toggle-right-panel-btn"
            >
              {showRightPanel ? <PanelRightClose size={18} /> : <PanelRightOpen size={18} />}
            </button>
          </Tooltip>
          <Tooltip text="Einstellungen (Ollama, LLM-Auswahl)" position="bottom">
            <button onClick={() => setShowSettings(true)} className="p-2 text-zinc-400 hover:text-white hover:bg-zinc-800/50 rounded-md" data-testid="settings-btn"><Settings size={18} /></button>
          </Tooltip>
          <Tooltip text="Öffnet die Live-Preview in einem neuen Tab" position="bottom">
            <button 
              onClick={() => previewInfo?.preview_url && window.open(`${PREVIEW_BASE}${previewInfo.preview_url}`, '_blank')}
              disabled={!previewInfo?.has_preview}
              className="flex items-center gap-2 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 disabled:bg-zinc-800 disabled:text-zinc-500 text-white text-sm font-medium rounded-md transition-colors" 
              data-testid="external-preview-btn"
            >
              <ExternalLink size={14} />
              Preview öffnen
            </button>
          </Tooltip>
        </div>
      </nav>

      {/* Workspace Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* File Explorer */}
        {showFileExplorer && (
          <div className="w-56 border-r border-zinc-800 bg-zinc-950 flex flex-col shrink-0" data-testid="file-explorer">
            <div className="h-10 border-b border-zinc-800 flex items-center justify-between px-3">
              <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500">Dateien</span>
              <Tooltip text="Aktualisiert die Dateiliste" position="bottom">
                <button onClick={refreshData} className="p-1 text-zinc-500 hover:text-white"><RefreshCw size={12} /></button>
              </Tooltip>
            </div>
            <div className="flex-1 overflow-y-auto p-2">
              {fileTree.length > 0 ? (
                <FileTreeView items={fileTree} onSelect={loadFile} selectedPath={activeFileTab} />
              ) : (
                <div className="text-center py-8 text-zinc-600 text-sm">
                  <Folder size={24} className="mx-auto mb-2 opacity-50" />
                  <p>Keine Dateien</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Chat Panel - expands when right panel is hidden */}
        <div className={`border-r border-zinc-800 bg-zinc-950 flex flex-col shrink-0 overflow-hidden transition-all duration-300 ${showRightPanel ? 'w-[420px]' : 'flex-1'}`}>
          <div className="p-3 border-b border-zinc-800 bg-zinc-900/30 shrink-0" data-testid="agent-timeline">
            <h3 className="text-xs font-semibold uppercase tracking-widest text-zinc-500 mb-2">Agent Status</h3>
            <div className="flex flex-wrap gap-1.5">
              {agents.map((agent) => <AgentStatusPill key={agent.agent_type} agent={agent} isProjectComplete={previewInfo?.ready_for_push} allAgents={agents} />)}
            </div>
          </div>

          {/* Agent Activity Feed - Live-Anzeige was gerade passiert */}
          {(isLoading || agentActivities.length > 0) && (
            <div className="border-b border-zinc-800 bg-zinc-900/20 shrink-0">
              <div className="p-2 border-b border-zinc-800/50 flex items-center justify-between">
                <h4 className="text-xs font-semibold uppercase tracking-widest text-zinc-500 flex items-center gap-2">
                  {isLoading && <Loader2 size={10} className="animate-spin text-blue-400" />}
                  Live-Aktivität
                </h4>
                {agentActivities.length > 0 && (
                  <span className="text-xs text-zinc-600">{agentActivities.length} Aktionen</span>
                )}
              </div>
              <div 
                ref={activityContainerRef} 
                className="max-h-48 overflow-y-auto p-2 space-y-1.5"
                data-testid="agent-activity-feed"
              >
                {agentActivities.map(activity => (
                  <AgentActivityItem key={activity.id} activity={activity} />
                ))}
                {isLoading && agentActivities.length === 0 && (
                  <div className="flex items-center gap-2 p-2 text-zinc-500 text-xs">
                    <Loader2 size={12} className="animate-spin" />
                    <span>Warte auf Agent-Aktivität...</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Project Summary when ready for push */}
          {previewInfo?.ready_for_push && (
            <div className="p-3 border-b border-zinc-800 shrink-0">
              <ProjectSummary 
                previewInfo={previewInfo} 
                onPush={handlePush} 
                isPushing={isPushing}
                onDeploy={startDeployment}
                isDeploying={isDeploying}
              />
            </div>
          )}

          <div ref={chatContainerRef} className="flex-1 overflow-y-auto p-4 space-y-4 min-h-0" data-testid="chat-message-list">
            {messages.map((message) => <ChatMessage key={message.id} message={message} />)}
            {isLoading && messages[messages.length - 1]?.role === "user" && (
              <div className="flex items-center gap-2 text-zinc-500">
                <Loader2 size={16} className="animate-spin" />
                <span className="text-sm">Agent arbeitet autonom...</span>
              </div>
            )}
          </div>

          <div className="px-3 py-1 border-t border-zinc-800/50 shrink-0">
            <button onClick={scrollToBottom} className="w-full text-xs text-zinc-500 hover:text-zinc-300 py-1 transition-colors">↓ Zum Ende scrollen</button>
          </div>

          {/* Chat Input Area */}
          <div className="p-3 border-t border-zinc-800 bg-zinc-900/50 shrink-0">
            {/* Uploaded Files Preview */}
            {uploadedFiles.length > 0 && (
              <div className="mb-2 flex flex-wrap gap-2">
                {uploadedFiles.map((file, idx) => (
                  <div key={idx} className="relative group">
                    {file.preview ? (
                      <img src={file.preview} alt={file.name} className="h-16 w-16 object-cover rounded border border-zinc-700" />
                    ) : (
                      <div className="h-16 w-16 bg-zinc-800 rounded border border-zinc-700 flex items-center justify-center">
                        <File size={24} className="text-zinc-500" />
                      </div>
                    )}
                    <button
                      onClick={() => removeFile(idx)}
                      className="absolute -top-1 -right-1 bg-red-500 hover:bg-red-600 text-white rounded-full p-0.5 opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      <X size={12} />
                    </button>
                    <div className="text-xs text-zinc-500 mt-1 max-w-[64px] truncate">{file.name}</div>
                  </div>
                ))}
              </div>
            )}
            
            <div className="flex items-end gap-2">
              <textarea value={inputValue} onChange={(e) => setInputValue(e.target.value)} onKeyDown={handleKeyDown} placeholder={isListening ? "Sprich jetzt..." : "Nachricht an Agent..."} rows={2} className={`flex-1 bg-zinc-800 border text-white px-3 py-2 rounded-md focus:outline-none placeholder:text-zinc-600 resize-none text-sm transition-colors ${isListening ? 'border-red-500 bg-red-500/10' : 'border-zinc-700 focus:border-zinc-500'}`} data-testid="chat-input" />
              
              {/* File Upload Button */}
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept="image/*,text/*"
                onChange={handleFileUpload}
                className="hidden"
              />
              <Tooltip text="Dateien anhängen (Bilder, Logs, Screenshots)" position="top">
                <button
                  onClick={() => fileInputRef.current?.click()}
                  disabled={isLoading}
                  className="p-2 bg-zinc-700 text-zinc-300 rounded-md hover:bg-zinc-600 hover:text-white disabled:opacity-50 transition-colors"
                >
                  <Paperclip size={18} />
                </button>
              </Tooltip>
              
              {speechSupported && (
                <Tooltip text={isListening ? "Spracherkennung stoppen" : "Spracherkennung starten (Deutsch)"} position="top">
                  <button 
                    onClick={toggleVoiceInput} 
                    disabled={isLoading}
                    className={`p-2 rounded-md transition-all ${
                      isListening 
                        ? 'bg-red-500 text-white animate-pulse hover:bg-red-600' 
                        : 'bg-zinc-700 text-zinc-300 hover:bg-zinc-600 hover:text-white'
                    } disabled:opacity-50`} 
                    data-testid="voice-input-btn"
                  >
                    {isListening ? <MicOff size={18} /> : <Mic size={18} />}
                  </button>
                </Tooltip>
              )}
              <Tooltip text="Sendet die Nachricht an den KI-Agenten" position="top">
                <button onClick={() => sendMessage(inputValue)} disabled={!inputValue.trim() || isLoading} className="p-2 bg-white text-black rounded-md hover:bg-zinc-200 disabled:opacity-50" data-testid="send-message-btn">
                  {isLoading ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
                </button>
              </Tooltip>
            </div>
            {isListening && (
              <div className="flex items-center gap-2 mt-2 text-xs text-red-400">
                <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
                <span>Aufnahme läuft... Sprich deutlich auf Deutsch</span>
              </div>
            )}
          </div>
        </div>

        {/* Right Panel - Preview/Editor/Logs/Roadmap */}
        {showRightPanel && (
        <div className="flex-1 bg-zinc-900/50 flex flex-col overflow-hidden panel-expanded">
          <div className="h-10 border-b border-zinc-800 flex items-center px-2 bg-zinc-950/50 shrink-0">
            <div className="flex items-center gap-1">
              {[
                { id: "preview", label: "Live Preview", icon: Eye, tip: "Zeigt eine Live-Vorschau des Projekts" },
                { id: "editor", label: "Editor", icon: Code, tip: "Code-Editor mit Syntax-Highlighting" },
                { id: "logs", label: "Logs", icon: Terminal, tip: "Zeigt System- und Agent-Logs" },
                { id: "roadmap", label: "Roadmap", icon: ListTodo, tip: "Zeigt den Projektplan und Fortschritt" },
              ].map(({ id, label, icon: Icon, tip }) => (
                <Tooltip key={id} text={tip} position="bottom">
                  <button onClick={() => setActiveTab(id)} className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium border-b-2 transition-all ${activeTab === id ? "border-white text-white" : "border-transparent text-zinc-400 hover:text-zinc-100"}`} data-testid={`tab-${id}`}>
                    <Icon size={12} />
                    <span className="max-w-[120px] truncate">{label}</span>
                    {id === "editor" && dirtyFiles.size > 0 && <span className="w-2 h-2 bg-amber-400 rounded-full" />}
                  </button>
                </Tooltip>
              ))}
            </div>
            <div className="flex-1" />
            {activeTab === "editor" && dirtyFiles.size > 0 && (
              <Tooltip text="Speichert alle geänderten Dateien" position="bottom">
                <button onClick={saveAllFiles} className="flex items-center gap-1 px-2 py-1 text-xs text-amber-400 hover:text-amber-300" data-testid="save-all-btn"><Save size={12} />Alle speichern ({dirtyFiles.size})</button>
              </Tooltip>
            )}
            {activeTab === "preview" && (
              <Tooltip text="Lädt die Preview neu" position="bottom">
                <button onClick={refreshPreview} className="p-1.5 text-zinc-400 hover:text-white"><RefreshCw size={14} /></button>
              </Tooltip>
            )}
            <Tooltip text="Panel schließen" position="bottom">
              <button onClick={() => setShowRightPanel(false)} className="p-1.5 text-zinc-400 hover:text-white ml-2"><X size={14} /></button>
            </Tooltip>
          </div>

          <div className="flex-1 overflow-hidden">
            {activeTab === "preview" && (
              <div className="h-full p-3" data-testid="preview-panel">
                <div className="h-full bg-zinc-950 rounded-lg border border-zinc-800 overflow-hidden flex flex-col">
                  <div className="h-8 bg-zinc-900 border-b border-zinc-800 flex items-center px-3 gap-2 shrink-0">
                    <div className="flex gap-1">
                      <div className="w-2.5 h-2.5 rounded-full bg-rose-500" />
                      <div className="w-2.5 h-2.5 rounded-full bg-amber-500" />
                      <div className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
                    </div>
                    <div className="flex-1 mx-2">
                      <div className="bg-zinc-800 rounded px-2 py-0.5 text-xs text-zinc-500">
                        {previewInfo?.has_preview ? previewInfo.entry_point : "Keine Preview verfügbar"}
                      </div>
                    </div>
                    <Tooltip text="Preview in neuem Tab öffnen" position="bottom">
                      <button 
                        onClick={() => previewInfo?.preview_url && window.open(`${PREVIEW_BASE}${previewInfo.preview_url}`, '_blank')}
                        className="p-1 text-zinc-500 hover:text-white"
                      >
                        <ExternalLink size={12} />
                      </button>
                    </Tooltip>
                  </div>
                  <div className="flex-1 bg-white" data-testid="live-preview-iframe">
                    {previewInfo?.has_preview ? (
                      <iframe
                        ref={iframeRef}
                        src={`${PREVIEW_BASE}${previewInfo.preview_url}`}
                        className="w-full h-full border-0"
                        title="Live Preview"
                      />
                    ) : (
                      <div className="h-full flex items-center justify-center bg-zinc-950 text-zinc-600">
                        <div className="text-center space-y-3">
                          <div className="w-12 h-12 mx-auto bg-zinc-800 rounded-lg flex items-center justify-center">
                            <Eye size={24} className="text-zinc-600" />
                          </div>
                          <p className="font-medium text-zinc-400">Keine Preview verfügbar</p>
                          <p className="text-sm text-zinc-600">Erstelle eine index.html Datei</p>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
            
            {activeTab === "editor" && (
              <div className="h-full flex flex-col" data-testid="editor-panel">
                {/* File Tabs */}
                {openTabs.length > 0 && (
                  <div className="flex items-center border-b border-zinc-800 bg-zinc-900/50 overflow-x-auto shrink-0">
                    {openTabs.map(path => {
                      const fileName = path.split('/').pop();
                      const isDirty = dirtyFiles.has(path);
                      const isActive = activeFileTab === path;
                      return (
                        <div
                          key={path}
                          onClick={() => setActiveFileTab(path)}
                          className={`flex items-center gap-2 px-3 py-2 text-xs cursor-pointer border-r border-zinc-800 transition-colors group ${
                            isActive ? 'bg-zinc-800 text-white' : 'text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-200'
                          }`}
                          data-testid={`file-tab-${fileName}`}
                        >
                          <File size={12} />
                          <span className="max-w-[100px] truncate">{fileName}</span>
                          {isDirty && <span className="w-1.5 h-1.5 bg-amber-400 rounded-full" />}
                          <button
                            onClick={(e) => closeTab(path, e)}
                            className="p-0.5 opacity-0 group-hover:opacity-100 hover:bg-zinc-700 rounded transition-opacity"
                            data-testid={`close-tab-${fileName}`}
                          >
                            <X size={10} />
                          </button>
                        </div>
                      );
                    })}
                  </div>
                )}
                {/* Editor Content */}
                <div className="flex-1 overflow-hidden">
                  {activeFileTab ? (
                    <SyntaxEditor 
                      content={fileContents[activeFileTab] || ''} 
                      onChange={(val) => updateFileContent(activeFileTab, val)} 
                      language={getFileLanguage(activeFileTab)} 
                    />
                  ) : (
                    <div className="h-full flex items-center justify-center text-zinc-600">
                      <div className="text-center space-y-3">
                        <Code size={32} className="mx-auto opacity-50" />
                        <p>Wähle eine Datei aus dem Explorer</p>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
            
            {activeTab === "logs" && (
              <div className="h-full p-3 overflow-auto" data-testid="log-console-view">
                <div className="min-h-full bg-zinc-950 rounded-lg border border-zinc-800 p-3 font-mono">
                  {logs.length === 0 ? (
                    <div className="text-zinc-600 text-center py-8">
                      <Terminal size={24} className="mx-auto mb-2 opacity-50" />
                      <p className="text-sm">Noch keine Logs</p>
                    </div>
                  ) : (
                    <div className="space-y-1">{logs.map((log) => <LogEntry key={log.id} log={log} onClick={(log) => setSelectedLog(log)} />)}</div>
                  )}
                </div>
              </div>
            )}
            
            {activeTab === "roadmap" && (
              <div className="h-full p-4 overflow-auto" data-testid="roadmap-panel">
                <RoadmapView items={roadmap} />
              </div>
            )}
          </div>
        </div>
        )}
      </div>

      {/* Settings Modal */}
      {showSettings && (
        <SettingsModal 
          isOpen={showSettings} 
          onClose={() => setShowSettings(false)}
          onRefreshLLMStatus={checkOllamaStatus}
        />
      )}

      {/* Deploy Modal */}
      {showDeployModal && (
        <DeployModal
          projectId={projectId}
          projectName={project?.name || 'Unbekannt'}
          onClose={() => setShowDeployModal(false)}
        />
      )}
      
      {/* Log Detail Modal */}
      {selectedLog && (
        <LogDetailModal
          log={selectedLog}
          onClose={() => setSelectedLog(null)}
        />
      )}
    </div>
  );
};

// ============== App ==============

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<StartScreen />} />
          <Route path="/workspace/:projectId" element={<Workspace />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;
