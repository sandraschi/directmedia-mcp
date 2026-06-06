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
  if (Array.isArray(record.content)) {
    const text = record.content
      .filter((chunk): chunk is { type: string; text?: string } => typeof chunk === "object" && chunk !== null)
      .filter((chunk) => chunk.type === "text" && typeof chunk.text === "string")
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

async function callTool<T>(name: string, args: Record<string, unknown> = {}): Promise<T> {
  const res = await fetch("/api/v1/call", {
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
  const res = await fetch("/api/v1/status");
  if (!res.ok) throw new Error("Backend unreachable");
  return res.json();
}

export async function setLibraryPath(path: string) {
  return callTool<{ success?: boolean; error?: string; volumes_found?: number; message?: string }>(
    "set_library_path",
    { path },
  );
}

export async function listVolumes(): Promise<VolumeRow[]> {
  return callTool<VolumeRow[]>("list_volumes");
}

export async function getVolumeInfo(volumeId: string) {
  return callTool<VolumeRow & { error?: string }>("get_volume_info", { volume_id: volumeId });
}

export async function searchText(query: string, volumeId?: string, limit = 25) {
  const args: Record<string, unknown> = { query, limit };
  if (volumeId) args.volume_id = volumeId;
  return callTool<SearchHit[]>("search_text", args);
}

export async function getTextContent(volumeId: string, startPos = 0, length = 4000) {
  return callTool<{ content?: string; error?: string }>("get_text_content", {
    volume_id: volumeId,
    start_pos: startPos,
    length,
  });
}

export async function getNavigationTree(volumeId: string) {
  return callTool<Record<string, unknown>>("get_navigation_tree", { volume_id: volumeId });
}

export async function convertVolumeToEpub(volumeId: string, outputDir: string) {
  return callTool<Record<string, unknown>>("convert_volume_to_epub_file", {
    volume_id: volumeId,
    output_dir: outputDir,
  });
}
