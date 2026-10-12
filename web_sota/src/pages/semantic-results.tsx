import { BookMarked } from "lucide-react";
import { Link } from "react-router-dom";
import type { SemanticResult } from "@/lib/api";

/** Works that match a meaning-based query, then the closest passages. */
export function SemanticResults({
  result,
  volumeTitle,
}: {
  result: SemanticResult;
  volumeTitle: (id: string) => string;
}) {
  if (!result.hits.length) {
    return (
      <p className="text-sm text-slate-400">
        No passages found. Build a semantic index for more volumes.
      </p>
    );
  }
  return (
    <div className="space-y-6" data-testid="semantic-results">
      <section>
        <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-400">
          Works that match
        </h3>
        <div className="grid gap-2 md:grid-cols-2">
          {result.works.slice(0, 6).map((w) => (
            <Link
              key={`${w.volume_id}-${w.work}`}
              to={`/read/${w.volume_id}/${w.record}`}
              className="flex items-start gap-2 rounded-lg border border-slate-800 bg-slate-950/50 px-3 py-2 hover:border-amber-800"
            >
              <BookMarked className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" />
              <div>
                <div className="text-sm text-white">
                  {w.work.split(" > ").slice(-1)[0] || volumeTitle(w.volume_id)}
                </div>
                <div className="text-xs text-slate-500">
                  {w.volume_id} {volumeTitle(w.volume_id)}
                  {w.work.includes(" > ") &&
                    ` › ${w.work.split(" > ").slice(0, -1).join(" › ")}`}{" "}
                  · {w.hits} passage{w.hits > 1 ? "s" : ""}
                </div>
              </div>
            </Link>
          ))}
        </div>
      </section>

      <section className="space-y-3">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-400">
          Closest passages
        </h3>
        {result.hits.map((h) => (
          <Link
            key={`${h.volume_id}-${h.record}-${h.text.slice(0, 24)}`}
            to={`/read/${h.volume_id}/${h.record}`}
            className="block rounded-lg border border-slate-800 bg-slate-950/50 px-4 py-3 hover:border-amber-800"
          >
            <div className="mb-1 flex flex-wrap items-center gap-2 text-xs text-slate-400">
              <span className="font-mono text-amber-400">{h.volume_id}</span>
              <span>{volumeTitle(h.volume_id)}</span>
              {h.work && (
                <span className="text-slate-500">
                  › {h.work.replaceAll(" > ", " › ")}
                </span>
              )}
              <span className="ml-auto text-slate-600">
                page {h.record + 1} · {Math.round(h.score * 100)}%
              </span>
            </div>
            <p className="line-clamp-4 font-serif text-slate-200">{h.text}</p>
          </Link>
        ))}
        <p className="text-xs text-slate-600">
          Embedding model: {result.model}
        </p>
      </section>
    </div>
  );
}
