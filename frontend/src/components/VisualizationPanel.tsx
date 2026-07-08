import { useEffect, useMemo, useRef, useState } from "react";
import Plot from "react-plotly.js";
import Plotly from "plotly.js-dist-min";
import { CircleMarker, MapContainer, Popup, TileLayer } from "react-leaflet";

import { VisualizationRequest, VisualizationResponse, VisualizationType } from "../types";

interface Props {
  columns: string[];
  defaultTimeColumn: string | null;
  defaultVariables: string[];
  loading: boolean;
  response: VisualizationResponse | null;
  onBuild: (payload: VisualizationRequest) => Promise<void>;
}

const CHART_OPTIONS: Array<{ value: VisualizationType; label: string }> = [
  { value: "time_series", label: "Time series" },
  { value: "scatter", label: "Scatter plot" },
  { value: "heatmap", label: "Heatmap" },
  { value: "map", label: "Geographic map" },
  { value: "anomaly_graph", label: "Anomaly graph" },
];

export function VisualizationPanel({
  columns,
  defaultTimeColumn,
  defaultVariables,
  loading,
  response,
  onBuild,
}: Props) {
  const [visualizationType, setVisualizationType] = useState<VisualizationType>("time_series");
  const [xColumn, setXColumn] = useState<string>("");
  const [yColumn, setYColumn] = useState<string>("");
  const [valueColumn, setValueColumn] = useState<string>("");

  const plotRef = useRef<Plotly.PlotlyHTMLElement | null>(null);

  useEffect(() => {
    setXColumn(defaultTimeColumn ?? columns[0] ?? "");
    setYColumn(defaultVariables[0] ?? columns[1] ?? "");
    setValueColumn(defaultVariables[0] ?? columns[0] ?? "");
  }, [columns, defaultTimeColumn, defaultVariables]);

  const build = async (): Promise<void> => {
    await onBuild({
      visualization_type: visualizationType,
      x_column: xColumn || null,
      y_column: yColumn || null,
      value_column: valueColumn || null,
      options: visualizationType === "map" ? { max_points: 5000 } : {},
    });
  };

  const mapPoints = useMemo(() => {
    if (!response || response.visualization_type !== "map") {
      return [];
    }
    const trace = response.figure.data[0] as {
      lat?: number[];
      lon?: number[];
      marker?: { color?: number[] };
    };

    const lats = trace.lat ?? [];
    const lons = trace.lon ?? [];
    const values = trace.marker?.color ?? [];

    return lats.map((lat, idx) => ({
      lat: Number(lat),
      lon: Number(lons[idx]),
      value: Number(values[idx] ?? 0),
    }));
  }, [response]);

  const exportPng = async (): Promise<void> => {
    if (!plotRef.current) {
      return;
    }
    await Plotly.downloadImage(plotRef.current, {
      filename: "climate_visualization",
      format: "png",
      width: 1400,
      height: 800,
    });
  };

  return (
    <section className="panel visualization-panel">
      <div className="panel-header">
        <h2>Visualization Panel</h2>
      </div>

      {columns.length === 0 ? (
        <p className="muted">Select a dataset to generate visualizations.</p>
      ) : (
        <>
          <div className="form-grid">
            <label>
              <span>Visualization type</span>
              <select
                value={visualizationType}
                onChange={(event) => setVisualizationType(event.target.value as VisualizationType)}
              >
                {CHART_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>

            <label>
              <span>X column</span>
              <select value={xColumn} onChange={(event) => setXColumn(event.target.value)}>
                <option value="">Auto</option>
                {columns.map((column) => (
                  <option key={column} value={column}>
                    {column}
                  </option>
                ))}
              </select>
            </label>

            <label>
              <span>Y column</span>
              <select value={yColumn} onChange={(event) => setYColumn(event.target.value)}>
                <option value="">Auto</option>
                {columns.map((column) => (
                  <option key={column} value={column}>
                    {column}
                  </option>
                ))}
              </select>
            </label>

            <label>
              <span>Value column</span>
              <select value={valueColumn} onChange={(event) => setValueColumn(event.target.value)}>
                <option value="">Auto</option>
                {columns.map((column) => (
                  <option key={column} value={column}>
                    {column}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="button-row">
            <button type="button" className="primary-btn" disabled={loading} onClick={build}>
              {loading ? "Building..." : "Build Visualization"}
            </button>
            <button type="button" className="secondary-btn" onClick={exportPng}>
              Export PNG
            </button>
          </div>

          {response ? (
            response.visualization_type === "map" ? (
              <div className="map-wrap">
                <MapContainer center={[20, 0]} zoom={2} scrollWheelZoom className="leaflet-map">
                  <TileLayer
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  />
                  {mapPoints.map((point, idx) => (
                    <CircleMarker
                      key={idx}
                      center={[point.lat, point.lon]}
                      radius={4}
                      pathOptions={{
                        color: "#1d4ed8",
                        fillColor: "#1d4ed8",
                        fillOpacity: 0.55,
                        weight: 1,
                      }}
                    >
                      <Popup>
                        lat: {point.lat.toFixed(3)} <br /> lon: {point.lon.toFixed(3)} <br /> value: {point.value.toFixed(3)}
                      </Popup>
                    </CircleMarker>
                  ))}
                </MapContainer>
              </div>
            ) : (
              <Plot
                data={response.figure.data as Plotly.Data[]}
                layout={response.figure.layout as unknown as Plotly.Layout}
                style={{ width: "100%", minHeight: "480px" }}
                config={{ responsive: true, displaylogo: false }}
                onInitialized={(_figure: unknown, graphDiv: Plotly.PlotlyHTMLElement) => {
                  plotRef.current = graphDiv;
                }}
                onUpdate={(_figure: unknown, graphDiv: Plotly.PlotlyHTMLElement) => {
                  plotRef.current = graphDiv;
                }}
              />
            )
          ) : (
            <p className="muted">Run a visualization to display charts and maps.</p>
          )}
        </>
      )}
    </section>
  );
}
