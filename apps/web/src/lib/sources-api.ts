/** Source Library API: types mirror apps/api/app/schemas/source_api.py (hand-maintained). */
import { api } from "@/lib/api";

export type SourceStatus = "discovered" | "importing" | "imported" | "failed";
export type TranscriptStatus = "pending" | "processing" | "ready" | "failed";
export type RunStatus = "queued" | "running" | "succeeded" | "failed" | "interrupted";
export type SourceKind = "youtube" | "transcript";

export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface RunError {
  code: string;
  message: string;
  retryable: boolean;
}

export interface RunRead {
  id: string;
  kind: string;
  subject_type: string;
  subject_id: string;
  status: RunStatus;
  attempt: number;
  progress: Record<string, unknown>;
  error: RunError | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
}

export interface SourceListItem {
  id: string;
  title: string;
  platform: string;
  kind: SourceKind;
  url: string | null;
  thumbnail_url: string | null;
  duration_seconds: number | null;
  language: string | null;
  status: SourceStatus;
  error: string | null;
  channel_title: string | null;
  transcript_status: TranscriptStatus | null;
  transcript_error: string | null;
  chunk_count: number;
  searchable: boolean;
  usage_count: number;
  created_at: string;
  updated_at: string;
}

export interface TranscriptSummary {
  id: string;
  version: number;
  status: TranscriptStatus;
  origin: string;
  language: string | null;
  segment_count: number;
  char_count: number;
  timed: boolean;
  normalizer_version: string | null;
  error: string | null;
  created_at: string;
}

export interface SourceDetail extends SourceListItem {
  description: string | null;
  published_at: string | null;
  fingerprint: string | null;
  transcript: TranscriptSummary | null;
  active_run: RunRead | null;
}

export interface AddSourceResult {
  source: SourceListItem;
  run: RunRead | null;
  already_exists: boolean;
  match: "identity" | "fingerprint" | null;
  transcript: TranscriptSummary | null;
}

export interface TranscriptSegment {
  start: number | null;
  end: number | null;
  text: string;
  speaker?: string | null;
}

export interface TranscriptContent {
  transcript: TranscriptSummary;
  text: string;
  segments: Page<TranscriptSegment>;
}

export interface ChunkRead {
  id: string;
  chunk_index: number;
  text: string;
  start_seconds: number | null;
  end_seconds: number | null;
}

export interface SearchHit {
  source: SourceListItem;
  chunk_id: string;
  chunk_index: number;
  /** Everything HTML-escaped except `<mark>…</mark>` around matches. Render with SafeSnippet only. */
  snippet: string;
  start_seconds: number | null;
  end_seconds: number | null;
  rank: number;
}

export interface SourceUsage {
  project_id: string;
  project_title: string;
  role: string;
  linked_at: string;
}

export interface ProjectSourceLink {
  source: SourceListItem;
  role: string;
  linked_at: string;
}

export const MAX_TRANSCRIPT_BYTES = 5 * 1024 * 1024; // mirrors Settings.max_transcript_bytes
export const TRANSCRIPT_EXTENSIONS = [".txt", ".srt", ".vtt"] as const;

type Params = Record<string, string | number | boolean | undefined | null>;

/** Build a query string, skipping undefined/null/empty values. */
export function qs(params: Params = {}): string {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === "") continue;
    sp.set(k, String(v));
  }
  const s = sp.toString();
  return s ? `?${s}` : "";
}

export interface ListSourcesParams {
  status?: SourceStatus;
  kind?: SourceKind;
  used?: boolean;
  limit?: number;
  offset?: number;
}

export const listSources = (p: ListSourcesParams = {}) =>
  api<Page<SourceListItem>>(`/sources${qs({ ...p })}`);
export const getSource = (id: string) => api<SourceDetail>(`/sources/${id}`);
export const addSourceFromUrl = (url: string) =>
  api<AddSourceResult>("/sources/from-url", { method: "POST", body: JSON.stringify({ url }) });
/** `form` fields: `file` or `text`, `title`, optional `language`, `reference_url`. */
export const addSourceFromTranscript = (form: FormData) =>
  api<AddSourceResult>("/sources/from-transcript", { method: "POST", body: form });
/**
 * Attach or replace the transcript of an EXISTING source (the no-captions fallback).
 * `form`: `file` OR `text`, optional `language` — no title. 409 `source_busy` while an import runs.
 */
export const attachTranscript = (sourceId: string, form: FormData) =>
  api<SourceDetail>(`/sources/${sourceId}/transcript`, { method: "POST", body: form });
export const retrySource = (id: string) =>
  api<{ run: RunRead }>(`/sources/${id}/retry`, { method: "POST" });
export const deleteSource = (id: string) => api<void>(`/sources/${id}`, { method: "DELETE" });

export interface SearchParams {
  q: string;
  exclude_used?: boolean;
  /** Restrict hits to one source (in-source search). */
  source_id?: string;
  limit?: number;
  offset?: number;
}
export const searchSources = (p: SearchParams) =>
  api<Page<SearchHit>>(`/sources/search${qs({ ...p })}`);

export interface PageParams {
  limit?: number;
  offset?: number;
}
export const getTranscript = (id: string, p: PageParams = {}) =>
  api<TranscriptContent>(`/sources/${id}/transcript${qs({ ...p })}`);
export const getChunks = (id: string, p: PageParams = {}) =>
  api<Page<ChunkRead>>(`/sources/${id}/chunks${qs({ ...p })}`);
export const getUsage = (id: string) => api<SourceUsage[]>(`/sources/${id}/usage`);

export const getRun = (id: string) => api<RunRead>(`/runs/${id}`);
export const listRuns = (subjectId: string, p: PageParams = {}) =>
  api<Page<RunRead>>(`/runs${qs({ subject_id: subjectId, ...p })}`);

export const listProjectSources = (projectId: string) =>
  api<ProjectSourceLink[]>(`/projects/${projectId}/sources`);
export const putProjectSource = (projectId: string, sourceId: string, role?: string) =>
  api<ProjectSourceLink>(`/projects/${projectId}/sources/${sourceId}`, {
    method: "PUT",
    body: JSON.stringify(role ? { role } : {}),
  });
export const deleteProjectSource = (projectId: string, sourceId: string) =>
  api<void>(`/projects/${projectId}/sources/${sourceId}`, { method: "DELETE" });

export const TERMINAL_RUN_STATUSES: ReadonlySet<RunStatus> = new Set([
  "succeeded",
  "failed",
  "interrupted",
]);
