export type AnalysisType =
  | "descriptive_stats"
  | "trend_detection"
  | "correlation"
  | "linear_regression"
  | "temperature_trend"
  | "precipitation_trend"
  | "seasonal_patterns"
  | "diurnal_cycle"
  | "annual_trend_signal"
  | "baseline_anomalies"
  | "extreme_events"
  | "decadal_distributions"
  | "anomaly_detection"
  | "random_forest_regression"
  | "time_series_forecasting"
  | "climate_workflow";

export type VisualizationType =
  | "time_series"
  | "scatter"
  | "heatmap"
  | "map"
  | "anomaly_graph";

export type TransformationOperation =
  | "kelvin_to_celsius"
  | "kelvin_to_fahrenheit"
  | "celsius_to_kelvin"
  | "ms_to_kmh"
  | "ms_to_mph"
  | "pa_to_hpa"
  | "multiply_constant"
  | "divide_constant"
  | "add_constant"
  | "subtract_constant"
  | "rolling_mean"
  | "aggregate_by_day"
  | "aggregate_by_month";

export interface TransformationRecipe {
  recipe_id: string;
  source_variable: string;
  operation: TransformationOperation;
  output_variable: string;
  parameters: Record<string, unknown>;
  created_at: string;
}

export interface TransformationSuggestion {
  source_variable: string;
  operation: TransformationOperation;
  suggested_output: string;
  reason: string;
}

export interface TransformationsResponse {
  dataset_id: string;
  transformations: TransformationRecipe[];
  suggestions: TransformationSuggestion[];
}

export interface TransformationCreateRequest {
  source_variable: string;
  operation: TransformationOperation;
  output_variable: string;
  parameters?: Record<string, unknown>;
}

export interface TemporalAggregationRequest {
  time_column?: string | null;
  value_columns: string[];
  frequency: "D" | "ME" | "YE";
  aggregations: Array<"mean" | "min" | "max" | "range" | "sum" | "count" | "std">;
  output_name?: string | null;
}

export interface ColumnInference {
  time_column: string | null;
  latitude_column: string | null;
  longitude_column: string | null;
  climate_variables: string[];
  column_types: Record<string, string>;
}

export interface DatasetSummary {
  dataset_id: string;
  name: string;
  source_format: string;
  created_at: string;
  row_count: number;
  columns: string[];
}

export interface DatasetMetadata extends DatasetSummary {
  parser_metadata: Record<string, unknown>;
  mapping: ColumnInference;
  transformations: TransformationRecipe[];
  derived_columns: string[];
}

export interface DatasetPreview {
  dataset_id: string;
  columns: string[];
  rows: Array<Record<string, unknown>>;
  row_count: number;
  derived_columns: string[];
}

export interface MappingUpdateRequest {
  time_column: string | null;
  latitude_column: string | null;
  longitude_column: string | null;
  climate_variables: string[];
}

export interface AnalysisRequest {
  analysis_type: AnalysisType;
  target_column?: string | null;
  feature_columns?: string[];
  time_column?: string | null;
  options?: Record<string, unknown>;
}

export interface AnalysisResponse {
  dataset_id: string;
  analysis_type: AnalysisType;
  result: Record<string, unknown>;
}

export interface VisualizationRequest {
  visualization_type: VisualizationType;
  x_column?: string | null;
  y_column?: string | null;
  value_column?: string | null;
  options?: Record<string, unknown>;
}

export interface VisualizationResponse {
  dataset_id: string;
  visualization_type: VisualizationType;
  figure: {
    data: Array<Record<string, unknown>>;
    layout: Record<string, unknown>;
  };
}
