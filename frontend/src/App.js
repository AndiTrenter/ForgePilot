import React, { useState, useEffect, useRef } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, useNavigate, useParams } from "react-router-dom";
import axios from "axios";
import { 
  Send, Loader2, GitBranch, FolderGit2, Play, RefreshCw, 
  Home, Settings, ChevronRight, FileCode, Terminal, 
  CheckCircle2, Zap, Bug, Eye, X, Code, ListTodo,
  Folder, File, ChevronDown, Save, LayoutPanelLeft, GitCommit,
  Check, Circle, ArrowRight, Lock, Globe, Upload, Search,
  ExternalLink, Mic, MicOff, Square
} from "lucide-react";
import Prism from 'prismjs';
import 'prismjs/themes/prism-tomorrow.css';
import 'prismjs/components/prism-javascript';
import 'prismjs/components/prism-css';
import 'prismjs/components/prism-markup';
import 'prismjs/components/prism-python';
import 'prismjs/components/prism-json';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// ============== API Functions ==============
const api = {
  getProjects: () => axios.get(`${API}/projects`),
  createProject: (data) => axios.post(`${API}/projects`, data),
  getProject: (id) => axios.get(`${API}/projects/${id}`),
  deleteProject: (id) => axios.delete(`${API}/projects/${id}`),
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
    <div className="w-6 h-6 bg-white rounded-sm flex items-center justify-center">
      <span className="text-black text-sm font-bold">F</span>
    </div>
    <span>ForgePilot</span>
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

const ProjectSummary = ({ previewInfo, onPush, isPushing }) => {
  if (!previewInfo?.ready_for_push) return null;
  
  return (
    <div className="p-4 bg-gradient-to-r from-emerald-500/10 to-blue-500/10 border border-emerald-500/30 rounded-lg animate-fade-in">
      <div className="flex items-start gap-3">
        <div className="p-2 bg-emerald-500/20 rounded-lg">
          <CheckCircle2 size={24} className="text-emerald-400" />
        </div>
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-emerald-300 flex items-center gap-2">
            Projekt fertig!
            <span className="px-2 py-0.5 bg-emerald-500/20 text-emerald-400 text-xs rounded-full">Bereit für Push</span>
          </h3>
          <p className="text-sm text-zinc-400 mt-1">{previewInfo.pending_commit_message}</p>
          
          {previewInfo.tested_features?.length > 0 && (
            <div className="mt-3">
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
          
          <div className="flex items-center gap-2 mt-4">
            <button 
              onClick={onPush}
              disabled={isPushing}
              className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-medium rounded-md transition-colors disabled:opacity-50"
            >
              {isPushing ? <Loader2 size={16} className="animate-spin" /> : <Upload size={16} />}
              Jetzt zu GitHub pushen
            </button>
            <button className="flex items-center gap-2 px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-white rounded-md transition-colors">
              <ExternalLink size={16} />
              Live Preview öffnen
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

const AgentStatusPill = ({ agent }) => {
  const statusColors = {
    idle: "bg-zinc-700",
    running: "bg-blue-500 animate-pulse",
    completed: "bg-emerald-500",
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

  return (
    <Tooltip text={agentDescriptions[agent.agent_type] || "Agent"} position="bottom">
      <div 
        className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-zinc-900 border transition-all duration-300 cursor-help ${
          agent.status === "running" ? "border-blue-500/50 shadow-lg shadow-blue-500/20" : "border-zinc-800"
        }`}
        data-testid={`agent-status-${agent.agent_type}`}
      >
        <div className={`w-2 h-2 rounded-full ${statusColors[agent.status]}`} />
        <Icon size={14} />
        <span className="text-sm capitalize text-zinc-300">{agent.agent_type}</span>
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
        className="absolute inset-0 p-4 overflow-auto pointer-events-none m-0 whitespace-pre-wrap break-words"
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
        className="absolute inset-0 w-full h-full bg-transparent text-transparent caret-white p-4 resize-none focus:outline-none leading-relaxed whitespace-pre-wrap break-words"
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

const LogEntry = ({ log }) => {
  const levelColors = { info: "text-zinc-400", success: "text-emerald-400", warning: "text-amber-400", error: "text-rose-400" };
  const levelIcons = { info: "○", success: "✓", warning: "⚠", error: "✕" };

  return (
    <div className={`flex gap-2 text-xs ${levelColors[log.level]}`}>
      <span className="text-zinc-600 shrink-0">{new Date(log.timestamp).toLocaleTimeString()}</span>
      <span className="shrink-0">{levelIcons[log.level]}</span>
      <span className="text-zinc-500 shrink-0">[{log.source}]</span>
      <span className="break-all">{log.message}</span>
    </div>
  );
};

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

// ============== Start Screen ==============

const StartScreen = () => {
  const navigate = useNavigate();
  const [prompt, setPrompt] = useState("");
  const [projectType, setProjectType] = useState("fullstack");
  const [isLoading, setIsLoading] = useState(false);
  const [recentProjects, setRecentProjects] = useState([]);
  const [showGitHubModal, setShowGitHubModal] = useState(false);

  useEffect(() => {
    api.getProjects().then(res => setRecentProjects(res.data.slice(0, 6))).catch(() => {});
  }, []);

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

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) handleSubmit();
  };

  const projectTypes = [
    { id: "fullstack", label: "Full Stack App", icon: Terminal, desc: "Komplette Web-App mit Frontend und Backend" },
    { id: "mobile", label: "Mobile App", icon: FileCode, desc: "Mobile-optimierte Web-Anwendung" },
    { id: "landing", label: "Landing Page", icon: Eye, desc: "Einzelseite für Marketing oder Produkte" },
  ];

  return (
    <div className="min-h-screen bg-zinc-950 flex flex-col">
      <nav className="h-14 border-b border-zinc-800 bg-zinc-950/80 backdrop-blur-xl flex items-center justify-between px-6 sticky top-0 z-50">
        <Logo />
        <div className="flex items-center gap-4">
          <Tooltip text="Importiere ein bestehendes Projekt von GitHub. Du kannst deine Repositories und Branches auswählen." position="bottom">
            <button onClick={() => setShowGitHubModal(true)} className="flex items-center gap-2 px-3 py-1.5 text-sm text-zinc-400 hover:text-white hover:bg-zinc-800/50 rounded-md transition-colors" data-testid="github-import-btn">
              <FolderGit2 size={16} />
              <span>GitHub Import</span>
            </button>
          </Tooltip>
          <Tooltip text="Einstellungen und Konfiguration von ForgePilot" position="bottom">
            <button className="p-2 text-zinc-400 hover:text-white hover:bg-zinc-800/50 rounded-md transition-colors">
              <Settings size={18} />
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
              <Tooltip text="Startet die KI-gestützte Entwicklung. ForgePilot wird zuerst im Web nach Best Practices recherchieren." position="top">
                <button onClick={handleSubmit} disabled={!prompt.trim() || isLoading} className="flex items-center gap-2 bg-white text-black hover:bg-zinc-200 font-medium px-5 py-2.5 rounded-md transition-all disabled:opacity-50 disabled:cursor-not-allowed" data-testid="submit-prompt-btn">
                  {isLoading ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
                  <span>Projekt starten</span>
                </button>
              </Tooltip>
            </div>
          </div>

          {recentProjects.length > 0 && (
            <div className="w-full space-y-4">
              <h3 className="text-sm font-semibold uppercase tracking-widest text-zinc-500">Aktuelle Projekte</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {recentProjects.map((project) => (
                  <Tooltip key={project.id} text={`Öffne "${project.name}" im Workspace`} position="top">
                    <button onClick={() => navigate(`/workspace/${project.id}`)} className="flex items-center gap-3 p-4 bg-zinc-900 border border-zinc-800 rounded-lg text-left hover:border-zinc-700 hover:bg-zinc-800/50 transition-all group w-full" data-testid={`recent-project-${project.id}`}>
                      <div className="w-10 h-10 bg-zinc-800 rounded-md flex items-center justify-center text-zinc-400 group-hover:text-white transition-colors"><FileCode size={20} /></div>
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-zinc-200 truncate">{project.name}</p>
                        <p className="text-xs text-zinc-500">{project.project_type}</p>
                      </div>
                      <ChevronRight size={16} className="text-zinc-600" />
                    </button>
                  </Tooltip>
                ))}
              </div>
            </div>
          )}
        </div>
      </main>

      {showGitHubModal && <GitHubImportModal onClose={() => setShowGitHubModal(false)} onImport={(p) => { setShowGitHubModal(false); navigate(`/workspace/${p.id}`); }} />}
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
    <div className="min-h-screen bg-zinc-950 flex flex-col">
      {/* Navigation */}
      <nav className="h-14 border-b border-zinc-800 bg-zinc-950/80 backdrop-blur-xl flex items-center justify-between px-4 sticky top-0 z-50">
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
          <Tooltip text="Einstellungen (Ollama, LLM-Auswahl)" position="bottom">
            <button onClick={() => setShowSettings(true)} className="p-2 text-zinc-400 hover:text-white hover:bg-zinc-800/50 rounded-md" data-testid="settings-btn"><Settings size={18} /></button>
          </Tooltip>
          <Tooltip text="Öffnet die Live-Preview in einem neuen Tab" position="bottom">
            <button 
              onClick={() => previewInfo?.preview_url && window.open(`${BACKEND_URL}${previewInfo.preview_url}`, '_blank')}
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
      <div className="flex-1 flex h-[calc(100vh-3.5rem)] overflow-hidden">
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

        {/* Chat Panel */}
        <div className="w-[420px] border-r border-zinc-800 bg-zinc-950 flex flex-col shrink-0 overflow-hidden">
          <div className="p-3 border-b border-zinc-800 bg-zinc-900/30 shrink-0" data-testid="agent-timeline">
            <h3 className="text-xs font-semibold uppercase tracking-widest text-zinc-500 mb-2">Agent Status</h3>
            <div className="flex flex-wrap gap-1.5">
              {agents.map((agent) => <AgentStatusPill key={agent.agent_type} agent={agent} />)}
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
              <ProjectSummary previewInfo={previewInfo} onPush={handlePush} isPushing={isPushing} />
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

          <div className="p-3 border-t border-zinc-800 bg-zinc-900/50 shrink-0">
            <div className="flex items-end gap-2">
              <textarea value={inputValue} onChange={(e) => setInputValue(e.target.value)} onKeyDown={handleKeyDown} placeholder={isListening ? "Sprich jetzt..." : "Nachricht an Agent..."} rows={2} className={`flex-1 bg-zinc-800 border text-white px-3 py-2 rounded-md focus:outline-none placeholder:text-zinc-600 resize-none text-sm transition-colors ${isListening ? 'border-red-500 bg-red-500/10' : 'border-zinc-700 focus:border-zinc-500'}`} data-testid="chat-input" />
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
        <div className="flex-1 bg-zinc-900/50 flex flex-col overflow-hidden isolate">
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
                  </div>
                  <div className="flex-1 bg-white" data-testid="live-preview-iframe">
                    {previewInfo?.has_preview ? (
                      <iframe
                        ref={iframeRef}
                        src={`${BACKEND_URL}${previewInfo.preview_url}`}
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
                    <div className="space-y-1">{logs.map((log) => <LogEntry key={log.id} log={log} />)}</div>
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
      </div>

      {/* Settings Modal */}
      {showSettings && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4" data-testid="settings-modal">
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg w-full max-w-md shadow-2xl">
            <div className="flex items-center justify-between p-4 border-b border-zinc-800">
              <div className="flex items-center gap-2">
                <Settings size={20} />
                <h2 className="text-lg font-medium">Einstellungen</h2>
              </div>
              <button onClick={() => setShowSettings(false)} className="p-1 text-zinc-400 hover:text-white"><X size={20} /></button>
            </div>
            
            <div className="p-4 space-y-6">
              {/* LLM Selection */}
              <div>
                <h3 className="text-sm font-semibold text-zinc-300 mb-3">LLM Auswahl</h3>
                <div className="space-y-3">
                  <div 
                    onClick={() => setUseOllama(false)}
                    className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                      !useOllama ? 'bg-blue-500/10 border-blue-500/50' : 'bg-zinc-800/50 border-zinc-700 hover:border-zinc-600'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Zap size={16} className={!useOllama ? 'text-blue-400' : 'text-zinc-500'} />
                        <span className="font-medium">OpenAI GPT-4o</span>
                      </div>
                      {!useOllama && <Check size={16} className="text-blue-400" />}
                    </div>
                    <p className="text-xs text-zinc-500 mt-1">Cloud-basiert, beste Qualität</p>
                  </div>
                  
                  <div 
                    onClick={() => ollamaStatus.available && toggleOllama()}
                    className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                      !ollamaStatus.available ? 'opacity-50 cursor-not-allowed' : ''
                    } ${
                      useOllama && ollamaStatus.available ? 'bg-emerald-500/10 border-emerald-500/50' : 'bg-zinc-800/50 border-zinc-700 hover:border-zinc-600'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Terminal size={16} className={useOllama ? 'text-emerald-400' : 'text-zinc-500'} />
                        <span className="font-medium">Ollama (Lokal)</span>
                        {ollamaStatus.available ? (
                          <span className="px-1.5 py-0.5 text-xs bg-emerald-500/20 text-emerald-400 rounded">Verfügbar</span>
                        ) : (
                          <span className="px-1.5 py-0.5 text-xs bg-zinc-700 text-zinc-400 rounded">Nicht verbunden</span>
                        )}
                      </div>
                      {useOllama && ollamaStatus.available && <Check size={16} className="text-emerald-400" />}
                    </div>
                    <p className="text-xs text-zinc-500 mt-1">
                      {ollamaStatus.available 
                        ? `Modelle: ${ollamaStatus.models.join(', ') || 'Keine gefunden'}`
                        : 'Starte Ollama auf deinem System'
                      }
                    </p>
                  </div>
                </div>
              </div>

              {/* Ollama Info */}
              {!ollamaStatus.available && (
                <div className="p-3 bg-zinc-800/50 rounded-lg border border-zinc-700">
                  <h4 className="text-sm font-medium text-zinc-300 mb-2">Ollama Setup</h4>
                  <ol className="text-xs text-zinc-500 space-y-1 list-decimal list-inside">
                    <li>Installiere Ollama: <code className="bg-zinc-700 px-1 rounded">curl -fsSL https://ollama.com/install.sh | sh</code></li>
                    <li>Starte Ollama: <code className="bg-zinc-700 px-1 rounded">ollama serve</code></li>
                    <li>Lade ein Modell: <code className="bg-zinc-700 px-1 rounded">ollama pull llama3</code></li>
                  </ol>
                </div>
              )}
            </div>
            
            <div className="flex items-center justify-end gap-3 p-4 border-t border-zinc-800">
              <button onClick={() => setShowSettings(false)} className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-white rounded-md">Schließen</button>
            </div>
          </div>
        </div>
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
