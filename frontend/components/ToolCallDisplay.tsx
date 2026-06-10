"use client";

import { useState } from "react";

type ToolCallDisplayProps = {
  toolName: string;
  args: string;
  result?: string;
};

export function ToolCallDisplay({ toolName, args, result }: ToolCallDisplayProps): React.ReactElement {
  const [open, setOpen] = useState(false);

  let parsedArgs: unknown = args;
  try {
    parsedArgs = JSON.parse(args);
  } catch {
    // keep as string
  }

  return (
    <div className="border border-slate-700 rounded-lg overflow-hidden text-xs">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-3 py-2 bg-slate-800 hover:bg-slate-750 text-left transition-colors"
      >
        <span className="flex items-center gap-2">
          <span className="text-violet-400 font-mono">{toolName}</span>
          <span className="text-slate-500">tool call</span>
        </span>
        <span className="text-slate-500">{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <div className="bg-slate-900 px-3 py-2 flex flex-col gap-2">
          <div>
            <p className="text-slate-500 mb-1">Arguments:</p>
            <pre className="text-slate-300 whitespace-pre-wrap break-all font-mono">
              {typeof parsedArgs === "string" ? parsedArgs : JSON.stringify(parsedArgs, null, 2)}
            </pre>
          </div>
          {result && (
            <div>
              <p className="text-slate-500 mb-1">Result:</p>
              <pre className="text-slate-300 whitespace-pre-wrap break-all font-mono max-h-48 overflow-y-auto">
                {result}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
