"use client";

import { useState } from "react";
import { IngestSourceType, CodebaseInfo, IngestResponse } from "@/lib/types";

type IngestionPanelProps = {
  onIngested: (info: CodebaseInfo) => void;
  backendUrl: string;
  githubToken: string | null;
  onGithubTokenSet: (token: string) => void;
};

export function IngestionPanel({ onIngested, backendUrl, githubToken, onGithubTokenSet }: IngestionPanelProps): React.ReactElement {
  const [sourceType, setSourceType] = useState<IngestSourceType>("github");
  const [source, setSource] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [files, setFiles] = useState<FileList | null>(null);

  // GitHub credentials form state — shown when a private repo returns 401
  const [showCredentials, setShowCredentials] = useState(false);
  const [credToken, setCredToken] = useState("");
  const [credLoading, setCredLoading] = useState(false);

  const doIngest = async (token: string | null): Promise<void> => {
    setError(null);
    setLoading(true);

    try {
      let res: Response;

      if (sourceType === "upload") {
        if (!files || files.length === 0) {
          setError("Please select files to upload.");
          setLoading(false);
          return;
        }
        const form = new FormData();
        Array.from(files).forEach((f) => form.append("files", f));
        res = await fetch(`${backendUrl}/ingest/upload`, { method: "POST", body: form });
      } else {
        if (!source.trim()) {
          setError("Please enter a source URL or path.");
          setLoading(false);
          return;
        }
        const body: Record<string, string> = {
          source: source.trim(),
          source_type: sourceType,
        };
        if (token) body.github_token = token;
        res = await fetch(`${backendUrl}/ingest`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
      }

      if (!res.ok) {
        const data: unknown = await res.json();
        const detail =
          typeof data === "object" && data !== null && "detail" in data
            ? String((data as { detail: unknown }).detail)
            : `HTTP ${res.status}`;

        if (res.status === 401) {
          // Private repo — ask for credentials
          setShowCredentials(true);
          setError(null);
          setLoading(false);
          return;
        }

        const prefix = res.status === 503 ? "⚠️ Mistral not responding — " : "";
        throw new Error(prefix + detail);
      }

      const data = (await res.json()) as IngestResponse;
      onIngested({
        id: data.codebase_id,
        source: sourceType === "upload" ? `${files?.length ?? 0} file(s)` : source,
        sourceType,
        documentsIndexed: data.documents_indexed,
        ingestedAt: new Date(),
      });
      setSource("");
      setFiles(null);
      setShowCredentials(false);
      setCredToken("");
      const fileInputs = document.querySelectorAll<HTMLInputElement>('input[type="file"]');
      fileInputs.forEach((el) => { el.value = ""; });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Ingestion failed.");
    } finally {
      setLoading(false);
    }
  };

  const handleIngest = (): Promise<void> => doIngest(githubToken);

  const handleCredentialsSubmit = async (): Promise<void> => {
    if (!credToken.trim()) {
      setError("Please enter a Personal Access Token.");
      return;
    }
    setCredLoading(true);
    setError(null);
    const token = credToken.trim();
    // Persist token for the rest of the session
    onGithubTokenSet(token);
    await doIngest(token);
    setCredLoading(false);
  };

  return (
    <div className="bg-slate-900 border border-slate-700 rounded-xl p-5 flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-slate-100">Ingest Codebase</h2>
        {githubToken && (
          <span className="flex items-center gap-1 text-xs text-emerald-400 bg-emerald-900/30 border border-emerald-700/50 rounded-full px-2 py-0.5">
            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 16 16">
              <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z" />
            </svg>
            GitHub connected
            <button
              onClick={() => { onGithubTokenSet(""); }}
              className="ml-1 text-emerald-500 hover:text-red-400 transition-colors font-medium"
              title="Clear GitHub token"
            >✕</button>
          </span>
        )}
      </div>

      {/* Source type tabs */}
      <div className="flex gap-1 bg-slate-800 rounded-lg p-1">
        {(["github", "local", "upload"] as IngestSourceType[]).map((t) => (
          <button
            key={t}
            onClick={() => setSourceType(t)}
            className={`flex-1 py-1.5 text-xs font-medium rounded-md transition-colors ${
              sourceType === t
                ? "bg-violet-600 text-white"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            {t === "github" ? "GitHub URL" : t === "local" ? "Local Path" : "Upload Files"}
          </button>
        ))}
      </div>

      {/* Input */}
      {sourceType === "github" && (
        <input
          type="text"
          value={source}
          onChange={(e) => setSource(e.target.value)}
          placeholder="https://github.com/owner/repo"
          className="bg-slate-800 border border-slate-700 text-slate-100 text-sm rounded-lg px-3 py-2.5 focus:ring-2 focus:ring-violet-500 focus:border-violet-500 outline-none placeholder-slate-500"
          onKeyDown={(e) => e.key === "Enter" && handleIngest()}
        />
      )}

      {sourceType === "local" && (
        <div className="flex gap-2">
          <input
            type="text"
            value={source}
            onChange={(e) => setSource(e.target.value)}
            placeholder="/path/to/your/project"
            className="flex-1 bg-slate-800 border border-slate-700 text-slate-100 text-sm rounded-lg px-3 py-2.5 focus:ring-2 focus:ring-violet-500 focus:border-violet-500 outline-none placeholder-slate-500"
            onKeyDown={(e) => e.key === "Enter" && handleIngest()}
          />
          <label className="flex items-center gap-1.5 bg-slate-700 hover:bg-slate-600 text-slate-200 text-xs font-medium px-3 py-2.5 rounded-lg cursor-pointer transition-colors whitespace-nowrap">
            Browse
            <input
              type="file"
              // @ts-expect-error — webkitdirectory is non-standard but widely supported
              webkitdirectory=""
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) {
                  // Extract the folder path from the first file's webkitRelativePath
                  const parts = (f as File & { webkitRelativePath: string }).webkitRelativePath.split("/");
                  setSource(parts[0] ?? f.name);
                }
              }}
            />
          </label>
        </div>
      )}

      {sourceType === "upload" && (
        <div className="flex flex-col gap-2">
          <label className="flex flex-col items-center justify-center gap-2 border-2 border-dashed border-slate-600 hover:border-violet-500 rounded-lg p-4 cursor-pointer transition-colors group">
            <svg className="w-6 h-6 text-slate-500 group-hover:text-violet-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
            <span className="text-xs text-slate-400 group-hover:text-slate-200">
              {files && files.length > 0
                ? `${files.length} file${files.length > 1 ? "s" : ""} selected — click to change`
                : "Click to select files or drag & drop"}
            </span>
            <input
              type="file"
              multiple
              className="hidden"
              onChange={(e) => setFiles(e.target.files)}
            />
          </label>
          {files && files.length > 0 && (
            <ul className="text-xs text-slate-400 max-h-24 overflow-y-auto space-y-0.5 bg-slate-800 rounded-lg px-3 py-2">
              {Array.from(files).map((f) => (
                <li key={f.name} className="truncate">📄 {f.name}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Error */}
      {error && (
        <p className="text-xs text-red-400 bg-red-900/20 border border-red-800 rounded-lg px-3 py-2">
          {error}
        </p>
      )}

      {/* GitHub credentials form — shown when repo returns 401 */}
      {showCredentials && (
        <div className="flex flex-col gap-3 bg-slate-800 border border-amber-700/60 rounded-lg p-4">
          <div className="flex items-start gap-2">
            <svg className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
            <div>
              <p className="text-xs font-semibold text-amber-300">Private repository detected</p>
              <p className="text-xs text-slate-400 mt-0.5">
                Enter a GitHub{" "}
                <a
                  href="https://github.com/settings/tokens/new?scopes=repo&description=DocTalk"
                  target="_blank"
                  rel="noreferrer"
                  className="text-violet-400 underline hover:text-violet-300"
                >
                  Personal Access Token
                </a>{" "}
                with <code className="bg-slate-700 px-1 rounded text-slate-300">repo</code> scope.
                It will be remembered for this session.
              </p>
            </div>
          </div>
          <input
            type="password"
            value={credToken}
            onChange={(e) => setCredToken(e.target.value)}
            placeholder="ghp_xxxxxxxxxxxxxxxxxxxx"
            autoFocus
            onKeyDown={(e) => e.key === "Enter" && handleCredentialsSubmit()}
            className="bg-slate-700 border border-slate-600 text-slate-100 text-sm rounded-lg px-3 py-2 focus:ring-2 focus:ring-amber-500 focus:border-amber-500 outline-none placeholder-slate-500 font-mono"
          />
          <div className="flex gap-2">
            <button
              onClick={handleCredentialsSubmit}
              disabled={credLoading}
              className="flex-1 bg-amber-600 hover:bg-amber-700 disabled:opacity-50 disabled:cursor-not-allowed text-white text-xs font-medium py-2 px-3 rounded-lg transition-colors"
            >
              {credLoading ? (
                <span className="flex items-center justify-center gap-1.5">
                  <span className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Authenticating...
                </span>
              ) : (
                "Connect & Ingest"
              )}
            </button>
            <button
              onClick={() => { setShowCredentials(false); setCredToken(""); setError(null); }}
              className="px-3 py-2 text-xs text-slate-400 hover:text-slate-200 transition-colors rounded-lg hover:bg-slate-700"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Submit button — hidden while credentials form is shown */}
      {!showCredentials && (
        <button
          onClick={handleIngest}
          disabled={loading}
          className="bg-violet-600 hover:bg-violet-700 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium py-2.5 px-4 rounded-lg transition-colors"
        >
          {loading ? (
            <span className="flex items-center justify-center gap-2">
              <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              Indexing...
            </span>
          ) : sourceType === "upload" ? (
            `Upload & Index${files && files.length > 0 ? ` (${files.length} file${files.length > 1 ? "s" : ""})` : ""}`
          ) : sourceType === "local" ? (
            "Index Local Path"
          ) : (
            "Ingest Codebase"
          )}
        </button>
      )}
    </div>
  );
}
