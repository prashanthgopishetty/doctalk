"use client";

import { AgentType, AGENT_LABELS } from "@/lib/types";

type AgentSelectorProps = {
  value: AgentType;
  onChange: (agent: AgentType) => void;
};

export function AgentSelector({ value, onChange }: AgentSelectorProps): React.ReactElement {
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor="agent-select" className="text-xs font-medium text-slate-400 uppercase tracking-wide">
        Agent Mode
      </label>
      <select
        id="agent-select"
        value={value}
        onChange={(e) => onChange(e.target.value as AgentType)}
        className="bg-slate-800 border border-slate-700 text-slate-100 text-sm rounded-lg px-3 py-2 focus:ring-2 focus:ring-violet-500 focus:border-violet-500 outline-none cursor-pointer"
      >
        {(Object.entries(AGENT_LABELS) as [AgentType, string][]).map(([key, label]) => (
          <option key={key} value={key}>
            {label}
          </option>
        ))}
      </select>
      {value !== "auto" && (
        <p className="text-xs text-violet-400 mt-0.5">
          Queries will be forced to the {AGENT_LABELS[value].split(" —")[0]} agent.
        </p>
      )}
    </div>
  );
}
