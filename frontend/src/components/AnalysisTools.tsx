import { useEffect, useMemo, useState } from "react";
import Plot from "react-plotly.js";
import Plotly from "plotly.js-dist-min";

import { AnalysisRequest, AnalysisResponse, AnalysisType } from "../types";

interface Props {
  columns: string[];
  defaultTimeColumn: string | null;
  defaultVariables: string[];
  running: boolean;
  result: AnalysisResponse | null;
  onRun: (payload: AnalysisRequest) => Promise<void>;
}

interface DescriptiveStatsRow {
  column: string;
  count: number | null;
  mean: number | null;
  std: number | null;
  min: number | null;
  "25%": number | null;
  "50%": number | null;
  "75%": number | null;
  max: number | null;
}

interface DescriptiveStatsAnalysisResult {
  columns: string[];
  summary: DescriptiveStatsRow[];
}

type PrimitiveDisplayValue = string | number | boolean | null;

interface DiurnalPoint {
  hour: number;
  mean: number | null;
  std: number | null;
  min: number | null;
  max: number | null;
  count: number;
}

interface DiurnalSeasonPoint extends DiurnalPoint {
  season: string;
}

interface DiurnalCycleAnalysisResult {
  time_column: string;
  target_column: string;
  timezone_offset_hours: number;
  valid_rows: number;
  data_quality: {
    observed_hours: number;
    complete_24_hour_profile: boolean;
  };
  summary: {
    diurnal_range: number | null;
    warmest_hour: number | null;
    warmest_value: number | null;
    coolest_hour: number | null;
    coolest_value: number | null;
  };
  hourly_profile: DiurnalPoint[];
  seasonal_hourly_profile: DiurnalSeasonPoint[];
}

interface ClimatologyPoint {
  month?: number;
  month_label?: string;
  season?: string;
  mean: number | null;
  std: number | null;
  min: number | null;
  max: number | null;
  count: number;
}

interface SeasonalClimatologyAnalysisResult {
  time_column: string;
  target_column: string;
  valid_rows: number;
  data_quality: {
    observed_months: number;
    complete_12_month_profile: boolean;
  };
  summary: {
    annual_mean: number | null;
    warmest_month: number | null;
    warmest_month_label: string | null;
    warmest_value: number | null;
    coolest_month: number | null;
    coolest_month_label: string | null;
    coolest_value: number | null;
    seasonal_range: number | null;
  };
  monthly_climatology: ClimatologyPoint[];
  seasonal_cycle: ClimatologyPoint[];
}

interface AnnualTrendPoint {
  year: number;
  mean: number | null;
  std: number | null;
  min: number | null;
  max: number | null;
  count: number;
  trend: number | null;
}

interface AnnualTrendSignalAnalysisResult {
  time_column: string;
  target_column: string;
  valid_rows: number;
  daily_periods: number;
  annual_periods: number;
  data_quality: {
    observed_years: number;
  };
  summary: {
    slope_per_year: number | null;
    warming_per_decade: number | null;
    slope_per_decade: number | null;
    total_change: number | null;
    r2: number | null;
    trend_direction: string;
    coldest_year: number | null;
    coldest_value: number | null;
    warmest_year: number | null;
    warmest_value: number | null;
    lowest_year?: number | null;
    lowest_value?: number | null;
    highest_year?: number | null;
    highest_value?: number | null;
  };
  annual_series: AnnualTrendPoint[];
}

interface BaselineAnomalyPoint {
  year: number;
  anomaly: number | null;
  std: number | null;
  min: number | null;
  max: number | null;
  count: number;
}

interface BaselineAnomaliesAnalysisResult {
  time_column: string;
  target_column: string;
  valid_rows: number;
  daily_periods: number;
  annual_periods: number;
  data_quality: {
    observed_years: number;
    baseline_months: number;
    complete_12_month_baseline: boolean;
  };
  baseline: {
    start: string;
    end: string;
    requested_start: string | null;
    requested_end: string | null;
    used_requested_period: boolean;
    periods: number;
    mean: number | null;
    observed_months: number;
  };
  summary: {
    baseline_mean: number | null;
    most_negative_year: number | null;
    most_negative_anomaly: number | null;
    most_positive_year: number | null;
    most_positive_anomaly: number | null;
    negative_years: number;
    positive_years: number;
  };
  annual_anomalies: BaselineAnomalyPoint[];
}

interface ExtremeEventPoint {
  year: number;
  high_days: number;
  low_days: number;
  observed_days: number;
  high_trend: number | null;
  low_trend: number | null;
}

interface ExtremeEventsAnalysisResult {
  time_column: string;
  target_column: string;
  valid_rows: number;
  daily_periods: number;
  annual_periods: number;
  data_quality: {
    observed_years: number;
  };
  thresholds: {
    high_quantile: number;
    low_quantile: number;
    high_threshold: number | null;
    low_threshold: number | null;
  };
  summary: {
    high_threshold: number | null;
    low_threshold: number | null;
    high_trend_per_decade: number | null;
    low_trend_per_decade: number | null;
    high_total_days: number;
    low_total_days: number;
    max_high_year: number | null;
    max_high_days: number | null;
    max_low_year: number | null;
    max_low_days: number | null;
  };
  annual_extremes: ExtremeEventPoint[];
}

interface DecadalHistogram {
  decade: number;
  label: string;
  count: number;
  bin_edges: Array<number | null>;
  density: Array<number | null>;
  step_x: Array<number | null>;
  step_y: Array<number | null>;
}

interface DecadalStatistic {
  decade: number;
  label: string;
  count: number;
  mean: number | null;
  std: number | null;
  min: number | null;
  q05: number | null;
  q25: number | null;
  median: number | null;
  q75: number | null;
  q95: number | null;
  max: number | null;
}

interface DecadalDistributionsAnalysisResult {
  time_column: string;
  target_column: string;
  valid_rows: number;
  daily_periods: number;
  settings: {
    bins: number;
  };
  data_quality: {
    observed_decades: number;
  };
  summary: {
    first_decade: DecadalStatistic;
    last_decade: DecadalStatistic;
    lowest_mean_decade: DecadalStatistic;
    highest_mean_decade: DecadalStatistic;
    mean_shift_first_to_last: number | null;
  };
  decadal_statistics: DecadalStatistic[];
  decadal_histograms: DecadalHistogram[];
}

const SEASON_ORDER = ["winter", "spring", "summer", "autumn"] as const;
type SeasonName = (typeof SEASON_ORDER)[number];

const SEASON_LABELS: Record<SeasonName, string> = {
  winter: "Winter",
  spring: "Spring",
  summer: "Summer",
  autumn: "Autumn",
};

const SEASON_COLORS: Record<SeasonName, string> = {
  winter: "#2563eb",
  spring: "#16a34a",
  summer: "#dc2626",
  autumn: "#f59e0b",
};

const DECADE_COLORS = [
  "#5b5f97",
  "#4f87b5",
  "#62b6cb",
  "#9bc1bc",
  "#f4d35e",
  "#ee964b",
  "#f26d5b",
  "#c94f7c",
  "#7c3aed",
  "#0f766e",
];

const ANALYSIS_OPTIONS: Array<{ value: AnalysisType; label: string }> = [
  { value: "descriptive_stats", label: "Descriptive statistics" },
  { value: "trend_detection", label: "Trend detection" },
  { value: "correlation", label: "Correlation" },
  { value: "linear_regression", label: "Linear regression" },
  { value: "temperature_trend", label: "Temperature trend" },
  { value: "precipitation_trend", label: "Precipitation trend" },
  { value: "seasonal_patterns", label: "Seasonal patterns" },
  { value: "diurnal_cycle", label: "Diurnal cycle" },
  { value: "annual_trend_signal", label: "Annual trend signal" },
  { value: "baseline_anomalies", label: "Baseline anomalies" },
  { value: "extreme_events", label: "Extreme events" },
  { value: "decadal_distributions", label: "Decadal distributions" },
  { value: "anomaly_detection", label: "Anomaly detection" },
  { value: "random_forest_regression", label: "Random forest regression" },
  { value: "time_series_forecasting", label: "Time series forecasting" },
  { value: "climate_workflow", label: "Climate workflow" },
];

export function AnalysisTools({
  columns,
  defaultTimeColumn,
  defaultVariables,
  running,
  result,
  onRun,
}: Props) {
  const [analysisType, setAnalysisType] = useState<AnalysisType>("descriptive_stats");
  const [targetColumn, setTargetColumn] = useState<string>("");
  const [timeColumn, setTimeColumn] = useState<string>("");
  const [featureColumns, setFeatureColumns] = useState<string[]>([]);
  const [horizon, setHorizon] = useState<number>(12);
  const [zThreshold, setZThreshold] = useState<number>(2);
  const [aggregationFrequency, setAggregationFrequency] = useState<"D" | "ME" | "YE">("D");
  const [baselineStart, setBaselineStart] = useState<string>("");
  const [baselineEnd, setBaselineEnd] = useState<string>("");
  const [hourOffset, setHourOffset] = useState<number>(0);
  const [highQuantile, setHighQuantile] = useState<number>(0.95);
  const [lowQuantile, setLowQuantile] = useState<number>(0.05);
  const [histogramBins, setHistogramBins] = useState<number>(50);

  useEffect(() => {
    setTimeColumn(defaultTimeColumn ?? "");
    setTargetColumn(defaultVariables[0] ?? columns[0] ?? "");
    setFeatureColumns(defaultVariables.slice(1, 4));
  }, [defaultTimeColumn, defaultVariables, columns]);

  const toggleFeature = (column: string): void => {
    setFeatureColumns((prev) =>
      prev.includes(column) ? prev.filter((item) => item !== column) : [...prev, column],
    );
  };

  const usesFeatureColumns = [
    "descriptive_stats",
    "correlation",
    "linear_regression",
    "random_forest_regression",
  ].includes(analysisType);

  const options = useMemo(() => {
    const base: Record<string, unknown> = {};
    if (analysisType === "anomaly_detection") {
      base.z_threshold = zThreshold;
    }
    if (analysisType === "time_series_forecasting") {
      base.horizon = horizon;
      base.lags = 6;
    }
    if (analysisType === "diurnal_cycle") {
      base.timezone_offset_hours = hourOffset;
    }
    if (analysisType === "extreme_events") {
      base.high_quantile = highQuantile;
      base.low_quantile = lowQuantile;
    }
    if (analysisType === "decadal_distributions") {
      base.bins = histogramBins;
    }
    if (analysisType === "climate_workflow" || analysisType === "baseline_anomalies") {
      base.aggregation_frequency = aggregationFrequency;
      if (baselineStart) {
        base.baseline_start = baselineStart;
      }
      if (baselineEnd) {
        base.baseline_end = baselineEnd;
      }
    }
    return base;
  }, [
    aggregationFrequency,
    analysisType,
    baselineEnd,
    baselineStart,
    highQuantile,
    histogramBins,
    horizon,
    hourOffset,
    lowQuantile,
    zThreshold,
  ]);

  const run = async (): Promise<void> => {
    await onRun({
      analysis_type: analysisType,
      target_column: targetColumn || null,
      feature_columns: featureColumns,
      time_column: timeColumn || null,
      options,
    });
  };

  return (
    <section className="panel analysis-panel">
      <div className="panel-header">
        <h2>Analysis Tools</h2>
      </div>

      {columns.length === 0 ? (
        <p className="muted">Select a dataset to run analyses.</p>
      ) : (
        <>
          <div className="form-grid">
            <label>
              <span>Analysis type</span>
              <select value={analysisType} onChange={(event) => setAnalysisType(event.target.value as AnalysisType)}>
                {ANALYSIS_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>

            <label>
              <span>Target variable</span>
              <select value={targetColumn} onChange={(event) => setTargetColumn(event.target.value)}>
                <option value="">Auto</option>
                {columns.map((column) => (
                  <option key={column} value={column}>
                    {column}
                  </option>
                ))}
              </select>
            </label>

            <label>
              <span>Time column</span>
              <select value={timeColumn} onChange={(event) => setTimeColumn(event.target.value)}>
                <option value="">Auto</option>
                {columns.map((column) => (
                  <option key={column} value={column}>
                    {column}
                  </option>
                ))}
              </select>
            </label>
          </div>

          {usesFeatureColumns ? (
            <div className="variables-list">
              <p>Feature columns</p>
              <div className="tag-grid">
                {columns.map((column) => (
                  <button
                    key={column}
                    type="button"
                    className={`tag ${featureColumns.includes(column) ? "tag-active" : ""}`}
                    onClick={() => toggleFeature(column)}
                  >
                    {column}
                  </button>
                ))}
              </div>
            </div>
          ) : null}

          {analysisType === "anomaly_detection" ? (
            <label>
              <span>Z-threshold</span>
              <input
                type="number"
                min={0.5}
                step={0.1}
                value={zThreshold}
                onChange={(event) => setZThreshold(Number(event.target.value))}
              />
            </label>
          ) : null}

          {analysisType === "time_series_forecasting" ? (
            <label>
              <span>Forecast horizon</span>
              <input
                type="number"
                min={1}
                max={120}
                value={horizon}
                onChange={(event) => setHorizon(Number(event.target.value))}
              />
            </label>
          ) : null}

          {analysisType === "diurnal_cycle" ? (
            <label className="inline-field">
              <span>Hour offset</span>
              <input
                type="number"
                min={-14}
                max={14}
                step={0.5}
                value={hourOffset}
                onChange={(event) => setHourOffset(Number(event.target.value))}
              />
            </label>
          ) : null}

          {analysisType === "extreme_events" ? (
            <div className="form-grid">
              <label>
                <span>High percentile</span>
                <input
                  type="number"
                  min={50}
                  max={99.9}
                  step={0.5}
                  value={Number((highQuantile * 100).toFixed(1))}
                  onChange={(event) => setHighQuantile(Number(event.target.value) / 100)}
                />
              </label>
              <label>
                <span>Low percentile</span>
                <input
                  type="number"
                  min={0.1}
                  max={50}
                  step={0.5}
                  value={Number((lowQuantile * 100).toFixed(1))}
                  onChange={(event) => setLowQuantile(Number(event.target.value) / 100)}
                />
              </label>
            </div>
          ) : null}

          {analysisType === "decadal_distributions" ? (
            <label className="inline-field">
              <span>Bins</span>
              <input
                type="number"
                min={10}
                max={100}
                step={5}
                value={histogramBins}
                onChange={(event) => setHistogramBins(Number(event.target.value))}
              />
            </label>
          ) : null}

          {analysisType === "climate_workflow" || analysisType === "baseline_anomalies" ? (
            <div className="form-grid">
              {analysisType === "climate_workflow" ? (
                <label>
                  <span>Aggregation</span>
                  <select
                    value={aggregationFrequency}
                    onChange={(event) => setAggregationFrequency(event.target.value as "D" | "ME" | "YE")}
                  >
                    <option value="D">Daily</option>
                    <option value="ME">Monthly</option>
                    <option value="YE">Yearly</option>
                  </select>
                </label>
              ) : null}
              <label>
                <span>Baseline start</span>
                <input
                  type="date"
                  value={baselineStart}
                  onChange={(event) => setBaselineStart(event.target.value)}
                />
              </label>
              <label>
                <span>Baseline end</span>
                <input
                  type="date"
                  value={baselineEnd}
                  onChange={(event) => setBaselineEnd(event.target.value)}
                />
              </label>
            </div>
          ) : null}

          <button type="button" className="primary-btn" disabled={running} onClick={run}>
            {running ? "Running..." : "Run Analysis"}
          </button>

          {result ? (
            <div className="result-panel">
              <h3>Analysis Result</h3>
              {result.analysis_type === "diurnal_cycle" ? (
                <DiurnalCycleResultView result={result.result as unknown as DiurnalCycleAnalysisResult} />
              ) : result.analysis_type === "seasonal_patterns" ? (
                <SeasonalClimatologyResultView
                  result={result.result as unknown as SeasonalClimatologyAnalysisResult}
                />
              ) : result.analysis_type === "annual_trend_signal" ? (
                <AnnualTrendSignalResultView
                  result={result.result as unknown as AnnualTrendSignalAnalysisResult}
                />
              ) : result.analysis_type === "baseline_anomalies" ? (
                <BaselineAnomaliesResultView
                  result={result.result as unknown as BaselineAnomaliesAnalysisResult}
                />
              ) : result.analysis_type === "extreme_events" ? (
                <ExtremeEventsResultView
                  result={result.result as unknown as ExtremeEventsAnalysisResult}
                />
              ) : result.analysis_type === "descriptive_stats" ? (
                <DescriptiveStatsResultView
                  result={result.result as unknown as DescriptiveStatsAnalysisResult}
                />
              ) : result.analysis_type === "decadal_distributions" ? (
                <DecadalDistributionsResultView
                  result={result.result as unknown as DecadalDistributionsAnalysisResult}
                />
              ) : (
                <ReadableAnalysisResultView result={result.result} />
              )}
            </div>
          ) : null}
        </>
      )}
    </section>
  );
}

function ReadableAnalysisResultView({ result }: { result: Record<string, unknown> }) {
  const entries = Object.entries(result);
  const primitiveEntries = entries.filter(([, value]) => isPrimitiveDisplayValue(value));
  const arrayEntries = entries.filter(([, value]) => Array.isArray(value)) as Array<[string, unknown[]]>;
  const objectEntries = entries.filter(([, value]) => isPlainObject(value)) as Array<[string, Record<string, unknown>]>;

  if (entries.length === 0) {
    return <p className="muted">No result values returned.</p>;
  }

  return (
    <div className="analysis-rich-result">
      {primitiveEntries.length > 0 ? (
        <div className="analysis-result-grid">
          {primitiveEntries.map(([key, value]) => (
            <AnalysisStat key={key} label={humanizeKey(key)} value={formatDisplayValue(value)} />
          ))}
        </div>
      ) : null}

      {arrayEntries.map(([key, value]) => (
        <ResultArraySection key={key} title={humanizeKey(key)} values={value} />
      ))}

      {objectEntries.map(([key, value]) => (
        <ResultObjectSection key={key} title={humanizeKey(key)} value={value} />
      ))}
    </div>
  );
}

function ResultArraySection({ title, values }: { title: string; values: unknown[] }) {
  const records = values.filter(isPlainObject);
  const allValuesAreRecords = records.length === values.length && records.length > 0;
  const headers = allValuesAreRecords
    ? Array.from(new Set(records.flatMap((record) => Object.keys(record)))).slice(0, 12)
    : [];
  const previewRows = records.slice(0, 50);
  const primitivePreview = values.slice(0, 20).filter(isPrimitiveDisplayValue);

  return (
    <div className="analysis-chart-card">
      <h4>{title}</h4>
      {allValuesAreRecords ? (
        <>
          <div className="analysis-table-wrapper">
            <table className="analysis-table">
              <thead>
                <tr>
                  {headers.map((header) => (
                    <th key={header}>{humanizeKey(header)}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {previewRows.map((row, index) => (
                  <tr key={index}>
                    {headers.map((header) => (
                      <td key={header}>{formatDisplayValue(row[header])}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {values.length > previewRows.length ? (
            <p className="muted">Showing first {previewRows.length} of {values.length} rows.</p>
          ) : null}
        </>
      ) : primitivePreview.length > 0 ? (
        <div className="analysis-context-row">
          {primitivePreview.map((value, index) => (
            <span key={`${String(value)}-${index}`}>{formatDisplayValue(value)}</span>
          ))}
        </div>
      ) : (
        <p className="muted">{values.length} items returned.</p>
      )}
    </div>
  );
}

function ResultObjectSection({ title, value }: { title: string; value: Record<string, unknown> }) {
  return (
    <div className="analysis-chart-card">
      <h4>{title}</h4>
      <div className="analysis-table-wrapper">
        <table className="analysis-table">
          <tbody>
            {Object.entries(value).map(([key, item]) => (
              <tr key={key}>
                <td>{humanizeKey(key)}</td>
                <td>{formatDisplayValue(item)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function DescriptiveStatsResultView({ result }: { result: DescriptiveStatsAnalysisResult }) {
  const summary = result.summary ?? [];
  const primary = summary[0];
  const selectedColumns = result.columns?.length ? result.columns : summary.map((row) => row.column);

  return (
    <div className="analysis-rich-result">
      <div className="analysis-result-grid">
        <AnalysisStat label="Variables" value={formatInteger(selectedColumns.length)} />
        <AnalysisStat label="Primary variable" value={primary?.column ?? "-"} />
        <AnalysisStat label="Rows" value={formatInteger(primary?.count)} />
        <AnalysisStat label="Mean" value={formatNullable(primary?.mean)} />
        <AnalysisStat label="Median" value={formatNullable(primary?.["50%"])} />
        <AnalysisStat label="Range" value={formatRange(primary?.min, primary?.max)} />
      </div>

      <div className="analysis-chart-card">
        <h4>Descriptive Statistics</h4>
        {summary.length > 0 ? (
          <div className="analysis-table-wrapper">
            <table className="analysis-table">
              <thead>
                <tr>
                  <th>Variable</th>
                  <th>Count</th>
                  <th>Mean</th>
                  <th>Std</th>
                  <th>Min</th>
                  <th>Q25</th>
                  <th>Median</th>
                  <th>Q75</th>
                  <th>Max</th>
                  <th>Range</th>
                </tr>
              </thead>
              <tbody>
                {summary.map((row) => (
                  <tr key={row.column}>
                    <td>{row.column}</td>
                    <td>{formatInteger(row.count)}</td>
                    <td>{formatNullable(row.mean)}</td>
                    <td>{formatNullable(row.std)}</td>
                    <td>{formatNullable(row.min)}</td>
                    <td>{formatNullable(row["25%"])}</td>
                    <td>{formatNullable(row["50%"])}</td>
                    <td>{formatNullable(row["75%"])}</td>
                    <td>{formatNullable(row.max)}</td>
                    <td>{formatRange(row.min, row.max)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="muted">No numeric summary returned.</p>
        )}
      </div>

      {selectedColumns.length > 0 ? (
        <div className="analysis-context-row">
          {selectedColumns.map((column) => (
            <span key={column}>{column}</span>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function DecadalDistributionsResultView({ result }: { result: DecadalDistributionsAnalysisResult }) {
  const histograms = result.decadal_histograms ?? [];
  const statistics = result.decadal_statistics ?? [];

  const traces = useMemo<Plotly.Data[]>(
    () =>
      histograms.map((item, index) => ({
        type: "scatter",
        mode: "lines",
        name: item.label,
        x: item.step_x,
        y: item.step_y,
        line: {
          color: DECADE_COLORS[index % DECADE_COLORS.length],
          width: 2.4,
        },
        opacity: 0.82,
        hovertemplate: `${item.label}<br>${result.target_column} %{x:.2f}<br>Density %{y:.4f}<extra></extra>`,
      })),
    [histograms, result.target_column],
  );

  const layout = {
    margin: { l: 64, r: 24, t: 28, b: 56 },
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "#ffffff",
    xaxis: { title: { text: `Daily mean ${result.target_column}` } },
    yaxis: { title: { text: "Density" } },
    legend: { orientation: "v", x: 1.02, y: 1 },
    hovermode: "closest",
  };

  return (
    <div className="analysis-rich-result">
      <div className="analysis-result-grid">
        <AnalysisStat label="Decades" value={formatInteger(result.data_quality?.observed_decades)} />
        <AnalysisStat
          label="First mean"
          value={`${result.summary?.first_decade?.label ?? "-"} (${formatNullable(
            result.summary?.first_decade?.mean,
          )})`}
        />
        <AnalysisStat
          label="Last mean"
          value={`${result.summary?.last_decade?.label ?? "-"} (${formatNullable(
            result.summary?.last_decade?.mean,
          )})`}
        />
        <AnalysisStat label="Mean shift" value={formatSignedNumber(result.summary?.mean_shift_first_to_last)} />
      </div>

      <div className="analysis-chart-card">
        <h4>Distribution by Decade</h4>
        <Plot
          data={traces}
          layout={layout as unknown as Plotly.Layout}
          style={{ width: "100%", height: "460px" }}
          config={{ responsive: true, displaylogo: false }}
        />
      </div>

      <div className="analysis-chart-card">
        <h4>Decadal Statistics</h4>
        <div className="analysis-table-wrapper">
          <table className="analysis-table">
            <thead>
              <tr>
                <th>Decade</th>
                <th>Mean</th>
                <th>Std</th>
                <th>Min</th>
                <th>Median</th>
                <th>Max</th>
                <th>Days</th>
              </tr>
            </thead>
            <tbody>
              {statistics.map((item) => (
                <tr key={item.decade}>
                  <td>{item.label}</td>
                  <td>{formatNullable(item.mean)}</td>
                  <td>{formatNullable(item.std)}</td>
                  <td>{formatNullable(item.min)}</td>
                  <td>{formatNullable(item.median)}</td>
                  <td>{formatNullable(item.max)}</td>
                  <td>{formatInteger(item.count)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="analysis-context-row">
        <span>{result.target_column}</span>
        <span>{result.time_column}</span>
        <span>{result.settings?.bins ?? 50} bins</span>
        <span>{formatInteger(result.daily_periods)} daily periods</span>
      </div>
    </div>
  );
}

function ExtremeEventsResultView({ result }: { result: ExtremeEventsAnalysisResult }) {
  const annualExtremes = result.annual_extremes ?? [];
  const years = annualExtremes.map((point) => point.year);
  const highDays = annualExtremes.map((point) => point.high_days);
  const lowDays = annualExtremes.map((point) => point.low_days);
  const highTrend = annualExtremes.map((point) => point.high_trend);
  const lowTrend = annualExtremes.map((point) => point.low_trend);

  const highTraces = useMemo<Plotly.Data[]>(
    () => [
      {
        type: "bar",
        name: "High extreme days",
        x: years,
        y: highDays,
        marker: { color: "#f97316" },
        opacity: 0.84,
        hovertemplate: "Year %{x}<br>Days %{y}<extra></extra>",
      },
      {
        type: "scatter",
        mode: "lines",
        name: `Trend ${formatSignedNumber(result.summary?.high_trend_per_decade, 1)} days/decade`,
        x: years,
        y: highTrend,
        line: { color: "#dc2626", width: 3 },
        hovertemplate: "Trend %{y:.1f}<extra></extra>",
      },
    ],
    [highDays, highTrend, result.summary?.high_trend_per_decade, years],
  );

  const lowTraces = useMemo<Plotly.Data[]>(
    () => [
      {
        type: "bar",
        name: "Low extreme days",
        x: years,
        y: lowDays,
        marker: { color: "#5f95bd" },
        opacity: 0.84,
        hovertemplate: "Year %{x}<br>Days %{y}<extra></extra>",
      },
      {
        type: "scatter",
        mode: "lines",
        name: `Trend ${formatSignedNumber(result.summary?.low_trend_per_decade, 1)} days/decade`,
        x: years,
        y: lowTrend,
        line: { color: "#2563eb", width: 3 },
        hovertemplate: "Trend %{y:.1f}<extra></extra>",
      },
    ],
    [lowDays, lowTrend, result.summary?.low_trend_per_decade, years],
  );

  const sharedLayout = {
    margin: { l: 56, r: 20, t: 28, b: 52 },
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "#ffffff",
    xaxis: { title: { text: "Year" } },
    yaxis: { title: { text: "Number of days" } },
    legend: { orientation: "h" },
    hovermode: "x unified",
    bargap: 0.2,
  };

  return (
    <div className="analysis-rich-result">
      <div className="analysis-result-grid">
        <AnalysisStat label="High threshold" value={formatNullable(result.summary?.high_threshold)} />
        <AnalysisStat label="Low threshold" value={formatNullable(result.summary?.low_threshold)} />
        <AnalysisStat
          label="High trend"
          value={`${formatSignedNumber(result.summary?.high_trend_per_decade, 1)} days/decade`}
        />
        <AnalysisStat
          label="Low trend"
          value={`${formatSignedNumber(result.summary?.low_trend_per_decade, 1)} days/decade`}
        />
        <AnalysisStat
          label="Peak high year"
          value={`${result.summary?.max_high_year ?? "-"} (${formatInteger(result.summary?.max_high_days)})`}
        />
        <AnalysisStat
          label="Peak low year"
          value={`${result.summary?.max_low_year ?? "-"} (${formatInteger(result.summary?.max_low_days)})`}
        />
      </div>

      <div className="analysis-chart-grid">
        <div className="analysis-chart-card">
          <h4>High Extreme Days</h4>
          <Plot
            data={highTraces}
            layout={sharedLayout as unknown as Plotly.Layout}
            style={{ width: "100%", height: "380px" }}
            config={{ responsive: true, displaylogo: false }}
          />
        </div>
        <div className="analysis-chart-card">
          <h4>Low Extreme Days</h4>
          <Plot
            data={lowTraces}
            layout={sharedLayout as unknown as Plotly.Layout}
            style={{ width: "100%", height: "380px" }}
            config={{ responsive: true, displaylogo: false }}
          />
        </div>
      </div>

      <div className="analysis-context-row">
        <span>{result.target_column}</span>
        <span>{result.time_column}</span>
        <span>High {formatPercentile(result.thresholds?.high_quantile)}</span>
        <span>Low {formatPercentile(result.thresholds?.low_quantile)}</span>
        <span>{formatInteger(result.valid_rows)} valid rows</span>
      </div>
    </div>
  );
}

function BaselineAnomaliesResultView({ result }: { result: BaselineAnomaliesAnalysisResult }) {
  const annualAnomalies = result.annual_anomalies ?? [];
  const years = annualAnomalies.map((point) => point.year);
  const values = annualAnomalies.map((point) => point.anomaly);
  const colors = values.map((value) => (typeof value === "number" && value < 0 ? "#5f95bd" : "#f97316"));
  const zeroLineX = years.length > 0 ? [years[0], years[years.length - 1]] : [];

  const anomalyTraces = useMemo<Plotly.Data[]>(
    () => [
      {
        type: "bar",
        name: "Annual anomaly",
        x: years,
        y: values,
        marker: {
          color: colors,
          line: { color: "#4b5563", width: 0.8 },
        },
        hovertemplate: "Year %{x}<br>Anomaly %{y:.2f}<extra></extra>",
      },
      {
        type: "scatter",
        mode: "lines",
        name: "Baseline",
        x: zeroLineX,
        y: zeroLineX.map(() => 0),
        line: { color: "#111827", width: 2 },
        hoverinfo: "skip",
      },
    ],
    [colors, values, years, zeroLineX],
  );

  const layout = {
    margin: { l: 64, r: 24, t: 28, b: 56 },
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "#ffffff",
    xaxis: { title: { text: "Year" } },
    yaxis: {
      title: { text: `${result.target_column} anomaly` },
      zeroline: true,
      zerolinecolor: "#111827",
    },
    showlegend: false,
    hovermode: "x unified",
    bargap: 0.18,
  };

  return (
    <div className="analysis-rich-result">
      <div className="analysis-result-grid">
        <AnalysisStat label="Baseline mean" value={formatNullable(result.summary?.baseline_mean)} />
        <AnalysisStat
          label="Most negative"
          value={`${result.summary?.most_negative_year ?? "-"} (${formatSignedNumber(
            result.summary?.most_negative_anomaly,
          )})`}
        />
        <AnalysisStat
          label="Most positive"
          value={`${result.summary?.most_positive_year ?? "-"} (${formatSignedNumber(
            result.summary?.most_positive_anomaly,
          )})`}
        />
        <AnalysisStat label="Negative years" value={formatInteger(result.summary?.negative_years)} />
        <AnalysisStat label="Positive years" value={formatInteger(result.summary?.positive_years)} />
      </div>

      <div className="analysis-chart-card">
        <h4>Annual Baseline Anomalies</h4>
        <Plot
          data={anomalyTraces}
          layout={layout as unknown as Plotly.Layout}
          style={{ width: "100%", height: "430px" }}
          config={{ responsive: true, displaylogo: false }}
        />
      </div>

      <div className="analysis-context-row">
        <span>{result.target_column}</span>
        <span>{result.time_column}</span>
        <span>{formatDateRange(result.baseline?.start, result.baseline?.end)}</span>
        <span>{result.data_quality?.baseline_months ?? 0}/12 baseline months</span>
        <span>{formatInteger(result.valid_rows)} valid rows</span>
      </div>
    </div>
  );
}

function AnnualTrendSignalResultView({ result }: { result: AnnualTrendSignalAnalysisResult }) {
  const annualSeries = result.annual_series ?? [];
  const years = annualSeries.map((point) => point.year);
  const annualMeans = annualSeries.map((point) => point.mean);
  const trendLine = annualSeries.map((point) => point.trend);
  const trendPerDecade = result.summary?.warming_per_decade ?? result.summary?.slope_per_decade;
  const lowestYear = result.summary?.lowest_year ?? result.summary?.coldest_year;
  const lowestValue = result.summary?.lowest_value ?? result.summary?.coldest_value;
  const highestYear = result.summary?.highest_year ?? result.summary?.warmest_year;
  const highestValue = result.summary?.highest_value ?? result.summary?.warmest_value;
  const trendLabel = `Trend: ${formatSignedNumber(trendPerDecade)} / decade`;

  const trendTraces = useMemo<Plotly.Data[]>(
    () => [
      {
        type: "bar",
        name: "Annual mean",
        x: years,
        y: annualMeans,
        marker: {
          color: "#5f95bd",
          line: { color: "#1d4ed8", width: 1 },
        },
        opacity: 0.84,
        hovertemplate: "Year %{x}<br>Mean %{y:.2f}<extra></extra>",
      },
      {
        type: "scatter",
        mode: "lines",
        name: trendLabel,
        x: years,
        y: trendLine,
        line: { color: "#dc2626", width: 3, dash: "dash" },
        hovertemplate: "Trend %{y:.2f}<extra></extra>",
      },
    ],
    [annualMeans, trendLabel, trendLine, years],
  );

  const layout = {
    margin: { l: 64, r: 24, t: 28, b: 56 },
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "#ffffff",
    xaxis: { title: { text: "Year" } },
    yaxis: { title: { text: `Annual mean ${result.target_column}` } },
    legend: { orientation: "h" },
    hovermode: "x unified",
    bargap: 0.18,
  };

  return (
    <div className="analysis-rich-result">
      <div className="analysis-result-grid">
        <AnalysisStat label="Change / decade" value={formatSignedNumber(trendPerDecade)} />
        <AnalysisStat label="Total change" value={formatSignedNumber(result.summary?.total_change)} />
        <AnalysisStat
          label="Lowest year"
          value={`${lowestYear ?? "-"} (${formatNullable(lowestValue)})`}
        />
        <AnalysisStat
          label="Highest year"
          value={`${highestYear ?? "-"} (${formatNullable(highestValue)})`}
        />
        <AnalysisStat label="R2" value={formatNullable(result.summary?.r2)} />
      </div>

      <div className="analysis-chart-card">
        <h4>Annual Trend Signal</h4>
        <Plot
          data={trendTraces}
          layout={layout as unknown as Plotly.Layout}
          style={{ width: "100%", height: "430px" }}
          config={{ responsive: true, displaylogo: false }}
        />
      </div>

      <div className="analysis-context-row">
        <span>{result.target_column}</span>
        <span>{result.time_column}</span>
        <span>{result.data_quality?.observed_years ?? 0} years</span>
        <span>{formatInteger(result.valid_rows)} valid rows</span>
      </div>
    </div>
  );
}

function SeasonalClimatologyResultView({ result }: { result: SeasonalClimatologyAnalysisResult }) {
  const monthly = result.monthly_climatology ?? [];
  const seasonal = result.seasonal_cycle ?? [];
  const monthLabels = monthly.map((point) => point.month_label ?? String(point.month ?? ""));
  const monthlyMeans = monthly.map((point) => point.mean);
  const monthlyStd = monthly.map((point) => point.std ?? 0);
  const annualLine = monthly.map(() => result.summary?.annual_mean ?? null);

  const monthlyTraces = useMemo<Plotly.Data[]>(
    () => [
      {
        type: "bar",
        name: "Monthly mean",
        x: monthLabels,
        y: monthlyMeans,
        marker: {
          color: "#5f95bd",
          line: { color: "#1d4ed8", width: 1.2 },
        },
        opacity: 0.86,
        error_y: {
          type: "data",
          array: monthlyStd,
          visible: true,
          color: "#111827",
          thickness: 1.4,
          width: 4,
        },
        hovertemplate: "%{x}<br>Mean %{y:.2f}<extra></extra>",
      },
      {
        type: "scatter",
        mode: "lines",
        name: `Annual mean: ${formatNullable(result.summary?.annual_mean)}`,
        x: monthLabels,
        y: annualLine,
        line: { color: "#dc2626", width: 2, dash: "dash" },
        hovertemplate: "Annual mean %{y:.2f}<extra></extra>",
      },
    ],
    [annualLine, monthLabels, monthlyMeans, monthlyStd, result.summary?.annual_mean],
  );

  const seasonalTraces = useMemo<Plotly.Data[]>(
    () => [
      {
        type: "bar",
        name: "Season mean",
        x: seasonal.map((point) => SEASON_LABELS[(point.season ?? "winter") as SeasonName] ?? point.season),
        y: seasonal.map((point) => point.mean),
        marker: {
          color: seasonal.map((point) => SEASON_COLORS[(point.season ?? "winter") as SeasonName] ?? "#5f95bd"),
        },
        error_y: {
          type: "data",
          array: seasonal.map((point) => point.std ?? 0),
          visible: true,
          color: "#111827",
          thickness: 1.4,
          width: 4,
        },
        hovertemplate: "%{x}<br>Mean %{y:.2f}<extra></extra>",
      },
    ],
    [seasonal],
  );

  const monthlyLayout = {
    margin: { l: 56, r: 20, t: 24, b: 52 },
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "#ffffff",
    xaxis: { title: { text: "Month" } },
    yaxis: { title: { text: result.target_column } },
    legend: { orientation: "h" },
    hovermode: "x unified",
    bargap: 0.22,
  };

  const seasonalLayout = {
    margin: { l: 56, r: 20, t: 24, b: 52 },
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "#ffffff",
    xaxis: { title: { text: "Season" } },
    yaxis: { title: { text: result.target_column } },
    showlegend: false,
    bargap: 0.28,
  };

  return (
    <div className="analysis-rich-result">
      <div className="analysis-result-grid">
        <AnalysisStat label="Annual mean" value={formatNullable(result.summary?.annual_mean)} />
        <AnalysisStat
          label="Warmest month"
          value={`${result.summary?.warmest_month_label ?? "-"} (${formatNullable(result.summary?.warmest_value)})`}
        />
        <AnalysisStat
          label="Coolest month"
          value={`${result.summary?.coolest_month_label ?? "-"} (${formatNullable(result.summary?.coolest_value)})`}
        />
        <AnalysisStat label="Seasonal range" value={formatNullable(result.summary?.seasonal_range)} />
      </div>

      <div className="analysis-chart-grid">
        <div className="analysis-chart-card">
          <h4>Monthly Climatology</h4>
          <Plot
            data={monthlyTraces}
            layout={monthlyLayout as unknown as Plotly.Layout}
            style={{ width: "100%", height: "380px" }}
            config={{ responsive: true, displaylogo: false }}
          />
        </div>
        <div className="analysis-chart-card">
          <h4>Seasonal Cycle</h4>
          <Plot
            data={seasonalTraces}
            layout={seasonalLayout as unknown as Plotly.Layout}
            style={{ width: "100%", height: "380px" }}
            config={{ responsive: true, displaylogo: false }}
          />
        </div>
      </div>

      <div className="analysis-context-row">
        <span>{result.target_column}</span>
        <span>{result.time_column}</span>
        <span>{result.data_quality?.observed_months ?? 0}/12 months</span>
        <span>{formatInteger(result.valid_rows)} valid rows</span>
      </div>
    </div>
  );
}

function DiurnalCycleResultView({ result }: { result: DiurnalCycleAnalysisResult }) {
  const hourlyProfile = result.hourly_profile ?? [];
  const seasonalProfile = result.seasonal_hourly_profile ?? [];

  const overallTrace = useMemo<Plotly.Data[]>(
    () => [
      {
        type: "scatter",
        mode: "lines+markers",
        name: "Average",
        x: hourlyProfile.map((point) => point.hour),
        y: hourlyProfile.map((point) => point.mean),
        line: { color: "#f97316", width: 3 },
        marker: { color: "#fb923c", size: 7 },
        hovertemplate: "Hour %{x}:00<br>Mean %{y:.2f}<extra></extra>",
      },
    ],
    [hourlyProfile],
  );

  const seasonalTraces = useMemo<Plotly.Data[]>(
    () =>
      SEASON_ORDER.map((season) => {
        const points = seasonalProfile.filter((point) => point.season === season);
        return {
          type: "scatter",
          mode: "lines+markers",
          name: SEASON_LABELS[season],
          x: points.map((point) => point.hour),
          y: points.map((point) => point.mean),
          line: { color: SEASON_COLORS[season], width: 3 },
          marker: { color: SEASON_COLORS[season], size: 6 },
          hovertemplate: `${SEASON_LABELS[season]}<br>Hour %{x}:00<br>Mean %{y:.2f}<extra></extra>`,
        };
      }),
    [seasonalProfile],
  );

  const sharedLayout = {
    margin: { l: 56, r: 20, t: 40, b: 52 },
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "#ffffff",
    xaxis: {
      title: { text: "Hour of day" },
      tickmode: "array",
      tickvals: [0, 3, 6, 9, 12, 15, 18, 21, 23],
      range: [-0.5, 23.5],
    },
    yaxis: { title: { text: result.target_column } },
    legend: { orientation: "h" },
    hovermode: "x unified",
  };

  return (
    <div className="analysis-rich-result">
      <div className="analysis-result-grid">
        <AnalysisStat label="Range" value={formatNullable(result.summary?.diurnal_range)} />
        <AnalysisStat
          label="Warmest hour"
          value={`${formatHour(result.summary?.warmest_hour)} (${formatNullable(result.summary?.warmest_value)})`}
        />
        <AnalysisStat
          label="Coolest hour"
          value={`${formatHour(result.summary?.coolest_hour)} (${formatNullable(result.summary?.coolest_value)})`}
        />
        <AnalysisStat label="Valid rows" value={formatInteger(result.valid_rows)} />
      </div>

      <div className="analysis-chart-grid">
        <div className="analysis-chart-card">
          <h4>Average Diurnal Cycle</h4>
          <Plot
            data={overallTrace}
            layout={{ ...sharedLayout, title: { text: "" } } as unknown as Plotly.Layout}
            style={{ width: "100%", height: "360px" }}
            config={{ responsive: true, displaylogo: false }}
          />
        </div>
        <div className="analysis-chart-card">
          <h4>Diurnal Cycle by Season</h4>
          <Plot
            data={seasonalTraces}
            layout={{ ...sharedLayout, title: { text: "" } } as unknown as Plotly.Layout}
            style={{ width: "100%", height: "360px" }}
            config={{ responsive: true, displaylogo: false }}
          />
        </div>
      </div>

      <div className="analysis-context-row">
        <span>{result.target_column}</span>
        <span>{result.time_column}</span>
        <span>UTC offset {formatSigned(result.timezone_offset_hours)}</span>
        <span>{result.data_quality?.observed_hours ?? 0}/24 hours</span>
      </div>
    </div>
  );
}

function AnalysisStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="analysis-stat-card">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function formatNullable(value: number | null | undefined): string {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return "-";
  }
  return value.toFixed(2);
}

function formatRange(min: number | null | undefined, max: number | null | undefined): string {
  if (typeof min !== "number" || typeof max !== "number" || !Number.isFinite(min) || !Number.isFinite(max)) {
    return "-";
  }
  return (max - min).toFixed(2);
}

function formatInteger(value: number | null | undefined): string {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return "-";
  }
  return Math.round(value).toLocaleString();
}

function formatHour(value: number | null | undefined): string {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return "-";
  }
  return `${Math.round(value).toString().padStart(2, "0")}:00`;
}

function formatSigned(value: number | null | undefined): string {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return "+0";
  }
  return value >= 0 ? `+${value}` : `${value}`;
}

function formatSignedNumber(value: number | null | undefined, digits = 2): string {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return "-";
  }
  const formatted = value.toFixed(digits);
  return value >= 0 ? `+${formatted}` : formatted;
}

function formatDateRange(start: string | null | undefined, end: string | null | undefined): string {
  if (!start || !end) {
    return "Baseline";
  }
  return `${start.slice(0, 10)} to ${end.slice(0, 10)}`;
}

function formatPercentile(value: number | null | undefined): string {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return "-";
  }
  return `P${(value * 100).toFixed(1).replace(/\.0$/, "")}`;
}

function isPrimitiveDisplayValue(value: unknown): value is PrimitiveDisplayValue {
  return value === null || ["string", "number", "boolean"].includes(typeof value);
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function formatDisplayValue(value: unknown): string {
  if (typeof value === "number") {
    if (!Number.isFinite(value)) {
      return "-";
    }
    return Number.isInteger(value)
      ? value.toLocaleString()
      : value.toLocaleString(undefined, { maximumFractionDigits: 4 });
  }
  if (typeof value === "boolean") {
    return value ? "Yes" : "No";
  }
  if (typeof value === "string") {
    return value;
  }
  if (value === null || value === undefined) {
    return "-";
  }
  if (Array.isArray(value)) {
    return `${value.length} item${value.length === 1 ? "" : "s"}`;
  }
  if (isPlainObject(value)) {
    return Object.entries(value)
      .map(([key, item]) => `${humanizeKey(key)}: ${formatDisplayValue(item)}`)
      .join(", ");
  }
  return String(value);
}

function humanizeKey(key: string): string {
  return key
    .replace(/_/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}
