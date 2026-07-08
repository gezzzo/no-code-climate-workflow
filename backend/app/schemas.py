from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class DatasetSummary(BaseModel):
    dataset_id: str
    name: str
    source_format: str
    created_at: datetime
    row_count: int
    columns: list[str]


class ColumnInference(BaseModel):
    time_column: str | None = None
    latitude_column: str | None = None
    longitude_column: str | None = None
    climate_variables: list[str] = Field(default_factory=list)
    column_types: dict[str, str] = Field(default_factory=dict)


TransformationOperation = Literal[
    "kelvin_to_celsius",
    "kelvin_to_fahrenheit",
    "celsius_to_kelvin",
    "ms_to_kmh",
    "ms_to_mph",
    "pa_to_hpa",
    "multiply_constant",
    "divide_constant",
    "add_constant",
    "subtract_constant",
    "rolling_mean",
    "aggregate_by_day",
    "aggregate_by_month",
]


class TransformationRecipe(BaseModel):
    recipe_id: str
    source_variable: str
    operation: TransformationOperation
    output_variable: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class TransformationCreateRequest(BaseModel):
    source_variable: str
    operation: TransformationOperation
    output_variable: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class TransformationSuggestion(BaseModel):
    source_variable: str
    operation: TransformationOperation
    suggested_output: str
    reason: str


class TransformationsResponse(BaseModel):
    dataset_id: str
    transformations: list[TransformationRecipe] = Field(default_factory=list)
    suggestions: list[TransformationSuggestion] = Field(default_factory=list)


class DatasetMetadata(DatasetSummary):
    parser_metadata: dict[str, Any] = Field(default_factory=dict)
    mapping: ColumnInference
    transformations: list[TransformationRecipe] = Field(default_factory=list)
    derived_columns: list[str] = Field(default_factory=list)


class GitHubImportRequest(BaseModel):
    url: str


class TemporalAggregationRequest(BaseModel):
    time_column: str | None = None
    value_columns: list[str] = Field(default_factory=list)
    frequency: Literal["D", "ME", "YE"] = "D"
    aggregations: list[Literal["mean", "min", "max", "range", "sum", "count", "std"]] = Field(
        default_factory=lambda: ["mean", "min", "max"]
    )
    output_name: str | None = None


class DatasetPreview(BaseModel):
    dataset_id: str
    columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int
    derived_columns: list[str] = Field(default_factory=list)


class MappingUpdateRequest(BaseModel):
    time_column: str | None = None
    latitude_column: str | None = None
    longitude_column: str | None = None
    climate_variables: list[str] = Field(default_factory=list)


class AnalysisRequest(BaseModel):
    analysis_type: Literal[
        "descriptive_stats",
        "trend_detection",
        "correlation",
        "linear_regression",
        "temperature_trend",
        "precipitation_trend",
        "seasonal_patterns",
        "diurnal_cycle",
        "annual_trend_signal",
        "baseline_anomalies",
        "extreme_events",
        "decadal_distributions",
        "anomaly_detection",
        "random_forest_regression",
        "time_series_forecasting",
        "climate_workflow",
    ]
    target_column: str | None = None
    feature_columns: list[str] = Field(default_factory=list)
    time_column: str | None = None
    options: dict[str, Any] = Field(default_factory=dict)


class AnalysisResponse(BaseModel):
    dataset_id: str
    analysis_type: str
    result: dict[str, Any]


class VisualizationRequest(BaseModel):
    visualization_type: Literal[
        "time_series",
        "scatter",
        "heatmap",
        "map",
        "anomaly_graph",
    ]
    x_column: str | None = None
    y_column: str | None = None
    value_column: str | None = None
    options: dict[str, Any] = Field(default_factory=dict)


class VisualizationResponse(BaseModel):
    dataset_id: str
    visualization_type: str
    figure: dict[str, Any]


class ErrorResponse(BaseModel):
    detail: str
