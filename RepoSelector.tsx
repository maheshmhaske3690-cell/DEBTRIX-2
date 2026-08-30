"use client";

import { useEffect, useState } from "react";
import { api, RepoSummary } from "@/lib/api";

interface Props {
  repos: RepoSummary[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onScanComplete: () => void;
}

export function RepoSelector({ repos, selectedId, onSelect, onScanComplete }: Props) {
  const [scanning, setScanning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleScan() {
    if (!selectedId) return;
    setScanning(true);
    setError(null);
    try {
      const { scan_job_id } = await api.triggerScan(selectedId);
      await pollUntilDone(scan_job_id);
      onScanComplete();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Scan failed");
    } finally {
      setScanning(false);
    }
  }

  async function pollUntilDone(scanJobId: string) {
    for (let i = 0; i < 60; i++) {
      const status = await api.getScanStatus(scanJobId);
      if (status.status === "completed") return;
      if (status.status === "failed") throw new Error(status.error_message || "Scan failed");
      await new Promise((r) => setTimeout(r, 5000));
    }
    throw new Error("Scan timed out — check the worker process is running.");
  }

  return (
    <div className="flex flex-col sm:flex-row gap-3 sm:items-center">
      <select
        value={selectedId ?? ""}
        onChange={(e) => onSelect(e.target.value)}
        className="flex-1 rounded-md border border-ink-700 bg-ink-900 px-4 py-2.5 text-sm font-body text-paper focus:border-gold outline-none"
      >
        <option value="" disabled>
          Select a repository
        </option>
        {repos.map((r) => (
          <option key={r.id} value={r.id}>
            {r.full_name}
          </option>
        ))}
      </select>
      <button
        onClick={handleScan}
        disabled={!selectedId || scanning}
        className="rounded-md bg-gold px-5 py-2.5 text-sm font-body font-semibold text-ink-950 hover:bg-gold-soft disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
      >
        {scanning ? "Scanning…" : "Run scan"}
      </button>
      {error && <p className="text-xs text-loss font-body sm:ml-2">{error}</p>}
    </div>
  );
}
