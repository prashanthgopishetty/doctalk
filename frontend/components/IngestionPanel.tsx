"use client";

import { useState } from "react";
import { IngestSourceType, CodebaseInfo, IngestResponse } from "@/lib/types";

type IngestionPanelProps = {
  onIngested: (info: CodebaseInfo) => void;
  backendUrl: string;
};

export function IngestionPanel({ onIngested, backendUrl }: IngestionPanelProps): React.ReactElement {
  const [sourceType, setSourceType] = useState<IngestSourceType>("github");
  const [source, setSource] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [files, setFiles] = useState<FileList | null>(null);

  const handleIngest = async (): Promise<void> => {
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
        res = await fetch(`${backendUrl}/ingest`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ source: source.trim(), source_type: sourceType }),
        });
      }

      if (!res.ok) {
        const data: unknown = await res.json();
        const detail = typeof data === "object" && data !== null && "detail" in data
          ? String((data as { detail: unknown }).detail)
          : `HTTP ${res.status}`;
        const prefix = res.status === 503 ? "⚠️ Ollama not running — " : "";
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
      // reset file input visually
      const fileInputs = document.querySelectorAll<HTMLInputElement>('input[type="file"]');
      fileInputs.forEach((el) => { el.value = ""; });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Ingestion failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-700 rounded-xl p-5 flex flex-col gap-4">
      <h2 className="text-base font-semibold text-slate-100">Ingest Codebase</h2>

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

      {/* Button */}
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
    </div>
  );
}
