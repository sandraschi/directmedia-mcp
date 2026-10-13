import {
  ChevronLeft,
  ChevronRight,
  Database,
  Loader2,
  Search as SearchIcon,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import {
  type ReaderSearchResult,
  type ReaderVolume,
  readerBuildIndex,
  readerSearch,
  readerVolumes,
  splitSnippet,
} from "@/lib/api";

const PAGE_SIZE = 20;

export function Search() {
  const [params, setParams] = useSearchParams();
  const q = params.get("q") ?? "";
  const scope = params.get("vol") ?? "";
  const offset = Number.parseInt(params.get("o") ?? "0", 10) || 0;

  const [input, setInput] = useState(q);
  const [volumes, setVolumes] = useState<ReaderVolume[]>([]);
  const [result, setResult] = useState<ReaderSearchResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [indexMsg, setIndexMsg] = useState<string | null>(null);

  useEffect(() => {
    readerVolumes()
      .then(setVolumes)
      .catch((e: unknown) =>
        setError(e instanceof Error ? e.message : "Failed to load volumes"),
      );
  }, []);

  useEffect(() => {
    if (!q.trim()) {
      setResult(null);
      return;
    }
    setLoading(true);
    setError(null);
    readerSearch(q, scope ? [scope] : [], PAGE_SIZE, offset)
      .then(setResult)
      .catch((e: unknown) =>
        setError(e instanceof Error ? e.message : "Search failed"),
      )
      .finally(() => setLoading(false));
  }, [q, scope, offset]);

  function update(next: { q?: string; vol?: string; o?: number }) {
    const merged = { q, vol: scope, o: 0, ...next };
    const p: Record<string, string> = {};
    if (merged.q) p.q = merged.q;
    if (merged.vol) p.vol = merged.vol;
    if (merged.o) p.o = String(merged.o);
    setParams(p);
  }

  async function indexScope() {
    if (!scope) return;
    try {
      await readerBuildIndex(scope);
      setIndexMsg(
        `Indexing ${scope} started. Progress is shown on the volume page; search again when it is done.`,
      );
    } catch (e) {
      setIndexMsg(e instanceof Error ? e.message : "Index build failed");
    }
  }

  const indexed = volumes.filter((v) => v.index_state === "ready").length;
  const volumeTitle = (id: string) =>
    volumes.find((v) => v.id === id)?.short_title ?? id;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white">Full-text search</h2>
        <p className="text-slate-400">
          Ranked search across indexed volumes ({indexed} of {volumes.length}{" "}
          indexed). Words are combined with AND; use "quotes" for phrases and
          word* for prefixes.
        </p>
      </div>

      <form
        className="flex flex-col gap-3 md:flex-row"
        onSubmit={(e) => {
          e.preventDefault();
          update({ q: input.trim() });
        }}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder='e.g. Werther Lotte, "Minna von Barnhelm", tugend*'
          className="flex-1 rounded-md border border-slate-800 bg-slate-900 px-3 py-2 text-white"
          data-testid="search-input"
        />
        <select
          value={scope}
          onChange={(e) => update({ vol: e.target.value })}
          className="rounded-md border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-white md:w-72"
          data-testid="search-scope"
        >
          <option value="">All indexed volumes</option>
          {volumes.map((v) => (
            <option key={v.id} value={v.id}>
              {v.id} · {v.short_title}
              {v.index_state === "ready" ? "" : " (not indexed)"}
            </option>
          ))}
        </select>
        <Button
          type="submit"
          className="bg-amber-700 hover:bg-amber-600"
          data-testid="search-submit"
        >
          <SearchIcon className="mr-2 h-4 w-4" /> Search
        </Button>
      </form>

      {error && (
        <div className="rounded-md border border-red-900/50 bg-red-950/30 px-4 py-3 text-sm text-red-200">
          {error}
        </div>
      )}

      {result && result.not_indexed.length > 0 && (
        <div className="flex flex-wrap items-center gap-3 rounded-md border border-amber-900/50 bg-amber-950/20 px-4 py-3 text-sm text-amber-200">
          {scope ? (
            <>
              {scope} is not indexed yet, so it cannot be searched.
              <Button
                size="sm"
                variant="outline"
                className="border-amber-800"
                onClick={indexScope}
              >
                <Database className="mr-2 h-4 w-4" /> Index {scope}
              </Button>
            </>
          ) : (
            <>
              {result.not_indexed.length} volumes are not indexed and were
              skipped. Build their index on each volume's page in the{" "}
              <Link to="/volumes" className="underline">
                Library
              </Link>
              .
            </>
          )}
          {indexMsg && (
            <span className="w-full text-amber-300">{indexMsg}</span>
          )}
        </div>
      )}

      {loading && (
        <p className="flex items-center gap-2 text-slate-400">
          <Loader2 className="h-4 w-4 animate-spin" /> Searching…
        </p>
      )}

      {result && !loading && (
        <div className="space-y-3" data-testid="search-results">
          <p className="text-sm text-slate-400">
            {result.total ? (
              <>
                {offset + 1}–{offset + result.hits.length} of{" "}
                {result.total.toLocaleString("de-DE")} pages
                {Object.keys(result.totals).length > 1 &&
                  ` in ${Object.values(result.totals).filter((n) => n > 0).length} volumes`}
              </>
            ) : (
              `No matches for “${result.query}”.`
            )}
          </p>
          {result.hits.map((h) => (
            <Link
              key={`${h.volume_id}-${h.record}`}
              to={`/read/${h.volume_id}/${h.record}?q=${encodeURIComponent(q)}`}
              className="block rounded-lg border border-slate-800 bg-slate-950/50 px-4 py-3 hover:border-amber-800"
            >
              <div className="mb-1 flex flex-wrap items-center gap-2 text-xs text-slate-400">
                <span className="font-mono text-amber-400">{h.volume_id}</span>
                <span>{volumeTitle(h.volume_id)}</span>
                {h.breadcrumb.length > 0 && (
                  <span className="text-slate-500">
                    › {h.breadcrumb.join(" › ")}
                  </span>
                )}
                <span className="ml-auto text-slate-600">
                  page {h.record + 1}
                </span>
              </div>
              <p className="font-serif text-slate-200">
                {splitSnippet(h.snippet, result.markers).map((part) =>
                  part.hit ? (
                    <mark
                      key={part.key}
                      className="rounded bg-amber-500/30 px-0.5 text-amber-100"
                    >
                      {part.text}
                    </mark>
                  ) : (
                    <span key={part.key}>{part.text}</span>
                  ),
                )}
              </p>
            </Link>
          ))}
          {result.total > PAGE_SIZE && (
            <div className="flex items-center justify-end gap-2 text-sm text-slate-400">
              <button
                type="button"
                disabled={offset === 0}
                onClick={() => update({ o: Math.max(0, offset - PAGE_SIZE) })}
                className="rounded p-1 hover:bg-slate-800 disabled:opacity-30"
                aria-label="Previous results"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              Page {Math.floor(offset / PAGE_SIZE) + 1} of{" "}
              {Math.ceil(result.total / PAGE_SIZE)}
              <button
                type="button"
                disabled={offset + PAGE_SIZE >= result.total}
                onClick={() => update({ o: offset + PAGE_SIZE })}
                className="rounded p-1 hover:bg-slate-800 disabled:opacity-30"
                aria-label="Next results"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
