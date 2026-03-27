import React, { useState, useEffect, useRef, useCallback } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, useNavigate, useParams } from "react-router-dom";
import axios from "axios";
import { 
  Send, Loader2, GitBranch, FolderGit2, Play, RefreshCw, 
  Home, Settings, ChevronRight, FileCode, Terminal, 
  CheckCircle2, Zap, Bug, Eye, X, Code, ListTodo,
  Folder, File, ChevronDown, Save, LayoutPanelLeft, GitCommit,
  Check, Circle, ArrowRight, Lock, Globe
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

const AgentStatusPill = ({ agent }) => {
  const statusColors = {
    idle: "bg-zinc-700",
    running: "bg-blue-500 animate-pulse",
    completed: "bg-emerald-500",
    error: "bg-rose-500",
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
    <div 
      className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-zinc-900 border transition-all duration-300 ${
        agent.status === "running" ? "border-blue-500/50 shadow-lg shadow-blue-500/20" : "border-zinc-800"
      }`}
      data-testid={`agent-status-${agent.agent_type}`}
    >
      <div className={`w-2 h-2 rounded-full ${statusColors[agent.status]}`} />
      <Icon size={14} />
      <span className="text-sm capitalize text-zinc-300">{agent.agent_type}</span>
    </div>
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

// Syntax Highlighted Code Editor
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
    { id: "fullstack", label: "Full Stack App", icon: Terminal },
    { id: "mobile", label: "Mobile App", icon: FileCode },
    { id: "landing", label: "Landing Page", icon: Eye },
  ];

  return (
    <div className="min-h-screen bg-zinc-950 flex flex-col">
      <nav className="h-14 border-b border-zinc-800 bg-zinc-950/80 backdrop-blur-xl flex items-center justify-between px-6 sticky top-0 z-50">
        <Logo />
        <div className="flex items-center gap-4">
          <button onClick={() => setShowGitHubModal(true)} className="flex items-center gap-2 px-3 py-1.5 text-sm text-zinc-400 hover:text-white hover:bg-zinc-800/50 rounded-md transition-colors" data-testid="github-import-btn">
            <FolderGit2 size={16} />
            <span>GitHub Import</span>
          </button>
          <button className="p-2 text-zinc-400 hover:text-white hover:bg-zinc-800/50 rounded-md transition-colors">
            <Settings size={18} />
          </button>
        </div>
      </nav>

      <main className="flex-1 flex flex-col items-center justify-center p-6 sm:p-12 md:p-24">
        <div className="max-w-3xl w-full flex flex-col items-center space-y-12">
          <div className="text-center space-y-4">
            <h1 className="text-4xl sm:text-5xl font-medium tracking-tighter text-zinc-50">Was möchtest du bauen?</h1>
            <p className="text-lg text-zinc-500">Beschreibe dein Projekt. ForgePilot plant, entwickelt und testet es für dich.</p>
          </div>

          <div className="flex items-center gap-2 p-1 bg-zinc-900 rounded-lg border border-zinc-800">
            {projectTypes.map(({ id, label, icon: Icon }) => (
              <button key={id} onClick={() => setProjectType(id)} className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all ${projectType === id ? "bg-zinc-800 text-white" : "text-zinc-400 hover:text-zinc-200"}`} data-testid={`project-type-${id}`}>
                <Icon size={16} />{label}
              </button>
            ))}
          </div>

          <div className="w-full bg-zinc-900 border border-zinc-800 rounded-lg shadow-2xl overflow-hidden focus-within:border-zinc-600 transition-colors" data-testid="prompt-container">
            <textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} onKeyDown={handleKeyDown} placeholder="Beschreibe dein Projekt in natürlicher Sprache..." className="w-full min-h-[200px] bg-transparent p-6 text-lg placeholder:text-zinc-600 focus:outline-none" data-testid="main-prompt-input" />
            <div className="flex items-center justify-between p-4 border-t border-zinc-800 bg-zinc-900/50">
              <span className="text-xs text-zinc-500">⌘ + Enter zum Starten</span>
              <button onClick={handleSubmit} disabled={!prompt.trim() || isLoading} className="flex items-center gap-2 bg-white text-black hover:bg-zinc-200 font-medium px-5 py-2.5 rounded-md transition-all disabled:opacity-50 disabled:cursor-not-allowed" data-testid="submit-prompt-btn">
                {isLoading ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
                <span>Projekt starten</span>
              </button>
            </div>
          </div>

          {recentProjects.length > 0 && (
            <div className="w-full space-y-4">
              <h3 className="text-sm font-semibold uppercase tracking-widest text-zinc-500">Aktuelle Projekte</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {recentProjects.map((project) => (
                  <button key={project.id} onClick={() => navigate(`/workspace/${project.id}`)} className="flex items-center gap-3 p-4 bg-zinc-900 border border-zinc-800 rounded-lg text-left hover:border-zinc-700 hover:bg-zinc-800/50 transition-all group" data-testid={`recent-project-${project.id}`}>
                    <div className="w-10 h-10 bg-zinc-800 rounded-md flex items-center justify-center text-zinc-400 group-hover:text-white transition-colors"><FileCode size={20} /></div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-zinc-200 truncate">{project.name}</p>
                      <p className="text-xs text-zinc-500">{project.project_type}</p>
                    </div>
                    <ChevronRight size={16} className="text-zinc-600" />
                  </button>
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

// ============== GitHub Import Modal with Dropdowns ==============

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

  useEffect(() => {
    loadRepos();
  }, []);

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
          {/* Toggle between dropdown and manual URL */}
          <div className="flex gap-2">
            <button onClick={() => setUseManualUrl(false)} className={`flex-1 py-2 rounded-md text-sm font-medium transition-colors ${!useManualUrl ? 'bg-zinc-800 text-white' : 'text-zinc-400 hover:text-zinc-200'}`}>
              Meine Repos
            </button>
            <button onClick={() => setUseManualUrl(true)} className={`flex-1 py-2 rounded-md text-sm font-medium transition-colors ${useManualUrl ? 'bg-zinc-800 text-white' : 'text-zinc-400 hover:text-zinc-200'}`}>
              URL eingeben
            </button>
          </div>

          {useManualUrl ? (
            <div>
              <label className="block text-sm font-medium text-zinc-400 mb-2">Repository URL</label>
              <input type="text" value={manualUrl} onChange={(e) => setManualUrl(e.target.value)} placeholder="https://github.com/user/repo" className="w-full bg-zinc-800 border border-zinc-700 text-white px-3 py-2.5 rounded-md focus:outline-none focus:border-zinc-500 placeholder:text-zinc-600" data-testid="github-repo-url-input" />
            </div>
          ) : (
            <React.Fragment>
              {/* Repository Dropdown */}
              <div>
                <label className="block text-sm font-medium text-zinc-400 mb-2">Repository auswählen</label>
                {isLoadingRepos ? (
                  <div className="flex items-center gap-2 text-zinc-500 py-2">
                    <Loader2 size={16} className="animate-spin" />
                    <span>Lade Repositories...</span>
                  </div>
                ) : (
                  <div className="relative">
                    <select
                      value={selectedRepo?.full_name || ""}
                      onChange={(e) => handleRepoSelect(e.target.value)}
                      className="w-full bg-zinc-800 border border-zinc-700 text-white px-3 py-2.5 rounded-md focus:outline-none focus:border-zinc-500 appearance-none cursor-pointer"
                      data-testid="github-repo-select"
                    >
                      <option value="">-- Repository wählen --</option>
                      {repos.map((repo) => (
                        <option key={repo.full_name} value={repo.full_name}>
                          {repo.private ? "🔒 " : "🌐 "}{repo.full_name}
                        </option>
                      ))}
                    </select>
                    <ChevronDown size={16} className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-400 pointer-events-none" />
                  </div>
                )}
              </div>

              {/* Selected Repo Info */}
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

              {/* Branch Dropdown */}
              {selectedRepo && (
                <div>
                  <label className="block text-sm font-medium text-zinc-400 mb-2">Branch auswählen</label>
                  {isLoadingBranches ? (
                    <div className="flex items-center gap-2 text-zinc-500 py-2">
                      <Loader2 size={16} className="animate-spin" />
                      <span>Lade Branches...</span>
                    </div>
                  ) : (
                    <div className="relative">
                      <select
                        value={selectedBranch}
                        onChange={(e) => setSelectedBranch(e.target.value)}
                        className="w-full bg-zinc-800 border border-zinc-700 text-white px-3 py-2.5 rounded-md focus:outline-none focus:border-zinc-500 appearance-none cursor-pointer"
                        data-testid="github-branch-select"
                      >
                        <option value="">-- Branch wählen --</option>
                        {branches.map((branch) => (
                          <option key={branch} value={branch}>{branch}</option>
                        ))}
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
          <button
            onClick={handleImport}
            disabled={(useManualUrl ? !manualUrl.trim() : (!selectedRepo || !selectedBranch)) || isImporting}
            className="flex items-center gap-2 bg-white text-black hover:bg-zinc-200 font-medium px-4 py-2 rounded-md disabled:opacity-50"
            data-testid="github-import-confirm-btn"
          >
            {isImporting ? <Loader2 size={16} className="animate-spin" /> : <GitBranch size={16} />}
            Importieren
          </button>
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
  const [selectedFile, setSelectedFile] = useState(null);
  const [fileContent, setFileContent] = useState("");
  const [isFileDirty, setIsFileDirty] = useState(false);
  const [showFileExplorer, setShowFileExplorer] = useState(true);
  const [autoScroll, setAutoScroll] = useState(false);
  const chatContainerRef = useRef(null);
  const pollingRef = useRef(null);

  useEffect(() => {
    loadProjectData();
    pollingRef.current = setInterval(refreshData, 5000);
    return () => { if (pollingRef.current) clearInterval(pollingRef.current); };
  }, [projectId]);

  // NO auto-scroll - user controls scroll position

  const loadProjectData = async () => {
    try {
      const [projectRes, messagesRes, agentsRes, logsRes, roadmapRes, filesRes] = await Promise.all([
        api.getProject(projectId),
        api.getMessages(projectId),
        api.getAgents(projectId),
        api.getLogs(projectId),
        api.getRoadmap(projectId),
        api.getFiles(projectId),
      ]);
      setProject(projectRes.data);
      setMessages(messagesRes.data);
      setAgents(agentsRes.data);
      setLogs(logsRes.data);
      setRoadmap(roadmapRes.data);
      setFileTree(filesRes.data.tree || []);
      
      if (messagesRes.data.length === 0 && projectRes.data.description) {
        sendMessage(projectRes.data.description);
      }
    } catch (e) {
      navigate("/");
    }
  };

  const refreshData = async () => {
    try {
      const [agentsRes, logsRes, filesRes, roadmapRes] = await Promise.all([
        api.getAgents(projectId),
        api.getLogs(projectId),
        api.getFiles(projectId),
        api.getRoadmap(projectId),
      ]);
      setAgents(agentsRes.data);
      setLogs(logsRes.data);
      setFileTree(filesRes.data.tree || []);
      setRoadmap(roadmapRes.data);
    } catch (e) {}
  };

  const loadFile = async (path) => {
    try {
      const res = await api.getFiles(projectId, path);
      if (res.data.type === "file") {
        setSelectedFile(path);
        setFileContent(res.data.content);
        setIsFileDirty(false);
        setActiveTab("editor");
      }
    } catch (e) {}
  };

  const saveFile = async () => {
    if (!selectedFile || !isFileDirty) return;
    try {
      await api.saveFile(projectId, selectedFile, fileContent);
      setIsFileDirty(false);
      refreshData();
    } catch (e) {}
  };

  const getFileLanguage = (path) => {
    const ext = path?.split('.').pop()?.toLowerCase() || '';
    return ext;
  };

  const sendMessage = async (content) => {
    if (!content?.trim()) return;
    
    const userMessage = { id: Date.now().toString(), role: "user", content: content.trim(), created_at: new Date().toISOString() };
    setMessages(prev => [...prev, userMessage]);
    setInputValue("");
    setIsLoading(true);

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
              if (data.agent) {
                setAgents(prev => prev.map(a => a.agent_type === data.agent ? { ...a, status: data.status } : a));
              }
              if (data.done) {
                filesCreated = data.files_created || [];
                if (filesCreated.length > 0) {
                  setMessages(prev => prev.map(msg => msg.id === aiMessageId ? { ...msg, files_created: filesCreated } : msg));
                }
                refreshData();
              }
            } catch (e) {}
          }
        }
      }
    } catch (e) {
      console.error("Chat error:", e);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(inputValue);
    }
  };

  const scrollToBottom = () => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  };

  if (!project) {
    return <div className="min-h-screen bg-zinc-950 flex items-center justify-center"><Loader2 size={32} className="animate-spin text-zinc-500" /></div>;
  }

  return (
    <div className="min-h-screen bg-zinc-950 flex flex-col">
      {/* Navigation */}
      <nav className="h-14 border-b border-zinc-800 bg-zinc-950/80 backdrop-blur-xl flex items-center justify-between px-4 sticky top-0 z-50">
        <div className="flex items-center gap-4">
          <button onClick={() => navigate("/")} className="p-2 text-zinc-400 hover:text-white hover:bg-zinc-800/50 rounded-md" data-testid="home-btn"><Home size={18} /></button>
          <div className="h-6 w-px bg-zinc-800" />
          <Logo />
          <div className="h-6 w-px bg-zinc-800" />
          <span className="text-sm text-zinc-400 max-w-[200px] truncate">{project.name}</span>
        </div>
        <div className="flex items-center gap-2">
          {project.github_url && (
            <button className="flex items-center gap-2 px-3 py-1.5 text-zinc-400 hover:text-white hover:bg-zinc-800/50 text-sm rounded-md" data-testid="commit-btn"><GitCommit size={14} />Commit</button>
          )}
          <button onClick={() => setShowFileExplorer(!showFileExplorer)} className={`p-2 rounded-md ${showFileExplorer ? 'bg-zinc-800 text-white' : 'text-zinc-400 hover:text-white hover:bg-zinc-800/50'}`} data-testid="toggle-file-explorer-btn"><LayoutPanelLeft size={18} /></button>
          <button className="flex items-center gap-2 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium rounded-md" data-testid="deploy-btn"><Play size={14} />Deploy</button>
        </div>
      </nav>

      {/* Workspace Layout */}
      <div className="flex-1 flex h-[calc(100vh-3.5rem)] overflow-hidden">
        {/* File Explorer */}
        {showFileExplorer && (
          <div className="w-56 border-r border-zinc-800 bg-zinc-950 flex flex-col shrink-0" data-testid="file-explorer">
            <div className="h-10 border-b border-zinc-800 flex items-center justify-between px-3">
              <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500">Dateien</span>
              <button onClick={refreshData} className="p-1 text-zinc-500 hover:text-white"><RefreshCw size={12} /></button>
            </div>
            <div className="flex-1 overflow-y-auto p-2">
              {fileTree.length > 0 ? (
                <FileTreeView items={fileTree} onSelect={loadFile} selectedPath={selectedFile} />
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
        <div className="w-96 border-r border-zinc-800 bg-zinc-950 flex flex-col shrink-0">
          <div className="p-3 border-b border-zinc-800 bg-zinc-900/30" data-testid="agent-timeline">
            <h3 className="text-xs font-semibold uppercase tracking-widest text-zinc-500 mb-2">Agent Status</h3>
            <div className="flex flex-wrap gap-1.5">
              {agents.map((agent) => <AgentStatusPill key={agent.agent_type} agent={agent} />)}
            </div>
          </div>

          {/* Chat Messages - NO AUTO-SCROLL */}
          <div ref={chatContainerRef} className="flex-1 overflow-y-auto p-4 space-y-4" data-testid="chat-message-list">
            {messages.map((message) => <ChatMessage key={message.id} message={message} />)}
            {isLoading && messages[messages.length - 1]?.role === "user" && (
              <div className="flex items-center gap-2 text-zinc-500">
                <Loader2 size={16} className="animate-spin" />
                <span className="text-sm">Agent arbeitet...</span>
              </div>
            )}
          </div>

          {/* Scroll to bottom button */}
          <div className="px-3 py-1 border-t border-zinc-800/50">
            <button onClick={scrollToBottom} className="w-full text-xs text-zinc-500 hover:text-zinc-300 py-1 transition-colors">
              ↓ Zum Ende scrollen
            </button>
          </div>

          {/* Chat Input */}
          <div className="p-3 border-t border-zinc-800 bg-zinc-900/50">
            <div className="flex items-end gap-2">
              <textarea value={inputValue} onChange={(e) => setInputValue(e.target.value)} onKeyDown={handleKeyDown} placeholder="Nachricht an Agent..." rows={2} className="flex-1 bg-zinc-800 border border-zinc-700 text-white px-3 py-2 rounded-md focus:outline-none focus:border-zinc-500 placeholder:text-zinc-600 resize-none text-sm" data-testid="chat-input" />
              <button onClick={() => sendMessage(inputValue)} disabled={!inputValue.trim() || isLoading} className="p-2 bg-white text-black rounded-md hover:bg-zinc-200 disabled:opacity-50" data-testid="send-message-btn">
                {isLoading ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
              </button>
            </div>
          </div>
        </div>

        {/* Right Panel */}
        <div className="flex-1 bg-zinc-900/50 flex flex-col overflow-hidden">
          <div className="h-10 border-b border-zinc-800 flex items-center px-2 bg-zinc-950/50 shrink-0">
            <div className="flex items-center gap-1">
              {[
                { id: "preview", label: "Preview", icon: Eye },
                { id: "editor", label: selectedFile || "Editor", icon: Code },
                { id: "logs", label: "Logs", icon: Terminal },
                { id: "roadmap", label: "Roadmap", icon: ListTodo },
              ].map(({ id, label, icon: Icon }) => (
                <button key={id} onClick={() => setActiveTab(id)} className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium border-b-2 transition-all ${activeTab === id ? "border-white text-white" : "border-transparent text-zinc-400 hover:text-zinc-100"}`} data-testid={`tab-${id}`}>
                  <Icon size={12} />
                  <span className="max-w-[120px] truncate">{label}</span>
                  {id === "editor" && isFileDirty && <span className="w-2 h-2 bg-amber-400 rounded-full" />}
                </button>
              ))}
            </div>
            <div className="flex-1" />
            {activeTab === "editor" && selectedFile && (
              <button onClick={saveFile} disabled={!isFileDirty} className="flex items-center gap-1 px-2 py-1 text-xs text-zinc-400 hover:text-white disabled:opacity-50" data-testid="save-file-btn"><Save size={12} />Speichern</button>
            )}
            <button className="p-1.5 text-zinc-400 hover:text-white" onClick={refreshData}><RefreshCw size={14} /></button>
          </div>

          <div className="flex-1 overflow-hidden">
            {activeTab === "preview" && (
              <div className="h-full p-3" data-testid="preview-panel">
                <div className="h-full bg-zinc-950 rounded-lg border border-zinc-800 overflow-hidden flex flex-col">
                  <div className="h-8 bg-zinc-900 border-b border-zinc-800 flex items-center px-3 gap-2 shrink-0">
                    <div className="flex gap-1">
                      <div className="w-2.5 h-2.5 rounded-full bg-zinc-700" />
                      <div className="w-2.5 h-2.5 rounded-full bg-zinc-700" />
                      <div className="w-2.5 h-2.5 rounded-full bg-zinc-700" />
                    </div>
                    <div className="flex-1 mx-2">
                      <div className="bg-zinc-800 rounded px-2 py-0.5 text-xs text-zinc-500">localhost:3000</div>
                    </div>
                  </div>
                  <div className="flex-1 flex items-center justify-center text-zinc-600" data-testid="live-preview-iframe">
                    {fileTree.length > 0 ? (
                      <div className="text-center space-y-3">
                        <div className="w-12 h-12 mx-auto bg-emerald-500/10 rounded-lg flex items-center justify-center">
                          <CheckCircle2 size={24} className="text-emerald-500" />
                        </div>
                        <div>
                          <p className="font-medium text-zinc-300">Projekt bereit</p>
                          <p className="text-sm text-zinc-500">{fileTree.length} Elemente erstellt</p>
                        </div>
                      </div>
                    ) : (
                      <div className="text-center space-y-3">
                        <div className="w-12 h-12 mx-auto bg-zinc-800 rounded-lg flex items-center justify-center">
                          <Eye size={24} className="text-zinc-600" />
                        </div>
                        <p className="font-medium text-zinc-400">Preview nicht verfügbar</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
            
            {activeTab === "editor" && (
              <div className="h-full" data-testid="editor-panel">
                {selectedFile ? (
                  <SyntaxEditor
                    content={fileContent}
                    onChange={(val) => { setFileContent(val); setIsFileDirty(true); }}
                    language={getFileLanguage(selectedFile)}
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
