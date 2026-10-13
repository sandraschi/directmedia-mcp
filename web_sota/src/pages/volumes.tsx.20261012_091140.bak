import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { BookOpen, FileText, Image, Music } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { listVolumes, type VolumeRow } from "@/lib/api";

export function Volumes() {
  const [volumes, setVolumes] = useState<VolumeRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const rows = await listVolumes();
        if (Array.isArray(rows) && rows[0]?.error) {
          setError(rows[0].error);
          setVolumes([]);
        } else {
          setVolumes(rows.filter((v) => !v.error));
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load volumes");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const needle = filter.trim().toLowerCase();
  const filtered = volumes.filter(
    (v) =>
      !needle ||
      v.id.toLowerCase().includes(needle) ||
      v.title.toLowerCase().includes(needle) ||
      v.short_title.toLowerCase().includes(needle),
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">Volumes</h2>
          <p className="text-slate-400">Directmedia bands (DBxxx) in your Digitale Bibliothek</p>
        </div>
        <input
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="Filter by ID or title…"
          className="w-full sm:w-72 rounded-md border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-white"
        />
      </div>

      {loading && <p className="text-slate-400">Loading volumes…</p>}
      {error && (
        <div className="rounded-md border border-amber-900/50 bg-amber-950/30 px-4 py-3 text-sm text-amber-200">
          {error}. Set the library path in <Link to="/settings" className="underline">Settings</Link>.
        </div>
      )}

      <div className="grid gap-3">
        {filtered.map((vol) => (
          <Card key={vol.id} className="border-slate-800 bg-slate-950/50">
            <CardHeader className="pb-2">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <CardTitle className="text-base text-white flex items-center gap-2">
                    <BookOpen className="h-4 w-4 text-amber-500" />
                    {vol.id}
                    <span className="font-normal text-slate-400">· {vol.short_title}</span>
                  </CardTitle>
                  <p className="mt-1 text-sm text-slate-300">{vol.title}</p>
                </div>
                <Link
                  to={`/volumes/${vol.id}`}
                  className="text-sm text-amber-400 hover:text-amber-300 whitespace-nowrap"
                >
                  Open →
                </Link>
              </div>
            </CardHeader>
            <CardContent className="flex flex-wrap items-center gap-2 text-xs">
              <Badge variant="outline" className="border-slate-700 text-slate-300">
                {vol.size_mb.toFixed(1)} MB
              </Badge>
              {vol.has_text && (
                <Badge className="bg-emerald-950 text-emerald-300 border-emerald-800">
                  <FileText className="mr-1 h-3 w-3" /> text
                </Badge>
              )}
              {vol.has_images && (
                <Badge className="bg-slate-800 text-slate-200">
                  <Image className="mr-1 h-3 w-3" /> images
                </Badge>
              )}
              {vol.has_audio && (
                <Badge className="bg-slate-800 text-slate-200">
                  <Music className="mr-1 h-3 w-3" /> audio
                </Badge>
              )}
            </CardContent>
          </Card>
        ))}
        {!loading && !error && filtered.length === 0 && (
          <p className="text-slate-500">No volumes match your filter.</p>
        )}
      </div>
    </div>
  );
}
