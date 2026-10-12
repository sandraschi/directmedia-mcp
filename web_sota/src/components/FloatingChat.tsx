import {
  BookOpen,
  Download,
  Library,
  MessageSquare,
  Trash2,
  X,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  type ChatSource,
  type LlmProvider,
  llmChat,
  llmProviders,
} from "@/lib/api";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: ChatSource[];
  note?: string | null;
}

const newMessage = (m: Omit<Message, "id">): Message => ({
  ...m,
  id: crypto.randomUUID(),
});

const PERSONALITIES = [
  { id: "librarian", label: "Librarian", prompt: "" },
  {
    id: "scholar",
    label: "Scholar",
    prompt: "Answer like a literary scholar: precise, with context and dates.",
  },
  {
    id: "concise",
    label: "Concise",
    prompt: "Answer briefly, in two or three sentences.",
  },
];

const EXAMPLES = [
  "Welches Goethe-Buch handelt von unglücklicher Liebe?",
  "Wer war Kalif Vathek?",
  "Was sagt Lessing über Toleranz?",
];

const STORE = {
  chat: "fc_chat",
  model: "llm_model",
  personality: "fc_personality",
  library: "fc_use_library",
};

function load(key: string, fallback: string): string {
  try {
    return localStorage.getItem(key) ?? fallback;
  } catch {
    return fallback;
  }
}

function save(key: string, value: string | null): void {
  try {
    if (value === null) localStorage.removeItem(key);
    else localStorage.setItem(key, value);
  } catch {
    // storage unavailable: chat still works for this session
  }
}

export default function FloatingChat() {
  const [open, setOpen] = useState(false);
  const [chat, setChat] = useState<Message[]>(() => {
    try {
      const saved = JSON.parse(load(STORE.chat, "[]")) as Omit<Message, "id">[];
      return saved.map(newMessage);
    } catch {
      return [];
    }
  });
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [providers, setProviders] = useState<LlmProvider[] | null>(null);
  const [model, setModel] = useState(() => load(STORE.model, ""));
  const [personality, setPersonality] = useState(() =>
    load(STORE.personality, "librarian"),
  );
  const [useLibrary, setUseLibrary] = useState(
    () => load(STORE.library, "1") === "1",
  );
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    save(STORE.chat, chat.length ? JSON.stringify(chat.slice(-100)) : null);
  }, [chat]);

  useEffect(() => {
    if (!open || providers) return;
    llmProviders()
      .then((list) => {
        setProviders(list);
        const options = list.flatMap((p) =>
          p.models.map((m) => `${p.name}::${m}`),
        );
        if (options.length && !options.includes(model)) {
          setModel(options[0]);
          save(STORE.model, options[0]);
        }
      })
      .catch(() => setProviders([]));
  }, [open, providers, model]);

  useEffect(() => {
    if (open && chat.length >= 0)
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chat.length, open]);

  const available =
    providers?.filter((p) => p.available && p.models.length) ?? [];

  async function sendMessage(text: string) {
    const [provider, ...rest] = model.split("::");
    const modelId = rest.join("::");
    const history = chat.map(({ role, content }) => ({ role, content }));
    setChat((prev) => [...prev, newMessage({ role: "user", content: text })]);
    setLoading(true);
    try {
      const reply = await llmChat({
        provider,
        model: modelId,
        prompt: text,
        system:
          PERSONALITIES.find((p) => p.id === personality)?.prompt || undefined,
        history,
        use_library: useLibrary,
      });
      setChat((prev) => [
        ...prev,
        newMessage({
          role: "assistant",
          content: reply.response || "(empty answer)",
          sources: reply.sources,
          note: reply.note,
        }),
      ]);
    } catch (e) {
      setChat((prev) => [
        ...prev,
        newMessage({
          role: "assistant",
          content:
            e instanceof Error
              ? e.message
              : "Request failed. Is the backend running?",
        }),
      ]);
    }
    setLoading(false);
  }

  function handleSend() {
    if (!input.trim() || !model || loading) return;
    sendMessage(input.trim());
    setInput("");
  }

  function handleExport() {
    if (!chat.length) return;
    const lines = chat.map((m) => {
      const refs = m.sources
        ?.map(
          (s) => `  [${s.n}] ${s.volume_id} ${s.work} (page ${s.record + 1})`,
        )
        .join("\n");
      return `[${m.role.toUpperCase()}] ${m.content}${refs ? `\n${refs}` : ""}`;
    });
    const url = URL.createObjectURL(
      new Blob([lines.join("\n\n")], { type: "text/plain" }),
    );
    const a = document.createElement("a");
    a.href = url;
    a.download = "digibib-chat.txt";
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    // bottom-24 keeps the button clear of the reader's bottom page navigation
    <div className="fixed bottom-24 right-5 z-50" data-testid="floating-chat">
      {open ? (
        <div className="flex h-[560px] max-h-[calc(100vh-8rem)] w-[400px] max-w-[calc(100vw-2.5rem)] flex-col overflow-hidden rounded-2xl border border-slate-700 bg-slate-900 shadow-2xl animate-in fade-in zoom-in-95 duration-200">
          <div className="flex items-center justify-between gap-2 border-b border-slate-700 px-3 py-2">
            <span className="text-sm font-semibold text-slate-200">
              Ask the library
            </span>
            <div className="flex items-center gap-1.5">
              <select
                className="max-w-[90px] rounded border border-slate-600 bg-slate-800 px-1.5 py-1 text-[11px] text-slate-300"
                value={personality}
                onChange={(e) => {
                  setPersonality(e.target.value);
                  save(STORE.personality, e.target.value);
                }}
                aria-label="Answer style"
              >
                {PERSONALITIES.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.label}
                  </option>
                ))}
              </select>
              {available.length > 0 && (
                <select
                  className="max-w-[150px] rounded border border-slate-600 bg-slate-800 px-1.5 py-1 text-[11px] text-slate-300"
                  value={model}
                  onChange={(e) => {
                    setModel(e.target.value);
                    save(STORE.model, e.target.value);
                  }}
                  aria-label="Model"
                  data-testid="floating-chat-model"
                >
                  {available.map((p) => (
                    <optgroup key={p.name} label={p.name}>
                      {p.models.map((m) => (
                        <option
                          key={`${p.name}::${m}`}
                          value={`${p.name}::${m}`}
                        >
                          {m}
                        </option>
                      ))}
                    </optgroup>
                  ))}
                </select>
              )}
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="text-slate-500 hover:text-slate-300"
                aria-label="Close chat"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>

          <div className="flex-1 space-y-2 overflow-y-auto p-3 text-sm">
            {providers && available.length === 0 && (
              <p className="rounded-md border border-amber-900/50 bg-amber-950/30 p-2 text-xs text-amber-200">
                No local LLM found. Start LM Studio (port 1234) or Ollama (port
                11434), then reopen the chat.
              </p>
            )}
            {chat.length === 0 && (
              <div className="pt-4 text-center">
                <p className="mb-3 text-xs text-slate-500">
                  Questions are answered from passages of your indexed volumes
                  (semantic index), with sources.
                </p>
                <div
                  className="flex flex-wrap justify-center gap-1.5"
                  data-testid="example-prompts"
                >
                  {EXAMPLES.map((ex) => (
                    <button
                      type="button"
                      key={ex}
                      onClick={() => setInput(ex)}
                      className="rounded-full border border-slate-700 bg-slate-800 px-2 py-1 text-[11px] text-slate-400 transition-colors hover:bg-slate-700 hover:text-slate-200"
                    >
                      {ex}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {chat.map((msg) => (
              <div
                key={msg.id}
                className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[88%] whitespace-pre-wrap rounded-xl px-3 py-2 ${
                    msg.role === "user"
                      ? "bg-amber-800/80 text-amber-50"
                      : "bg-slate-800 text-slate-200"
                  }`}
                >
                  {msg.content}
                  {msg.note && (
                    <p className="mt-2 text-[11px] text-amber-300">
                      {msg.note}
                    </p>
                  )}
                  {msg.sources && msg.sources.length > 0 && (
                    <ol className="mt-2 space-y-1 border-t border-slate-700 pt-2 text-[11px]">
                      {msg.sources.map((s) => (
                        <li key={s.n}>
                          <Link
                            to={`/read/${s.volume_id}/${s.record}`}
                            className="flex gap-1 text-slate-400 hover:text-amber-300"
                            title={s.snippet}
                          >
                            <span className="text-amber-400">[{s.n}]</span>
                            <BookOpen className="mt-0.5 h-3 w-3 shrink-0" />
                            <span>
                              {s.volume_id} {s.work || "page"} · p.{" "}
                              {s.record + 1}
                            </span>
                          </Link>
                        </li>
                      ))}
                    </ol>
                  )}
                </div>
              </div>
            ))}
            {loading && (
              <div className="animate-pulse text-xs text-slate-500">
                Searching the library and thinking…
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          <div className="flex flex-col gap-2 border-t border-slate-700 p-3">
            <div className="flex gap-2">
              <input
                className="flex-1 rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-sm text-slate-200 focus:border-amber-500 focus:outline-none"
                placeholder="Ask about your books…"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSend()}
                data-testid="floating-chat-input"
              />
              <button
                type="button"
                onClick={handleSend}
                disabled={loading || !input.trim() || !model}
                className="rounded-lg bg-amber-700 px-3 py-2 text-sm font-medium text-white hover:bg-amber-600 disabled:bg-slate-700"
                data-testid="floating-chat-send"
              >
                Ask
              </button>
            </div>
            <div className="flex items-center justify-between">
              <label className="flex items-center gap-1.5 text-[11px] text-slate-400">
                <input
                  type="checkbox"
                  checked={useLibrary}
                  onChange={(e) => {
                    setUseLibrary(e.target.checked);
                    save(STORE.library, e.target.checked ? "1" : "0");
                  }}
                  data-testid="floating-chat-library"
                />
                <Library className="h-3 w-3" /> Answer from my library
              </label>
              <div className="flex gap-1">
                <button
                  type="button"
                  onClick={handleExport}
                  disabled={!chat.length}
                  className="rounded p-1 text-slate-500 hover:text-slate-300 disabled:text-slate-700"
                  title="Export chat"
                >
                  <Download className="h-3.5 w-3.5" />
                </button>
                <button
                  type="button"
                  onClick={() => setChat([])}
                  disabled={!chat.length}
                  className="rounded p-1 text-slate-500 hover:text-slate-300 disabled:text-slate-700"
                  title="Clear chat"
                  data-testid="floating-chat-clear"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="flex h-12 w-12 items-center justify-center rounded-full bg-amber-700 text-white shadow-xl transition-colors hover:bg-amber-600"
          title="Ask the library"
          data-testid="floating-chat-open"
        >
          <MessageSquare className="h-5 w-5" />
        </button>
      )}
    </div>
  );
}
