import { useEffect, useMemo, useState } from "react";

import { api } from "../api/client";
import {
  DatasetPreview,
  TransformationCreateRequest,
  TransformationOperation,
  TransformationRecipe,
  TransformationSuggestion,
} from "../types";

interface Props {
  datasetId: string | null;
  columns: string[];
  defaultTimeColumn: string | null;
  transformations: TransformationRecipe[];
  preview: DatasetPreview | null;
  applying: boolean;
  onApply: (payload: TransformationCreateRequest) => Promise<void>;
}

interface FormProps extends Props {
  embedded?: boolean;
}

const OPERATION_OPTIONS: Array<{ value: TransformationOperation; label: string }> = [
  { value: "kelvin_to_celsius", label: "Kelvin -> Celsius" },
  { value: "kelvin_to_fahrenheit", label: "Kelvin -> Fahrenheit" },
  { value: "celsius_to_kelvin", label: "Celsius -> Kelvin" },
  { value: "ms_to_kmh", label: "m/s -> km/h" },
  { value: "ms_to_mph", label: "m/s -> mph" },
  { value: "pa_to_hpa", label: "Pa -> hPa" },
  { value: "multiply_constant", label: "Multiply by constant" },
  { value: "divide_constant", label: "Divide by constant" },
  { value: "add_constant", label: "Add constant" },
  { value: "subtract_constant", label: "Subtract constant" },
  { value: "rolling_mean", label: "Rolling mean" },
  { value: "aggregate_by_day", label: "Aggregation by day" },
  { value: "aggregate_by_month", label: "Aggregation by month" },
];

const MATH_OPS: TransformationOperation[] = [
  "multiply_constant",
  "divide_constant",
  "add_constant",
  "subtract_constant",
];

const TIME_OPS: TransformationOperation[] = [
  "rolling_mean",
  "aggregate_by_day",
  "aggregate_by_month",
];

export function TransformVariablesPanel({
  datasetId,
  columns,
  defaultTimeColumn,
  transformations,
  preview,
  applying,
  onApply,
}: Props) {
  return (
    <section className="panel transform-panel">
      <div className="panel-header">
        <h2>Transform Variables</h2>
      </div>

      <TransformVariablesForm
        datasetId={datasetId}
        columns={columns}
        defaultTimeColumn={defaultTimeColumn}
        transformations={transformations}
        preview={preview}
        applying={applying}
        onApply={onApply}
      />
    </section>
  );
}

export function TransformVariablesForm({
  datasetId,
  columns,
  defaultTimeColumn,
  transformations,
  preview,
  applying,
  onApply,
  embedded = false,
}: FormProps) {
  const [sourceVariable, setSourceVariable] = useState<string>("");
  const [operation, setOperation] = useState<TransformationOperation>("kelvin_to_celsius");
  const [outputVariable, setOutputVariable] = useState<string>("");
  const [constant, setConstant] = useState<number>(1);
  const [windowSize, setWindowSize] = useState<number>(7);
  const [timeColumn, setTimeColumn] = useState<string>("");

  const [suggestions, setSuggestions] = useState<TransformationSuggestion[]>([]);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  useEffect(() => {
    setSourceVariable(columns[0] ?? "");
    setTimeColumn(defaultTimeColumn ?? "");
  }, [columns, defaultTimeColumn]);

  useEffect(() => {
    if (!datasetId) {
      setSuggestions([]);
      return;
    }

    let canceled = false;
    const loadSuggestions = async (): Promise<void> => {
      try {
        setLoadingSuggestions(true);
        const response = await api.getTransformations(datasetId);
        if (!canceled) {
          setSuggestions(response.suggestions);
        }
      } catch {
        if (!canceled) {
          setSuggestions([]);
        }
      } finally {
        if (!canceled) {
          setLoadingSuggestions(false);
        }
      }
    };

    void loadSuggestions();

    return () => {
      canceled = true;
    };
  }, [datasetId, transformations.length]);

  useEffect(() => {
    if (!sourceVariable) {
      setOutputVariable("");
      return;
    }

    const suggestion = suggestions.find(
      (item) => item.source_variable === sourceVariable && item.operation === operation,
    );

    if (suggestion) {
      setOutputVariable(suggestion.suggested_output);
      return;
    }

    setOutputVariable(defaultOutputName(sourceVariable, operation));
  }, [sourceVariable, operation, suggestions]);

  const latestOutputName = useMemo(() => {
    if (!preview || !outputVariable || !preview.columns.includes(outputVariable)) {
      return null;
    }
    return outputVariable;
  }, [preview, outputVariable]);

  const applyTransformation = async (): Promise<void> => {
    if (!sourceVariable) {
      setLocalError("Select a source variable before applying a transformation.");
      return;
    }
    if (!outputVariable.trim()) {
      setLocalError("Output variable name is required.");
      return;
    }

    setLocalError(null);

    const parameters: Record<string, unknown> = {};
    if (MATH_OPS.includes(operation)) {
      parameters.constant = constant;
    }
    if (operation === "rolling_mean") {
      parameters.window = windowSize;
      parameters.time_column = timeColumn || null;
    }
    if (operation === "aggregate_by_day" || operation === "aggregate_by_month") {
      parameters.time_column = timeColumn || null;
    }

    await onApply({
      source_variable: sourceVariable,
      operation,
      output_variable: outputVariable.trim(),
      parameters,
    });
  };

  return (
    <div className={embedded ? "transform-form transform-form-embedded" : "transform-form"}>
      {columns.length === 0 ? (
        <p className="muted">Select a dataset to create derived variables.</p>
      ) : (
        <>
          <div className="form-grid">
            <label>
              <span>Select variable</span>
              <select value={sourceVariable} onChange={(event) => setSourceVariable(event.target.value)}>
                <option value="">Select source variable</option>
                {columns.map((column) => (
                  <option key={column} value={column}>
                    {column}
                  </option>
                ))}
              </select>
            </label>

            <label>
              <span>Transformation type</span>
              <select
                value={operation}
                onChange={(event) => setOperation(event.target.value as TransformationOperation)}
              >
                {OPERATION_OPTIONS.map((item) => (
                  <option key={item.value} value={item.value}>
                    {item.label}
                  </option>
                ))}
              </select>
            </label>

            <label>
              <span>Output variable name</span>
              <input
                type="text"
                value={outputVariable}
                onChange={(event) => setOutputVariable(event.target.value)}
                placeholder="example: t2m_c"
              />
            </label>
          </div>

          {MATH_OPS.includes(operation) ? (
            <label className="inline-field">
              <span>Constant value</span>
              <input
                type="number"
                value={constant}
                step={0.1}
                onChange={(event) => setConstant(Number(event.target.value))}
              />
            </label>
          ) : null}

          {TIME_OPS.includes(operation) ? (
            <div className="form-grid transform-time-grid">
              <label>
                <span>Time column</span>
                <select value={timeColumn} onChange={(event) => setTimeColumn(event.target.value)}>
                  <option value="">Use mapped time column</option>
                  {columns.map((column) => (
                    <option key={column} value={column}>
                      {column}
                    </option>
                  ))}
                </select>
              </label>

              {operation === "rolling_mean" ? (
                <label>
                  <span>Rolling window</span>
                  <input
                    type="number"
                    min={1}
                    value={windowSize}
                    onChange={(event) => setWindowSize(Number(event.target.value))}
                  />
                </label>
              ) : null}
            </div>
          ) : null}

          <div className="button-row">
            <button type="button" className="primary-btn" onClick={applyTransformation} disabled={applying}>
              {applying ? "Applying..." : "Apply Transformation"}
            </button>
          </div>

          {localError ? <p className="inline-error">{localError}</p> : null}

          <div className="transform-info-grid">
            <article className="transform-info-card">
              <h3>Automatic Suggestions</h3>
              {loadingSuggestions ? <p className="muted">Detecting suggestions...</p> : null}
              {!loadingSuggestions && suggestions.length === 0 ? (
                <p className="muted">No unit-based suggestions available.</p>
              ) : (
                <ul>
                  {suggestions.map((item) => (
                    <li key={`${item.source_variable}-${item.operation}`}>
                      <strong>{item.source_variable}</strong>
                      {" -> "}
                      {item.operation} ({item.suggested_output})
                    </li>
                  ))}
                </ul>
              )}
            </article>

            <article className="transform-info-card">
              <h3>Applied Recipes</h3>
              {transformations.length === 0 ? (
                <p className="muted">No transformations applied yet.</p>
              ) : (
                <ul>
                  {transformations.map((item) => (
                    <li key={item.recipe_id}>
                      <strong>{item.output_variable}</strong> = {item.source_variable} ({item.operation})
                    </li>
                  ))}
                </ul>
              )}
            </article>
          </div>

          {latestOutputName && preview ? (
            <div className="transform-preview">
              <h3>Transformation Preview</h3>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>{sourceVariable}</th>
                      <th className="derived-column-cell">{latestOutputName}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {preview.rows.slice(0, 10).map((row, idx) => (
                      <tr key={`${latestOutputName}-${idx}`}>
                        <td>{formatCell(row[sourceVariable])}</td>
                        <td className="derived-column-cell">{formatCell(row[latestOutputName])}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : null}
        </>
      )}
    </div>
  );
}

function defaultOutputName(source: string, operation: TransformationOperation): string {
  const suffixMap: Record<TransformationOperation, string> = {
    kelvin_to_celsius: "c",
    kelvin_to_fahrenheit: "f",
    celsius_to_kelvin: "k",
    ms_to_kmh: "kmh",
    ms_to_mph: "mph",
    pa_to_hpa: "hpa",
    multiply_constant: "mul",
    divide_constant: "div",
    add_constant: "add",
    subtract_constant: "sub",
    rolling_mean: "rollmean",
    aggregate_by_day: "daymean",
    aggregate_by_month: "monthmean",
  };

  return `${source}_${suffixMap[operation]}`;
}

function formatCell(value: unknown): string {
  if (value === null || value === undefined) {
    return "";
  }
  if (typeof value === "number") {
    return Number.isFinite(value) ? value.toFixed(4) : String(value);
  }
  return String(value);
}
