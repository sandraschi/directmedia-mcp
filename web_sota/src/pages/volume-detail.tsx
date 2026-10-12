import {
  BookOpenText,
  ChevronDown,
  ChevronRight,
  Database,
  Download,
  Loader2,
  Sparkles,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  convertVolumeToEpub,
  getStoredEpubOutputDir,
  type IndexStatus,
  type ReaderVolume,
  readerBuildIndex,
  readerIndexStatus,
  readerToc,
  readerVolumes,
  type SemanticStatus,
  semanticBuild,
  semanticStatus,
  type TocEntry,
} from "@/lib/api";
import { IndexBadge } from "@/pages/volumes";

function TocNode({ volumeId, entry }: { volumeId: string; entry: TocEntry }) {
  const [open, setOpen] = useState(false);
  const [children, setChildren] = useState<TocEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function toggle() {
    if (!open && children === null) {
      try {
        setChildren((await readerToc(volumeId, entry.index)).entries);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load");
      }
    }
    setOpen(!open);
  }

  return (
    <li>
      <div className="group flex items-center gap-1 rounded py-0.5 pr-2 hover:bg-slate-900">
        {entry.child_count > 0 ? (
          <button
            type="button"
            onClick={toggle}
            className="rounded p-0.5 text-slate-500 hover:text-white"
            aria-label={open ? "Collapse" : "Expand"}
            data-testid={`toc-toggle-${entry.index}`}
          >
            {open ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
          </button>
        ) : (
          <span className="w-5" />
        )}
        {entry.record !== null ? (
          <Link
            to={`/read/${volumeId}/${entry.record}`}
            className="text-slate-200 hover:text-amber-300"
          >
            {entry.title}
          </Link>
        ) : (
          <button
            type="button"
            onClick={toggle}
            className="text-left text-slate-200"
          >
            {entry.title}
          </button>
        )}
        {entry.child_count > 0 && (
          <span className="ml-1 text-xs text-slate-600">
            {entry.child_count}
          </span>
        )}
      </div>
      {error && <p className="ml-6 text-xs text-red-400">{error}</p>}
      {open && children && (
        <ul className="ml-4 border-l border-slate-800 pl-2">
          {children.map((c) => (
            <TocNode key={c.index} volumeId={volumeId} entry={c} />
          ))}
        </ul>
      )}
    </li>
  );
}

function SemanticIndexControl({ volumeId }: { volumeId: string }) {
  const [st, setSt] = useState<SemanticStatus | null>(null);

  const refresh = useCallback(async () => {
    const all = await semanticStatus();
    setSt(all.find((s) => s.volume_id === volumeId) ?? null);
  }, [volumeId]);

  useEffect(() => {
    refresh().catch(() => undefined);
  }, [refresh]);

  useEffect(() => {
    if (st?.state !== "building" && st?.state !== "queued") return;
    const timer = window.setInterval(() => {
      refresh().catch(() => undefined);
    }, 2000);
    return () => window.clearInterval(timer);
  }, [st?.state, refresh]);

  if (st?.state === "queued") {
    return (
      <span className="text-sm text-amber-300">Semantic index queued…</span>
    );
  }
  if (st?.state === "building") {
    const pct = st.total ? Math.round((100 * st.done) / st.total) : 0;
    return (
      <span
        className="flex items-center gap-2 text-sm text-amber-300"
        data-testid="volume-semantic-progress"
      >
        <Loader2 className="h-4 w-4 animate-spin" /> Embedding… {pct}% (
        {st.chunks.toLocaleString("de-DE")} passages)
      </span>
    );
  }
  if (st?.state === "ready") {
    return (
      <span className="flex items-center gap-1 text-sm text-emerald-300">
        <Sparkles className="h-4 w-4" /> semantic (
        {st.chunks.toLocaleString("de-DE")} passages)
      </span>
    );
  }
  return (
    <>
      <Button
        variant="outline"
        className="border-slate-700"
        onClick={() =>
          semanticBuild(volumeId)
            .then(setSt)
            .catch(() => undefined)
        }
        data-testid="volume-semantic"
      >
        <Sparkles className="mr-2 h-4 w-4" />
        {st?.state === "stale" ? "Rebuild" : "Build"} semantic index
      </Button>
      {st?.state === "error" && (
        <span className="text-sm text-red-400">{st.error}</span>
      )}
    </>
  );
}

export function VolumeDetail() {
  const { volumeId = "" } = useParams();
  const [volume, setVolume] = useState<ReaderVolume | null>(null);
  const [top, setTop] = useState<TocEntry[]>([]);
  const [hasMap, setHasMap] = useState(true);
  const [index, setIndex] = useState<IndexStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [exportMsg, setExportMsg] = useState<string | null>(null);

  const refreshIndex = useCallback(async () => {
    const all = await readerIndexStatus();
    setIndex(all.find((s) => s.volume_id === volumeId) ?? null);
  }, [volumeId]);

  useEffect(() => {
    if (!volumeId) return;
    Promise.all([readerVolumes(), readerToc(volumeId), readerIndexStatus()])
      .then(([vols, toc, idx]) => {
        setVolume(vols.find((v) => v.id === volumeId) ?? null);
        setTop(toc.entries);
        setHasMap(toc.has_record_map);
        setIndex(idx.find((s) => s.volume_id === volumeId) ?? null);
      })
      .catch((e: unknown) =>
        setError(e instanceof Error ? e.message : "Failed to load volume"),
      );
  }, [volumeId]);

  useEffect(() => {
    if (index?.state !== "building") return;
    const timer = window.setInterval(() => {
      refreshIndex().catch(() => undefined);
    }, 1500);
    return () => window.clearInterval(timer);
  }, [index?.state, refreshIndex]);

  async function handleIndex() {
    try {
      setIndex(await readerBuildIndex(volumeId));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Index build failed");
    }
  }

  async function handleEpubExport() {
    const out = getStoredEpubOutputDir();
    if (!out) {
      setExportMsg("Set an EPUB output folder in Settings first.");
      return;
    }
    setExportMsg("Converting…");
    try {
      const result = await convertVolumeToEpub(volumeId, out);
      setExportMsg(
        result.success
          ? `EPUB written under ${out}`
          : String(result.message ?? result.error ?? "Conversion failed"),
      );
    } catch (e) {
      setExportMsg(e instanceof Error ? e.message : "Conversion failed");
    }
  }

  const pct = index?.total ? Math.round((100 * index.done) / index.total) : 0;

  return (
    <div className="space-y-6">
      <Link to="/volumes" className="text-sm text-slate-400 hover:text-white">
        ← Library
      </Link>

      {error && (
        <div className="rounded-md border border-red-900/50 bg-red-950/30 px-4 py-3 text-sm text-red-200">
          {error}
        </div>
      )}

      <Card className="border-slate-800 bg-slate-950/50">
        <CardHeader>
          <p className="font-mono text-sm text-amber-400">{volumeId}</p>
          <CardTitle className="text-2xl text-white">
            {volume?.short_title ?? volumeId}
          </CardTitle>
          {volume && (
            <p className="text-sm text-slate-400">
              {volume.title} · {volume.records.toLocaleString("de-DE")} pages ·
              format {volume.format}
            </p>
          )}
        </CardHeader>
        <CardContent className="flex flex-wrap items-center gap-3">
          <Button
            asChild
            className="bg-amber-700 hover:bg-amber-600"
            data-testid="volume-read"
          >
            <Link to={`/read/${volumeId}/0`}>
              <BookOpenText className="mr-2 h-4 w-4" /> Read from the start
            </Link>
          </Button>
          {index?.state === "building" ? (
            <span
              className="flex items-center gap-2 text-sm text-amber-300"
              data-testid="volume-index-progress"
            >
              <Loader2 className="h-4 w-4 animate-spin" /> Indexing… {pct}% (
              {index.done.toLocaleString("de-DE")} /{" "}
              {index.total.toLocaleString("de-DE")})
            </span>
          ) : index?.state === "ready" ? (
            <IndexBadge state="ready" />
          ) : (
            <Button
              variant="outline"
              className="border-slate-700"
              onClick={handleIndex}
              data-testid="volume-index"
            >
              <Database className="mr-2 h-4 w-4" />{" "}
              {index?.state === "stale" ? "Rebuild" : "Build"} search index
            </Button>
          )}
          {index?.state === "error" && (
            <span className="text-sm text-red-400">{index.error}</span>
          )}
          <SemanticIndexControl volumeId={volumeId} />
          <Button
            variant="outline"
            className="border-slate-700"
            onClick={handleEpubExport}
            data-testid="volume-epub"
          >
            <Download className="mr-2 h-4 w-4" /> Export EPUB
          </Button>
          {exportMsg && (
            <span className="text-sm text-slate-400">{exportMsg}</span>
          )}
        </CardContent>
      </Card>

      <Card className="border-slate-800 bg-slate-950/50">
        <CardHeader>
          <CardTitle className="text-white">Contents</CardTitle>
          {!hasMap && (
            <p className="text-sm text-amber-300">
              This volume's table of contents uses a layout that is not decoded
              yet: titles are shown, but they do not link to pages. Use “Read”
              or search instead.
            </p>
          )}
        </CardHeader>
        <CardContent>
          {top.length ? (
            <ul className="text-sm" data-testid="volume-toc">
              {top.map((e) => (
                <TocNode key={e.index} volumeId={volumeId} entry={e} />
              ))}
            </ul>
          ) : (
            <p className="text-sm text-slate-500">
              {error ? "" : "Loading contents…"}
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
