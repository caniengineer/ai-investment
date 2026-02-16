"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { fetchStrategy } from "@/lib/api";
import type { StrategyDetail } from "@/lib/types";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

export default function StrategyDetailPage() {
  const params = useParams<{ id: string }>();
  const [strategy, setStrategy] = useState<StrategyDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!params.id) return;
    fetchStrategy(params.id)
      .then(setStrategy)
      .catch(() => setStrategy(null))
      .finally(() => setLoading(false));
  }, [params.id]);

  if (loading) {
    return <p className="text-muted-foreground">Loading strategy…</p>;
  }

  if (!strategy) {
    return <p className="text-muted-foreground">Strategy not found.</p>;
  }

  const chartData = strategy.backtest_history.map((b) => ({
    iteration: b.iteration,
    return: +(b.total_return * 100).toFixed(2),
    sharpe: +b.sharpe_ratio.toFixed(2),
  }));

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <h2 className="text-2xl font-bold" data-testid="strategy-name">
          {strategy.name}
        </h2>
        <Badge>{strategy.status}</Badge>
      </div>

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="backtest">Backtest</TabsTrigger>
          <TabsTrigger value="logs">Agent Logs</TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <Card>
            <CardHeader>
              <CardTitle>Strategy Details</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-2 text-sm">
              <div>
                <span className="text-muted-foreground">Asset: </span>
                <span className="font-medium">{strategy.asset}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Type: </span>
                <span className="font-medium">{strategy.strategy_type}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Indicator: </span>
                <span className="font-medium">{strategy.indicator}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Entry Rule: </span>
                <span className="font-medium">{strategy.entry_rule}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Exit Rule: </span>
                <span className="font-medium">{strategy.exit_rule}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Stop Loss: </span>
                <span className="font-medium">
                  {(strategy.stop_loss_pct * 100).toFixed(1)}%
                </span>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="backtest">
          <Card>
            <CardHeader>
              <CardTitle>Backtest Results</CardTitle>
            </CardHeader>
            <CardContent>
              {chartData.length === 0 ? (
                <p className="text-muted-foreground">No backtest data.</p>
              ) : (
                <div data-testid="backtest-chart" className="h-64 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="iteration" />
                      <YAxis />
                      <Tooltip />
                      <Line
                        type="monotone"
                        dataKey="return"
                        stroke="hsl(var(--chart-1))"
                        name="Return %"
                      />
                      <Line
                        type="monotone"
                        dataKey="sharpe"
                        stroke="hsl(var(--chart-2))"
                        name="Sharpe"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="logs">
          <Card>
            <CardHeader>
              <CardTitle>Agent Logs</CardTitle>
            </CardHeader>
            <CardContent>
              {strategy.agent_log.length === 0 ? (
                <p className="text-muted-foreground">No agent logs.</p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Agent</TableHead>
                      <TableHead>Action</TableHead>
                      <TableHead>Detail</TableHead>
                      <TableHead>Time</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {strategy.agent_log.map((log) => (
                      <TableRow key={log.id}>
                        <TableCell className="font-medium">
                          {log.agent}
                        </TableCell>
                        <TableCell>{log.action}</TableCell>
                        <TableCell className="max-w-xs truncate">
                          {log.detail}
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {new Date(log.created_at).toLocaleString()}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
