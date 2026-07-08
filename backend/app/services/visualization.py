from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from app.schemas import ColumnInference, VisualizationRequest


class VisualizationBuilder:
    def build(self, df: pd.DataFrame, mapping: ColumnInference, request: VisualizationRequest) -> dict[str, Any]:
        chart_type = request.visualization_type

        if chart_type == "time_series":
            return self.time_series(df, mapping, request)
        if chart_type == "scatter":
            return self.scatter(df, mapping, request)
        if chart_type == "heatmap":
            return self.heatmap(df, mapping, request)
        if chart_type == "map":
            return self.map_plot(df, mapping, request)
        if chart_type == "anomaly_graph":
            return self.anomaly_graph(df, mapping, request)

        raise ValueError(f"Unsupported visualization type: {chart_type}")

    def time_series(self, df: pd.DataFrame, mapping: ColumnInference, request: VisualizationRequest) -> dict[str, Any]:
        time_col = request.x_column or mapping.time_column
        value_col = request.y_column or request.value_column or _default_value(mapping)

        if not time_col or time_col not in df.columns:
            raise ValueError("Time series plot requires a valid time column.")
        if not value_col or value_col not in df.columns:
            raise ValueError("Time series plot requires a valid value column.")

        working = df[[time_col, value_col]].dropna().copy()
        working[time_col] = pd.to_datetime(working[time_col], errors="coerce", utc=True)
        working[value_col] = pd.to_numeric(working[value_col], errors="coerce")
        working = working.dropna().sort_values(time_col)

        if working.empty:
            raise ValueError("No valid rows for time series visualization.")

        return {
            "data": [
                {
                    "type": "scatter",
                    "mode": "lines",
                    "x": [t.isoformat() for t in working[time_col]],
                    "y": working[value_col].astype(float).round(6).tolist(),
                    "name": value_col,
                }
            ],
            "layout": {
                "title": f"Time Series: {value_col}",
                "xaxis": {"title": time_col},
                "yaxis": {"title": value_col},
                "template": "plotly_white",
            },
        }

    def scatter(self, df: pd.DataFrame, mapping: ColumnInference, request: VisualizationRequest) -> dict[str, Any]:
        numeric_cols = list(df.select_dtypes(include=[np.number]).columns)
        x_col = request.x_column or (numeric_cols[0] if numeric_cols else None)
        y_col = request.y_column or (numeric_cols[1] if len(numeric_cols) > 1 else None)

        if not x_col or not y_col:
            raise ValueError("Scatter plot requires two numeric columns.")

        working = df[[x_col, y_col]].dropna().copy()

        return {
            "data": [
                {
                    "type": "scatter",
                    "mode": "markers",
                    "x": pd.to_numeric(working[x_col], errors="coerce").tolist(),
                    "y": pd.to_numeric(working[y_col], errors="coerce").tolist(),
                    "marker": {"size": 7, "opacity": 0.7},
                    "name": f"{y_col} vs {x_col}",
                }
            ],
            "layout": {
                "title": f"Scatter Plot: {y_col} vs {x_col}",
                "xaxis": {"title": x_col},
                "yaxis": {"title": y_col},
                "template": "plotly_white",
            },
        }

    def heatmap(self, df: pd.DataFrame, mapping: ColumnInference, request: VisualizationRequest) -> dict[str, Any]:
        lat_col = mapping.latitude_column
        lon_col = mapping.longitude_column
        value_col = request.value_column or request.y_column or _default_value(mapping)

        if lat_col and lon_col and value_col and value_col in df.columns:
            working = df[[lat_col, lon_col, value_col]].dropna().copy()
            working[value_col] = pd.to_numeric(working[value_col], errors="coerce")
            working = working.dropna()
            if working.empty:
                raise ValueError("No valid rows for spatial heatmap.")

            lat_bins = int(request.options.get("lat_bins", 45))
            lon_bins = int(request.options.get("lon_bins", 90))
            binned = (
                working.assign(
                    lat_bin=pd.cut(working[lat_col], bins=lat_bins),
                    lon_bin=pd.cut(working[lon_col], bins=lon_bins),
                )
                .groupby(["lat_bin", "lon_bin"], observed=False)[value_col]
                .mean()
                .unstack(fill_value=np.nan)
            )

            z = binned.values
            x = [str(interval) for interval in binned.columns]
            y = [str(interval) for interval in binned.index]
            title = f"Spatial Heatmap: {value_col}"
        else:
            numeric_cols = list(df.select_dtypes(include=[np.number]).columns)
            if len(numeric_cols) < 2:
                raise ValueError("Heatmap requires either lat/lon/value mapping or 2+ numeric columns.")
            corr = df[numeric_cols].corr(numeric_only=True).round(6)
            z = corr.values
            x = corr.columns.tolist()
            y = corr.index.tolist()
            title = "Correlation Heatmap"

        return {
            "data": [
                {
                    "type": "heatmap",
                    "x": x,
                    "y": y,
                    "z": np.nan_to_num(z).tolist(),
                    "colorscale": "Viridis",
                }
            ],
            "layout": {
                "title": title,
                "template": "plotly_white",
            },
        }

    def map_plot(self, df: pd.DataFrame, mapping: ColumnInference, request: VisualizationRequest) -> dict[str, Any]:
        lat_col = request.options.get("lat_column") or mapping.latitude_column
        lon_col = request.options.get("lon_column") or mapping.longitude_column
        value_col = request.value_column or request.y_column or _default_value(mapping)

        if not lat_col or not lon_col:
            raise ValueError("Map visualization requires latitude and longitude columns.")
        if lat_col not in df.columns or lon_col not in df.columns:
            raise ValueError("Mapped latitude/longitude columns not found in dataset.")

        columns = [lat_col, lon_col] + ([value_col] if value_col and value_col in df.columns else [])
        working = df[columns].dropna().copy()

        max_points = int(request.options.get("max_points", 5000))
        if len(working) > max_points:
            sample_idx = np.linspace(0, len(working) - 1, num=max_points, dtype=int)
            working = working.iloc[sample_idx]

        marker: dict[str, Any] = {"size": 6, "opacity": 0.75}
        if value_col and value_col in working.columns:
            working[value_col] = pd.to_numeric(working[value_col], errors="coerce")
            marker.update(
                {
                    "color": working[value_col].fillna(0).round(6).tolist(),
                    "colorscale": "Turbo",
                    "showscale": True,
                    "colorbar": {"title": value_col},
                }
            )

        return {
            "data": [
                {
                    "type": "scattergeo",
                    "lat": pd.to_numeric(working[lat_col], errors="coerce").tolist(),
                    "lon": pd.to_numeric(working[lon_col], errors="coerce").tolist(),
                    "mode": "markers",
                    "marker": marker,
                    "name": value_col or "data",
                }
            ],
            "layout": {
                "title": "Climate Spatial Map",
                "geo": {
                    "projection": {"type": "natural earth"},
                    "showland": True,
                    "landcolor": "#f6f8f9",
                    "showocean": True,
                    "oceancolor": "#ddeef9",
                },
                "template": "plotly_white",
            },
        }

    def anomaly_graph(self, df: pd.DataFrame, mapping: ColumnInference, request: VisualizationRequest) -> dict[str, Any]:
        time_col = request.x_column or mapping.time_column
        target = request.y_column or request.value_column or _default_value(mapping)
        threshold = float(request.options.get("z_threshold", 2.0))

        if not target or target not in df.columns:
            raise ValueError("Anomaly graph requires a valid numeric target variable.")

        cols = [target] + ([time_col] if time_col and time_col in df.columns else [])
        working = df[cols].copy()
        working[target] = pd.to_numeric(working[target], errors="coerce")
        working = working.dropna(subset=[target])
        if working.empty:
            raise ValueError("No valid data for anomaly graph.")

        mean = working[target].mean()
        std = working[target].std(ddof=0)
        if std == 0:
            raise ValueError("Cannot build anomaly graph because standard deviation is zero.")

        working["z"] = (working[target] - mean) / std
        anomalies = working[working["z"].abs() >= threshold]

        if time_col and time_col in working.columns:
            working[time_col] = pd.to_datetime(working[time_col], errors="coerce", utc=True)
            x = [item.isoformat() if pd.notna(item) else None for item in working[time_col]]
            ax = [item.isoformat() if pd.notna(item) else None for item in anomalies[time_col]]
        else:
            x = list(range(len(working)))
            ax = anomalies.index.tolist()

        return {
            "data": [
                {
                    "type": "scatter",
                    "mode": "lines",
                    "x": x,
                    "y": working[target].round(6).tolist(),
                    "name": target,
                    "line": {"color": "#1f77b4"},
                },
                {
                    "type": "scatter",
                    "mode": "markers",
                    "x": ax,
                    "y": anomalies[target].round(6).tolist(),
                    "name": "Anomalies",
                    "marker": {"color": "#d62728", "size": 9, "symbol": "x"},
                },
            ],
            "layout": {
                "title": f"Anomaly Graph ({target})",
                "template": "plotly_white",
            },
        }



def _default_value(mapping: ColumnInference) -> str | None:
    return mapping.climate_variables[0] if mapping.climate_variables else None


visualization_builder = VisualizationBuilder()
