import { useEffect, useState } from "react";
import {
  ApiError,
  clearToken,
  getPrompt,
  updatePrompt,
  type AgentStatus,
} from "../lib/api";
import { AgentToggle } from "./AgentToggle";
import { Logo } from "./Logo";

const PROMPT_KEY = "chat_system";

const PLACEHOLDERS: Array<{ name: string; description: string }> = [
  { name: "edificio", description: "Nombre canónico del edificio del cliente." },
  { name: "depto", description: "Número de departamento." },
  { name: "nombre", description: "Nombre que dio el cliente al identificarse." },
  { name: "nombre_sheet", description: "Nombre tal como figura en la planilla." },
  { name: "row_dump", description: "Desglose completo de la cuota del mes (todas las columnas)." },
];

const REQUIRED = PLACEHOLDERS.map((p) => p.name);

type Props = {
  username: string;
  onLogout: () => void;
};

export function PromptEditor({ username, onLogout }: Props) {
  const [content, setContent] = useState("");
  const [original, setOriginal] = useState("");
  const [updatedAt, setUpdatedAt] = useState<string | null>(null);
  const [updatedBy, setUpdatedBy] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedAt, setSavedAt] = useState<Date | null>(null);
  const [agentStatus, setAgentStatus] = useState<AgentStatus | null>(null);

  useEffect(() => {
    void loadPrompt();
  }, []);

  async function loadPrompt() {
    setLoading(true);
    setError(null);
    try {
      const p = await getPrompt(PROMPT_KEY);
      setContent(p.content);
      setOriginal(p.content);
      setUpdatedAt(p.updated_at);
      setUpdatedBy(p.updated_by);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        handleLogout();
        return;
      }
      setError(err instanceof Error ? err.message : "Error desconocido");
    } finally {
      setLoading(false);
    }
  }

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      const p = await updatePrompt(PROMPT_KEY, content);
      setOriginal(p.content);
      setUpdatedAt(p.updated_at);
      setUpdatedBy(p.updated_by);
      setSavedAt(new Date());
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        handleLogout();
        return;
      }
      setError(err instanceof Error ? err.message : "Error desconocido");
    } finally {
      setSaving(false);
    }
  }

  function handleLogout() {
    clearToken();
    onLogout();
  }

  const dirty = content !== original;
  const missing = REQUIRED.filter((p) => !content.includes(`{${p}}`));
  const charCount = content.length;
  const lineCount = content.split("\n").length;

  return (
    <div className="min-h-full bg-zinc-950 text-zinc-100">
      {/* Top nav */}
      <header className="sticky top-0 z-10 border-b border-zinc-800/60 bg-zinc-950/80 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-3">
          <div className="flex items-center gap-3">
            <Logo />
            <div className="flex flex-col leading-tight">
              <span className="text-sm font-semibold tracking-tight">
                ARIABLE
              </span>
              <span className="text-[11px] text-zinc-500 font-mono">
                editor del prompt
              </span>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <AgentToggle
              onUnauthorized={handleLogout}
              onChange={setAgentStatus}
            />
            <span className="hidden md:inline text-xs text-zinc-500 font-mono">
              {username || "admin"}
            </span>
            <button
              onClick={handleLogout}
              className="rounded-md border border-zinc-800 px-3 py-1.5 text-xs text-zinc-300 transition hover:bg-zinc-900 hover:text-white"
            >
              Cerrar sesión
            </button>
          </div>
        </div>
      </header>

      {agentStatus && !agentStatus.enabled && (
        <div className="border-b border-red-500/30 bg-red-500/10">
          <div className="mx-auto max-w-7xl px-6 py-2.5 flex items-center gap-3 text-sm text-red-200">
            <span className="inline-block h-2 w-2 rounded-full bg-red-400 animate-pulse" />
            <span>
              <strong className="font-semibold">Agente apagado.</strong>{" "}
              Los mensajes entrantes de WhatsApp no recibirán respuesta hasta que lo enciendas.
              {agentStatus.updated_by && (
                <span className="text-red-300/80 font-mono ml-2">
                  · pausado por {agentStatus.updated_by}
                </span>
              )}
            </span>
          </div>
        </div>
      )}

      <main className="mx-auto max-w-7xl px-6 py-8">
        {loading ? (
          <div className="flex items-center gap-3 text-sm text-zinc-400">
            <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-zinc-700 border-t-indigo-400" />
            Cargando prompt…
          </div>
        ) : (
          <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
            {/* EDITOR PANEL */}
            <section className="rounded-xl border border-zinc-800 bg-zinc-900/40 backdrop-blur">
              <div className="flex items-center justify-between border-b border-zinc-800 px-5 py-3">
                <div className="flex items-center gap-3">
                  <span className="rounded-md bg-indigo-500/10 px-2 py-0.5 text-xs font-mono text-indigo-300 ring-1 ring-indigo-500/20">
                    chat_system
                  </span>
                  <span className="text-xs text-zinc-500">
                    {lineCount} líneas · {charCount} chars
                  </span>
                </div>
                <span className="text-xs text-zinc-500 font-mono">
                  {updatedAt
                    ? `editado ${new Date(updatedAt).toLocaleString("es-PE")}`
                    : ""}
                  {updatedBy ? ` · ${updatedBy}` : ""}
                </span>
              </div>

              <textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                spellCheck={false}
                className="block w-full resize-none border-0 bg-transparent p-5 font-mono text-sm leading-relaxed text-zinc-100 placeholder-zinc-600 outline-none"
                style={{ minHeight: "560px" }}
              />

              {missing.length > 0 && (
                <div className="border-t border-amber-500/20 bg-amber-500/5 px-5 py-3 text-sm text-amber-300">
                  ⚠ Faltan placeholders requeridos:{" "}
                  <span className="font-mono">
                    {missing.map((p) => `{${p}}`).join(", ")}
                  </span>
                </div>
              )}

              {error && (
                <div className="border-t border-red-500/30 bg-red-500/10 px-5 py-3 text-sm text-red-300 whitespace-pre-wrap">
                  {error}
                </div>
              )}

              <div className="flex items-center justify-between border-t border-zinc-800 px-5 py-3">
                <div className="text-xs text-zinc-500">
                  {dirty ? (
                    <span className="text-amber-400">● Cambios sin guardar</span>
                  ) : savedAt ? (
                    <span className="text-emerald-400">
                      ✓ Guardado a las {savedAt.toLocaleTimeString("es-PE")}
                    </span>
                  ) : (
                    <span>Sin cambios</span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setContent(original)}
                    disabled={!dirty}
                    className="rounded-md border border-zinc-800 px-3 py-1.5 text-xs text-zinc-300 transition hover:bg-zinc-900 hover:text-white disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    Descartar
                  </button>
                  <button
                    onClick={handleSave}
                    disabled={saving || !dirty || missing.length > 0}
                    className="group inline-flex items-center gap-2 rounded-md bg-gradient-to-r from-indigo-500 to-violet-500 px-4 py-1.5 text-xs font-medium text-white shadow-lg shadow-indigo-500/20 transition hover:shadow-indigo-500/40 disabled:cursor-not-allowed disabled:opacity-40 disabled:shadow-none"
                  >
                    {saving ? "Guardando…" : "Guardar cambios"}
                    {!saving && (
                      <svg className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                    )}
                  </button>
                </div>
              </div>
            </section>

            {/* SIDEBAR */}
            <aside className="space-y-6">
              <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-5">
                <h3 className="text-xs font-medium uppercase tracking-wider text-zinc-400 mb-3">
                  Variables disponibles
                </h3>
                <p className="text-xs text-zinc-500 mb-4 leading-relaxed">
                  El backend rellena estos valores antes de enviar el prompt al
                  modelo. Usa la sintaxis <code className="rounded bg-zinc-800 px-1.5 py-0.5 font-mono text-zinc-300">{"{nombre}"}</code>.
                </p>
                <ul className="space-y-3">
                  {PLACEHOLDERS.map((p) => {
                    const present = content.includes(`{${p.name}}`);
                    return (
                      <li key={p.name} className="space-y-1">
                        <button
                          onClick={() => navigator.clipboard.writeText(`{${p.name}}`)}
                          className="group flex items-center gap-2 text-left"
                        >
                          <span
                            className={`h-1.5 w-1.5 rounded-full ${present ? "bg-emerald-400" : "bg-zinc-700"}`}
                          />
                          <code className="font-mono text-sm text-indigo-300 group-hover:text-indigo-200">
                            {`{${p.name}}`}
                          </code>
                          <span className="text-[10px] text-zinc-600 opacity-0 transition group-hover:opacity-100">
                            copiar
                          </span>
                        </button>
                        <p className="text-xs text-zinc-500 pl-3.5">
                          {p.description}
                        </p>
                      </li>
                    );
                  })}
                </ul>
              </div>

              <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-5 text-xs text-zinc-400 leading-relaxed">
                <h3 className="text-xs font-medium uppercase tracking-wider text-zinc-400 mb-2">
                  Tip
                </h3>
                <p>
                  Los cambios entran en vigencia en el siguiente mensaje del
                  cliente (cache invalidado al guardar).
                </p>
              </div>
            </aside>
          </div>
        )}
      </main>
    </div>
  );
}
