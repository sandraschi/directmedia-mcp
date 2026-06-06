import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { BookOpen, Database, FileText, Image, Music, Server } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { fetchStatus, listVolumes, type ServerStatus, type VolumeRow } from "@/lib/api";

export function Dashboard() {
  const [status, setStatus] = useState<ServerStatus | null>(null);
  const [volumes, setVolumes] = useState<VolumeRow[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const s = await fetchStatus();
        if (!active) return;
        setStatus(s);
        if (s.library_initialized) {
          const rows = await listVolumes();
          if (!active) return;
          if (Array.isArray(rows) && rows[0]?.error) {
            setError(rows[0].error);
          } else {
            setVolumes(rows.filter((v) => !v.error));
          }
        }
      } catch (e) {
        if (active) setError(e instanceof Error ? e.message : "Failed to load status");
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const withText = volumes.filter((v) => v.has_text).length;
  const withImages = volumes.filter((v) => v.has_images).length;
  const withAudio = volumes.filter((v) => v.has_audio).length;
  const totalMb = volumes.reduce((sum, v) => sum + (v.size_mb || 0), 0);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-white">Digitale Bibliothek</h2>
        <p className="text-slate-400">
          Browse, search, and export Directmedia Publishing CD-ROM volumes (DBxxx bands).
        </p>
      </div>

      {error && (
        <div className="rounded-md border border-amber-900/50 bg-amber-950/30 px-4 py-3 text-sm text-amber-200">
          {error}
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card className="border-slate-800 bg-slate-950/50">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-slate-200">MCP Server</CardTitle>
            <Server className="h-4 w-4 text-amber-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-white">{status?.status === "healthy" ? "Online" : "—"}</div>
            <p className="text-xs text-slate-400">HTTP :10827 · MCP /mcp</p>
          </CardContent>
        </Card>

        <Card className="border-slate-800 bg-slate-950/50">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-slate-200">Volumes</CardTitle>
            <BookOpen className="h-4 w-4 text-amber-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-white">{status?.volume_count ?? 0}</div>
            <p className="text-xs text-slate-400">
              {status?.library_initialized ? "DB folders indexed" : "Library not configured"}
            </p>
          </CardContent>
        </Card>

        <Card className="border-slate-800 bg-slate-950/50">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-slate-200">Text bands</CardTitle>
            <FileText className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-white">{withText}</div>
            <p className="text-xs text-slate-400">Volumes with TEXT.DKI / extracted text</p>
          </CardContent>
        </Card>

        <Card className="border-slate-800 bg-slate-950/50">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-slate-200">Archive size</CardTitle>
            <Database className="h-4 w-4 text-slate-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-white">{totalMb > 0 ? `${totalMb.toFixed(0)} MB` : "—"}</div>
            <p className="text-xs text-slate-400">Sum of on-disk volume folders</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="border-slate-800 bg-slate-950/50">
          <CardHeader>
            <CardTitle className="text-white">Library path</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-slate-300">
            {status?.library_initialized ? (
              <p className="font-mono text-xs break-all text-amber-100/90">{status.library_path}</p>
            ) : (
              <p className="text-slate-400">
                Point the server at your Digitale Bibliothek root (folder containing DB001, DB002, …).
              </p>
            )}
            <Button asChild variant="outline" className="border-slate-700 text-slate-200">
              <Link to="/settings">Configure library</Link>
            </Button>
          </CardContent>
        </Card>

        <Card className="border-slate-800 bg-slate-950/50">
          <CardHeader>
            <CardTitle className="text-white">Media coverage</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div className="flex items-center gap-2 text-slate-300">
              <Image className="h-4 w-4 text-slate-500" />
              <span>{withImages} volumes with images</span>
            </div>
            <div className="flex items-center gap-2 text-slate-300">
              <Music className="h-4 w-4 text-slate-500" />
              <span>{withAudio} volumes with audio</span>
            </div>
            <div className="flex gap-2 pt-1">
              <Button asChild size="sm" className="bg-amber-700 hover:bg-amber-600">
                <Link to="/volumes">Browse volumes</Link>
              </Button>
              <Button asChild size="sm" variant="outline" className="border-slate-700">
                <Link to="/search">Search text</Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
