import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  fetchStatus,
  setLibraryPath,
  getStoredLibraryPath,
  setStoredLibraryPath,
  getStoredEpubOutputDir,
  setStoredEpubOutputDir,
} from "@/lib/api";

export function Settings() {
  const [libraryPath, setPath] = useState("");
  const [epubDir, setEpubDir] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [initialized, setInitialized] = useState(false);

  useEffect(() => {
    setPath(getStoredLibraryPath());
    setEpubDir(getStoredEpubOutputDir());
    fetchStatus()
      .then((s) => setInitialized(s.library_initialized))
      .catch(() => setInitialized(false));
  }, []);

  async function saveLibrary() {
    setMessage(null);
    setStoredLibraryPath(libraryPath);
    try {
      const result = await setLibraryPath(libraryPath);
      if (result.error) {
        setMessage(result.error);
      } else {
        setMessage(result.message ?? `Library ready (${result.volumes_found ?? "?"} volumes)`);
        setInitialized(true);
      }
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Failed to set library path");
    }
  }

  function saveEpubDir() {
    setStoredEpubOutputDir(epubDir);
    setMessage("EPUB output folder saved locally.");
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white">Settings</h2>
        <p className="text-slate-400">Configure the Digitale Bibliothek root and EPUB export folder</p>
      </div>

      {message && (
        <div className="rounded-md border border-slate-700 bg-slate-900/80 px-4 py-3 text-sm text-slate-200">
          {message}
        </div>
      )}

      <Card className="border-slate-800 bg-slate-950/50">
        <CardHeader>
          <CardTitle className="text-white">Digitale Bibliothek path</CardTitle>
          <CardDescription className="text-slate-400">
            Folder containing DB001, DB002, … volume directories. Calls MCP tool{" "}
            <code className="text-amber-300">set_library_path</code>.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-2">
            <Label className="text-slate-300">Library root</Label>
            <Input
              value={libraryPath}
              onChange={(e) => setPath(e.target.value)}
              placeholder="D:\Media\Digitale Bibliothek"
              className="bg-slate-900 border-slate-800 text-slate-100 font-mono text-sm"
            />
          </div>
          <p className="text-xs text-slate-500">
            Status: {initialized ? "library initialized on server" : "not initialized — set path and save"}
          </p>
          <Button onClick={saveLibrary} className="bg-amber-700 hover:bg-amber-600">
            Save &amp; initialize library
          </Button>
        </CardContent>
      </Card>

      <Card className="border-slate-800 bg-slate-950/50">
        <CardHeader>
          <CardTitle className="text-white">EPUB export</CardTitle>
          <CardDescription className="text-slate-400">
            Default output directory for <code className="text-amber-300">convert_volume_to_epub_file</code>
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-2">
            <Label className="text-slate-300">Output folder</Label>
            <Input
              value={epubDir}
              onChange={(e) => setEpubDir(e.target.value)}
              placeholder="D:\Exports\directmedia-epub"
              className="bg-slate-900 border-slate-800 text-slate-100 font-mono text-sm"
            />
          </div>
          <Button variant="outline" className="border-slate-700 text-slate-200" onClick={saveEpubDir}>
            Save output folder
          </Button>
        </CardContent>
      </Card>

      <Card className="border-slate-800 bg-slate-950/50">
        <CardHeader>
          <CardTitle className="text-white">MCP tools</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="grid gap-1 text-sm font-mono text-slate-400 sm:grid-cols-2">
            {[
              "set_library_path",
              "list_volumes",
              "get_volume_info",
              "search_text",
              "get_text_content",
              "get_navigation_tree",
              "analyze_volume_structure",
              "convert_volume_to_epub_file",
              "batch_convert_to_epub",
            ].map((tool) => (
              <li key={tool}>{tool}</li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
