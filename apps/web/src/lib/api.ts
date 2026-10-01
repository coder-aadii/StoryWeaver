/** Thin typed client. The browser only ever talks to the StoryWeaver API; provider keys stay server-side. */

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    /** Stable machine code from the API (`{detail, code}` bodies), when present. */
    public code: string | null = null,
  ) {
    super(message);
  }
}

/** One FastAPI/Pydantic validation error item. */
interface ValidationItem {
  msg?: string;
  loc?: (string | number)[];
}

/** Turn an error response into a readable message. Never throws. */
async function errorFrom(res: Response): Promise<ApiError> {
  const fallback = `${res.status} ${res.statusText}`.trim();
  let body: unknown;
  try {
    body = await res.json();
  } catch {
    return new ApiError(res.status, fallback);
  }
  const detail = (body as { detail?: unknown } | null)?.detail;
  const code = (body as { code?: unknown } | null)?.code;
  const codeStr = typeof code === "string" ? code : null;
  if (typeof detail === "string" && detail) return new ApiError(res.status, detail, codeStr);
  if (Array.isArray(detail) && detail.length > 0) {
    const messages = (detail as ValidationItem[])
      .map((d) => (d.msg ?? "").replace(/^Value error, /, ""))
      .filter(Boolean);
    if (messages.length) return new ApiError(res.status, messages.join("; "), codeStr);
  }
  return new ApiError(res.status, fallback, codeStr);
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  // Only JSON string bodies get a Content-Type: FormData must set its own multipart boundary, and a
  // header-less GET avoids a needless CORS preflight.
  const headers: Record<string, string> = {};
  if (typeof init?.body === "string") headers["Content-Type"] = "application/json";
  let res: Response;
  try {
    res = await fetch(`${API_URL}/api/v1${path}`, {
      ...init,
      headers: { ...headers, ...(init?.headers as Record<string, string> | undefined) },
    });
  } catch {
    throw new ApiError(0, `Cannot reach the API at ${API_URL}. Is it running?`);
  }
  if (!res.ok) throw await errorFrom(res);
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
