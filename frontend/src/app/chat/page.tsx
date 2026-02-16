"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { sendChat } from "@/lib/api";
import type { ChatResponse } from "@/lib/types";

interface Message {
  role: "user" | "assistant";
  content: string;
  result?: ChatResponse;
}

function StrategyResultCard({ result }: { result: ChatResponse }) {
  return (
    <Card data-testid="strategy-result-card">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          Strategy Result
          <Badge
            variant={result.backtest.passed ? "default" : "destructive"}
            data-testid="pass-fail-badge"
          >
            {result.backtest.passed ? "PASSED" : "FAILED"}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div>
          <h4 className="text-sm font-medium text-muted-foreground">Summary</h4>
          <p data-testid="strategy-summary">{result.summary}</p>
        </div>
        <div>
          <h4 className="text-sm font-medium text-muted-foreground">Metrics</h4>
          <div className="flex flex-wrap gap-2" data-testid="strategy-metrics">
            {Object.entries(result.backtest.metrics).map(([key, value]) => (
              <Badge key={key} variant="outline">
                {key}: {typeof value === "number" ? value.toFixed(2) : String(value)}
              </Badge>
            ))}
          </div>
        </div>
        {result.ace_feedback && (
          <div>
            <h4 className="text-sm font-medium text-muted-foreground">
              ACE Feedback
            </h4>
            <p className="text-sm" data-testid="ace-feedback">
              {JSON.stringify(result.ace_feedback)}
            </p>
          </div>
        )}
        <a
          href={`/strategies/${result.strategy_id}`}
          className="text-sm text-primary underline"
          data-testid="view-strategy-link"
        >
          View Strategy Details
        </a>
      </CardContent>
    </Card>
  );
}

export default function ChatPage() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);

  async function handleSend() {
    const text = input.trim();
    if (!text || loading) return;

    const userMessage: Message = { role: "user", content: text };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      const result = await sendChat({ message: text });
      const assistantMessage: Message = {
        role: "assistant",
        content: result.summary,
        result,
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      const errorMessage: Message = {
        role: "assistant",
        content: `Error: ${err instanceof Error ? err.message : "Unknown error"}`,
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex h-full flex-col gap-4">
      <h2 className="text-2xl font-bold">Chat</h2>

      <div
        className="flex-1 space-y-4 overflow-y-auto"
        data-testid="message-history"
      >
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[80%] rounded-lg p-3 ${
                msg.role === "user"
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted"
              }`}
              data-testid={`message-${msg.role}`}
            >
              <p>{msg.content}</p>
              {msg.result && <StrategyResultCard result={msg.result} />}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="rounded-lg bg-muted p-3" data-testid="loading-indicator">
              Thinking...
            </div>
          </div>
        )}
      </div>

      <div className="flex gap-2">
        <Textarea
          placeholder="Describe your investment strategy..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSend();
            }
          }}
          data-testid="chat-input"
        />
        <Button
          onClick={handleSend}
          disabled={loading || !input.trim()}
          data-testid="send-button"
        >
          Send
        </Button>
      </div>
    </div>
  );
}
