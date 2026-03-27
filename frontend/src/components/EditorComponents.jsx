import React, { useState, useRef, useMemo } from "react";
import { ChevronRight, Folder, File, ChevronDown, Zap, ListTodo, Code, Eye, CheckCircle2 } from "lucide-react";
import Prism from 'prismjs';

// ============== File Tree View ==============
export const FileTreeView = ({ items, onSelect, selectedPath }) => {
  const [openFolders, setOpenFolders] = useState(new Set([""]));
  
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

// ============== Syntax Editor ==============
export const SyntaxEditor = ({ content, onChange, language = "javascript", readOnly = false }) => {
  const textareaRef = useRef(null);
  const highlightRef = useRef(null);
  
  const getLanguage = (lang) => {
    const map = { js: 'javascript', jsx: 'javascript', ts: 'javascript', tsx: 'javascript', py: 'python', html: 'markup', css: 'css', json: 'json' };
    return map[lang] || lang || 'javascript';
  };

  const highlighted = useMemo(() => {
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

// ============== Chat Message ==============
export const ChatMessage = ({ message }) => {
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
          </div>
        )}
        <div className="text-sm leading-relaxed">{formatContent(message.content)}</div>
        {message.files_created?.length > 0 && (
          <div className="mt-3 pt-3 border-t border-zinc-800">
            <p className="text-xs text-zinc-500 mb-2">Erstellte Dateien:</p>
            <div className="flex flex-wrap gap-1">
              {message.files_created.map((file, i) => (
                <span key={i} className="px-2 py-0.5 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs rounded flex items-center gap-1">
                  <File size={10} />
                  {file}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// ============== Roadmap View ==============
export const RoadmapView = ({ items }) => {
  if (!items?.length) {
    return (
      <div className="flex items-center justify-center h-full text-zinc-600">
        <div className="text-center space-y-2">
          <ListTodo size={32} className="mx-auto opacity-50" />
          <p>Keine Roadmap-Einträge</p>
        </div>
      </div>
    );
  }

  const statusStyles = {
    completed: { icon: CheckCircle2, color: "text-emerald-400 bg-emerald-500/10 border-emerald-500/30" },
    in_progress: { icon: Eye, color: "text-blue-400 bg-blue-500/10 border-blue-500/30" },
    pending: { icon: ListTodo, color: "text-zinc-400 bg-zinc-500/10 border-zinc-500/30" },
  };

  return (
    <div className="space-y-3">
      {items.map((item, index) => {
        const style = statusStyles[item.status] || statusStyles.pending;
        const Icon = style.icon;
        return (
          <div key={item.id || index} className={`p-3 rounded-lg border ${style.color}`}>
            <div className="flex items-start gap-3">
              <div className="p-1.5 rounded">
                <Icon size={16} />
              </div>
              <div className="flex-1 min-w-0">
                <h4 className="font-medium text-sm">{item.title}</h4>
                {item.description && <p className="text-xs text-zinc-500 mt-1">{item.description}</p>}
              </div>
              <span className="text-xs capitalize px-2 py-0.5 rounded bg-zinc-800">{item.status?.replace("_", " ")}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
};

// ============== Helper Function ==============
export const getFileLanguage = (filename) => {
  if (!filename) return "javascript";
  const ext = filename.split('.').pop()?.toLowerCase();
  const langMap = { js: "javascript", jsx: "javascript", ts: "typescript", tsx: "typescript", py: "python", html: "markup", css: "css", json: "json", md: "markdown" };
  return langMap[ext] || "javascript";
};
