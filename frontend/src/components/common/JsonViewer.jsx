import React, { useState } from 'react';
import { Copy, Check, Code2 } from 'lucide-react';

export const JsonViewer = ({ data, title, maxHeight = 'max-h-96' }) => {
  const [copied, setCopied] = useState(false);

  const jsonString = typeof data === 'string' ? data : JSON.stringify(data, null, 2);

  const handleCopy = () => {
    if (!navigator.clipboard) return;
    navigator.clipboard.writeText(jsonString).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/80 overflow-hidden shadow-inner">
      <div className="flex items-center justify-between border-b border-slate-800 bg-slate-900/60 px-4 py-2.5">
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-300">
          <Code2 className="w-3.5 h-3.5 text-emerald-400" />
          <span>{title || 'JSON Payload'}</span>
        </div>
        <button
          onClick={handleCopy}
          type="button"
          aria-label="Copy JSON to clipboard"
          className="inline-flex items-center gap-1.5 rounded bg-slate-800 px-2.5 py-1 text-xs font-medium text-slate-300 transition-colors hover:bg-slate-700 hover:text-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
        >
          {copied ? (
            <>
              <Check className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-emerald-400">Copied!</span>
            </>
          ) : (
            <>
              <Copy className="w-3.5 h-3.5" />
              <span>Copy</span>
            </>
          )}
        </button>
      </div>

      <pre className={`p-4 text-xs font-mono text-emerald-300 overflow-x-auto overflow-y-auto leading-relaxed ${maxHeight}`}>
        <code>{jsonString}</code>
      </pre>
    </div>
  );
};

export default JsonViewer;

