"use client";

import { useQuery } from "@tanstack/react-query";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  Activity,
  Clock,
  Coins,
  MessageCircle,
  SearchX,
  Users,
} from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge, Skeleton } from "@/components/ui/misc";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api } from "@/lib/api";
import { formatCurrency, formatNumber } from "@/lib/utils";

const CHART_COLORS = ["#6366f1", "#8b5cf6", "#ec4899", "#f59e0b", "#10b981", "#06b6d4"];

export default function DashboardPage() {
  const { data: dash, isLoading } = useQuery({
    queryKey: ["dashboard"],
    queryFn: () => api.dashboard(30),
  });
  const { data: cost } = useQuery({ queryKey: ["cost-by-model"], queryFn: () => api.costByModel() });
  const { data: reviews } = useQuery({ queryKey: ["reviews"], queryFn: () => api.reviewQueue() });

  return (
    <div className="h-full overflow-y-auto scrollbar-thin">
      <div className="mx-auto max-w-5xl space-y-6 p-6">
        <h1 className="text-2xl font-bold">Dashboard</h1>

        <Tabs defaultValue="overview">
          <TabsList>
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="cost">Cost</TabsTrigger>
            <TabsTrigger value="feedback">Feedback</TabsTrigger>
          </TabsList>

          {/* Overview / usage */}
          <TabsContent value="overview">
            {isLoading || !dash ? (
              <div className="grid grid-cols-2 gap-4 lg:grid-cols-3">
                {Array.from({ length: 6 }).map((_, i) => (
                  <Skeleton key={i} className="h-24" />
                ))}
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-4 lg:grid-cols-3">
                <Stat icon={MessageCircle} label="Questions (30d)" value={formatNumber(dash.questions_asked)} />
                <Stat icon={Users} label="Active users" value={formatNumber(dash.active_users)} />
                <Stat icon={Activity} label="Total tokens" value={formatNumber(dash.total_tokens)} />
                <Stat icon={Coins} label="Total cost" value={formatCurrency(dash.total_cost_usd)} />
                <Stat icon={Clock} label="Avg latency" value={`${dash.avg_latency_ms} ms`} />
                <Stat icon={SearchX} label="Failed searches" value={formatNumber(dash.failed_searches)} />
              </div>
            )}
          </TabsContent>

          {/* Cost */}
          <TabsContent value="cost">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Cost & token usage by model</CardTitle>
              </CardHeader>
              <CardContent>
                {!cost?.length ? (
                  <p className="py-8 text-center text-sm text-[var(--muted-foreground)]">
                    No usage recorded yet.
                  </p>
                ) : (
                  <>
                    <div className="h-64">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={cost}>
                          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                          <XAxis dataKey="model" tick={{ fontSize: 11 }} />
                          <YAxis tick={{ fontSize: 11 }} />
                          <Tooltip
                            formatter={(value: number | string | (number | string)[]) =>
                              formatCurrency(Number(value))
                            }
                            contentStyle={{
                              background: "var(--popover)",
                              border: "1px solid var(--border)",
                              borderRadius: 8,
                              fontSize: 12,
                            }}
                          />
                          <Bar dataKey="cost_usd" radius={[4, 4, 0, 0]}>
                            {cost.map((_, i) => (
                              <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                    <ul className="mt-4 space-y-1.5 text-sm">
                      {cost.map((c) => (
                        <li key={c.model} className="flex items-center justify-between">
                          <span className="font-mono text-xs">{c.model}</span>
                          <span className="text-[var(--muted-foreground)]">
                            {formatNumber(c.tokens)} tokens · {c.calls} calls ·{" "}
                            {formatCurrency(c.cost_usd)}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Feedback / review queue */}
          <TabsContent value="feedback">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Human review queue</CardTitle>
              </CardHeader>
              <CardContent>
                {!reviews?.items.length ? (
                  <p className="py-8 text-center text-sm text-[var(--muted-foreground)]">
                    No items awaiting review. 🎉
                  </p>
                ) : (
                  <ul className="divide-y divide-[var(--border)]">
                    {reviews.items.map((r) => (
                      <li key={r.id} className="flex items-center justify-between py-2.5 text-sm">
                        <span>{r.reason}</span>
                        <Badge
                          variant={
                            r.status === "resolved"
                              ? "success"
                              : r.status === "pending"
                                ? "warning"
                                : "secondary"
                          }
                          className="capitalize"
                        >
                          {r.status}
                        </Badge>
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}

function Stat({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
}) {
  return (
    <Card>
      <CardContent className="pt-5">
        <div className="flex items-center gap-2 text-[var(--muted-foreground)]">
          <Icon className="h-4 w-4" />
          <span className="text-xs">{label}</span>
        </div>
        <p className="mt-1.5 text-2xl font-bold">{value}</p>
      </CardContent>
    </Card>
  );
}
