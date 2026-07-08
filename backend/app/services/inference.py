from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


TIME_HINTS = {"time", "date", "datetime", "timestamp", "year", "month", "day"}
LAT_HINTS = {"lat", "latitude", "y"}
LON_HINTS = {"lon", "lng", "longitude", "x"}
VARIABLE_HINTS = {
    "temp",
    "temperature",
    "precip",
    "precipitation",
    "rain",
    "humidity",
    "wind",
    "pressure",
    "co2",
}


def _contains_hint(column: str, hints: set[str]) -> bool:
    lowered = column.lower()
    return any(hint in lowered for hint in hints)


def _is_datetime_like(series: pd.Series) -> bool:
    if pd.api.types.is_datetime64_any_dtype(series):
        return True

    if not pd.api.types.is_object_dtype(series) and not pd.api.types.is_string_dtype(series):
        return False

    sample = series.dropna().astype(str).head(200)
    if sample.empty:
        return False

    parsed = pd.to_datetime(sample, errors="coerce", utc=True)
    return parsed.notna().mean() >= 0.8


def infer_column_roles(df: pd.DataFrame) -> dict[str, Any]:
    time_column: str | None = None
    latitude_column: str | None = None
    longitude_column: str | None = None
    climate_variables: list[str] = []
    column_types: dict[str, str] = {}

    for column in df.columns:
        series = df[column]
        lowered = column.lower()

        if _is_datetime_like(series):
            inferred_type = "time"
            if time_column is None or _contains_hint(lowered, TIME_HINTS):
                time_column = column
        elif pd.api.types.is_numeric_dtype(series):
            inferred_type = "numeric"

            if latitude_column is None and _contains_hint(lowered, LAT_HINTS):
                latitude_column = column
                inferred_type = "latitude"
            elif longitude_column is None and _contains_hint(lowered, LON_HINTS):
                longitude_column = column
                inferred_type = "longitude"
            elif _contains_hint(lowered, VARIABLE_HINTS):
                climate_variables.append(column)
        else:
            inferred_type = "categorical"

        column_types[column] = inferred_type

    if latitude_column is None:
        latitude_column = _guess_geo_column(df, "lat")
        if latitude_column:
            column_types[latitude_column] = "latitude"

    if longitude_column is None:
        longitude_column = _guess_geo_column(df, "lon")
        if longitude_column:
            column_types[longitude_column] = "longitude"

    if not climate_variables:
        numeric_columns = [
            col
            for col in df.select_dtypes(include=[np.number]).columns
            if col not in {latitude_column, longitude_column}
        ]
        climate_variables = numeric_columns[:8]

    return {
        "time_column": time_column,
        "latitude_column": latitude_column,
        "longitude_column": longitude_column,
        "climate_variables": climate_variables,
        "column_types": column_types,
    }


def _guess_geo_column(df: pd.DataFrame, axis: str) -> str | None:
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    candidates: list[str] = []
    for col in numeric_cols:
        series = df[col].dropna()
        if series.empty:
            continue
        min_val = float(series.min())
        max_val = float(series.max())
        if axis == "lat" and -90.0 <= min_val <= 90.0 and -90.0 <= max_val <= 90.0:
            candidates.append(col)
        if axis == "lon" and -180.0 <= min_val <= 180.0 and -180.0 <= max_val <= 180.0:
            candidates.append(col)

    if not candidates:
        return None

    # Prefer name-based matches among range-compatible columns.
    preferred_hints = LAT_HINTS if axis == "lat" else LON_HINTS
    for col in candidates:
        if _contains_hint(col, preferred_hints):
            return col
    return candidates[0]
