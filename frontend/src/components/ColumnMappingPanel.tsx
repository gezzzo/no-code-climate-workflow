import { useEffect, useState } from "react";

import { ColumnInference, MappingUpdateRequest } from "../types";

interface Props {
  columns: string[];
  mapping: ColumnInference | null;
  saving: boolean;
  onSave: (payload: MappingUpdateRequest) => Promise<void>;
}

export function ColumnMappingPanel({ columns, mapping, saving, onSave }: Props) {
  const [timeColumn, setTimeColumn] = useState<string>("");
  const [latitudeColumn, setLatitudeColumn] = useState<string>("");
  const [longitudeColumn, setLongitudeColumn] = useState<string>("");
  const [climateVariables, setClimateVariables] = useState<string[]>([]);

  useEffect(() => {
    setTimeColumn(mapping?.time_column ?? "");
    setLatitudeColumn(mapping?.latitude_column ?? "");
    setLongitudeColumn(mapping?.longitude_column ?? "");
    setClimateVariables(mapping?.climate_variables ?? []);
  }, [mapping]);

  const toggleVariable = (column: string): void => {
    setClimateVariables((prev) =>
      prev.includes(column) ? prev.filter((item) => item !== column) : [...prev, column],
    );
  };

  const save = async (): Promise<void> => {
    await onSave({
      time_column: timeColumn || null,
      latitude_column: latitudeColumn || null,
      longitude_column: longitudeColumn || null,
      climate_variables: climateVariables,
    });
  };

  return (
    <section className="panel mapping-panel">
      <div className="panel-header">
        <h2>Column Mapping</h2>
      </div>

      {columns.length === 0 ? (
        <p className="muted">No dataset selected.</p>
      ) : (
        <>
          <div className="mapping-grid">
            <label>
              <span>Time column</span>
              <select value={timeColumn} onChange={(event) => setTimeColumn(event.target.value)}>
                <option value="">Not mapped</option>
                {columns.map((column) => (
                  <option key={column} value={column}>
                    {column}
                  </option>
                ))}
              </select>
            </label>

            <label>
              <span>Latitude</span>
              <select value={latitudeColumn} onChange={(event) => setLatitudeColumn(event.target.value)}>
                <option value="">Not mapped</option>
                {columns.map((column) => (
                  <option key={column} value={column}>
                    {column}
                  </option>
                ))}
              </select>
            </label>

            <label>
              <span>Longitude</span>
              <select value={longitudeColumn} onChange={(event) => setLongitudeColumn(event.target.value)}>
                <option value="">Not mapped</option>
                {columns.map((column) => (
                  <option key={column} value={column}>
                    {column}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="variables-list">
            <p>Climate variable columns</p>
            <div className="tag-grid">
              {columns.map((column) => (
                <button
                  key={column}
                  type="button"
                  className={`tag ${climateVariables.includes(column) ? "tag-active" : ""}`}
                  onClick={() => toggleVariable(column)}
                >
                  {column}
                </button>
              ))}
            </div>
          </div>

          <button type="button" className="primary-btn" onClick={save} disabled={saving}>
            {saving ? "Saving..." : "Save Mapping"}
          </button>
        </>
      )}
    </section>
  );
}
