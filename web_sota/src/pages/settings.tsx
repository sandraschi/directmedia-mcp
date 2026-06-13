import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  fetchStatus,
  formatFetchError,
  setLibraryPath,
  getStoredLibraryPath,
  setStoredLibraryPath,
  getStoredEpubOutputDir,
  setStoredEpubOutputDir,
} from "@/lib/api";

function LLMSettings() {
    const [providers, setProviders] = useState<Record<string, {name:string}[]>>({});
    const [selectedProvider, setSelectedProvider] = useState("ollama");
    const [selectedModel, setSelectedModel] = useState("");
    const [status, setStatus] = useState<"loading"|"ready"|"error">("loading");
    useEffect(() => {
        fetch("/api/llm/providers").then(r => r.json()).then(d => {
            setProviders(d);
            const savedP = localStorage.getItem("llm_provider") || "ollama";
            const savedM = localStorage.getItem("llm_model") || "";
            setSelectedProvider(savedP);
            const models = d[savedP === "ollama" ? "ollama" : "lm_studio"] || [];
            setSelectedModel(savedM && models.some((m:{name:string}) => m.name === savedM) ? savedM : (models[0]?.name || ""));
            setStatus(models.length > 0 ? "ready" : "error");
        }).catch(() => {
            setProviders({ ollama: [{name:"llama3.2:3b"}] });
            setSelectedModel(localStorage.getItem("llm_model") || "llama3.2:3b");
            setStatus("ready");
        });
    }, []);
    const save = (p:string, m:string) => { localStorage.setItem("llm_provider", p); localStorage.setItem("llm_model", m); };
    const models = providers[selectedProvider === "ollama" ? "ollama" : "lm_studio"] || [];
    return (
        <Card className="border-slate-800 bg-slate-950/50">
            <CardHeader>
                <CardTitle className="text-white">Local LLM</CardTitle>
                <CardDescription className="text-slate-400">Select provider and model for AI features</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
                <select className="h-9 w-full rounded-md border border-slate-700 bg-slate-900 px-3 text-sm text-slate-200"
                    value={selectedProvider} onChange={(e) => { setSelectedProvider(e.target.value); save(e.target.value, ""); }}>
                    <option value="ollama">Ollama</option>
                    <option value="lm_studio">LM Studio</option>
                </select>
                <select className="h-9 w-full rounded-md border border-slate-700 bg-slate-900 px-3 text-sm text-slate-200"
                    value={selectedModel} onChange={(e) => { setSelectedModel(e.target.value); save(selectedProvider, e.target.value); }}>
                    {models.map((m) => <option key={m.name} value={m.name}>{m.name}</option>)}
                </select>
            </CardContent>
        </Card>
    );
}

export function Settings() {
  const [libraryPath, setPath] = useState("");
  const [epubDir, setEpubDir] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [initialized, setInitialized] = useState(false);
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);

  useEffect(() => {
    const stored = getStoredLibraryPath();
    setPath(stored);
    setEpubDir(getStoredEpubOutputDir());
    fetchStatus()
      .then(async (s) => {
        setBackendOnline(true);
        setInitialized(s.library_initialized);
        if (!s.library_initialized && stored.trim()) {
          setMessage("Restoring library path on server …");
          try {
            const result = await setLibraryPath(stored);
            if (result.error) {
              setMessage(result.error);
            } else {
              setMessage(result.message ?? `Library ready (${result.volumes_found ?? "?"} volumes)`);
              setInitialized(true);
            }
          } catch (e) {
            setMessage(formatFetchError(e));
          }
        }
      })
      .catch(() => {
        setBackendOnline(false);
        setInitialized(false);
        if (stored.trim()) {
          setMessage("Backend offline — run start.bat from directmedia-mcp, then click Save again.");
        }
      });
  }, []);

  async function saveLibrary() {
    setMessage(null);
    const trimmed = libraryPath.trim();
    if (!trimmed) {
      setMessage("Enter the folder that contains DB001, DB002, …");
      return;
    }
    setPath(trimmed);
    setStoredLibraryPath(trimmed);
    try {
      const result = await setLibraryPath(trimmed);
      if (result.error) {
        setMessage(result.error);
      } else {
        setMessage(result.message ?? `Library ready (${result.volumes_found ?? "?"} volumes)`);
        setInitialized(true);
      }
    } catch (e) {
      setMessage(formatFetchError(e));
      setBackendOnline(false);
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
            Backend:{" "}
            {backendOnline === null
              ? "checking…"
              : backendOnline
                ? "online (port 10827)"
                : "offline — run start.bat"}
            {" · "}
            Library:{" "}
            {initialized ? "initialized on server" : "not initialized — set path and save"}
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

      <LLMSettings />

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
