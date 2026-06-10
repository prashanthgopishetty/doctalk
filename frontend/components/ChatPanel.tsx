"use client";

import { useRef, useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import { AgentType } from "@/lib/types";
import { AgentThinking } from "./AgentThinking";
import { ToolCallDisplay } from "./ToolCallDisplay";

const AGENT_LABELS: Record<string, string> = {
  developer_agent:         "Developer Agent",
  architecture_agent:      "Architecture Agent",
  testing_agent:           "Testing Agent",
  self_improvement_agent:  "Self-Improvement Agent",
  documentation_agent:     "Documentation Agent",
  out_of_scope_agent:      "DocTalk",
  out_of_scope:            "DocTalk",
  "Out Of Scope Agent":    "DocTalk",
  DocTalk:                 "DocTalk",
};

type ChatPanelProps = {
  codebaseId: string | null;
  agentHint: AgentType;
  backendUrl: string;
};

type ToolCall = {
  id: string;
  name: string;
  args: string;
  result?: string;
};

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  toolCalls?: ToolCall[];
  agentName?: string;
};

export function ChatPanel({ codebaseId, agentHint, backendUrl }: ChatPanelProps): React.ReactElement {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentAgent, setCurrentAgent] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isStreaming]);

  const sendMessage = async (): Promise<void> => {
    const text = input.trim();
    if (!text || isStreaming) return;

    setInput("");
    const userMsg: ChatMessage = { id: Date.now().toString(), role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);
    setIsStreaming(true);
    setCurrentAgent(null);

    const assistantId = (Date.now() + 1).toString();
    setMessages((prev) => [...prev, { id: assistantId, role: "assistant", content: "" }]);

    try {
      const payload = {
        threadId: "thread_" + Date.now(),
        runId: "run_" + Date.now(),
        messages: [...messages, userMsg].map((m) => ({ role: m.role, content: m.content })),
        state: { codebaseId, agentHint },
      };

      const res = await fetch(`${backendUrl}/agent`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok || !res.body) {
        throw new Error(`Request failed: ${res.status}`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      const pendingToolCalls: Record<string, ToolCall> = {};
      let agentName = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split("\n");

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const raw = line.slice(6).trim();
          if (!raw) continue;

          let event: Record<string, unknown>;
          try {
            event = JSON.parse(raw) as Record<string, unknown>;
          } catch {
            continue;
          }

          const type = event.type as string;

          if (type === "StepStarted") {
            agentName = event.stepName as string;
            setCurrentAgent(agentName);
          } else if (type === "StepFinished") {
            setCurrentAgent(null);
          } else if (type === "TextMessageContent") {
            const delta = event.delta as string;
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? { ...m, content: m.content + delta, agentName }
                  : m
              )
            );
          } else if (type === "ToolCallStart") {
            const id = event.toolCallId as string;
            pendingToolCalls[id] = { id, name: event.toolCallName as string, args: "" };
          } else if (type === "ToolCallArgs") {
            const id = event.toolCallId as string;
            if (pendingToolCalls[id]) {
              pendingToolCalls[id].args += event.delta as string;
            }
          } else if (type === "ToolCallResult") {
            const id = event.toolCallId as string;
            if (pendingToolCalls[id]) {
              pendingToolCalls[id].result = event.content as string;
            }
            setMessages((prev) =>
              prev.map((m) => {
                if (m.id !== assistantId) return m;
                const existing = m.toolCalls ?? [];
                const tc = pendingToolCalls[id];
                if (!tc) return m;
                const updated = existing.filter((t) => t.id !== id);
                return { ...m, toolCalls: [...updated, { ...tc }] };
              })
            );
          }
        }
      }
    } catch (err: unknown) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId
            ? { ...m, content: `Error: ${err instanceof Error ? err.message : "Unknown error"}` }
            : m
        )
      );
    } finally {
      setIsStreaming(false);
      setCurrentAgent(null);
    }
  };

  const isEmpty = messages.length === 0;

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4 min-h-0">
        {isEmpty && (
          <div className="flex flex-col items-center justify-center h-full gap-3 text-center text-slate-500">
            <div className="text-4xl">💬</div>
            <p className="text-base font-medium text-slate-300">Ask about the codebase</p>
            <p className="text-sm max-w-xs">
              {codebaseId
                ? `Codebase loaded. Ask how something works, where it lives, or request tests.`
                : "First ingest a codebase using the panel on the left."}
            </p>
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex flex-col gap-2 ${msg.role === "user" ? "items-end" : "items-start"}`}
          >
            {msg.agentName && msg.role === "assistant" && (
              <span className="text-xs text-slate-500 px-1">
                {AGENT_LABELS[msg.agentName] ?? msg.agentName}
              </span>
            )}
            {msg.toolCalls && msg.toolCalls.length > 0 && (
              <div className="w-full max-w-2xl space-y-1">
                {msg.toolCalls.map((tc) => (
                  <ToolCallDisplay key={tc.id} toolName={tc.name} args={tc.args} result={tc.result} />
                ))}
              </div>
            )}
            {msg.content && (
              <div
                className={`max-w-2xl rounded-xl px-4 py-3 text-sm ${
                  msg.role === "user"
                    ? "bg-violet-600 text-white whitespace-pre-wrap break-words"
                    : "bg-slate-800 text-slate-100 border border-slate-700"
                }`}
              >
                {msg.role === "user" ? (
                  msg.content
                ) : (
                  <div className="prose-sm prose-invert max-w-none">
                    <ReactMarkdown
                      components={{
                        p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                        code: ({ inline, children }) => 
                          inline ? (
                            <code className="bg-slate-900 px-1.5 py-0.5 rounded text-slate-200 font-mono text-xs">
                              {children}
                            </code>
                          ) : (
                            <code className="bg-slate-900 text-slate-200 font-mono text-xs block p-3 rounded mb-2 overflow-auto">
                              {children}
                            </code>
                          ),
                        pre: ({ children }) => <pre className="mb-2">{children}</pre>,
                        h1: ({ children }) => <h1 className="text-lg font-bold mb-2 mt-3 first:mt-0">{children}</h1>,
                        h2: ({ children }) => <h2 className="text-base font-bold mb-2 mt-2 first:mt-0">{children}</h2>,
                        h3: ({ children }) => <h3 className="text-sm font-bold mb-1 mt-2 first:mt-0">{children}</h3>,
                        ul: ({ children }) => <ul className="list-disc list-inside mb-2 space-y-1">{children}</ul>,
                        ol: ({ children }) => <ol className="list-decimal list-inside mb-2 space-y-1">{children}</ol>,
                        li: ({ children }) => <li className="ml-2">{children}</li>,
                        blockquote: ({ children }) => <blockquote className="border-l-4 border-violet-500 pl-3 italic mb-2">{children}</blockquote>,
                        a: ({ children, href }) => <a href={href} target="_blank" rel="noopener noreferrer" className="text-violet-400 hover:text-violet-300 underline">{children}</a>,
                        strong: ({ children }) => <strong className="font-bold">{children}</strong>,
                        em: ({ children }) => <em className="italic">{children}</em>,
                      }}
                    >
                      {msg.content}
                    </ReactMarkdown>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}

        {isStreaming && currentAgent && (
          <AgentThinking agentName={currentAgent} />
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="border-t border-slate-700 px-4 py-3 bg-slate-900">
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={
              codebaseId
                ? "Ask about the codebase..."
                : "Ingest a codebase first, then ask questions..."
            }
            disabled={!codebaseId}
            rows={2}
            className="flex-1 resize-none bg-slate-800 border border-slate-700 text-slate-100 text-sm rounded-lg px-3 py-2.5 focus:ring-2 focus:ring-violet-500 focus:border-violet-500 outline-none placeholder-slate-500 disabled:opacity-50 disabled:cursor-not-allowed"
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
              }
            }}
          />
          <button
            onClick={sendMessage}
            disabled={!codebaseId || !input.trim() || isStreaming}
            className="self-end bg-violet-600 hover:bg-violet-700 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium py-2.5 px-4 rounded-lg transition-colors"
          >
            Send
          </button>
        </div>
        <p className="text-xs text-slate-600 mt-1.5">Shift+Enter for new line · Enter to send</p>
      </div>
    </div>
  );
}
