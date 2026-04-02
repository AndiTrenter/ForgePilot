import React from 'react';
import { Circle, CheckCircle2, Clock, AlertCircle, XCircle } from 'lucide-react';

/**
 * Task Board Component
 * Zeigt Tasks mit Status an (TODO, IN_PROGRESS, BLOCKED, DONE, FAILED)
 */

const STATUS_CONFIG = {
  queued: { label: 'Queued', icon: Circle, color: 'text-zinc-500', bg: 'bg-zinc-900' },
  in_progress: { label: 'In Progress', icon: Clock, color: 'text-blue-400', bg: 'bg-blue-500/10' },
  blocked: { label: 'Blocked', icon: AlertCircle, color: 'text-amber-400', bg: 'bg-amber-500/10' },
  under_review: { label: 'Under Review', icon: Circle, color: 'text-purple-400', bg: 'bg-purple-500/10' },
  under_test: { label: 'Under Test', icon: Circle, color: 'text-cyan-400', bg: 'bg-cyan-500/10' },
  failed: { label: 'Failed', icon: XCircle, color: 'text-red-400', bg: 'bg-red-500/10' },
  passed: { label: 'Passed', icon: CheckCircle2, color: 'text-green-400', bg: 'bg-green-500/10' },
  done: { label: 'Done', icon: CheckCircle2, color: 'text-green-400', bg: 'bg-green-500/10' }
};

const TaskCard = ({ task }) => {
  const status = STATUS_CONFIG[task.status] || STATUS_CONFIG.queued;
  const Icon = status.icon;

  return (
    <div className={`p-4 rounded-lg border border-zinc-800 ${status.bg} transition-all hover:border-zinc-700`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <Icon size={16} className={status.color} />
            <span className={`text-xs font-medium ${status.color}`}>{status.label}</span>
          </div>
          <h4 className="font-medium text-white">{task.name || task.title}</h4>
          {task.description && (
            <p className="text-sm text-zinc-400 mt-1">{task.description}</p>
          )}
        </div>
        {task.priority && (
          <span className={`text-xs px-2 py-0.5 rounded ${
            task.priority === 'high' ? 'bg-red-500/20 text-red-400' :
            task.priority === 'medium' ? 'bg-amber-500/20 text-amber-400' :
            'bg-zinc-700 text-zinc-400'
          }`}>
            {task.priority}
          </span>
        )}
      </div>
      
      {task.acceptance_criteria && task.acceptance_criteria.length > 0 && (
        <div className="mt-3 pt-3 border-t border-zinc-800">
          <p className="text-xs text-zinc-500 mb-2">Acceptance Criteria:</p>
          <div className="space-y-1">
            {task.acceptance_criteria.map((criterion, idx) => (
              <div key={idx} className="flex items-start gap-2 text-xs">
                <CheckCircle2 
                  size={12} 
                  className={criterion.met ? 'text-green-500 mt-0.5' : 'text-zinc-600 mt-0.5'} 
                />
                <span className={criterion.met ? 'text-zinc-400' : 'text-zinc-500'}>
                  {criterion.description}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

const TaskBoard = ({ tasks = [], className = '' }) => {
  const groupedTasks = {
    queued: tasks.filter(t => t.status === 'queued'),
    in_progress: tasks.filter(t => ['in_progress', 'under_review', 'under_test'].includes(t.status)),
    blocked: tasks.filter(t => t.status === 'blocked'),
    done: tasks.filter(t => ['done', 'passed'].includes(t.status)),
    failed: tasks.filter(t => t.status === 'failed')
  };

  return (
    <div className={`space-y-4 ${className}`}>
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-white">Tasks</h3>
        <div className="flex items-center gap-2 text-sm">
          <span className="text-zinc-500">{tasks.length} total</span>
          <span className="text-blue-400">{groupedTasks.in_progress.length} active</span>
          <span className="text-green-400">{groupedTasks.done.length} done</span>
        </div>
      </div>

      {tasks.length === 0 ? (
        <div className="text-center py-12 text-zinc-500">
          <Clock size={48} className="mx-auto mb-3 opacity-30" />
          <p>Keine Tasks vorhanden</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {tasks.map((task) => (
            <TaskCard key={task.id} task={task} />
          ))}
        </div>
      )}
    </div>
  );
};

export default TaskBoard;
