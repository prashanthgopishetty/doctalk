export type AgentType = "auto" | "developer" | "architecture" | "testing" | "self_improvement" | "documentation";

export type IngestSourceType = "github" | "local" | "upload";

export type CodebaseInfo = {
  id: string;
  source: string;
  sourceType: IngestSourceType;
  documentsIndexed: number;
  ingestedAt: Date;
};

export type IngestResponse = {
  codebase_id: string;
  documents_indexed: number;
  message: string;
};

export type DocTalkState = {
  codebaseId: string | null;
  agentHint: AgentType;
};

export const AGENT_LABELS: Record<AgentType, string> = {
  auto: "Auto (Supervisor Routes)",
  developer: "Developer — Code Explanation",
  architecture: "Architecture — System Structure",
  testing: "Testing — Test Generation",
  self_improvement: "Self-Improvement — Refactoring",
  documentation: "Documentation — Docstrings & Docs",
};
