"use client";

type AgentThinkingProps = {
  agentName: string;
};

const AGENT_DISPLAY: Record<string, { label: string; color: string }> = {
  "Developer Agent": { label: "Developer Agent", color: "text-blue-400" },
  "Architecture Agent": { label: "Architecture Agent", color: "text-emerald-400" },
  "Testing Agent": { label: "Testing Agent", color: "text-yellow-400" },
  "Self Improvement Agent": { label: "Self-Improvement Agent", color: "text-orange-400" },
  "Documentation Agent": { label: "Documentation Agent", color: "text-purple-400" },
};

export function AgentThinking({ agentName }: AgentThinkingProps): React.ReactElement {
  const display = AGENT_DISPLAY[agentName] ?? { label: agentName, color: "text-violet-400" };

  return (
    <div className="flex items-center gap-2 px-4 py-2 bg-slate-800/50 rounded-lg border border-slate-700 text-sm">
      <span className="flex gap-1">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="w-1.5 h-1.5 rounded-full bg-violet-400 animate-bounce"
            style={{ animationDelay: `${i * 0.15}s` }}
          />
        ))}
      </span>
      <span className={`font-medium ${display.color}`}>{display.label}</span>
      <span className="text-slate-400">is thinking...</span>
    </div>
  );
}
