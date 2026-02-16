"use client";

import { useEffect, useState } from "react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { fetchMetrics } from "@/lib/api";
import type { MetricsResponse } from "@/lib/types";
import {
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

const CHART_COLORS = [
  "var(--chart-1)",
  "var(--chart-2)",
  "var(--chart-3)",
  "var(--chart-4)",
  "var(--chart-5)",
];

export default function MetricsPage() {
  const [data, setData] = useState<MetricsResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchMetrics()
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, []);

  const totalCalls =
    data?.llm_usage.reduce((sum, m) => sum + m.total_calls, 0) ?? 0;
  const totalTokens =
    data?.llm_usage.reduce(
      (sum, m) => sum + m.total_prompt_tokens + m.total_completion_tokens,
      0
    ) ?? 0;
  const avgLatency =
    data && data.llm_usage.length > 0
      ? (
          data.llm_usage.reduce((sum, m) => sum + m.avg_latency_ms, 0) /
          data.llm_usage.length
        ).toFixed(0)
      : "0";

  if (loading) {
    return (
      <div className="space-y-4">
        <h2 className="text-2xl font-bold">Metrics</h2>
        <p className="text-muted-foreground">Loading...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Metrics</h2>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3" data-testid="stat-cards">
        <Card data-testid="stat-calls">
          <CardHeader>
            <CardTitle className="text-sm text-muted-foreground">
              Total Calls
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{totalCalls.toLocaleString()}</p>
          </CardContent>
        </Card>
        <Card data-testid="stat-tokens">
          <CardHeader>
            <CardTitle className="text-sm text-muted-foreground">
              Total Tokens
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{totalTokens.toLocaleString()}</p>
          </CardContent>
        </Card>
        <Card data-testid="stat-latency">
          <CardHeader>
            <CardTitle className="text-sm text-muted-foreground">
              Avg Latency
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{avgLatency} ms</p>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="llm" data-testid="metrics-tabs">
        <TabsList>
          <TabsTrigger value="llm" data-testid="tab-llm">
            LLM Usage
          </TabsTrigger>
          <TabsTrigger value="tools" data-testid="tab-tools">
            Tool Calls
          </TabsTrigger>
          <TabsTrigger value="agents" data-testid="tab-agents">
            Agent Activity
          </TabsTrigger>
        </TabsList>

        {/* LLM Usage Tab */}
        <TabsContent value="llm">
          <div className="space-y-4">
            <Table data-testid="llm-table">
              <TableHeader>
                <TableRow>
                  <TableHead>Provider</TableHead>
                  <TableHead>Model</TableHead>
                  <TableHead>Calls</TableHead>
                  <TableHead>Prompt Tokens</TableHead>
                  <TableHead>Completion Tokens</TableHead>
                  <TableHead>Avg Latency</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data?.llm_usage.map((m, i) => (
                  <TableRow key={i}>
                    <TableCell>{m.provider}</TableCell>
                    <TableCell>{m.model}</TableCell>
                    <TableCell>{m.total_calls}</TableCell>
                    <TableCell>{m.total_prompt_tokens.toLocaleString()}</TableCell>
                    <TableCell>
                      {m.total_completion_tokens.toLocaleString()}
                    </TableCell>
                    <TableCell>{m.avg_latency_ms.toFixed(0)} ms</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <div className="h-64" data-testid="llm-chart">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data?.llm_usage ?? []}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="model" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="total_calls" name="Calls" fill={CHART_COLORS[0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </TabsContent>

        {/* Tool Calls Tab */}
        <TabsContent value="tools">
          <div className="space-y-4">
            <div className="h-64" data-testid="tools-chart">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={data?.tool_calls ?? []}
                    dataKey="count"
                    nameKey="tool"
                    cx="50%"
                    cy="50%"
                    outerRadius={80}
                    label
                  >
                    {data?.tool_calls.map((_, i) => (
                      <Cell
                        key={i}
                        fill={CHART_COLORS[i % CHART_COLORS.length]}
                      />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <Table data-testid="tools-table">
              <TableHeader>
                <TableRow>
                  <TableHead>Tool</TableHead>
                  <TableHead>Count</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data?.tool_calls.map((t, i) => (
                  <TableRow key={i}>
                    <TableCell>{t.tool}</TableCell>
                    <TableCell>{t.count}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </TabsContent>

        {/* Agent Activity Tab */}
        <TabsContent value="agents">
          <div className="space-y-4">
            <div className="h-64" data-testid="agents-chart">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data?.agent_actions ?? []}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="agent" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Bar
                    dataKey="count"
                    name="Actions"
                    fill={CHART_COLORS[1]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <Table data-testid="agents-table">
              <TableHeader>
                <TableRow>
                  <TableHead>Agent</TableHead>
                  <TableHead>Action</TableHead>
                  <TableHead>Count</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data?.agent_actions.map((a, i) => (
                  <TableRow key={i}>
                    <TableCell>{a.agent}</TableCell>
                    <TableCell>{a.action}</TableCell>
                    <TableCell>{a.count}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
