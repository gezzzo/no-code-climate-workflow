from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, cast
from uuid import uuid4

import pandas as pd

from app.schemas import (
    ColumnInference,
    DatasetMetadata,
    TransformationCreateRequest,
    TransformationOperation,
    TransformationRecipe,
    TransformationSuggestion,
)


MATH_OPERATIONS = {
    "multiply_constant",
    "divide_constant",
    "add_constant",
    "subtract_constant",
}


def build_transformation_recipe(
    payload: TransformationCreateRequest,
    mapping: ColumnInference,
) -> TransformationRecipe:
    source_variable = payload.source_variable.strip()
    output_variable = payload.output_variable.strip()
    if not source_variable:
        raise ValueError("Source variable is required.")
    if not output_variable:
        raise ValueError("Output variable name is required.")

    if source_variable == output_variable:
        raise ValueError("Output variable must be different from source variable.")

    parameters = dict(payload.parameters)

    if payload.operation in MATH_OPERATIONS:
        constant = _to_float(parameters.get("constant"))
        if constant is None:
            raise ValueError("This transformation requires a numeric constant parameter.")
        if payload.operation == "divide_constant" and constant == 0:
            raise ValueError("Cannot divide by zero.")
        parameters = {"constant": constant}

    if payload.operation == "rolling_mean":
        window = int(parameters.get("window", 7))
        if window <= 0:
            raise ValueError("Rolling mean requires window >= 1.")
        time_column = str(parameters.get("time_column") or mapping.time_column or "").strip()
        if not time_column:
            raise ValueError("Rolling mean requires a mapped time column.")
        parameters = {
            "window": window,
            "time_column": time_column,
        }

    if payload.operation in {"aggregate_by_day", "aggregate_by_month"}:
        time_column = str(parameters.get("time_column") or mapping.time_column or "").strip()
        if not time_column:
            raise ValueError("Day/month aggregation requires a mapped time column.")
        parameters = {"time_column": time_column}

    return TransformationRecipe(
        recipe_id=uuid4().hex,
        source_variable=source_variable,
        operation=payload.operation,
        output_variable=output_variable,
        parameters=parameters,
        created_at=datetime.now(timezone.utc),
    )



def apply_transformation_recipes(
    df: pd.DataFrame,
    recipes: list[TransformationRecipe],
    mapping: ColumnInference,
) -> pd.DataFrame:
    working = df.copy()
    for recipe in recipes:
        working = apply_transformation_recipe(working, recipe, mapping)
    return working



def apply_transformation_recipe(
    df: pd.DataFrame,
    recipe: TransformationRecipe,
    mapping: ColumnInference,
) -> pd.DataFrame:
    if recipe.source_variable not in df.columns:
        raise ValueError(f"Source variable '{recipe.source_variable}' not found in dataset.")

    source_series = pd.to_numeric(df[recipe.source_variable], errors="coerce")
    operation = recipe.operation

    if operation == "kelvin_to_celsius":
        result = source_series - 273.15
    elif operation == "kelvin_to_fahrenheit":
        result = (source_series - 273.15) * 9.0 / 5.0 + 32.0
    elif operation == "celsius_to_kelvin":
        result = source_series + 273.15
    elif operation == "ms_to_kmh":
        result = source_series * 3.6
    elif operation == "ms_to_mph":
        result = source_series * 2.2369362921
    elif operation == "pa_to_hpa":
        result = source_series / 100.0
    elif operation == "multiply_constant":
        result = source_series * float(recipe.parameters["constant"])
    elif operation == "divide_constant":
        result = source_series / float(recipe.parameters["constant"])
    elif operation == "add_constant":
        result = source_series + float(recipe.parameters["constant"])
    elif operation == "subtract_constant":
        result = source_series - float(recipe.parameters["constant"])
    elif operation == "rolling_mean":
        result = _apply_rolling_mean(df, source_series, recipe.parameters, mapping)
    elif operation == "aggregate_by_day":
        result = _apply_group_aggregation(df, source_series, recipe.parameters, "day", mapping)
    elif operation == "aggregate_by_month":
        result = _apply_group_aggregation(df, source_series, recipe.parameters, "month", mapping)
    else:
        raise ValueError(f"Unsupported transformation operation: {operation}")

    transformed = df.copy()
    transformed[recipe.output_variable] = result
    return transformed



def suggest_transformations(metadata: DatasetMetadata) -> list[TransformationSuggestion]:
    unit_map = _extract_unit_map(metadata)
    existing_columns = set(metadata.columns)
    suggestions: list[TransformationSuggestion] = []

    for column in metadata.columns:
        unit = unit_map.get(column)

        if unit in {"k", "kelvin"}:
            _append_suggestion(
                suggestions,
                existing_columns,
                column,
                "kelvin_to_celsius",
                "unit metadata indicates Kelvin",
            )
        elif unit in {"pa", "pascal", "pascals"}:
            _append_suggestion(
                suggestions,
                existing_columns,
                column,
                "pa_to_hpa",
                "unit metadata indicates Pascals",
            )
        elif unit in {"m/s", "m s-1", "m s**-1", "mps"}:
            _append_suggestion(
                suggestions,
                existing_columns,
                column,
                "ms_to_kmh",
                "unit metadata indicates meters per second",
            )

        lowered = column.lower()
        if unit is None and lowered.endswith("_k"):
            _append_suggestion(
                suggestions,
                existing_columns,
                column,
                "kelvin_to_celsius",
                "column name suffix suggests Kelvin values",
            )

    return suggestions



def suggested_output_name(source_variable: str, operation: str) -> str:
    suffix_map: dict[str, str] = {
        "kelvin_to_celsius": "c",
        "kelvin_to_fahrenheit": "f",
        "celsius_to_kelvin": "k",
        "ms_to_kmh": "kmh",
        "ms_to_mph": "mph",
        "pa_to_hpa": "hpa",
        "multiply_constant": "mul",
        "divide_constant": "div",
        "add_constant": "add",
        "subtract_constant": "sub",
        "rolling_mean": "rollmean",
        "aggregate_by_day": "daymean",
        "aggregate_by_month": "monthmean",
    }
    suffix = suffix_map.get(operation, "derived")
    return f"{source_variable}_{suffix}"



def _apply_rolling_mean(
    df: pd.DataFrame,
    source_series: pd.Series,
    parameters: dict[str, Any],
    mapping: ColumnInference,
) -> pd.Series:
    time_column = str(parameters.get("time_column") or mapping.time_column or "").strip()
    if not time_column:
        raise ValueError("Rolling mean requires time_column parameter.")
    if time_column not in df.columns:
        raise ValueError(f"Time column '{time_column}' not found for rolling mean.")

    window = int(parameters.get("window", 7))
    if window <= 0:
        raise ValueError("Rolling mean requires window >= 1.")

    timestamps = _parse_time_series(df[time_column], time_column)
    order = timestamps.sort_values(kind="mergesort").index
    sorted_values = source_series.loc[order]
    rolled = sorted_values.rolling(window=window, min_periods=1).mean()

    output = pd.Series(index=df.index, dtype=float)
    output.loc[order] = rolled.to_numpy()
    return output



def _apply_group_aggregation(
    df: pd.DataFrame,
    source_series: pd.Series,
    parameters: dict[str, Any],
    frequency: str,
    mapping: ColumnInference,
) -> pd.Series:
    time_column = str(parameters.get("time_column") or mapping.time_column or "").strip()
    if not time_column:
        raise ValueError("Aggregation requires time_column parameter.")
    if time_column not in df.columns:
        raise ValueError(f"Time column '{time_column}' not found for aggregation.")

    timestamps = _parse_time_series(df[time_column], time_column)
    naive = timestamps.dt.tz_localize(None)

    if frequency == "day":
        keys = naive.dt.floor("D")
    else:
        keys = naive.dt.to_period("M").astype(str)

    return source_series.groupby(keys).transform("mean")



def _parse_time_series(series: pd.Series, label: str) -> pd.Series:
    parsed = pd.to_datetime(series, errors="coerce", utc=True)
    if parsed.notna().sum() == 0:
        raise ValueError(f"Column '{label}' does not contain parseable datetime values.")
    return parsed



def _extract_unit_map(metadata: DatasetMetadata) -> dict[str, str]:
    parser_metadata = metadata.parser_metadata or {}
    variable_attributes = parser_metadata.get("variable_attributes", {})
    if not isinstance(variable_attributes, dict):
        return {}

    units: dict[str, str] = {}
    for variable, attrs in variable_attributes.items():
        if not isinstance(attrs, dict):
            continue
        unit_value = attrs.get("units")
        if unit_value is None:
            continue
        normalized = str(unit_value).strip().lower()
        if normalized:
            units[str(variable)] = normalized

    return units



def _append_suggestion(
    suggestions: list[TransformationSuggestion],
    existing_columns: set[str],
    source_variable: str,
    operation: str,
    reason: str,
) -> None:
    suggested_output = suggested_output_name(source_variable, operation)

    if suggested_output in existing_columns:
        return

    already_exists = any(
        item.source_variable == source_variable and item.operation == operation
        for item in suggestions
    )
    if already_exists:
        return

    suggestions.append(
        TransformationSuggestion(
            source_variable=source_variable,
            operation=cast(TransformationOperation, operation),
            suggested_output=suggested_output,
            reason=reason,
        )
    )



def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
