import { useEffect, useState } from "react";
import {
  ApiError,
  getAgentStatus,
  setAgentStatus,
  type AgentStatus,
} from "../lib/api";

type Props = {
  onUnauthorized: () => void;
  onChange?: (status: AgentStatus) => void;
};

export function AgentToggle({ onUnauthorized, onChange }: Props) {
  const [status, setStatus] = useState<AgentStatus | null>(null);
  const [updating, setUpdating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void load();
  }, []);

  async function load() {
    try {
      const s = await getAgentStatus();
      setStatus(s);
      onChange?.(s);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        onUnauthorized();
      }
    }
  }

  async function toggle() {
    if (!status) return;
    const next = !status.enabled;
    const action = next ? "encender" : "apagar";
    if (!confirm(`¿Seguro que quieres ${action} el agente?`)) return;

    setUpdating(true);
    setError(null);
    try {
      const s = await setAgentStatus(next);
      setStatus(s);
      onChange?.(s);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        onUnauthorized();
        return;
      }
      setError(err instanceof Error ? err.message : "Error desconocido");
    } finally {
      setUpdating(false);
    }
  }

  if (!status) {
    return (
      <div className="flex items-center gap-2 text-xs text-zinc-500">
        <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-zinc-700 border-t-zinc-400" />
        Cargando estado…
      </div>
    );
  }

  const enabled = status.enabled;

  return (
    <div className="flex items-center gap-3">
      <span
        className={`flex items-center gap-2 text-xs ${
          enabled ? "text-emerald-300" : "text-red-300"
        }`}
      >
        <span
          className={`h-2 w-2 rounded-full ring-2 ${
            enabled
              ? "bg-emerald-400 ring-emerald-400/20"
              : "bg-red-400 ring-red-400/20 animate-pulse"
          }`}
        />
        {enabled ? "Agente activo" : "Agente apagado"}
      </span>

      <button
        onClick={toggle}
        disabled={updating}
        className={
          enabled
            ? "rounded-md border border-red-500/30 bg-red-500/10 px-3 py-1.5 text-xs font-medium text-red-300 transition hover:bg-red-500/20 disabled:opacity-50"
            : "rounded-md border border-emerald-500/30 bg-emerald-500/10 px-3 py-1.5 text-xs font-medium text-emerald-300 transition hover:bg-emerald-500/20 disabled:opacity-50"
        }
      >
        {updating ? "…" : enabled ? "Apagar agente" : "Encender agente"}
      </button>

      {error && <span className="text-xs text-red-400">{error}</span>}
    </div>
  );
}
