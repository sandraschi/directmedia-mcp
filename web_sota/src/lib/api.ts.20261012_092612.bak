export interface ServerStatus {
  status: string;
  service: string;
  library_initialized: boolean;
  library_path: string | null;
  volume_count: number;
  tools: string[];
}

export interface VolumeRow {
  id: string;
  title: string;
  short_title: string;
  path: string;
  size_mb: number;
  has_text: boolean;
  has_images: boolean;
  has_audio: boolean;
  error?: string;
}

export interface SearchHit {
  volume_id: string;
  title: string;
  content_preview: string;
  position: number;
}

const STORAGE_LIBRARY = "directmedia.library_path";
const STORAGE_EPUB_OUT = "directmedia.epub_output_dir";

/** Dev: Vite proxies /api -> :10827. Override with VITE_BACKEND_URL for direct access. */
export const API_BASE =
  (import.meta.env.VITE_BACKEND_URL as string | undefined)?.replace(
    /\/$/,
    "",
  ) ?? "http://127.0.0.1:10827";

export function formatFetchError(error: unknown): string {
  if (error instanceof TypeError && /fetch/i.test(error.message)) {
    return "Backend offline — run start.bat from directmedia-mcp (needs API on port 10827).";
  }
  return error instanceof Error ? error.message : "Request failed";
}

export function getStoredLibraryPath(): string {
  return localStorage.getItem(STORAGE_LIBRARY) ?? "";
}

export function setStoredLibraryPath(path: string): void {
  localStorage.setItem(STORAGE_LIBRARY, path);
}

export function getStoredEpubOutputDir(): string {
  return localStorage.getItem(STORAGE_EPUB_OUT) ?? "";
}

export function setStoredEpubOutputDir(path: string): void {
  localStorage.setItem(STORAGE_EPUB_OUT, path);
}

export function unwrapToolResult<T>(result: unknown): T {
  if (result == null || typeof result !== "object") {
    return result as T;
  }
  const record = result as Record<string, unknown>;
  if (record.structuredContent !== undefined) {
    return record.structuredContent as T;
  }
  if (record.structured_content !== undefined) {
    return record.structured_content as T;
  }
  if (
    record.success !== undefined ||
    record.error !== undefined ||
    Array.isArray(result)
  ) {
    return result as T;
  }
  if (Array.isArray(record.content)) {
    const text = record.content
      .filter(
        (chunk): chunk is { type: string; text?: string } =>
          typeof chunk === "object" && chunk !== null,
      )
      .filter(
        (chunk) => chunk.type === "text" && typeof chunk.text === "string",
      )
      .map((chunk) => chunk.text as string)
      .join("");
    if (!text) return result as T;
    try {
      return JSON.parse(text) as T;
    } catch {
      return text as T;
    }
  }
  return result as T;
}

async function callTool<T>(
  name: string,
  args: Record<string, unknown> = {},
): Promise<T> {
  const res = await fetch(`${API_BASE}/api/v1/call`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, arguments: args }),
  });
  if (!res.ok) {
    throw new Error(await res.text());
  }
  const payload = await res.json();
  return unwrapToolResult<T>(payload);
}

export async function fetchStatus(): Promise<ServerStatus> {
  const res = await fetch(`${API_BASE}/api/v1/status`);
  if (!res.ok) throw new Error("Backend unreachable");
  return res.json();
}

export async function setLibraryPath(path: string) {
  const trimmed = path.trim();
  const res = await fetch(`${API_BASE}/api/v1/library/path`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path: trimmed }),
  });
  const payload = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail =
      typeof payload === "object" && payload !== null && "detail" in payload
        ? String((payload as { detail: unknown }).detail)
        : res.statusText;
    throw new Error(detail || "Failed to set library path");
  }
  return payload as {
    success?: boolean;
    error?: string;
    volumes_found?: number;
    message?: string;
  };
}

export async function listVolumes(): Promise<VolumeRow[]> {
  return callTool<VolumeRow[]>("list_volumes");
}

export async function getVolumeInfo(volumeId: string) {
  return callTool<VolumeRow & { error?: string }>("get_volume_info", {
    volume_id: volumeId,
  });
}

export async function searchText(query: string, volumeId?: string, limit = 25) {
  const args: Record<string, unknown> = { query, limit };
  if (volumeId) args.volume_id = volumeId;
  return callTool<SearchHit[]>("search_text", args);
}

export async function getTextContent(
  volumeId: string,
  startPos = 0,
  length = 4000,
) {
  return callTool<{ content?: string; error?: string }>("get_text_content", {
    volume_id: volumeId,
    start_pos: startPos,
    length,
  });
}

export async function getNavigationTree(volumeId: string) {
  return callTool<Record<string, unknown>>("get_navigation_tree", {
    volume_id: volumeId,
  });
}

export async function convertVolumeToEpub(volumeId: string, outputDir: string) {
  return callTool<Record<string, unknown>>("convert_volume_to_epub_file", {
    volume_id: volumeId,
    output_dir: outputDir,
  });
}

// ---- Reader API (REST, /api/v1/reader) ----

export type IndexState = "missing" | "building" | "ready" | "stale" | "error";

export interface ReaderVolume {
  id: string;
  title: string;
  short_title: string;
  size_mb: number;
  records: number;
  format: string;
  index_state: IndexState;
}

export interface TocEntry {
  index: number;
  title: string;
  level: number;
  record: number | null;
  child_count: number;
}

export interface TocLevel {
  volume_id: string;
  parent: number | null;
  entries: TocEntry[];
  breadcrumb: TocEntry[];
  has_record_map: boolean;
}

export interface ReaderPage {
  volume_id: string;
  record: number;
  total: number;
  text: string;
  print_pages: number[];
  source: string | null;
  prev: number | null;
  next: number | null;
  breadcrumb: TocEntry[];
}

export interface IndexStatus {
  volume_id: string;
  state: IndexState;
  done: number;
  total: number;
  error: string | null;
}

export interface ReaderHit {
  volume_id: string;
  record: number;
  snippet: string;
  score: number;
  breadcrumb: string[];
}

export interface ReaderSearchResult {
  query: string;
  total: number;
  totals: Record<string, number>;
  offset: number;
  hits: ReaderHit[];
  not_indexed: string[];
  markers: [string, string];
}

async function readerGet<T>(
  path: string,
  params?: Record<string, string | number | undefined>,
): Promise<T> {
  const url = new URL(`${API_BASE}/api/v1/reader${path}`);
  for (const [key, value] of Object.entries(params ?? {})) {
    if (value !== undefined && value !== "")
      url.searchParams.set(key, String(value));
  }
  const res = await fetch(url);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(
      (body as { detail?: string }).detail ?? `${res.status} ${res.statusText}`,
    );
  }
  return res.json() as Promise<T>;
}

export function readerVolumes() {
  return readerGet<ReaderVolume[]>("/volumes");
}

export function readerToc(volumeId: string, parent?: number) {
  return readerGet<TocLevel>(`/volumes/${encodeURIComponent(volumeId)}/toc`, {
    parent,
  });
}

export function readerPage(volumeId: string, record: number) {
  return readerGet<ReaderPage>(
    `/volumes/${encodeURIComponent(volumeId)}/records/${record}`,
  );
}

export function readerIndexStatus() {
  return readerGet<IndexStatus[]>("/index");
}

export async function readerBuildIndex(volumeId: string): Promise<IndexStatus> {
  const res = await fetch(
    `${API_BASE}/api/v1/reader/index/${encodeURIComponent(volumeId)}`,
    { method: "POST" },
  );
  if (!res.ok) throw new Error(`Index build failed to start: ${res.status}`);
  return res.json();
}

export function readerSearch(
  q: string,
  volumes: string[] = [],
  limit = 20,
  offset = 0,
) {
  return readerGet<ReaderSearchResult>("/search", {
    q,
    volumes: volumes.length ? volumes.join(",") : undefined,
    limit,
    offset,
  });
}

export interface TextPart {
  text: string;
  hit: boolean;
  /** Character offset of the part in the original string: a stable React key. */
  key: number;
}

function withKeys(parts: Omit<TextPart, "key">[]): TextPart[] {
  let pos = 0;
  return parts
    .filter((p) => p.text)
    .map((p) => {
      const part = { ...p, key: pos };
      pos += p.text.length;
      return part;
    });
}

/** Split a snippet on the server's highlight markers into alternating plain/highlighted parts. */
export function splitSnippet(
  snippet: string,
  [start, end]: [string, string],
): TextPart[] {
  const parts: Omit<TextPart, "key">[] = [];
  for (const chunk of snippet.split(start)) {
    const [hit, ...rest] = chunk.split(end);
    if (rest.length) {
      parts.push(
        { text: hit, hit: true },
        { text: rest.join(end), hit: false },
      );
    } else {
      parts.push({ text: chunk, hit: false });
    }
  }
  return withKeys(parts);
}

/** Split text on a capturing regex: odd parts are matches. */
export function splitMatches(text: string, re: RegExp): TextPart[] {
  return withKeys(
    text.split(re).map((t, i) => ({ text: t, hit: i % 2 === 1 })),
  );
}
