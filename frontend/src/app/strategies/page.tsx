"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchStrategies } from "@/lib/api";
import type { Strategy } from "@/lib/types";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const STATUS_COLORS: Record<Strategy["status"], string> = {
  created: "bg-gray-500 text-white",
  backtested: "bg-blue-500 text-white",
  deployed: "bg-green-500 text-white",
  paused: "bg-yellow-500 text-black",
};

export default function StrategiesPage() {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>("all");

  useEffect(() => {
    fetchStrategies()
      .then(setStrategies)
      .catch(() => setStrategies([]))
      .finally(() => setLoading(false));
  }, []);

  const filtered =
    filter === "all"
      ? strategies
      : strategies.filter((s) => s.status === filter);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Strategies</h2>
        <div data-testid="status-filter">
          <Select value={filter} onValueChange={setFilter}>
            <SelectTrigger aria-label="Filter by status">
              <SelectValue placeholder="Filter by status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All</SelectItem>
              <SelectItem value="created">Created</SelectItem>
              <SelectItem value="backtested">Backtested</SelectItem>
              <SelectItem value="deployed">Deployed</SelectItem>
              <SelectItem value="paused">Paused</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {loading ? (
        <p className="text-muted-foreground">Loading strategies…</p>
      ) : filtered.length === 0 ? (
        <p className="text-muted-foreground">No strategies found.</p>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((s) => (
            <Link
              key={s.id}
              href={`/strategies/${s.id}`}
              data-testid="strategy-card"
            >
              <Card className="cursor-pointer transition-shadow hover:shadow-md">
                <CardHeader>
                  <CardTitle className="flex items-center justify-between">
                    <span data-testid="strategy-name">{s.name}</span>
                    <Badge
                      data-testid="strategy-badge"
                      data-status={s.status}
                      className={STATUS_COLORS[s.status]}
                    >
                      {s.status}
                    </Badge>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">
                    Asset:{" "}
                    <span data-testid="strategy-asset" className="font-medium text-foreground">
                      {s.asset}
                    </span>
                  </p>
                  <p className="text-sm text-muted-foreground">
                    Type: <span className="font-medium text-foreground">{s.strategy_type}</span>
                  </p>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
