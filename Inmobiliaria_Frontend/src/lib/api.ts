const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

const TOKEN_KEY = "admin_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((init.headers as Record<string, string>) ?? {}),
  };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(`${API_URL}${path}`, { ...init, headers });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      // body no es json
    }
    throw new ApiError(detail, res.status);
  }
  return (await res.json()) as T;
}

// ----- Endpoints --------------------------------------------------------

export type LoginResponse = {
  access_token: string;
  token_type: string;
  expires_at: string;
  username: string;
};

export function login(username: string, password: string) {
  return request<LoginResponse>("/api/admin/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export type Prompt = {
  key: string;
  content: string;
  updated_by: string | null;
  updated_at: string;
};

export function getPrompt(key: string) {
  return request<Prompt>(`/api/admin/prompts/${key}`);
}

export function updatePrompt(key: string, content: string) {
  return request<Prompt>(`/api/admin/prompts/${key}`, {
    method: "PUT",
    body: JSON.stringify({ content }),
  });
}

export type AgentStatus = {
  enabled: boolean;
  updated_by: string | null;
  updated_at: string | null;
};

export function getAgentStatus() {
  return request<AgentStatus>("/api/admin/agent-status");
}

export function setAgentStatus(enabled: boolean) {
  return request<AgentStatus>("/api/admin/agent-status", {
    method: "PUT",
    body: JSON.stringify({ enabled }),
  });
}
