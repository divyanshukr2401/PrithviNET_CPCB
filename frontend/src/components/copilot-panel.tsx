"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import {
  X,
  Send,
  Sparkles,
  BarChart3,
  Lightbulb,
  Loader2,
  Bot,
  User,
  ChevronDown,
} from "lucide-react";
import {
  sendCopilotMessage,
  getCopilotSuggestions,
  type CopilotMessage,
} from "@/lib/api";

interface CopilotPanelProps {
  isOpen: boolean;
  onClose: () => void;
  activeLayer: string;
}

/** Simple Markdown-ish renderer: bold, bullet lists, headings, inline code */
function renderMarkdown(text: string) {
  const lines = text.split("\n");
  const elements: React.ReactNode[] = [];

  lines.forEach((line, i) => {
    const trimmed = line.trim();

    // Heading
    if (trimmed.startsWith("### ")) {
      elements.push(
        <h4 key={i} className="font-semibold text-sm mt-3 mb-1">
          {formatInline(trimmed.slice(4))}
        </h4>
      );
    } else if (trimmed.startsWith("## ")) {
      elements.push(
        <h3 key={i} className="font-bold text-sm mt-3 mb-1">
          {formatInline(trimmed.slice(3))}
        </h3>
      );
    } else if (trimmed.startsWith("# ")) {
      elements.push(
        <h2 key={i} className="font-bold text-base mt-3 mb-1">
          {formatInline(trimmed.slice(2))}
        </h2>
      );
    }
    // Bullet list
    else if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
      elements.push(
        <div key={i} className="flex gap-1.5 ml-2 text-[13px] leading-relaxed">
          <span className="text-muted-foreground mt-0.5">•</span>
          <span>{formatInline(trimmed.slice(2))}</span>
        </div>
      );
    }
    // Numbered list
    else if (/^\d+\.\s/.test(trimmed)) {
      const match = trimmed.match(/^(\d+)\.\s(.*)/);
      if (match) {
        elements.push(
          <div key={i} className="flex gap-1.5 ml-2 text-[13px] leading-relaxed">
            <span className="text-muted-foreground font-medium min-w-[1.2em]">
              {match[1]}.
            </span>
            <span>{formatInline(match[2])}</span>
          </div>
        );
      }
    }
    // Empty line → spacer
    else if (trimmed === "") {
      elements.push(<div key={i} className="h-1.5" />);
    }
    // Regular paragraph
    else {
      elements.push(
        <p key={i} className="text-[13px] leading-relaxed">
          {formatInline(trimmed)}
        </p>
      );
    }
  });

  return <>{elements}</>;
}

/** Format inline markdown: **bold**, `code`, *italic* */
function formatInline(text: string): React.ReactNode {
  // Split by bold, code, and italic patterns
  const parts: React.ReactNode[] = [];
  let remaining = text;
  let key = 0;

  while (remaining.length > 0) {
    // Bold **text**
    const boldMatch = remaining.match(/\*\*(.+?)\*\*/);
    // Code `text`
    const codeMatch = remaining.match(/`(.+?)`/);

    if (boldMatch && (!codeMatch || boldMatch.index! <= codeMatch.index!)) {
      if (boldMatch.index! > 0) {
        parts.push(remaining.slice(0, boldMatch.index));
      }
      parts.push(
        <strong key={key++} className="font-semibold">
          {boldMatch[1]}
        </strong>
      );
      remaining = remaining.slice(boldMatch.index! + boldMatch[0].length);
    } else if (codeMatch) {
      if (codeMatch.index! > 0) {
        parts.push(remaining.slice(0, codeMatch.index));
      }
      parts.push(
        <code
          key={key++}
          className="px-1 py-0.5 bg-muted rounded text-xs font-mono"
        >
          {codeMatch[1]}
        </code>
      );
      remaining = remaining.slice(codeMatch.index! + codeMatch[0].length);
    } else {
      parts.push(remaining);
      break;
    }
  }

  return <>{parts}</>;
}

export function CopilotPanel({ isOpen, onClose, activeLayer }: CopilotPanelProps) {
  const [messages, setMessages] = useState<
    { role: "user" | "assistant"; content: string }[]
  >([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [mode, setMode] = useState<"analyst" | "advisor">("analyst");
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  // Focus input when panel opens
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 300);
    }
  }, [isOpen]);

  // Fetch suggestions when layer changes
  useEffect(() => {
    if (isOpen) {
      getCopilotSuggestions(activeLayer)
        .then((res) => setSuggestions(res.suggestions))
        .catch(() =>
          setSuggestions(["What are the most polluted areas right now?"])
        );
    }
  }, [isOpen, activeLayer]);

  const sendMessage = useCallback(
    async (text?: string) => {
      const msg = (text || input).trim();
      if (!msg || isLoading) return;

      const userMsg = { role: "user" as const, content: msg };
      setMessages((prev) => [...prev, userMsg]);
      setInput("");
      setIsLoading(true);

      try {
        const history: CopilotMessage[] = messages.map((m) => ({
          role: m.role,
          content: m.content,
        }));

        const res = await sendCopilotMessage({
          message: msg,
          active_layer: activeLayer,
          history,
          mode,
        });

        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: res.response },
        ]);
      } catch (err: unknown) {
        const errorMessage =
          err instanceof Error && err.message.includes("429")
            ? "The AI service is temporarily rate-limited. Please wait a moment and try again."
            : "I encountered an error connecting to the AI service. Please check your connection and try again.";
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: errorMessage,
          },
        ]);
      } finally {
        setIsLoading(false);
      }
    },
    [input, isLoading, messages, activeLayer, mode]
  );

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-y-0 right-0 w-full sm:w-[420px] bg-card border-l border-border shadow-2xl z-[60] flex flex-col animate-in slide-in-from-right duration-300">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-gradient-to-r from-emerald-50 to-blue-50">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-500 to-blue-600 flex items-center justify-center">
            <Sparkles className="w-4 h-4 text-white" />
          </div>
          <div>
            <h2 className="text-sm font-bold leading-tight">
              Smart Co-pilot
            </h2>
            <p className="text-[11px] text-muted-foreground leading-tight">
              AI Environmental Intelligence
            </p>
          </div>
        </div>
        <button
          onClick={onClose}
          className="p-1.5 rounded-lg hover:bg-muted/60 transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Mode Toggle */}
      <div className="flex gap-1 px-3 py-2 border-b border-border bg-muted/30">
        <button
          onClick={() => setMode("analyst")}
          className={`flex items-center gap-1.5 flex-1 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
            mode === "analyst"
              ? "bg-card text-foreground shadow-sm border border-border"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          <BarChart3 className="w-3.5 h-3.5" />
          Data Analyst
        </button>
        <button
          onClick={() => setMode("advisor")}
          className={`flex items-center gap-1.5 flex-1 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
            mode === "advisor"
              ? "bg-card text-foreground shadow-sm border border-border"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          <Lightbulb className="w-3.5 h-3.5" />
          Policy Advisor
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-3">
        {messages.length === 0 && !isLoading && (
          <div className="text-center py-8">
            <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-gradient-to-br from-emerald-100 to-blue-100 flex items-center justify-center">
              <Bot className="w-6 h-6 text-emerald-700" />
            </div>
            <p className="text-sm font-medium mb-1">
              Ask me anything about India&apos;s environment
            </p>
            <p className="text-xs text-muted-foreground mb-4">
              I have access to live AQI, Water Quality, and Noise data
            </p>

            {/* Suggestion chips */}
            <div className="space-y-1.5">
              {suggestions.slice(0, 4).map((s, i) => (
                <button
                  key={i}
                  onClick={() => sendMessage(s)}
                  className="block w-full text-left px-3 py-2 rounded-lg border border-border text-xs text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex gap-2 ${
              msg.role === "user" ? "justify-end" : "justify-start"
            }`}
          >
            {msg.role === "assistant" && (
              <div className="w-6 h-6 rounded-full bg-gradient-to-br from-emerald-500 to-blue-600 flex items-center justify-center flex-shrink-0 mt-0.5">
                <Bot className="w-3.5 h-3.5 text-white" />
              </div>
            )}
            <div
              className={`max-w-[85%] rounded-xl px-3 py-2 ${
                msg.role === "user"
                  ? "bg-primary text-primary-foreground rounded-br-sm"
                  : "bg-muted/60 border border-border rounded-bl-sm"
              }`}
            >
              {msg.role === "assistant" ? (
                <div className="text-[13px]">{renderMarkdown(msg.content)}</div>
              ) : (
                <p className="text-[13px]">{msg.content}</p>
              )}
            </div>
            {msg.role === "user" && (
              <div className="w-6 h-6 rounded-full bg-muted flex items-center justify-center flex-shrink-0 mt-0.5">
                <User className="w-3.5 h-3.5 text-muted-foreground" />
              </div>
            )}
          </div>
        ))}

        {isLoading && (
          <div className="flex gap-2 justify-start">
            <div className="w-6 h-6 rounded-full bg-gradient-to-br from-emerald-500 to-blue-600 flex items-center justify-center flex-shrink-0 mt-0.5">
              <Bot className="w-3.5 h-3.5 text-white" />
            </div>
            <div className="bg-muted/60 border border-border rounded-xl rounded-bl-sm px-4 py-3">
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                Analyzing environmental data...
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-border p-3 bg-card">
        {/* Quick suggestions after conversation started */}
        {messages.length > 0 && messages.length < 6 && (
          <div className="flex gap-1.5 mb-2 overflow-x-auto pb-1 scrollbar-none">
            {suggestions.slice(0, 3).map((s, i) => (
              <button
                key={i}
                onClick={() => sendMessage(s)}
                disabled={isLoading}
                className="flex-shrink-0 px-2.5 py-1 rounded-full border border-border text-[11px] text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors disabled:opacity-50"
              >
                {s.length > 40 ? s.slice(0, 37) + "..." : s}
              </button>
            ))}
          </div>
        )}

        <div className="flex gap-2">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              mode === "advisor"
                ? "Ask for policy recommendations..."
                : "Ask about environmental data..."
            }
            disabled={isLoading}
            className="flex-1 px-3 py-2 rounded-lg border border-border bg-background text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary disabled:opacity-50"
          />
          <button
            onClick={() => sendMessage()}
            disabled={!input.trim() || isLoading}
            className="px-3 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
        <p className="text-[10px] text-muted-foreground text-center mt-1.5">
          Powered by Gemini AI &middot; Grounded in live CPCB data
        </p>
      </div>
    </div>
  );
}
