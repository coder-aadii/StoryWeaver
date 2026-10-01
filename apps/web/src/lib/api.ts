/** Thin typed client. The browser only ever talks to the StoryWeaver API; provider keys stay server-side. */

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}/api/v1${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
  } catch {
    throw new ApiError(0, `Cannot reach the API at ${API_URL}. Is it running?`);
  }
  if (!res.ok) {
    throw new ApiError(res.status, `${res.status} ${res.statusText}`);
  }
  return res.status === 204 ? (undefined as T) : ((await res.json()) as T);
}

export interface Health {
  status: string;
  service: string;
}
export interface Ready {
  status: string;
  database: boolean;
  pgvector: boolean;
}
export interface ProviderHealth {
  default_llm_provider: string;
  default_llm_model_set: boolean;
  llm: Record<string, boolean>;
  ollama_reachable: boolean;
  comfyui: { configured: boolean; reachable: boolean };
  temporal_configured: boolean;
}
export interface Project {
  id: string;
  title: string;
  description: string | null;
  status: string;
  error: string | null;
  created_at: string;
}
