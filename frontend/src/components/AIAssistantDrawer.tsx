"use client";

import React, { useState } from "react";
import { apiFetch } from "@/lib/api";
import { X, Sparkles, Send, Bot, Database, AlertTriangle } from "lucide-react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

/** GitHub-flavoured Markdown (tables, lists, headings). Raw HTML is not rendered, so model output is XSS-safe. */
const MD_COMPONENTS: Components = {
  h1: ({ children }) => <h3 className="text-[13px] font-bold text-slate-900 mt-3 mb-1.5">{children}</h3>,
  h2: ({ children }) => <h3 className="text-[13px] font-bold text-slate-900 mt-3 mb-1.5">{children}</h3>,
  h3: ({ children }) => <h4 className="text-[12.5px] font-bold text-slate-900 mt-3 mb-1.5">{children}</h4>,
  h4: ({ children }) => <h4 className="text-xs font-semibold text-slate-800 mt-2 mb-1">{children}</h4>,
  p: ({ children }) => <p className="my-1.5 leading-relaxed">{children}</p>,
  ul: ({ children }) => <ul className="my-1.5 pl-4 list-disc space-y-1 marker:text-indigo-400">{children}</ul>,
  ol: ({ children }) => <ol className="my-1.5 pl-4 list-decimal space-y-1 marker:text-indigo-500 marker:font-semibold">{children}</ol>,
  li: ({ children }) => <li className="leading-relaxed pl-0.5">{children}</li>,
  strong: ({ children }) => <strong className="font-semibold text-slate-900">{children}</strong>,
  em: ({ children }) => <em className="text-slate-500">{children}</em>,
  code: ({ children }) => <code className="px-1 py-0.5 rounded bg-slate-200/70 text-[10.5px] font-mono">{children}</code>,
  a: ({ children }) => <span className="text-indigo-600 font-medium">{children}</span>,
  table: ({ children }) => (
    <div className="my-2 overflow-x-auto rounded-lg border border-slate-200 bg-white">
      <table className="w-full text-[11px] border-collapse">{children}</table>
    </div>
  ),
  thead: ({ children }) => <thead className="bg-slate-50 text-slate-600">{children}</thead>,
  th: ({ children }) => <th className="px-2.5 py-1.5 text-left font-semibold border-b border-slate-200 whitespace-nowrap">{children}</th>,
  td: ({ children }) => <td className="px-2.5 py-1.5 border-b border-slate-100 align-top">{children}</td>,
  hr: () => <hr className="my-3 border-slate-200" />,
};

const MarkdownText: React.FC<{ text: string }> = ({ text }) => (
  <div className="text-[12px] text-slate-700">
    <ReactMarkdown remarkPlugins={[remarkGfm]} components={MD_COMPONENTS}>
      {text}
    </ReactMarkdown>
  </div>
);

interface SourceRef {
  type: string;
  id: string | null;
  label: string;
}

interface AIAssistantDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  /** Opens the dashboard view that holds a cited record (e.g. "projects", "employees"). */
  onNavigate?: (view: string) => void;
}

const SOURCE_VIEW: Record<string, string> = { project: "projects", employee: "employees", task: "tasks" };

interface ChatMessage {
  id: string;
  sender: "user" | "ai";
  text: string;
  sources?: SourceRef[];
  meta?: string;
  isError?: boolean;
  timestamp: string;
}

export const AIAssistantDrawer: React.FC<AIAssistantDrawerProps> = ({ isOpen, onClose, onNavigate }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "m1",
      sender: "ai",
      text: "Hello! I'm your Project Manager assistant. I answer from your live project data — ask me about projects, people, deadlines or risks. How can I help today?",
      timestamp: "Just now"
    }
  ]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);

  const handleSend = async (textToSend?: string) => {
    const query = textToSend || input;
    if (!query.trim()) return;

    const userMsg: ChatMessage = {
      id: `u-${Date.now()}`,
      sender: "user",
      text: query,
      timestamp: "Just now"
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsTyping(true);

    try {
      const history = messages.slice(-4).map((m) => ({
        role: m.sender === "user" ? "user" : "assistant",
        content: m.text
      }));

      const res = await apiFetch(`${API_BASE_URL}/ai/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt: query,
          history
        })
      });

      if (res.ok) {
        const data = await res.json();
        const aiMsg: ChatMessage = {
          id: `ai-${Date.now()}`,
          sender: "ai",
          text: data.response || "No response received.",
          sources: data.sources || [],
          meta:
            data.mode === "deterministic"
              ? `From live project data · as of ${data.as_of}`
              : data.mode === "tools_explained"
              ? `From live project data · as of ${data.as_of}`
              : data.mode === "llm_grounded"
              ? `Summary of live project data · as of ${data.as_of}`
              : `Key figures only (summary temporarily unavailable) · as of ${data.as_of}`,
          timestamp: new Date().toLocaleTimeString()
        };
        setMessages((prev) => [...prev, aiMsg]);
      } else {
        throw new Error("Backend AI endpoint error");
      }
    } catch {
      const fallbackMsg: ChatMessage = {
        id: `ai-${Date.now()}`,
        sender: "ai",
        text: "The assistant is unavailable right now. Please try again in a moment.",
        isError: true,
        timestamp: new Date().toLocaleTimeString()
      };
      setMessages((prev) => [...prev, fallbackMsg]);
    } finally {
      setIsTyping(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden flex justify-end bg-slate-900/40 backdrop-blur-xs transition-opacity animate-in fade-in" role="dialog" aria-modal="true" aria-label="AI Assistant">
      <div className="w-full max-w-2xl bg-white h-[100dvh] shadow-2xl flex flex-col sm:border-l border-slate-200 pt-[env(safe-area-inset-top)]">
        {/* Header */}
        <div className="p-4 border-b border-slate-200 flex items-center justify-between bg-slate-50/80">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-purple-600 text-white flex items-center justify-center shadow-md shadow-purple-600/20">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-semibold text-slate-900 text-sm flex items-center gap-1.5">
                AI Assistant
              </h3>
              <p className="text-[11px] text-slate-500">Answers from your live project data</p>
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close assistant"
            className="p-2.5 sm:p-1.5 rounded-lg text-slate-500 hover:text-slate-700 hover:bg-slate-200/60"
          >
            <X className="w-5 h-5 sm:w-4 sm:h-4" />
          </button>
        </div>

        {/* Messages */}
        <div className="flex-1 p-3 sm:p-4 overflow-y-auto overscroll-contain space-y-4 text-[13px] sm:text-xs">
          {messages.map((m) => (
            <div
              key={m.id}
              className={`flex gap-2.5 ${m.sender === "user" ? "justify-end" : "justify-start"}`}
            >
              {m.sender === "ai" && (
                <div className="w-7 h-7 rounded-lg bg-purple-100 text-purple-700 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <Bot className="w-4 h-4" />
                </div>
              )}
              <div
                className={`max-w-[88%] sm:max-w-[85%] min-w-0 break-words rounded-2xl p-3 shadow-2xs ${
                  m.sender === "user"
                    ? "bg-indigo-600 text-white rounded-br-xs"
                    : "bg-slate-50 border border-slate-200/70 text-slate-800 rounded-bl-xs"
                }`}
              >
                {m.sender === "user" ? (
                  <p className="whitespace-pre-line leading-relaxed">{m.text}</p>
                ) : (
                  <div className={m.isError ? "text-red-700 flex gap-1.5" : ""}>
                    {m.isError && <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />}
                    <MarkdownText text={m.text} />
                  </div>
                )}
                {(m.meta || (m.sources && m.sources.length > 0)) && (
                  <div className="mt-3 pt-2.5 border-t border-slate-200/80 space-y-1.5">
                    {m.sources && m.sources.length > 0 && (
                      <div className="flex flex-wrap gap-1.5">
                        {m.sources.map((c, idx) => {
                          const view = SOURCE_VIEW[c.type];
                          const chip = (
                            <>
                              <Database className="w-2.5 h-2.5" />
                              {c.type}: {c.label}
                            </>
                          );
                          return view && onNavigate ? (
                            <button
                              key={idx}
                              onClick={() => onNavigate(view)}
                              className="inline-flex items-center gap-1 bg-white border border-indigo-200 hover:border-indigo-500 hover:bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded text-[10px] font-medium transition-colors"
                              title={`Open ${view} view`}
                            >
                              {chip}
                            </button>
                          ) : (
                            <span
                              key={idx}
                              className="inline-flex items-center gap-1 bg-white border border-indigo-200 text-indigo-700 px-2 py-0.5 rounded text-[10px] font-medium"
                            >
                              {chip}
                            </span>
                          );
                        })}
                      </div>
                    )}
                    {m.meta && <p className="text-[10px] text-slate-500">{m.meta}</p>}
                  </div>
                )}
                <span
                  className={`block text-[9px] mt-1.5 text-right ${
                    m.sender === "user" ? "text-indigo-200" : "text-slate-400"
                  }`}
                >
                  {m.timestamp}
                </span>
              </div>
              {m.sender === "user" && (
                <div className="w-7 h-7 rounded-lg bg-indigo-600 text-white flex items-center justify-center flex-shrink-0 mt-0.5 font-bold text-[10px]">
                  A
                </div>
              )}
            </div>
          ))}

          {isTyping && (
            <div className="flex items-center gap-2 text-slate-400 text-xs italic">
              <Sparkles className="w-3.5 h-3.5 animate-spin text-purple-600" />
              <span>Querying verified database metrics...</span>
            </div>
          )}
        </div>

        {/* Input Footer */}
        <div className="p-3 border-t border-slate-200 bg-white flex items-center gap-2 pb-[max(0.75rem,env(safe-area-inset-bottom))]">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
            placeholder="Ask about projects, people, deadlines or risks…"
            className="flex-1 text-xs border border-slate-200 rounded-xl px-3 py-2.5 focus:outline-hidden focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
          />
          <button
            onClick={() => handleSend()}
            disabled={!input.trim()}
            aria-label="Send"
            className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-40 text-white p-3 sm:p-2.5 rounded-xl shadow-md shadow-indigo-600/20 transition-all"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};

