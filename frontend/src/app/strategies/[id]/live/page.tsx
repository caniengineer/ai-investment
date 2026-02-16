"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { fetchLiveTrading } from "@/lib/api";
import type { PaperTrade } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

export default function LiveTradingPage() {
  const params = useParams<{ id: string }>();
  const [trade, setTrade] = useState<PaperTrade | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshCount, setRefreshCount] = useState(0);

  const loadData = useCallback(() => {
    if (!params.id) return;
    fetchLiveTrading(params.id)
      .then(setTrade)
      .catch(() => setTrade(null))
      .finally(() => setLoading(false));
  }, [params.id]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Auto-refresh every 30 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      loadData();
      setRefreshCount((c) => c + 1);
    }, 30_000);
    return () => clearInterval(interval);
  }, [loadData]);

  if (loading) {
    return <p className="text-muted-foreground">Loading live data…</p>;
  }

  if (!trade) {
    return <p className="text-muted-foreground">No live trading data.</p>;
  }

  // Build PnL chart from order history
  const pnlData = trade.order_history.map((order, i) => ({
    index: i + 1,
    price: order.price,
    action: order.action,
  }));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Live Trading</h2>
        <Badge>{trade.status}</Badge>
      </div>

      <span data-testid="refresh-count" className="hidden">
        {refreshCount}
      </span>

      {/* Position Card */}
      <Card data-testid="position-card">
        <CardHeader>
          <CardTitle>Position</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-2 text-sm sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <span className="text-muted-foreground">Position: </span>
            <span className="font-medium">{trade.position}</span>
          </div>
          <div>
            <span className="text-muted-foreground">Entry Price: </span>
            <span className="font-medium">${trade.entry_price.toFixed(2)}</span>
          </div>
          <div>
            <span className="text-muted-foreground">Current Price: </span>
            <span className="font-medium">
              ${trade.current_price.toFixed(2)}
            </span>
          </div>
          <div>
            <span className="text-muted-foreground">PnL: </span>
            <span
              data-testid="pnl-value"
              className={`font-bold ${trade.pnl >= 0 ? "text-green-600" : "text-red-600"}`}
            >
              {trade.pnl >= 0 ? "+" : ""}
              {trade.pnl.toFixed(2)}%
            </span>
          </div>
        </CardContent>
      </Card>

      {/* PnL Area Chart */}
      <Card>
        <CardHeader>
          <CardTitle>Price History</CardTitle>
        </CardHeader>
        <CardContent>
          {pnlData.length === 0 ? (
            <p className="text-muted-foreground">No price data.</p>
          ) : (
            <div data-testid="pnl-chart" className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={pnlData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="index" />
                  <YAxis />
                  <Tooltip />
                  <Area
                    type="monotone"
                    dataKey="price"
                    stroke="hsl(var(--chart-1))"
                    fill="hsl(var(--chart-1))"
                    fillOpacity={0.2}
                    name="Price"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Order History Table */}
      <Card>
        <CardHeader>
          <CardTitle>Order History</CardTitle>
        </CardHeader>
        <CardContent>
          {trade.order_history.length === 0 ? (
            <p className="text-muted-foreground">No orders yet.</p>
          ) : (
            <Table data-testid="order-table">
              <TableHeader>
                <TableRow>
                  <TableHead>#</TableHead>
                  <TableHead>Action</TableHead>
                  <TableHead>Price</TableHead>
                  <TableHead>Time</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {trade.order_history.map((order, i) => (
                  <TableRow key={i}>
                    <TableCell>{i + 1}</TableCell>
                    <TableCell className="font-medium">
                      {order.action}
                    </TableCell>
                    <TableCell>${order.price.toFixed(2)}</TableCell>
                    <TableCell className="text-muted-foreground">
                      {new Date(order.timestamp).toLocaleString()}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
