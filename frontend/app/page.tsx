"use client";

import { useState } from "react";
import { IngestionPanel } from "@/components/IngestionPanel";
import { ChatPanel } from "@/components/ChatPanel";
import { AgentSelector } from "@/components/AgentSelector";
import { AgentType, CodebaseInfo } from "@/lib/types";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";

export default function Home(): React.ReactElement {
  const [codebase, setCodebase] = useState<CodebaseInfo | null>(null);
  const [agentHint, setAgentHint] = useState<AgentType>("auto");
  const [githubToken, setGithubToken] = useState<string | null>(null);

  return (
    <div className="flex flex-col h-screen">
      <header className="flex items-center justify-between px-6 py-3 border-b border-slate-800 bg-slate-950 shrink-0">
        <div className="flex items-center gap-3">
          <span className="text-xl">🔍</span>
          <div>
            <h1 className="text-base font-bold text-slate-100 leading-none">DocTalk</h1>
            <p className="text-xs text-slate-500 mt-0.5">Multi-agent code documentation assistant</p>
          </div>
        </div>
        {codebase && (
          <div className="text-right">
            <p className="text-xs text-slate-400 font-mono truncate max-w-xs">{codebase.source}</p>
            <p className="text-xs text-slate-600">{codebase.documentsIndexed.toLocaleString()} chunks indexed</p>
          </div>
        )}
      </header>
      <div className="flex flex-1 min-h-0">
        <aside className="w-80 shrink-0 flex flex-col gap-4 p-4 border-r border-slate-800 bg-slate-950 overflow-y-auto">
          <IngestionPanel
            onIngested={setCodebase}
            backendUrl={BACKEND_URL}
            githubToken={githubToken}
            onGithubTokenSet={setGithubToken}
          />
          {codebase && (
            <div className="bg-slate-900 border border-slate-700 rounded-xl p-4 flex flex-col gap-1">
              <p className="text-xs text-slate-500 uppercase tracking-wide font-medium">Active Codebase</p>
              <p className="text-sm font-mono text-violet-300 truncate">{codebase.source}</p>
              <p className="text-xs text-slate-500">{codebase.documentsIndexed.toLocaleString()} chunks · {codebase.sourceType}</p>
              <button onClick={() => setCodebase(null)} className="mt-2 text-xs text-slate-500 hover:text-red-400 transition-colors text-left">✕ Clear codebase</button>
            </div>
          )}
          <AgentSelector value={agentHint} onChange={setAgentHint} />
          <div className="mt-auto pt-4 border-t border-slate-800">
            <p className="text-xs text-slate-600 leading-relaxed">
              Powered by <span className="text-violet-500">LangGraph</span> · <span className="text-violet-500">AG-UI</span> · <span className="text-violet-500">Qwen</span>
            </p>
          </div>
        </aside>
        <main className="flex-1 flex flex-col min-w-0 bg-slate-950">
          <ChatPanel codebaseId={codebase?.id ?? null} agentHint={agentHint} backendUrl={BACKEND_URL} />
        </main>
      </div>
    </div>
  );
}
