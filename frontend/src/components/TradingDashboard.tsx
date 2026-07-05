"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertTriangle, Download, RefreshCcw } from "lucide-react";
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
  DailyReturnRow,
  PolicyResponse,
  StrategyDetail,
  StrategySummary,
  TimeSeriesPoint,
  TradeRow,
  WeightRow
} from "@/types/api";

const COLORS = ["#ff4b4b", "#1f77b4", "#2ca02c", "#ff7f0e", "#9467bd", "#17becf"];
const DEFAULT_ETFS = ["SPY", "QQQ", "IWM", "TLT", "IEF", "GLD"];
const DEFAULT_STOCKS = ["AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "JPM", "XOM", "UNH", "COST"];
const TABS = [
  { id: "overview", label: "Overview" },
  { id: "strategy", label: "Strategy Detail" },
  { id: "trades", label: "Trades" },
  { id: "universe", label: "Universe" },
  { id: "policy", label: "Policy" }
] as const;
type DashboardTab = (typeof TABS)[number]["id"];

function chartRows(series: Record<string, TimeSeriesPoint[]>, names: string[]) {
  const byDate = new Map<string, Record<string, string | number>>();
  names.forEach((name) => {
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
  anchor.download = `${strategyName.toLowerCase().replaceAll(/[^a-z0-9]+/g, "_")}_trades.csv`;
  anchor.click();
  URL.revokeObjectURL(url);
}

function bestStrategy(summary: StrategySummary[]) {
  return [...summary].sort((a, b) => b.ending_value - a.ending_value)[0];
}

function selectedBenchmark(summary: StrategySummary[]) {
  return summary.find((row) => row.name === "50/50 SPY/QQQ") || summary[0];
}

function defaultStrategyId(summary: StrategySummary[]) {
  return summary.find((row) => row.name === "70/30 Combined Policy")?.id || summary[0]?.id || "";
}

function hasStrategy(summary: StrategySummary[], strategyId: string) {
  return summary.some((strategy) => strategy.id === strategyId);
}

export function TradingDashboard() {
  const [initialCapital, setInitialCapital] = useState(50000);
  const [useRealData, setUseRealData] = useState(true);
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [policy, setPolicy] = useState<PolicyResponse | null>(null);
  const [selectedStrategyId, setSelectedStrategyId] = useState<string>("");
  const [selectedTradeStrategyId, setSelectedTradeStrategyId] = useState<string>("");
  const [strategyDetail, setStrategyDetail] = useState<StrategyDetail | null>(null);
  const [tradeDetail, setTradeDetail] = useState<StrategyDetail | null>(null);
  const [selectedActions, setSelectedActions] = useState<string[]>([]);
  const [loadingDashboard, setLoadingDashboard] = useState(true);
  const [loadingStrategy, setLoadingStrategy] = useState(false);
  const [loadingTrades, setLoadingTrades] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<DashboardTab>("overview");

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
      setSelectedStrategyId((current) =>
        hasStrategy(dashboardPayload.summary, current) ? current : defaultStrategyId(dashboardPayload.summary)
      );
      setSelectedTradeStrategyId((current) =>
        hasStrategy(dashboardPayload.summary, current) ? current : defaultStrategyId(dashboardPayload.summary)
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load dashboard.");
    } finally {
      setLoadingDashboard(false);
    }
  }, [initialCapital, useRealData]);

  useEffect(() => {
    void loadDashboard();
  }, [loadDashboard]);

  useEffect(() => {
    if (!selectedStrategyId) {
      return;
    }
    setLoadingStrategy(true);
    setError(null);
    fetchStrategyDetail(selectedStrategyId, initialCapital, useRealData)
      .then(setStrategyDetail)
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Unable to load strategy.");
      })
      .finally(() => setLoadingStrategy(false));
  }, [initialCapital, selectedStrategyId, useRealData]);

  useEffect(() => {
    if (!selectedTradeStrategyId) {
      return;
    }
    setLoadingTrades(true);
    setError(null);
    fetchStrategyDetail(selectedTradeStrategyId, initialCapital, useRealData)
      .then((payload) => {
        setTradeDetail(payload);
        setSelectedActions(Array.from(new Set(payload.trade_history.map((row) => row.action))).sort());
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Unable to load trades.");
      })
      .finally(() => setLoadingTrades(false));
  }, [initialCapital, selectedTradeStrategyId, useRealData]);

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
  const etfSymbols = dashboard?.sample_etfs || DEFAULT_ETFS;
  const stockSymbols = dashboard?.sample_stocks || DEFAULT_STOCKS;
  const etfPriceRows = useMemo(
    () => chartRows(dashboard?.prices || {}, etfSymbols),
    [dashboard, etfSymbols]
  );
  const stockPriceRows = useMemo(
    () => chartRows(dashboard?.prices || {}, stockSymbols),
    [dashboard, stockSymbols]
  );
  const recentReturns = useMemo(
    () => strategyDetail?.daily_returns.slice(-126) || [],
    [strategyDetail]
  );
  const tradeRows = tradeDetail?.trade_history || [];
  const filteredTrades = useMemo(
    () => tradeRows.filter((row) => selectedActions.includes(row.action)),
    [selectedActions, tradeRows]
  );
  const actionOptions = useMemo(
    () => Array.from(new Set(tradeRows.map((row) => row.action))).sort(),
    [tradeRows]
  );
  const rebalanceEvents = useMemo(
    () => new Set(tradeRows.map((row) => row.trade_date)).size,
    [tradeRows]
  );
  const openMarks = useMemo(
    () => tradeRows.filter((row) => row.action === "Mark").length,
    [tradeRows]
  );

  async function handleRefreshYahoo() {
    setRefreshing(true);
    setError(null);
    try {
      const payload = await refreshYahooData(initialCapital);
      setDashboard(payload.dashboard);
      setUseRealData(true);
      setSelectedStrategyId((current) =>
        hasStrategy(payload.dashboard.summary, current) ? current : defaultStrategyId(payload.dashboard.summary)
      );
      setSelectedTradeStrategyId((current) =>
        hasStrategy(payload.dashboard.summary, current) ? current : defaultStrategyId(payload.dashboard.summary)
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to refresh Yahoo data.");
    } finally {
      setRefreshing(false);
    }
  }

  const best = dashboard ? bestStrategy(dashboard.summary) : null;
  const benchmark = dashboard ? selectedBenchmark(dashboard.summary) : null;
  const combined = dashboard?.summary.find((row) => row.name === "70/30 Combined Policy") || null;
  const policyJson = policy
    ? {
        benchmark: policy.benchmark_weights,
        live_trading_enabled: policy.live_trading_enabled,
        manual_approval_required: policy.manual_approval_required,
        long_only: policy.long_only,
        allow_margin: policy.allow_margin,
        allow_shorting: policy.allow_shorting,
        gross_exposure_cap_pct: policy.gross_exposure_cap_pct,
        risk_per_trade_default_pct: policy.risk_per_trade_default_pct,
        risk_per_trade_max_pct: policy.risk_per_trade_max_pct
      }
    : null;

  return (
    <div className="streamlit-shell">
      <aside className="sidebar">
        <label className="st-field">
          <span>Initial capital</span>
          <input
            type="number"
            min="1000"
            max="1000000"
            step="1000"
            value={initialCapital}
            onChange={(event) => setInitialCapital(Number(event.target.value))}
          />
        </label>
        <label className="st-checkbox">
          <input
            type="checkbox"
            checked={useRealData}
            onChange={(event) => setUseRealData(event.target.checked)}
          />
          <span>Use real historical data</span>
        </label>
        <button
          className="st-button"
          type="button"
          onClick={() => void handleRefreshYahoo()}
          disabled={!useRealData || refreshing}
        >
          <RefreshCcw size={15} />
          {refreshing ? "Refreshing Yahoo data" : "Refresh Yahoo data"}
        </button>
        <p className="sidebar-caption">Yahoo cache: var/market_data/yahoo_close_prices.csv</p>
      </aside>

      <main className="main">
        <h1>Trading Agent</h1>

        {dashboard?.is_real_data ? (
          <p className="caption">Using real historical adjusted-close data: {dashboard.data_source}</p>
        ) : (
          <div className="warning">
            <AlertTriangle size={18} />
            <div>
              <strong>Using deterministic synthetic fallback data.</strong>
              <span>Real-data download failed or was disabled.</span>
              {dashboard?.data_error ? <small>{dashboard.data_error}</small> : null}
            </div>
          </div>
        )}

        {error ? (
          <div className="warning error">
            <AlertTriangle size={18} />
            <div>
              <strong>Unable to reach the trading API.</strong>
              <span>{error}</span>
            </div>
          </div>
        ) : null}

        <section className="metric-row four">
          <Metric label="Best demo strategy" value={best?.name || "-"} delta={best ? formatPercent(best.total_return) : ""} />
          <Metric label="Combined policy" value={combined ? formatCurrency(combined.ending_value) : "-"} delta={combined ? formatPercent(combined.total_return) : ""} />
          <Metric label="50/50 benchmark" value={benchmark ? formatCurrency(benchmark.ending_value) : "-"} delta={benchmark ? formatPercent(benchmark.total_return) : ""} />
          <Metric label="Data mode" value={dashboard?.is_real_data ? "Real" : "Synthetic"} delta="Live trading disabled" />
        </section>

        <nav className="st-tabs" aria-label="Dashboard sections">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              type="button"
              className={activeTab === tab.id ? "st-tab active" : "st-tab"}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </nav>

        {activeTab === "overview" ? (
          <>
            <Section title="Demo Backtest Summary">
              <StrategySummaryTable
                rows={dashboard?.summary || []}
                selectedStrategyId={selectedStrategyId}
                onSelect={(strategyId) => {
                  setSelectedStrategyId(strategyId);
                  setActiveTab("strategy");
                }}
              />
            </Section>

            <Section title="Equity Curve">
              <ChartFrame loading={loadingDashboard}>
                <SeriesLineChart rows={equityRows} names={strategyNames} valueKind="currency" height={390} />
              </ChartFrame>
            </Section>

            <Section title="Drawdown">
              <ChartFrame loading={loadingDashboard}>
                <SeriesLineChart rows={drawdownRows} names={strategyNames} valueKind="percent" height={360} />
              </ChartFrame>
            </Section>
          </>
        ) : null}

        {activeTab === "strategy" ? (
          <>
            <label className="st-select">
              <span>Strategy</span>
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
            </label>

            {strategyDetail?.description ? <p className="caption">{strategyDetail.description}</p> : null}

            <section className="metric-row four compact">
              <Metric label="Ending value" value={strategyDetail ? formatCurrency(strategyDetail.summary.ending_value) : "-"} delta="" />
              <Metric label="Total return" value={strategyDetail ? formatPercent(strategyDetail.summary.total_return) : "-"} delta="" />
              <Metric label="Max drawdown" value={strategyDetail ? formatPercent(strategyDetail.summary.max_drawdown) : "-"} delta="" />
              <Metric label="Sharpe-like" value={strategyDetail ? formatNumber(strategyDetail.summary.sharpe_like) : "-"} delta="" />
            </section>

            <Section title="Latest Demo Weights">
              <ChartFrame loading={loadingStrategy}>
                {strategyDetail && strategyDetail.latest_weights.length > 0 ? (
                  <>
                    <WeightsChart rows={strategyDetail.latest_weights} />
                    <WeightsTable rows={strategyDetail.latest_weights} />
                  </>
                ) : (
                  <div className="info">This strategy is currently in cash in the demo path.</div>
                )}
              </ChartFrame>
            </Section>

            <Section title="Daily Returns">
              <ChartFrame loading={loadingStrategy}>
                <DailyReturnsChart rows={recentReturns} />
              </ChartFrame>
            </Section>
          </>
        ) : null}

        {activeTab === "trades" ? (
          <>
            <label className="st-select">
              <span>Strategy</span>
              <select
                value={selectedTradeStrategyId}
                onChange={(event) => setSelectedTradeStrategyId(event.target.value)}
              >
                {dashboard?.summary.map((strategy) => (
                  <option key={strategy.id} value={strategy.id}>
                    {strategy.name}
                  </option>
                ))}
              </select>
            </label>

            <section className="metric-row three compact">
              <Metric label="Trade rows" value={tradeRows.length.toLocaleString()} delta="" />
              <Metric label="Rebalance events" value={rebalanceEvents.toLocaleString()} delta="" />
              <Metric label="Open marks" value={openMarks.toLocaleString()} delta="" />
            </section>

            <ChartFrame loading={loadingTrades}>
              {tradeRows.length === 0 ? (
                <div className="info">No simulated trades were generated for this strategy.</div>
              ) : (
                <>
                  <label className="st-multiselect">
                    <span>Action</span>
                    <div>
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
                  </label>
                  <TradesTable rows={filteredTrades} />
                  <button
                    className="st-button download"
                    type="button"
                    onClick={() => downloadTrades(tradeDetail?.summary.name || "strategy", filteredTrades)}
                  >
                    <Download size={15} />
                    Download trades CSV
                  </button>
                </>
              )}
            </ChartFrame>
          </>
        ) : null}

        {activeTab === "universe" ? (
          <>
            <Section title="ETF Prices">
              {etfPriceRows.length > 0 ? (
                <SeriesLineChart rows={etfPriceRows} names={etfSymbols} valueKind="price" height={390} />
              ) : (
                <div className="info">Price data is unavailable for the ETF universe.</div>
              )}
            </Section>

            <Section title="Stock Prices">
              {stockPriceRows.length > 0 ? (
                <SeriesLineChart rows={stockPriceRows} names={stockSymbols} valueKind="price" height={390} />
              ) : (
                <div className="info">Price data is unavailable for the stock universe.</div>
              )}
            </Section>
          </>
        ) : null}

        {activeTab === "policy" ? (
          <>
            <Section title="Policy">
              <pre className="json-block">{JSON.stringify(policyJson, null, 2)}</pre>
            </Section>
            <Section title="Recommendations">
              <div className="info">No recommendations file found at var/recommendations.json.</div>
            </Section>
          </>
        ) : null}

        <p className="footer">Demo/backtest returns are not live-trading proof.</p>
      </main>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="st-section">
      <h2>{title}</h2>
      {children}
    </section>
  );
}

function Metric({ label, value, delta }: { label: string; value: string; delta: string }) {
  return (
    <div className="st-metric">
      <span>{label}</span>
      <strong>{value}</strong>
      {delta ? <small>{delta}</small> : null}
    </div>
  );
}

function ChartFrame({ loading, children }: { loading: boolean; children: React.ReactNode }) {
  if (loading) {
    return <div className="loading">Running...</div>;
  }
  return children;
}

function SeriesLineChart({
  rows,
  names,
  valueKind,
  height
}: {
  rows: Record<string, string | number>[];
  names: string[];
  valueKind: "currency" | "percent" | "price";
  height: number;
}) {
  return (
    <div className="chart-box" style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={rows} margin={{ top: 12, right: 24, left: 6, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
          <XAxis dataKey="date" tickFormatter={compactDate} minTickGap={42} tickLine={false} axisLine={false} />
          <YAxis tickFormatter={(value) => formatAxis(value, valueKind)} tickLine={false} axisLine={false} width={72} />
          <Tooltip formatter={(value) => formatTooltip(Number(value), valueKind)} labelFormatter={(label) => compactDate(String(label))} />
          <Legend wrapperStyle={{ paddingTop: 12 }} />
          {names.map((name, index) => (
            <Line
              key={name}
              type="monotone"
              dataKey={name}
              dot={false}
              stroke={COLORS[index % COLORS.length]}
              strokeWidth={2}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function WeightsChart({ rows }: { rows: WeightRow[] }) {
  return (
    <div className="chart-box compact-chart">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} margin={{ top: 12, right: 24, left: 6, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
          <XAxis dataKey="symbol" tickLine={false} axisLine={false} />
          <YAxis tickFormatter={(value) => formatPercent(Number(value), 0)} tickLine={false} axisLine={false} />
          <Tooltip formatter={(value) => formatPercent(Number(value))} />
          <Bar dataKey="weight" fill="#ff4b4b" radius={[3, 3, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function DailyReturnsChart({ rows }: { rows: DailyReturnRow[] }) {
  return (
    <div className="chart-box" style={{ height: 390 }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} margin={{ top: 12, right: 24, left: 6, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
          <XAxis dataKey="date" tickFormatter={compactDate} minTickGap={24} tickLine={false} axisLine={false} />
          <YAxis tickFormatter={(value) => formatPercent(Number(value), 0)} tickLine={false} axisLine={false} />
          <Tooltip formatter={(value) => formatPercent(Number(value), 2)} labelFormatter={(label) => compactDate(String(label))} />
          <Bar dataKey="daily_return" fill="#ff4b4b" radius={[2, 2, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function StrategySummaryTable({
  rows,
  selectedStrategyId,
  onSelect
}: {
  rows: StrategySummary[];
  selectedStrategyId: string;
  onSelect: (strategyId: string) => void;
}) {
  return (
    <div className="dataframe summary-table">
      <table>
        <thead>
          <tr>
            <th>Strategy</th>
            <th>Sleeve</th>
            <th>Ending Value</th>
            <th>Total Return</th>
            <th>Annualized Return</th>
            <th>Max Drawdown</th>
            <th>Volatility</th>
            <th>Sharpe-like</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr
              key={row.id}
              className={row.id === selectedStrategyId ? "selected" : ""}
              onClick={() => onSelect(row.id)}
            >
              <td>{row.name}</td>
              <td>{row.sleeve}</td>
              <td>{formatCurrency(row.ending_value)}</td>
              <td>{formatPercent(row.total_return)}</td>
              <td>{formatPercent(row.annualized_return)}</td>
              <td>{formatPercent(row.max_drawdown)}</td>
              <td>{formatPercent(row.volatility)}</td>
              <td>{formatNumber(row.sharpe_like)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function WeightsTable({ rows }: { rows: WeightRow[] }) {
  return (
    <div className="dataframe weights-table">
      <table>
        <thead>
          <tr>
            <th>Symbol</th>
            <th>Weight</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.symbol}>
              <td>{row.symbol}</td>
              <td>{formatPercent(row.weight)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function TradesTable({ rows }: { rows: TradeRow[] }) {
  return (
    <div className="dataframe trades-table">
      <table>
        <thead>
          <tr>
            <th>Strategy</th>
            <th>Source Strategy</th>
            <th>Sleeve</th>
            <th>Trade Date</th>
            <th>Entry Date</th>
            <th>Exit/Trim Date</th>
            <th>Symbol</th>
            <th>Action</th>
            <th>Previous Weight</th>
            <th>Target Weight</th>
            <th>Weight Change</th>
            <th>Price</th>
            <th>Transaction Cost</th>
            <th>Realized/Marked Return</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={`${row.trade_date}-${row.symbol}-${row.action}-${index}`}>
              <td>{row.strategy}</td>
              <td>{row.source_strategy}</td>
              <td>{row.sleeve}</td>
              <td>{row.trade_date}</td>
              <td>{row.entry_date || ""}</td>
              <td>{row.exit_trim_date || ""}</td>
              <td>{row.symbol}</td>
              <td>{row.action}</td>
              <td>{formatPercent(row.previous_weight)}</td>
              <td>{formatPercent(row.target_weight)}</td>
              <td>{formatSignedPercent(row.weight_change)}</td>
              <td>{formatPrice(row.price)}</td>
              <td>{formatPercent(row.transaction_cost, 3)}</td>
              <td>{row.realized_marked_return === null ? "" : formatPercent(row.realized_marked_return)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function formatAxis(value: unknown, valueKind: "currency" | "percent" | "price") {
  const numeric = Number(value);
  if (valueKind === "percent") {
    return formatPercent(numeric, 0);
  }
  if (valueKind === "currency") {
    return `$${Math.round(numeric / 1000)}k`;
  }
  return `$${Math.round(numeric)}`;
}

function formatTooltip(value: number, valueKind: "currency" | "percent" | "price") {
  if (valueKind === "percent") {
    return formatPercent(value);
  }
  if (valueKind === "currency") {
    return formatCurrency(value);
  }
  return formatPrice(value);
}
