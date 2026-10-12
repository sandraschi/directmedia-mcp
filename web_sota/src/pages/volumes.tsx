import {
  BookOpen,
  BookOpenText,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Badge } from "@/components/ui/badge";
import { type ReaderVolume, readerVolumes } from "@/lib/api";

const PAGE_SIZE = 20;
type SortKey = "id" | "title" | "records" | "size";

function volumeNumber(id: string): number {
  const n = Number.parseInt(id.replace(/\D/g, ""), 10);
  return Number.isNaN(n) ? Number.MAX_SAFE_INTEGER : n;
}

const SORTERS: Record<SortKey, (a: ReaderVolume, b: ReaderVolume) => number> = {
  id: (a, b) =>
    a.id.localeCompare(b.id, undefined, { numeric: true }) ||
    volumeNumber(a.id) - volumeNumber(b.id),
  title: (a, b) => a.short_title.localeCompare(b.short_title, "de"),
  records: (a, b) => b.records - a.records,
  size: (a, b) => b.size_mb - a.size_mb,
};

export function IndexBadge({ state }: { state: ReaderVolume["index_state"] }) {
  const styles: Record<string, string> = {
    ready: "bg-emerald-950 text-emerald-300 border-emerald-800",
    building: "bg-amber-950 text-amber-300 border-amber-800",
    stale: "bg-amber-950 text-amber-300 border-amber-800",
    error: "bg-red-950 text-red-300 border-red-800",
    missing: "border-slate-700 text-slate-400",
  };
  const label =
    state === "ready"
      ? "searchable"
      : state === "missing"
        ? "not indexed"
        : state;
  return (
    <Badge variant="outline" className={styles[state] ?? styles.missing}>
      {label}
    </Badge>
  );
}

export function Volumes() {
  const [volumes, setVolumes] = useState<ReaderVolume[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [indexFilter, setIndexFilter] = useState("all");
  const [sort, setSort] = useState<SortKey>("id");
  const [page, setPage] = useState(1);

  useEffect(() => {
    readerVolumes()
      .then(setVolumes)
      .catch((e: unknown) =>
        setError(e instanceof Error ? e.message : "Failed to load volumes"),
      )
      .finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return volumes
      .filter(
        (v) =>
          !needle ||
          `${v.id} ${v.title} ${v.short_title}`.toLowerCase().includes(needle),
      )
      .filter(
        (v) =>
          indexFilter === "all" ||
          (indexFilter === "ready"
            ? v.index_state === "ready"
            : v.index_state !== "ready"),
      )
      .sort(SORTERS[sort]);
  }, [volumes, query, indexFilter, sort]);

  const pages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const shown = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  const reset =
    <T,>(setter: (v: T) => void) =>
    (v: T) => {
      setter(v);
      setPage(1);
    };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white">Library</h2>
        <p className="text-slate-400">
          Your Digitale Bibliothek volumes, decoded straight from the CDs
        </p>
      </div>

      <div
        className="flex flex-col gap-3 md:flex-row md:items-center"
        data-testid="volumes-controls"
      >
        <input
          data-testid="volumes-search"
          value={query}
          onChange={(e) => reset(setQuery)(e.target.value)}
          placeholder="Search volumes by number or title…"
          className="w-full md:w-80 rounded-md border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-white"
        />
        <select
          data-testid="volumes-filter"
          value={indexFilter}
          onChange={(e) => reset(setIndexFilter)(e.target.value)}
          className="rounded-md border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-white"
        >
          <option value="all">All volumes</option>
          <option value="ready">Searchable (indexed)</option>
          <option value="missing">Not indexed</option>
        </select>
        <select
          data-testid="volumes-sort"
          value={sort}
          onChange={(e) => reset(setSort)(e.target.value as SortKey)}
          className="rounded-md border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-white"
        >
          <option value="id">Sort: volume number</option>
          <option value="title">Sort: title</option>
          <option value="records">Sort: most pages</option>
          <option value="size">Sort: largest</option>
        </select>
        <span
          className="text-sm text-slate-400 md:ml-auto"
          data-testid="volumes-count"
        >
          {filtered.length} of {volumes.length} volumes
        </span>
      </div>

      {loading && <p className="text-slate-400">Loading volumes…</p>}
      {error && (
        <div className="rounded-md border border-amber-900/50 bg-amber-950/30 px-4 py-3 text-sm text-amber-200">
          {error} Set the library path in{" "}
          <Link to="/settings" className="underline">
            Settings
          </Link>
          .
        </div>
      )}

      <div className="overflow-hidden rounded-lg border border-slate-800">
        <table className="w-full text-sm">
          <thead className="bg-slate-900/80 text-left text-slate-400">
            <tr>
              <th className="px-4 py-2 font-medium">Band</th>
              <th className="px-4 py-2 font-medium">Title</th>
              <th className="hidden px-4 py-2 font-medium md:table-cell">
                Pages
              </th>
              <th className="hidden px-4 py-2 font-medium md:table-cell">
                Search
              </th>
              <th className="px-4 py-2" />
            </tr>
          </thead>
          <tbody>
            {shown.map((v) => (
              <tr
                key={v.id}
                className="border-t border-slate-800 hover:bg-slate-900/50"
                data-testid={`volume-row-${v.id}`}
              >
                <td className="px-4 py-3 font-mono text-amber-400">{v.id}</td>
                <td className="px-4 py-3">
                  <Link
                    to={`/volumes/${v.id}`}
                    className="font-medium text-white hover:text-amber-300"
                  >
                    {v.short_title}
                  </Link>
                  <div className="text-xs text-slate-400">{v.title}</div>
                </td>
                <td className="hidden px-4 py-3 text-slate-300 md:table-cell">
                  {v.records.toLocaleString("de-DE")}
                </td>
                <td className="hidden px-4 py-3 md:table-cell">
                  <IndexBadge state={v.index_state} />
                </td>
                <td className="px-4 py-3 text-right whitespace-nowrap">
                  <Link
                    to={`/volumes/${v.id}`}
                    className="mr-3 text-slate-300 hover:text-white"
                    title="Contents"
                  >
                    <BookOpen className="inline h-4 w-4" />
                  </Link>
                  <Link
                    to={`/read/${v.id}/0`}
                    className="text-amber-400 hover:text-amber-300"
                    title="Read"
                  >
                    <BookOpenText className="inline h-4 w-4" />
                  </Link>
                </td>
              </tr>
            ))}
            {!loading && shown.length === 0 && (
              <tr>
                <td
                  colSpan={5}
                  className="px-4 py-6 text-center text-slate-500"
                >
                  {volumes.length
                    ? "No volumes match your filter."
                    : "No volumes with text found."}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div
        className="flex items-center justify-end gap-2 text-sm text-slate-400"
        data-testid="volumes-pagination"
      >
        <button
          type="button"
          disabled={page <= 1}
          onClick={() => setPage(page - 1)}
          className="rounded p-1 hover:bg-slate-800 disabled:opacity-30"
          aria-label="Previous page"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
        Page {page} of {pages}
        <button
          type="button"
          disabled={page >= pages}
          onClick={() => setPage(page + 1)}
          className="rounded p-1 hover:bg-slate-800 disabled:opacity-30"
          aria-label="Next page"
        >
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
