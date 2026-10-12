import { ChevronLeft, ChevronRight, ListTree, Minus, Plus } from "lucide-react";
import { type ReactNode, useEffect, useMemo, useState } from "react";
import {
  Link,
  useNavigate,
  useParams,
  useSearchParams,
} from "react-router-dom";
import { type ReaderPage, readerPage, splitMatches } from "@/lib/api";

const FONT_KEY = "directmedia.reader_font_px";
const FONT_SIZES = [15, 17, 19, 21, 24];

function loadFontIndex(): number {
  try {
    const i = FONT_SIZES.indexOf(Number(localStorage.getItem(FONT_KEY)));
    return i >= 0 ? i : 1;
  } catch {
    return 1;
  }
}

function escapeRegExp(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/** Highlight every query word (prefix match, case-insensitive) in the page text. */
function highlight(text: string, query: string): ReactNode {
  const words = query
    .replace(/"/g, " ")
    .split(/\s+/)
    .map((w) => w.replace(/\*$/, ""))
    .filter((w) => w.length > 1);
  if (!words.length) return text;
  const re = new RegExp(`(${words.map(escapeRegExp).join("|")})`, "gi");
  return splitMatches(text, re).map((part) =>
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
  );
}

export function Reader() {
  const { volumeId = "", record = "0" } = useParams();
  const [params] = useSearchParams();
  const query = params.get("q") ?? "";
  const navigate = useNavigate();
  const [page, setPage] = useState<ReaderPage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [jump, setJump] = useState("");
  const [fontIndex, setFontIndex] = useState(loadFontIndex);
  const current = Number.parseInt(record, 10) || 0;

  useEffect(() => {
    setError(null);
    readerPage(volumeId, current)
      .then((p) => {
        setPage(p);
        setJump(String(p.record + 1));
        window.scrollTo({ top: 0 });
      })
      .catch((e: unknown) =>
        setError(e instanceof Error ? e.message : "Failed to load page"),
      );
  }, [volumeId, current]);

  const go = useMemo(
    () => (target: number | null) => {
      if (target === null) return;
      const suffix = query ? `?q=${encodeURIComponent(query)}` : "";
      navigate(`/read/${volumeId}/${target}${suffix}`);
    },
    [navigate, volumeId, query],
  );

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const tag = (e.target as HTMLElement | null)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || !page) return;
      if (e.key === "ArrowRight") go(page.next);
      if (e.key === "ArrowLeft") go(page.prev);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [page, go]);

  function changeFont(delta: number) {
    const next = Math.min(
      FONT_SIZES.length - 1,
      Math.max(0, fontIndex + delta),
    );
    setFontIndex(next);
    try {
      localStorage.setItem(FONT_KEY, String(FONT_SIZES[next]));
    } catch {
      // storage unavailable: keep the in-memory choice
    }
  }

  function submitJump(e: React.FormEvent) {
    e.preventDefault();
    const n = Number.parseInt(jump, 10);
    if (page && n >= 1 && n <= page.total) go(n - 1);
  }

  const crumbs = page?.breadcrumb ?? [];
  const printPages = page?.print_pages.length
    ? page.print_pages.length > 1
      ? `${page.print_pages[0]}–${page.print_pages[page.print_pages.length - 1]}`
      : String(page.print_pages[0])
    : null;

  const nav = page && (
    <div className="flex flex-wrap items-center justify-between gap-3 text-sm text-slate-400">
      <button
        type="button"
        onClick={() => go(page.prev)}
        disabled={page.prev === null}
        className="flex items-center gap-1 rounded-md px-3 py-1.5 hover:bg-slate-800 hover:text-white disabled:opacity-30"
        data-testid="reader-prev"
      >
        <ChevronLeft className="h-4 w-4" /> Previous
      </button>
      <form onSubmit={submitJump} className="flex items-center gap-2">
        Page
        <input
          value={jump}
          onChange={(e) => setJump(e.target.value.replace(/\D/g, ""))}
          className="w-20 rounded border border-slate-800 bg-slate-900 px-2 py-1 text-center text-white"
          aria-label="Go to page"
          data-testid="reader-jump"
        />
        of {page.total.toLocaleString("de-DE")}
        {printPages && (
          <span className="hidden text-slate-500 sm:inline">
            · print p. {printPages}
          </span>
        )}
      </form>
      <button
        type="button"
        onClick={() => go(page.next)}
        disabled={page.next === null}
        className="flex items-center gap-1 rounded-md px-3 py-1.5 hover:bg-slate-800 hover:text-white disabled:opacity-30"
        data-testid="reader-next"
      >
        Next <ChevronRight className="h-4 w-4" />
      </button>
    </div>
  );

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <div className="flex items-start justify-between gap-4">
        <nav
          className="flex flex-wrap items-center gap-1 text-sm text-slate-400"
          data-testid="reader-breadcrumb"
        >
          <Link
            to={`/volumes/${volumeId}`}
            className="flex items-center gap-1 font-mono text-amber-400 hover:text-amber-300"
          >
            <ListTree className="h-4 w-4" /> {volumeId}
          </Link>
          {crumbs.slice(1).map((c) => (
            <span key={c.index} className="flex items-center gap-1">
              <ChevronRight className="h-3 w-3 text-slate-600" />
              {c.record !== null ? (
                <Link
                  to={`/read/${volumeId}/${c.record}`}
                  className="hover:text-white"
                >
                  {c.title}
                </Link>
              ) : (
                c.title
              )}
            </span>
          ))}
        </nav>
        <div className="flex shrink-0 items-center gap-1 text-slate-400">
          <button
            type="button"
            onClick={() => changeFont(-1)}
            className="rounded p-1 hover:bg-slate-800"
            aria-label="Smaller text"
          >
            <Minus className="h-4 w-4" />
          </button>
          <button
            type="button"
            onClick={() => changeFont(1)}
            className="rounded p-1 hover:bg-slate-800"
            aria-label="Larger text"
          >
            <Plus className="h-4 w-4" />
          </button>
        </div>
      </div>

      {nav}

      {error && (
        <div className="rounded-md border border-red-900/50 bg-red-950/30 px-4 py-3 text-sm text-red-200">
          {error}
        </div>
      )}

      <article
        className="min-h-[50vh] whitespace-pre-wrap rounded-lg border border-slate-800 bg-slate-950/60 px-6 py-8 font-serif leading-relaxed text-slate-200 sm:px-10"
        style={{
          fontSize: FONT_SIZES[fontIndex],
          fontFamily: "'Iowan Old Style', 'Palatino Linotype', Georgia, serif",
        }}
        data-testid="reader-text"
      >
        {page
          ? highlight(page.text, query) || (
              <span className="text-slate-500">(empty page)</span>
            )
          : "Loading…"}
      </article>

      {nav}
      <p className="text-center text-xs text-slate-600">
        ← → keys turn pages{page?.source ? ` · source: ${page.source}` : ""}
      </p>
    </div>
  );
}
