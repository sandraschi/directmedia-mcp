import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  convertVolumeToEpub,
  getNavigationTree,
  getTextContent,
  getVolumeInfo,
  getStoredEpubOutputDir,
  type VolumeRow,
} from "@/lib/api";

export function VolumeDetail() {
  const { volumeId = "" } = useParams();
  const [info, setInfo] = useState<VolumeRow | null>(null);
  const [text, setText] = useState("");
  const [nav, setNav] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [exportMsg, setExportMsg] = useState<string | null>(null);

  useEffect(() => {
    if (!volumeId) return;
    (async () => {
      try {
        const meta = await getVolumeInfo(volumeId);
        if (meta.error) {
          setError(meta.error);
          return;
        }
        setInfo(meta);
        const content = await getTextContent(volumeId, 0, 6000);
        if (content.error) {
          setText(content.error);
        } else {
          setText(content.content ?? "(no text returned)");
        }
        const tree = await getNavigationTree(volumeId);
        setNav(JSON.stringify(tree, null, 2));
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load volume");
      }
    })();
  }, [volumeId]);

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
          : (result.message as string) || (result.error as string) || "Conversion failed",
      );
    } catch (e) {
      setExportMsg(e instanceof Error ? e.message : "Conversion failed");
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Link to="/volumes" className="text-sm text-slate-400 hover:text-white">
          ← Volumes
        </Link>
        <h2 className="text-2xl font-bold text-white">{volumeId}</h2>
      </div>

      {error && (
        <div className="rounded-md border border-red-900/50 bg-red-950/30 px-4 py-3 text-sm text-red-200">
          {error}
        </div>
      )}

      {info && (
        <Card className="border-slate-800 bg-slate-950/50">
          <CardHeader>
            <CardTitle className="text-white">{info.title}</CardTitle>
            <p className="text-sm text-slate-400 font-mono">{info.path}</p>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            <Button size="sm" className="bg-amber-700 hover:bg-amber-600" onClick={handleEpubExport}>
              Export EPUB
            </Button>
            {exportMsg && <span className="text-sm text-slate-400 self-center">{exportMsg}</span>}
          </CardContent>
        </Card>
      )}

      <Card className="border-slate-800 bg-slate-950/50">
        <CardHeader>
          <CardTitle className="text-white">Text preview</CardTitle>
        </CardHeader>
        <CardContent>
          <pre className="max-h-96 overflow-auto whitespace-pre-wrap font-mono text-xs text-slate-300 bg-slate-900/60 p-4 rounded-md border border-slate-800">
            {text || "Loading…"}
          </pre>
        </CardContent>
      </Card>

      <Card className="border-slate-800 bg-slate-950/50">
        <CardHeader>
          <CardTitle className="text-white">Navigation tree</CardTitle>
        </CardHeader>
        <CardContent>
          <pre className="max-h-64 overflow-auto font-mono text-xs text-slate-400 bg-slate-900/60 p-4 rounded-md border border-slate-800">
            {nav || "Loading…"}
          </pre>
        </CardContent>
      </Card>
    </div>
  );
}
