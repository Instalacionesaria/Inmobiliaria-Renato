import { useState, type FormEvent } from "react";
import { login, setToken, ApiError } from "../lib/api";
import { Logo } from "./Logo";

type Props = {
  onLogin: (username: string) => void;
};

export function LoginPage({ onLogin }: Props) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await login(username, password);
      setToken(res.access_token);
      onLogin(res.username);
    } catch (err) {
      if (err instanceof ApiError) setError(err.message);
      else setError("No pude conectar con el backend");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-full grid lg:grid-cols-2 bg-zinc-950 text-zinc-100">
      {/* HERO LEFT */}
      <aside className="relative hidden lg:flex flex-col justify-between p-12 overflow-hidden bg-glow">
        <div className="absolute inset-0 bg-grid opacity-60" />
        <div className="absolute inset-0 bg-gradient-to-br from-indigo-950/40 via-transparent to-violet-950/30" />

        <div className="relative flex items-center gap-3">
          <Logo className="h-9 w-9" />
          <span className="font-semibold tracking-tight text-xl">
            ARIABLE
          </span>
        </div>

        <div className="relative space-y-8 max-w-md">
          <h2 className="text-4xl font-semibold leading-tight tracking-tight text-white">
            Atiende a tus 18 edificios{" "}
            <span className="bg-gradient-to-r from-indigo-300 to-violet-300 bg-clip-text text-transparent">
              desde un solo agente.
            </span>
          </h2>

          <ul className="space-y-3 text-zinc-300">
            <Feature label="WhatsApp 24/7 vía HighLevel" />
            <Feature label="Datos de cuotas en vivo desde Google Sheets" />
            <Feature label="Memoria persistente por inquilino" />
            <Feature label="Edita el prompt sin redeployar" />
          </ul>
        </div>

        <p className="relative text-sm text-zinc-500 font-mono">
          v0.1 · panel interno
        </p>
      </aside>

      {/* FORM RIGHT */}
      <main className="flex items-center justify-center p-6 sm:p-12">
        <div className="w-full max-w-sm space-y-8">
          <div className="lg:hidden flex items-center gap-3 mb-8">
            <Logo />
            <span className="font-semibold tracking-tight text-lg">
              ARIABLE
            </span>
          </div>

          <div className="space-y-2">
            <h1 className="text-2xl font-semibold tracking-tight text-white">
              Bienvenido de vuelta
            </h1>
            <p className="text-sm text-zinc-400">
              Inicia sesión para administrar el agente.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            <Field
              label="Usuario"
              type="text"
              autoComplete="username"
              value={username}
              onChange={setUsername}
            />
            <Field
              label="Contraseña"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={setPassword}
            />

            {error && (
              <div className="rounded-md border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="group relative w-full overflow-hidden rounded-md bg-gradient-to-r from-indigo-500 to-violet-500 px-4 py-2.5 text-sm font-medium text-white shadow-lg shadow-indigo-500/20 transition-all hover:shadow-indigo-500/40 disabled:opacity-50"
            >
              <span className="relative z-10 inline-flex items-center justify-center gap-2">
                {loading ? "Entrando…" : "Iniciar sesión"}
                {!loading && (
                  <svg
                    className="h-4 w-4 transition-transform group-hover:translate-x-0.5"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M17 8l4 4m0 0l-4 4m4-4H3"
                    />
                  </svg>
                )}
              </span>
            </button>
          </form>

          <p className="text-xs text-zinc-500 font-mono">
            Acceso restringido · contacta al administrador
          </p>
        </div>
      </main>
    </div>
  );
}

function Feature({ label }: { label: string }) {
  return (
    <li className="flex items-start gap-3">
      <span className="mt-1 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-indigo-500/15 text-indigo-300 ring-1 ring-indigo-500/30">
        <svg className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth="3" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
        </svg>
      </span>
      <span className="text-base">{label}</span>
    </li>
  );
}

type FieldProps = {
  label: string;
  type: string;
  autoComplete: string;
  value: string;
  onChange: (v: string) => void;
};

function Field({ label, type, autoComplete, value, onChange }: FieldProps) {
  return (
    <label className="block">
      <span className="text-xs font-medium uppercase tracking-wider text-zinc-400">
        {label}
      </span>
      <input
        type={type}
        autoComplete={autoComplete}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required
        className="mt-1.5 block w-full rounded-md border border-zinc-800 bg-zinc-900/50 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 outline-none ring-0 transition focus:border-indigo-500/50 focus:bg-zinc-900 focus:ring-2 focus:ring-indigo-500/30"
      />
    </label>
  );
}
