import { useState } from "react";
import { Link } from "react-router-dom";
import { Search as SearchIcon } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { searchText, type SearchHit } from "@/lib/api";

export function Search() {
  const [query, setQuery] = useState("");
  const [volumeId, setVolumeId] = useState("");
  const [hits, setHits] = useState<SearchHit[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function runSearch() {
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const results = await searchText(query.trim(), volumeId.trim() || undefined, 30);
      if (Array.isArray(results) && (results[0] as SearchHit & { error?: string })?.error) {
        setError((results[0] as SearchHit & { error?: string }).error ?? "Search failed");
        setHits([]);
      } else {
        setHits(results);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Search failed");
      setHits([]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white">Full-text search</h2>
        <p className="text-slate-400">Query decompressed Directmedia text databases across volumes</p>
      </div>

      <Card className="border-slate-800 bg-slate-950/50">
        <CardHeader>
          <CardTitle className="text-white">Search</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid gap-3 sm:grid-cols-[1fr_160px_auto]">
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search terms (German literature, author, topic…)"
              className="bg-slate-900 border-slate-800 text-white"
              onKeyDown={(e) => e.key === "Enter" && runSearch()}
            />
            <Input
              value={volumeId}
              onChange={(e) => setVolumeId(e.target.value)}
              placeholder="DB002 (optional)"
              className="bg-slate-900 border-slate-800 text-white font-mono"
            />
            <Button onClick={runSearch} disabled={loading} className="bg-amber-700 hover:bg-amber-600">
              <SearchIcon className="mr-2 h-4 w-4" />
              {loading ? "Searching…" : "Search"}
            </Button>
          </div>
          {error && <p className="text-sm text-amber-300">{error}</p>}
        </CardContent>
      </Card>

      <div className="space-y-3">
        {hits.map((hit, idx) => (
          <Card key={`${hit.volume_id}-${hit.position}-${idx}`} className="border-slate-800 bg-slate-950/50">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between gap-2">
                <CardTitle className="text-sm text-white">
                  <Link to={`/volumes/${hit.volume_id}`} className="text-amber-400 hover:underline">
                    {hit.volume_id}
                  </Link>
                  <span className="text-slate-400 font-normal"> · {hit.title}</span>
                </CardTitle>
                <span className="text-xs text-slate-500 font-mono">pos {hit.position}</span>
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-slate-300 leading-relaxed">{hit.content_preview}</p>
            </CardContent>
          </Card>
        ))}
        {!loading && hits.length === 0 && query && !error && (
          <p className="text-slate-500">No matches. Try a broader query or check library path in Settings.</p>
        )}
      </div>
    </div>
  );
}
