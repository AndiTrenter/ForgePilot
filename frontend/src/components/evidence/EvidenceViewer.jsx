import React, { useState } from 'react';
import { FileText, Image as ImageIcon, TestTube2, Code, GitCommit, CheckCircle2, XCircle } from 'lucide-react';

/**
 * Evidence Viewer Component
 * Zeigt gesammelte Evidence an (Build-Logs, Test-Reports, Screenshots, Code-Diffs)
 */

const EVIDENCE_TYPES = {
  build: { label: 'Build Log', icon: Code, color: 'text-blue-400' },
  test: { label: 'Test Report', icon: TestTube2, color: 'text-green-400' },
  lint: { label: 'Lint Report', icon: FileText, color: 'text-purple-400' },
  screenshot: { label: 'Screenshot', icon: ImageIcon, color: 'text-cyan-400' },
  code_diff: { label: 'Code Diff', icon: GitCommit, color: 'text-amber-400' },
  gate_report: { label: 'Gate Report', icon: CheckCircle2, color: 'text-emerald-400' }
};

const EvidenceCard = ({ evidence, onClick }) => {
  const config = EVIDENCE_TYPES[evidence.type] || { label: 'Unknown', icon: FileText, color: 'text-zinc-400' };
  const Icon = config.icon;
  const isSuccess = evidence.status === 'success' || evidence.status === 'passed';
  const isFailure = evidence.status === 'failed' || evidence.status === 'error';

  return (
    <button
      onClick={() => onClick(evidence)}
      className="w-full p-4 bg-zinc-900 border border-zinc-800 rounded-lg hover:border-zinc-700 hover:bg-zinc-800/50 transition-all text-left"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3 flex-1">
          <div className={`p-2 rounded-lg bg-zinc-800`}>
            <Icon size={20} className={config.color} />
          </div>
          <div className="flex-1 min-w-0">
            <h4 className="font-medium text-white truncate">{config.label}</h4>
            <p className="text-xs text-zinc-500 mt-0.5">
              {new Date(evidence.timestamp).toLocaleString('de-DE')}
            </p>
          </div>
        </div>
        {evidence.status && (
          <div className="shrink-0">
            {isSuccess && <CheckCircle2 size={20} className="text-green-500" />}
            {isFailure && <XCircle size={20} className="text-red-500" />}
          </div>
        )}
      </div>
      
      {evidence.metadata && (
        <div className="mt-3 pt-3 border-t border-zinc-800 text-xs text-zinc-400 space-y-1">
          {evidence.type === 'test' && evidence.metadata.total && (
            <p>Tests: {evidence.metadata.passed}/{evidence.metadata.total} passed</p>
          )}
          {evidence.type === 'code_diff' && evidence.metadata.files_changed && (
            <p>{evidence.metadata.files_changed} files • +{evidence.metadata.lines_added} -{evidence.metadata.lines_removed}</p>
          )}
        </div>
      )}
    </button>
  );
};

const EvidenceModal = ({ evidence, onClose }) => {
  if (!evidence) return null;

  const config = EVIDENCE_TYPES[evidence.type] || { label: 'Unknown', icon: FileText };

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-[600] p-4" onClick={onClose}>
      <div
        className="bg-zinc-900 border border-zinc-700 rounded-lg w-full max-w-4xl max-h-[90vh] shadow-2xl flex flex-col"
        onClick={e => e.stopPropagation()}
      >
        <div className="p-6 border-b border-zinc-800 flex items-center justify-between shrink-0">
          <h3 className="text-xl font-bold text-white">{config.label}</h3>
          <button onClick={onClose} className="text-zinc-400 hover:text-white">
            <XCircle size={24} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          {evidence.type === 'screenshot' ? (
            <img src={evidence.content} alt="Evidence Screenshot" className="w-full rounded-lg" />
          ) : (
            <pre className="bg-zinc-950 p-4 rounded-lg text-sm text-zinc-300 overflow-x-auto border border-zinc-800">
              {typeof evidence.content === 'string' 
                ? evidence.content 
                : JSON.stringify(evidence.content, null, 2)}
            </pre>
          )}
        </div>
      </div>
    </div>
  );
};

const EvidenceViewer = ({ evidences = [], className = '' }) => {
  const [selectedEvidence, setSelectedEvidence] = useState(null);

  return (
    <>
      <div className={`space-y-4 ${className}`}>
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-white">Evidence Collection</h3>
          <span className="text-sm text-zinc-500">{evidences.length} artifacts</span>
        </div>

        {evidences.length === 0 ? (
          <div className="text-center py-12 text-zinc-500">
            <FileText size={48} className="mx-auto mb-3 opacity-30" />
            <p>Keine Evidence gesammelt</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {evidences.map((evidence) => (
              <EvidenceCard
                key={evidence.id || evidence._id}
                evidence={evidence}
                onClick={setSelectedEvidence}
              />
            ))}
          </div>
        )}
      </div>

      <EvidenceModal evidence={selectedEvidence} onClose={() => setSelectedEvidence(null)} />
    </>
  );
};

export default EvidenceViewer;
