import React from "react";
import { 
  Loader2, Zap, ListTodo, Code, Eye, CheckCircle2, Bug, 
  GitBranch, File, FileCode, X, Play, ArrowRight, Search, 
  Check, Circle, Upload, ExternalLink
} from "lucide-react";
import { Tooltip } from "./common";

// ============== Agent Activity Item ==============
export const AgentActivityItem = ({ activity }) => {
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

// ============== Agent Status Pill ==============
export const AgentStatusPill = ({ agent }) => {
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
          agent.status === "running" ? "border-blue-500/50" : "border-zinc-800"
        }`}
        data-testid={`agent-${agent.agent_type}`}
      >
        <div className={`w-2 h-2 rounded-full ${statusColors[agent.status]}`} />
        <Icon size={14} className="text-zinc-400" />
        <span className="text-xs font-medium text-zinc-300 capitalize">{agent.agent_type}</span>
      </div>
    </Tooltip>
  );
};

// ============== Project Summary ==============
export const ProjectSummary = ({ previewInfo, onPush, isPushing }) => {
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
