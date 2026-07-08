import { useEffect, useMemo, useState } from "react";

import {
  ColumnInference,
  DatasetPreview,
  TemporalAggregationRequest,
  TransformationCreateRequest,
  TransformationRecipe,
} from "../types";
import { TransformVariablesForm } from "./TransformVariablesPanel";

interface Props {
  datasetName: string | null;
  sourceFormat: string | null;
  rowCount: number;
  datasetId: string | null;
  columns: string[];
  mapping: ColumnInference | null;
  transformations: TransformationRecipe[];
  preview: DatasetPreview | null;
  applying: boolean;
  deriving: boolean;
  onApplyTransformation: (payload: TransformationCreateRequest) => Promise<void>;
  onDeriveTemporalAggregation: (payload: TemporalAggregationRequest) => Promise<void>;
}

type AggregationOperation = TemporalAggregationRequest["aggregations"][number];

const AGGREGATION_OPTIONS: Array<{ value: AggregationOperation; label: string }> = [
  { value: "mean", label: "Mean" },
  { value: "min", label: "Min" },
  { value: "max", label: "Max" },
  { value: "range", label: "Range" },
  { value: "sum", label: "Sum" },
  { value: "count", label: "Count" },
  { value: "std", label: "Std" },
];

const FREQUENCY_LABELS: Record<TemporalAggregationRequest["frequency"], string> = {
  D: "Daily",
  ME: "Monthly",
  YE: "Yearly",
};

export function PrepareWorkflowBuilder({
  datasetName,
  sourceFormat,
  rowCount,
  datasetId,
  columns,
  mapping,
  transformations,
  preview,
  applying,
  deriving,
  onApplyTransformation,
  onDeriveTemporalAggregation,
}: Props) {
  const numericColumns = useMemo(() => inferNumericColumns(columns, mapping), [columns, mapping]);
  const timeColumnDefault = mapping?.time_column ?? "";

  const [aggregationTimeColumn, setAggregationTimeColumn] = useState("");
  const [aggregationValueColumns, setAggregationValueColumns] = useState<string[]>([]);
  const [aggregationFrequency, setAggregationFrequency] =
    useState<TemporalAggregationRequest["frequency"]>("D");
  const [aggregationOperations, setAggregationOperations] = useState<AggregationOperation[]>([
    "mean",
    "min",
    "max",
    "range",
  ]);
  const [aggregationOutputName, setAggregationOutputName] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);

  useEffect(() => {
    setAggregationTimeColumn(timeColumnDefault);
    setAggregationValueColumns((mapping?.climate_variables ?? numericColumns).slice(0, 4));
    setAggregationOutputName(datasetName ? `${datasetName.replace(/\.[^.]+$/, "")}_analysis_ready` : "");
  }, [datasetName, mapping, numericColumns, timeColumnDefault]);

  const toggleAggregationColumn = (column: string): void => {
    setAggregationValueColumns((prev) =>
      prev.includes(column) ? prev.filter((item) => item !== column) : [...prev, column],
    );
  };

  const toggleAggregationOperation = (item: AggregationOperation): void => {
    setAggregationOperations((prev) =>
      prev.includes(item) ? prev.filter((operationName) => operationName !== item) : [...prev, item],
    );
  };

  const createAggregatedDataset = async (): Promise<void> => {
    if (!aggregationTimeColumn) {
      setLocalError("Select a time column before creating an analysis-ready dataset.");
      return;
    }
    if (aggregationValueColumns.length === 0) {
      setLocalError("Select at least one value column to aggregate.");
      return;
    }
    if (aggregationOperations.length === 0) {
      setLocalError("Select at least one aggregation.");
      return;
    }

    setLocalError(null);
    await onDeriveTemporalAggregation({
      time_column: aggregationTimeColumn,
      value_columns: aggregationValueColumns,
      frequency: aggregationFrequency,
      aggregations: aggregationOperations,
      output_name: aggregationOutputName.trim() || null,
    });
  };

  const profileItems = [
    { label: "Format", value: sourceFormat?.toUpperCase() ?? "-" },
    { label: "Rows", value: rowCount ? rowCount.toLocaleString() : "0" },
    { label: "Columns", value: columns.length.toLocaleString() },
    { label: "Time", value: mapping?.time_column ?? "Not mapped" },
  ];

  return (
    <section className="panel workflow-builder-panel">
      <div className="panel-header">
        <div>
          <h2>Prepare Workflow</h2>
          <p className="meta">{datasetName ?? "Select a dataset to build a preparation flow."}</p>
        </div>
      </div>

      {columns.length === 0 ? (
        <p className="muted">Upload or select a dataset to create a preparation workflow.</p>
      ) : (
        <>
          <div className="workflow-builder-grid">
            {profileItems.map((item) => (
              <article key={item.label} className="workflow-builder-stat">
                <span>{item.label}</span>
                <strong>{item.value}</strong>
              </article>
            ))}
          </div>

          <div className="workflow-step-list">
            <article className="workflow-step-card">
              <div className="workflow-step-index">1</div>
              <div className="workflow-step-body">
                <h3>Inspect and Map</h3>
                <div className="workflow-step-meta">
                  <span>{mapping?.time_column ? "Time column detected" : "Map a time column"}</span>
                  <span>{numericColumns.length} numeric candidates</span>
                </div>
              </div>
            </article>

            <article className="workflow-step-card">
              <div className="workflow-step-index">2</div>
              <div className="workflow-step-body">
                <div className="workflow-step-heading">
                  <h3>Transform Variables</h3>
                  <span>Unit conversion, math, rolling, daily/monthly derived variables</span>
                </div>
                <TransformVariablesForm
                  datasetId={datasetId}
                  columns={columns}
                  defaultTimeColumn={mapping?.time_column ?? null}
                  transformations={transformations}
                  preview={preview}
                  applying={applying}
                  onApply={onApplyTransformation}
                  embedded
                />
              </div>
            </article>

            <article className="workflow-step-card workflow-step-card-active">
              <div className="workflow-step-index">3</div>
              <div className="workflow-step-body">
                <h3>Create Analysis-Ready Dataset</h3>
                <div className="form-grid">
                  <label>
                    <span>Time column</span>
                    <select
                      value={aggregationTimeColumn}
                      onChange={(event) => setAggregationTimeColumn(event.target.value)}
                    >
                      <option value="">Select time column</option>
                      {columns.map((column) => (
                        <option key={column} value={column}>
                          {column}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    <span>Frequency</span>
                    <select
                      value={aggregationFrequency}
                      onChange={(event) =>
                        setAggregationFrequency(event.target.value as TemporalAggregationRequest["frequency"])
                      }
                    >
                      {Object.entries(FREQUENCY_LABELS).map(([value, label]) => (
                        <option key={value} value={value}>
                          {label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    <span>Output dataset</span>
                    <input
                      value={aggregationOutputName}
                      onChange={(event) => setAggregationOutputName(event.target.value)}
                      placeholder="analysis_ready_dataset"
                    />
                  </label>
                </div>

                <div className="variables-list">
                  <p>Value columns</p>
                  <div className="tag-grid">
                    {numericColumns.map((column) => (
                      <button
                        key={column}
                        type="button"
                        className={`tag ${aggregationValueColumns.includes(column) ? "tag-active" : ""}`}
                        onClick={() => toggleAggregationColumn(column)}
                      >
                        {column}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="variables-list">
                  <p>Metrics</p>
                  <div className="tag-grid">
                    {AGGREGATION_OPTIONS.map((item) => (
                      <button
                        key={item.value}
                        type="button"
                        className={`tag ${aggregationOperations.includes(item.value) ? "tag-active" : ""}`}
                        onClick={() => toggleAggregationOperation(item.value)}
                      >
                        {item.label}
                      </button>
                    ))}
                  </div>
                </div>

                <button
                  type="button"
                  className="primary-btn workflow-primary-action"
                  disabled={deriving}
                  onClick={createAggregatedDataset}
                >
                  {deriving ? "Creating..." : `Create ${FREQUENCY_LABELS[aggregationFrequency]} Dataset`}
                </button>
              </div>
            </article>
          </div>

          {localError ? <p className="inline-error">{localError}</p> : null}
        </>
      )}
    </section>
  );
}

function inferNumericColumns(columns: string[], mapping: ColumnInference | null): string[] {
  const mapped = mapping?.climate_variables.filter((column) => columns.includes(column)) ?? [];
  const typed = Object.entries(mapping?.column_types ?? {})
    .filter(([, type]) => type.includes("numeric") || type.includes("float") || type.includes("int"))
    .map(([column]) => column)
    .filter((column) => columns.includes(column));
  const detected = Array.from(new Set([...mapped, ...typed]));
  if (detected.length > 0) {
    return detected;
  }
  return columns.filter((column) => column !== mapping?.time_column);
}
