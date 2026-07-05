"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Download,
  Play,
  RefreshCcw,
  ShieldCheck
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import {
  fetchDashboard,
  fetchPolicy,
  fetchStrategyDetail,
  refreshYahooData
} from "@/lib/api";
import {
  compactDate,
  formatCurrency,
  formatNumber,
  formatPercent,
  formatPrice,
  formatSignedPercent
} from "@/lib/format";
import type {
  DashboardResponse,
  PolicyResponse,
  StrategyDetail,
  StrategySummary,
  TimeSeriesPoint,
  TradeRow
} from "@/types/api";

const COLORS = ["#2563eb", "#059669", "#d97706", "#dc2626", "#7c3aed", "#0891b2"];
const formatChartDate = (label: unknown) => compactDate(String(label));

function chartRows(series: Record<string, TimeSeriesPoint[]>, strategyNames: string[]) {
  const byDate = new Map<string, Record<string, string | number>>();
  strategyNames.forEach((name) => {
    (series[name] || []).forEach((point) => {
      const row = byDate.get(point.date) || { date: point.date };
      row[name] = point.value;
      byDate.set(point.date, row);
    });
  });
  return Array.from(byDate.values()).sort((a, b) => String(a.date).localeCompare(String(b.date)));
}

function csvValue(value: string | number | null) {
  if (value === null) {
    return "";
  }
  const text = String(value);
  return text.includes(",") ? `"${text.replaceAll('"', '""')}"` : text;
}

function downloadTrades(strategyName: string, rows: TradeRow[]) {
  const headers = [
    "strategy",
    "source_strategy",
    "sleeve",
    "trade_date",
    "entry_date",
    "exit_trim_date",
    "symbol",
    "action",
    "previous_weight",
    "target_weight",
    "weight_change",
    "price",
    "transaction_cost",
    "realized_marked_return"
  ];
  const csv = [
    headers.join(","),
    ...rows.map((row) => headers.map((key) => csvValue(row[key as keyof TradeRow])).join(","))
  ].join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `${strategyName.toLowerCase().replaceAll(/[^a-z0-9]+/g, "-")}-trades.csv`;
  anchor.click();
  URL.revokeObjectURL(url);
}

function bestStrategy(summary: StrategySummary[]) {
  return [...summary].sort((a, b) => b.ending_value - a.ending_value)[0];
}

function selectedBenchmark(summary: StrategySummary[]) {
  return summary.find((row) => row.name === "50/50 SPY/QQQ") || summary[0];
}

export function TradingDashboard() {
  const [initialCapital, setInitialCapital] = useState(50000);
  const [useRealData, setUseRealData] = useState(true);
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [policy, setPolicy] = useState<PolicyResponse | null>(null);
  const [selectedStrategyId, setSelectedStrategyId] = useState<string>("");
  const [detail, setDetail] = useState<StrategyDetail | null>(null);
  const [selectedActions, setSelectedActions] = useState<string[]>([]);
  const [loadingDashboard, setLoadingDashboard] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadDashboard = useCallback(async () => {
    setLoadingDashboard(true);
    setError(null);
    try {
      const [policyPayload, dashboardPayload] = await Promise.all([
        fetchPolicy(),
        fetchDashboard(initialCapital, useRealData)
      ]);
      setPolicy(policyPayload);
      setDashboard(dashboardPayload);
      if (
        dashboardPayload.summary.length > 0 &&
        !dashboardPayload.summary.some((strategy) => strategy.id === selectedStrategyId)
      ) {
        setSelectedStrategyId(dashboardPayload.summary[0].id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load dashboard.");
    } finally {
      setLoadingDashboard(false);
    }
  }, [initialCapital, selectedStrategyId, useRealData]);

  useEffect(() => {
    void loadDashboard();
  }, [loadDashboard]);

  useEffect(() => {
    if (!selectedStrategyId) {
      return;
    }
    setLoadingDetail(true);
    setError(null);
    fetchStrategyDetail(selectedStrategyId, initialCapital, useRealData)
      .then((payload) => {
        setDetail(payload);
        setSelectedActions(Array.from(new Set(payload.trade_history.map((row) => row.action))));
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Unable to load strategy.");
      })
      .finally(() => setLoadingDetail(false));
  }, [initialCapital, selectedStrategyId, useRealData]);

  const strategyNames = useMemo(
    () => dashboard?.summary.map((row) => row.name) || [],
    [dashboard]
  );
  const equityRows = useMemo(
    () => (dashboard ? chartRows(dashboard.equity_curves, strategyNames) : []),
    [dashboard, strategyNames]
  );
  const drawdownRows = useMemo(
    () => (dashboard ? chartRows(dashboard.drawdowns, strategyNames) : []),
    [dashboard, strategyNames]
  );
  const filteredTrades = useMemo(() => {
    if (!detail) {
      return [];
    }
    return detail.trade_history.filter((row) => selectedActions.includes(row.action));
  }, [detail, selectedActions]);
  const recentReturns = useMemo(
    () => detail?.daily_returns.slice(-126) || [],
    [detail]
  );
  const actionOptions = useMemo(
    () => Array.from(new Set(detail?.trade_history.map((row) => row.action) || [])),
    [detail]
  );

  async function handleRefreshYahoo() {
    setRefreshing(true);
    setError(null);
    try {
      const payload = await refreshYahooData(initialCapital);
      setDashboard(payload.dashboard);
      setUseRealData(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to refresh Yahoo data.");
    } finally {
      setRefreshing(false);
    }
  }

  const best = dashboard ? bestStrategy(dashboard.summary) : null;
  const benchmark = dashboard ? selectedBenchmark(dashboard.summary) : null;
  const combined = dashboard?.summary.find((row) => row.name === "70/30 Combined Policy") || null;

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <h1>Trading Agent</h1>
          <div className="meta-row">
            <span>{dashboard?.is_real_data ? "Real historical data" : "Synthetic validation data"}</span>
            <span>{dashboard?.data_source || "Loading data source"}</span>
          </div>
        </div>
        <div className="controls">
          <label className="field">
            <span>Initial capital</span>
            <input
              type="number"
              min="1000"
              step="1000"
              value={initialCapital}
              onChange={(event) => setInitialCapital(Number(event.target.value))}
            />
          </label>
          <label className="toggle">
            <input
              type="checkbox"
              checked={useRealData}
              onChange={(event) => setUseRealData(event.target.checked)}
            />
            <span>Real data</span>
          </label>
          <button className="button secondary" type="button" onClick={() => void loadDashboard()}>
            <Play size={16} />
            Run
          </button>
          <button
            className="button primary"
            type="button"
            onClick={() => void handleRefreshYahoo()}
            disabled={refreshing}
          >
            <RefreshCcw size={16} />
            {refreshing ? "Refreshing" : "Refresh Yahoo"}
          </button>
        </div>
      </header>

      {error ? (
        <div className="alert">
          <AlertTriangle size={18} />
          <span>{error}</span>
        </div>
      ) : null}

      <section className="metric-strip">
        <Metric label="Best strategy" value={best?.name || "-"} delta={best ? formatPercent(best.total_return) : ""} />
        <Metric label="Combined policy" value={combined ? formatCurrency(combined.ending_value) : "-"} delta={combined ? formatPercent(combined.total_return) : ""} />
        <Metric label="Benchmark" value={benchmark ? formatCurrency(benchmark.ending_value) : "-"} delta={benchmark ? formatPercent(benchmark.total_return) : ""} />
        <Metric label="Policy status" value={policy?.live_trading_enabled ? "Live enabled" : "Live disabled"} delta={policy?.manual_approval_required ? "Manual approval" : ""} />
      </section>

      <section className="grid grid-two">
        <Panel title="Equity Curve">
          <ChartFrame loading={loadingDashboard}>
            <ResponsiveContainer width="100%" height={330}>
              <LineChart data={equityRows}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis dataKey="date" tickFormatter={compactDate} minTickGap={42} />
                <YAxis tickFormatter={(value) => `$${Math.round(Number(value) / 1000)}k`} />
                <Tooltip formatter={(value) => formatCurrency(Number(value))} labelFormatter={formatChartDate} />
                <Legend />
                {strategyNames.map((name, index) => (
                  <Line key={name} type="monotone" dataKey={name} dot={false} stroke={COLORS[index % COLORS.length]} strokeWidth={2} />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </ChartFrame>
        </Panel>

        <Panel title="Drawdown">
          <ChartFrame loading={loadingDashboard}>
            <ResponsiveContainer width="100%" height={330}>
              <LineChart data={drawdownRows}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis dataKey="date" tickFormatter={compactDate} minTickGap={42} />
                <YAxis tickFormatter={(value) => formatPercent(Number(value), 0)} />
                <Tooltip formatter={(value) => formatPercent(Number(value))} labelFormatter={formatChartDate} />
                <Legend />
                {strategyNames.map((name, index) => (
                  <Line key={name} type="monotone" dataKey={name} dot={false} stroke={COLORS[index % COLORS.length]} strokeWidth={2} />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </ChartFrame>
        </Panel>
      </section>

      <section className="grid grid-dashboard">
        <Panel title="Strategy Summary">
          <div className="table-scroll summary-table">
            <table>
              <thead>
                <tr>
                  <th>Strategy</th>
                  <th>Sleeve</th>
                  <th>Ending</th>
                  <th>Total</th>
                  <th>Ann.</th>
                  <th>Max DD</th>
                  <th>Sharpe</th>
                </tr>
              </thead>
              <tbody>
                {dashboard?.summary.map((row) => (
                  <tr
                    key={row.id}
                    className={row.id === selectedStrategyId ? "selected" : ""}
                    onClick={() => setSelectedStrategyId(row.id)}
                  >
                    <td>{row.name}</td>
                    <td>{row.sleeve}</td>
                    <td>{formatCurrency(row.ending_value)}</td>
                    <td className={row.total_return >= 0 ? "positive" : "negative"}>{formatPercent(row.total_return)}</td>
                    <td>{formatPercent(row.annualized_return)}</td>
                    <td className="negative">{formatPercent(row.max_drawdown)}</td>
                    <td>{formatNumber(row.sharpe_like)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>

        <Panel title="Policy">
          <div className="policy-list">
            <PolicyItem ok={!policy?.live_trading_enabled} label="Live trading disabled" />
            <PolicyItem ok={Boolean(policy?.manual_approval_required)} label="Manual approval required" />
            <PolicyItem ok={Boolean(policy?.long_only)} label="Long-only policy" />
            <PolicyItem ok={!policy?.allow_margin && !policy?.allow_shorting} label="No margin or shorting" />
          </div>
          <dl className="definition-list">
            <div>
              <dt>Gross exposure cap</dt>
              <dd>{policy ? formatPercent(policy.gross_exposure_cap_pct) : "-"}</dd>
            </div>
            <div>
              <dt>Default risk/trade</dt>
              <dd>{policy ? formatPercent(policy.risk_per_trade_default_pct, 2) : "-"}</dd>
            </div>
            <div>
              <dt>Max risk/trade</dt>
              <dd>{policy ? formatPercent(policy.risk_per_trade_max_pct, 2) : "-"}</dd>
            </div>
          </dl>
        </Panel>
      </section>

      <section className="grid grid-two">
        <Panel title={detail ? detail.summary.name : "Strategy Detail"}>
          {loadingDetail || !detail ? (
            <div className="loading">Loading strategy</div>
          ) : (
            <div className="detail-stack">
              <p className="description">{detail.description}</p>
              <div className="detail-metrics">
                <Metric label="Ending value" value={formatCurrency(detail.summary.ending_value)} delta="" />
                <Metric label="Total return" value={formatPercent(detail.summary.total_return)} delta="" />
                <Metric label="Max drawdown" value={formatPercent(detail.summary.max_drawdown)} delta="" />
                <Metric label="Sharpe-like" value={formatNumber(detail.summary.sharpe_like)} delta="" />
              </div>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={detail.latest_weights}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis dataKey="symbol" />
                  <YAxis tickFormatter={(value) => formatPercent(Number(value), 0)} />
                  <Tooltip formatter={(value) => formatPercent(Number(value))} />
                  <Bar dataKey="weight" fill="#2563eb" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </Panel>

        <Panel title="Recent Daily Returns">
          <ChartFrame loading={loadingDetail}>
            <ResponsiveContainer width="100%" height={360}>
              <BarChart data={recentReturns}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis dataKey="date" tickFormatter={compactDate} minTickGap={24} />
                <YAxis tickFormatter={(value) => formatPercent(Number(value), 0)} />
                <Tooltip formatter={(value) => formatPercent(Number(value), 2)} labelFormatter={formatChartDate} />
                <Bar dataKey="daily_return" fill="#059669" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </ChartFrame>
        </Panel>
      </section>

      <Panel
        title="Trades"
        action={
          detail ? (
            <button className="button secondary" type="button" onClick={() => downloadTrades(detail.summary.name, filteredTrades)}>
              <Download size={16} />
              CSV
            </button>
          ) : null
        }
      >
        <div className="trade-toolbar">
          <select
            value={selectedStrategyId}
            onChange={(event) => setSelectedStrategyId(event.target.value)}
          >
            {dashboard?.summary.map((strategy) => (
              <option key={strategy.id} value={strategy.id}>
                {strategy.name}
              </option>
            ))}
          </select>
          <div className="action-filter">
            {actionOptions.map((action) => (
              <label key={action}>
                <input
                  type="checkbox"
                  checked={selectedActions.includes(action)}
                  onChange={(event) => {
                    setSelectedActions((current) =>
                      event.target.checked
                        ? [...current, action]
                        : current.filter((item) => item !== action)
                    );
                  }}
                />
                <span>{action}</span>
              </label>
            ))}
          </div>
        </div>
        <div className="table-scroll trades-table">
          <table>
            <thead>
              <tr>
                <th>Trade date</th>
                <th>Entry</th>
                <th>Exit/trim</th>
                <th>Symbol</th>
                <th>Action</th>
                <th>Source</th>
                <th>Prev.</th>
                <th>Target</th>
                <th>Change</th>
                <th>Price</th>
                <th>Cost drag</th>
                <th>Return</th>
              </tr>
            </thead>
            <tbody>
              {filteredTrades.map((row, index) => (
                <tr key={`${row.trade_date}-${row.symbol}-${row.action}-${index}`}>
                  <td>{row.trade_date}</td>
                  <td>{row.entry_date || ""}</td>
                  <td>{row.exit_trim_date || ""}</td>
                  <td>{row.symbol}</td>
                  <td>{row.action}</td>
                  <td>{row.source_strategy}</td>
                  <td>{formatPercent(row.previous_weight)}</td>
                  <td>{formatPercent(row.target_weight)}</td>
                  <td className={row.weight_change >= 0 ? "positive" : "negative"}>{formatSignedPercent(row.weight_change)}</td>
                  <td>{formatPrice(row.price)}</td>
                  <td>{formatPercent(row.transaction_cost, 3)}</td>
                  <td>{row.realized_marked_return === null ? "" : formatPercent(row.realized_marked_return)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      <footer className="footer">
        Demo/backtest returns are not live-trading proof.
      </footer>
    </main>
  );
}

function Metric({ label, value, delta }: { label: string; value: string; delta: string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
      {delta ? <small>{delta}</small> : null}
    </div>
  );
}

function Panel({
  title,
  action,
  children
}: {
  title: string;
  action?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section className="panel">
      <div className="panel-header">
        <h2>{title}</h2>
        {action}
      </div>
      {children}
    </section>
  );
}

function ChartFrame({ loading, children }: { loading: boolean; children: React.ReactNode }) {
  if (loading) {
    return <div className="loading">Loading chart</div>;
  }
  return children;
}

function PolicyItem({ ok, label }: { ok: boolean; label: string }) {
  return (
    <div className={ok ? "policy-item ok" : "policy-item warn"}>
      {ok ? <CheckCircle2 size={18} /> : <ShieldCheck size={18} />}
      <span>{label}</span>
    </div>
  );
}
