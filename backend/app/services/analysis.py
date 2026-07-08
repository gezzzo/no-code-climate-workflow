from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

from app.schemas import AnalysisRequest, ColumnInference


SEASON_ORDER = ["winter", "spring", "summer", "autumn"]
MONTH_LABELS = {
    1: "Jan",
    2: "Feb",
    3: "Mar",
    4: "Apr",
    5: "May",
    6: "Jun",
    7: "Jul",
    8: "Aug",
    9: "Sep",
    10: "Oct",
    11: "Nov",
    12: "Dec",
}


@dataclass
class AnalysisEngine:
    def run(self, df: pd.DataFrame, mapping: ColumnInference, request: AnalysisRequest) -> dict[str, Any]:
        analysis_type = request.analysis_type

        if analysis_type == "descriptive_stats":
            return self.descriptive_stats(df, mapping, request)
        if analysis_type in {"trend_detection", "temperature_trend", "precipitation_trend"}:
            return self.trend_detection(df, mapping, request)
        if analysis_type == "correlation":
            return self.correlation(df, mapping, request)
        if analysis_type == "linear_regression":
            return self.linear_regression(df, mapping, request)
        if analysis_type == "seasonal_patterns":
            return self.seasonal_patterns(df, mapping, request)
        if analysis_type == "diurnal_cycle":
            return self.diurnal_cycle(df, mapping, request)
        if analysis_type == "annual_trend_signal":
            return self.annual_trend_signal(df, mapping, request)
        if analysis_type == "baseline_anomalies":
            return self.baseline_anomalies(df, mapping, request)
        if analysis_type == "extreme_events":
            return self.extreme_events(df, mapping, request)
        if analysis_type == "decadal_distributions":
            return self.decadal_distributions(df, mapping, request)
        if analysis_type == "anomaly_detection":
            return self.anomaly_detection(df, mapping, request)
        if analysis_type == "random_forest_regression":
            return self.random_forest_regression(df, mapping, request)
        if analysis_type == "time_series_forecasting":
            return self.time_series_forecasting(df, mapping, request)
        if analysis_type == "climate_workflow":
            return self.climate_workflow(df, mapping, request)

        raise ValueError(f"Unsupported analysis type: {analysis_type}")

    def climate_workflow(
        self,
        df: pd.DataFrame,
        mapping: ColumnInference,
        request: AnalysisRequest,
    ) -> dict[str, Any]:
        time_col = request.time_column or mapping.time_column
        target = request.target_column or self._default_target(mapping)

        if not time_col:
            raise ValueError("Climate workflow requires a time column. Map one first.")
        if not target:
            raise ValueError("Climate workflow requires a numeric target variable.")
        if time_col not in df.columns:
            raise ValueError(f"Time column '{time_col}' not found.")
        if target not in df.columns:
            raise ValueError(f"Target column '{target}' not found.")

        frequency = _normalize_frequency(str(request.options.get("aggregation_frequency", "D")))
        baseline_start = request.options.get("baseline_start")
        baseline_end = request.options.get("baseline_end")
        high_quantile = _bounded_float(request.options.get("high_quantile"), 0.95, 0.5, 0.999)
        low_quantile = _bounded_float(request.options.get("low_quantile"), 0.05, 0.001, 0.5)

        working = df[[time_col, target]].copy()
        working[time_col] = pd.to_datetime(working[time_col], errors="coerce", utc=True)
        working[target] = pd.to_numeric(working[target], errors="coerce")

        source_rows = int(len(working))
        missing_time = int(working[time_col].isna().sum())
        missing_target = int(working[target].isna().sum())

        working = working.dropna(subset=[time_col, target]).sort_values(time_col)
        if len(working) < 3:
            raise ValueError("Climate workflow needs at least 3 valid time/value rows.")

        aggregated = (
            working.set_index(time_col)[target]
            .resample(frequency)
            .agg(["mean", "min", "max", "count"])
            .dropna(subset=["mean"])
        )
        if len(aggregated) < 3:
            raise ValueError("Climate workflow needs at least 3 aggregated periods.")

        aggregated["range"] = aggregated["max"] - aggregated["min"]
        aggregated.index.name = "time"

        summary = working[target].describe(percentiles=[0.25, 0.5, 0.75])
        month_summary = _monthly_summary(aggregated)
        season_summary = _seasonal_summary(aggregated)
        annual_summary = _annual_summary(aggregated)
        baseline = _baseline_monthly_means(aggregated, baseline_start, baseline_end)
        annual_anomalies = _annual_anomalies(aggregated, baseline["monthly_means"])
        extremes = _extreme_summary(aggregated, high_quantile, low_quantile)
        decade_summary = _decade_summary(aggregated)

        return {
            "time_column": time_col,
            "target_column": target,
            "aggregation_frequency": frequency,
            "source_rows": source_rows,
            "valid_rows": int(len(working)),
            "aggregated_periods": int(len(aggregated)),
            "date_range": {
                "start": working[time_col].iloc[0].isoformat(),
                "end": working[time_col].iloc[-1].isoformat(),
            },
            "data_quality": {
                "missing_time": missing_time,
                "missing_target": missing_target,
            },
            "summary": {
                "count": _clean_number(summary.get("count")),
                "mean": _clean_number(summary.get("mean")),
                "std": _clean_number(summary.get("std")),
                "min": _clean_number(summary.get("min")),
                "q25": _clean_number(summary.get("25%")),
                "median": _clean_number(summary.get("50%")),
                "q75": _clean_number(summary.get("75%")),
                "max": _clean_number(summary.get("max")),
            },
            "monthly_climatology": month_summary,
            "seasonal_cycle": season_summary,
            "annual_trend": annual_summary,
            "anomalies": {
                "baseline": baseline["metadata"],
                "annual": annual_anomalies,
            },
            "extremes": extremes,
            "decadal_distribution": decade_summary,
            "aggregated_preview": _aggregated_preview(aggregated),
        }

    def descriptive_stats(
        self,
        df: pd.DataFrame,
        mapping: ColumnInference,
        request: AnalysisRequest,
    ) -> dict[str, Any]:
        numeric_columns = self._numeric_columns(df)
        selected = request.feature_columns or mapping.climate_variables or numeric_columns
        selected = [col for col in selected if col in numeric_columns]
        if not selected:
            raise ValueError("No numeric columns available for descriptive statistics.")

        summary = (
            df[selected]
            .describe(percentiles=[0.25, 0.5, 0.75])
            .transpose()
            .reset_index()
            .rename(columns={"index": "column"})
            .round(6)
        )

        return {
            "columns": selected,
            "summary": summary.to_dict(orient="records"),
        }

    def trend_detection(
        self,
        df: pd.DataFrame,
        mapping: ColumnInference,
        request: AnalysisRequest,
    ) -> dict[str, Any]:
        time_col = request.time_column or mapping.time_column
        target = self._resolve_trend_target(df, mapping, request)

        if not time_col:
            raise ValueError("Trend detection requires a time column. Map one first.")
        if target not in df.columns:
            raise ValueError(f"Target column '{target}' not found.")

        working = df[[time_col, target]].dropna().copy()
        working[time_col] = pd.to_datetime(working[time_col], errors="coerce", utc=True)
        working = working.dropna(subset=[time_col])
        working[target] = pd.to_numeric(working[target], errors="coerce")
        working = working.dropna(subset=[target]).sort_values(time_col)
        if len(working) < 3:
            raise ValueError("Trend detection needs at least 3 valid time points.")

        x = working[time_col].astype("int64") / 1e9
        y = working[target].astype(float)
        slope, intercept = np.polyfit(x.to_numpy(), y.to_numpy(), 1)
        predictions = slope * x + intercept
        r2 = float(r2_score(y, predictions))

        direction = "increasing" if slope > 0 else "decreasing" if slope < 0 else "stable"

        return {
            "time_column": time_col,
            "target_column": target,
            "slope_per_second": float(slope),
            "intercept": float(intercept),
            "r2": r2,
            "trend_direction": direction,
            "points": [
                {
                    "time": t.isoformat(),
                    "value": float(v),
                    "fitted": float(f),
                }
                for t, v, f in zip(working[time_col], y, predictions)
            ],
        }

    def correlation(
        self,
        df: pd.DataFrame,
        mapping: ColumnInference,
        request: AnalysisRequest,
    ) -> dict[str, Any]:
        numeric_cols = self._numeric_columns(df)
        selected = request.feature_columns or mapping.climate_variables or numeric_cols
        selected = [col for col in selected if col in numeric_cols]
        if len(selected) < 2:
            raise ValueError("Correlation needs at least two numeric columns.")

        matrix = df[selected].corr(numeric_only=True).round(6)
        return {
            "columns": selected,
            "matrix": matrix.to_dict(orient="index"),
        }

    def linear_regression(
        self,
        df: pd.DataFrame,
        mapping: ColumnInference,
        request: AnalysisRequest,
    ) -> dict[str, Any]:
        target = request.target_column or self._default_target(mapping)
        if not target:
            raise ValueError("Select a target column for linear regression.")

        numeric_cols = self._numeric_columns(df)
        features = request.feature_columns or [col for col in mapping.climate_variables if col != target]
        features = [col for col in features if col in numeric_cols and col != target]
        if not features:
            raise ValueError("Linear regression requires at least one numeric feature column.")

        model_df = df[features + [target]].dropna().copy()
        if len(model_df) < 10:
            raise ValueError("Linear regression needs at least 10 complete rows.")

        X = model_df[features]
        y = pd.to_numeric(model_df[target], errors="coerce")
        valid = y.notna()
        X = X[valid]
        y = y[valid]

        X_train, X_test, y_train, y_test = train_test_split(
            X,
            y,
            test_size=0.2,
            random_state=42,
        )

        model = LinearRegression()
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)

        return {
            "target_column": target,
            "feature_columns": features,
            "coefficients": {feature: float(coef) for feature, coef in zip(features, model.coef_)},
            "intercept": float(model.intercept_),
            "r2": float(r2_score(y_test, y_pred)),
            "rmse": float(np.sqrt(mean_squared_error(y_test, y_pred))),
            "test_points": int(len(y_test)),
        }

    def seasonal_patterns(
        self,
        df: pd.DataFrame,
        mapping: ColumnInference,
        request: AnalysisRequest,
    ) -> dict[str, Any]:
        time_col = request.time_column or mapping.time_column
        target = request.target_column or self._default_target(mapping)

        if not time_col:
            raise ValueError("Seasonal analysis requires a mapped time column.")
        if not target:
            raise ValueError("Seasonal analysis requires a target climate variable.")
        if time_col not in df.columns:
            raise ValueError(f"Time column '{time_col}' not found.")
        if target not in df.columns:
            raise ValueError(f"Target column '{target}' not found.")

        working = df[[time_col, target]].copy()
        working[time_col] = pd.to_datetime(working[time_col], errors="coerce", utc=True)
        working[target] = pd.to_numeric(working[target], errors="coerce")

        source_rows = int(len(working))
        missing_time = int(working[time_col].isna().sum())
        missing_target = int(working[target].isna().sum())

        working = working.dropna(subset=[time_col, target]).sort_values(time_col)
        if len(working) < 3:
            raise ValueError("Seasonal analysis needs at least 3 valid time/value rows.")

        working["month"] = working[time_col].dt.month
        working["season"] = working["month"].map(_month_to_season)

        month_summary = (
            working.groupby("month")[target]
            .agg(["mean", "std", "min", "max", "count"])
            .reindex(range(1, 13))
        )
        season_summary = (
            working.groupby("season")[target]
            .agg(["mean", "std", "min", "max", "count"])
            .reindex(SEASON_ORDER)
        )

        valid_months = month_summary.dropna(subset=["mean"])
        warmest_month = int(valid_months["mean"].idxmax())
        coolest_month = int(valid_months["mean"].idxmin())
        annual_mean = float(working[target].mean())
        monthly_records = _monthly_climatology_records(month_summary)
        seasonal_records = _seasonal_cycle_records(season_summary)

        return {
            "time_column": time_col,
            "target_column": target,
            "source_rows": source_rows,
            "valid_rows": int(len(working)),
            "date_range": {
                "start": working[time_col].iloc[0].isoformat(),
                "end": working[time_col].iloc[-1].isoformat(),
            },
            "data_quality": {
                "missing_time": missing_time,
                "missing_target": missing_target,
                "observed_months": int(working["month"].nunique()),
                "complete_12_month_profile": int(working["month"].nunique()) == 12,
            },
            "summary": {
                "annual_mean": _clean_number(annual_mean),
                "warmest_month": warmest_month,
                "warmest_month_label": MONTH_LABELS[warmest_month],
                "warmest_value": _clean_number(valid_months.loc[warmest_month, "mean"]),
                "coolest_month": coolest_month,
                "coolest_month_label": MONTH_LABELS[coolest_month],
                "coolest_value": _clean_number(valid_months.loc[coolest_month, "mean"]),
                "seasonal_range": _clean_number(
                    float(valid_months.loc[warmest_month, "mean"])
                    - float(valid_months.loc[coolest_month, "mean"])
                ),
            },
            "monthly_climatology": monthly_records,
            "seasonal_cycle": seasonal_records,
            "monthly_pattern": [
                {"month": item["month"], "mean_value": item["mean"]}
                for item in monthly_records
                if item["mean"] is not None
            ],
            "seasonal_pattern": [
                {"season": item["season"], "mean_value": item["mean"]}
                for item in seasonal_records
                if item["mean"] is not None
            ],
        }

    def diurnal_cycle(
        self,
        df: pd.DataFrame,
        mapping: ColumnInference,
        request: AnalysisRequest,
    ) -> dict[str, Any]:
        time_col = request.time_column or mapping.time_column
        target = request.target_column or self._default_target(mapping)

        if not time_col:
            raise ValueError("Diurnal cycle requires a mapped time column.")
        if not target:
            raise ValueError("Diurnal cycle requires a numeric target variable.")
        if time_col not in df.columns:
            raise ValueError(f"Time column '{time_col}' not found.")
        if target not in df.columns:
            raise ValueError(f"Target column '{target}' not found.")

        hour_offset = _bounded_float(
            request.options.get("timezone_offset_hours"),
            0.0,
            -14.0,
            14.0,
        )
        working = df[[time_col, target]].copy()
        working[time_col] = pd.to_datetime(working[time_col], errors="coerce", utc=True)
        working[target] = pd.to_numeric(working[target], errors="coerce")

        source_rows = int(len(working))
        missing_time = int(working[time_col].isna().sum())
        missing_target = int(working[target].isna().sum())

        working = working.dropna(subset=[time_col, target]).sort_values(time_col)
        if len(working) < 3:
            raise ValueError("Diurnal cycle needs at least 3 valid time/value rows.")

        shifted_time = working[time_col] + pd.to_timedelta(hour_offset, unit="h")
        working["hour"] = shifted_time.dt.hour
        working["month"] = shifted_time.dt.month
        working["season"] = working["month"].map(_month_to_season)

        observed_hours = int(working["hour"].nunique())
        if observed_hours < 2:
            raise ValueError(
                "Diurnal cycle needs at least 2 distinct hours. Use data with sub-daily timestamps."
            )

        hourly = (
            working.groupby("hour")[target]
            .agg(["mean", "std", "min", "max", "count"])
            .reindex(range(24))
        )
        hourly["count"] = hourly["count"].fillna(0)
        valid_hourly = hourly.dropna(subset=["mean"])
        warmest_hour = int(valid_hourly["mean"].idxmax())
        coolest_hour = int(valid_hourly["mean"].idxmin())
        warmest_value = float(valid_hourly.loc[warmest_hour, "mean"])
        coolest_value = float(valid_hourly.loc[coolest_hour, "mean"])

        seasonal = (
            working.groupby(["season", "hour"])[target]
            .agg(["mean", "std", "min", "max", "count"])
        )

        return {
            "time_column": time_col,
            "target_column": target,
            "timezone_offset_hours": hour_offset,
            "source_rows": source_rows,
            "valid_rows": int(len(working)),
            "date_range": {
                "start": working[time_col].iloc[0].isoformat(),
                "end": working[time_col].iloc[-1].isoformat(),
            },
            "data_quality": {
                "missing_time": missing_time,
                "missing_target": missing_target,
                "observed_hours": observed_hours,
                "complete_24_hour_profile": observed_hours == 24,
            },
            "summary": {
                "diurnal_range": _clean_number(warmest_value - coolest_value),
                "warmest_hour": warmest_hour,
                "warmest_value": _clean_number(warmest_value),
                "coolest_hour": coolest_hour,
                "coolest_value": _clean_number(coolest_value),
                "seasonal_peaks": _seasonal_hour_peaks(seasonal),
            },
            "hourly_profile": _hourly_profile_records(hourly),
            "seasonal_hourly_profile": _seasonal_hourly_profile_records(seasonal),
            "season_definitions": {
                "winter": [12, 1, 2],
                "spring": [3, 4, 5],
                "summer": [6, 7, 8],
                "autumn": [9, 10, 11],
            },
        }

    def annual_trend_signal(
        self,
        df: pd.DataFrame,
        mapping: ColumnInference,
        request: AnalysisRequest,
    ) -> dict[str, Any]:
        time_col = request.time_column or mapping.time_column
        target = request.target_column or self._default_target(mapping)

        if not time_col:
            raise ValueError("Annual trend signal requires a mapped time column.")
        if not target:
            raise ValueError("Annual trend signal requires a numeric target variable.")
        if time_col not in df.columns:
            raise ValueError(f"Time column '{time_col}' not found.")
        if target not in df.columns:
            raise ValueError(f"Target column '{target}' not found.")

        working = df[[time_col, target]].copy()
        working[time_col] = pd.to_datetime(working[time_col], errors="coerce", utc=True)
        working[target] = pd.to_numeric(working[target], errors="coerce")

        source_rows = int(len(working))
        missing_time = int(working[time_col].isna().sum())
        missing_target = int(working[target].isna().sum())

        working = working.dropna(subset=[time_col, target]).sort_values(time_col)
        if len(working) < 3:
            raise ValueError("Annual trend signal needs at least 3 valid time/value rows.")

        daily = (
            working.set_index(time_col)[target]
            .resample("D")
            .agg(["mean", "min", "max", "count"])
            .dropna(subset=["mean"])
        )
        if len(daily) < 3:
            raise ValueError("Annual trend signal needs at least 3 daily periods.")

        annual = daily.assign(year=daily.index.year).groupby("year")["mean"].agg(["mean", "std", "min", "max", "count"])
        annual = annual.dropna(subset=["mean"])
        if len(annual) < 3:
            raise ValueError("Annual trend signal needs at least 3 observed years.")

        years = annual.index.to_numpy(dtype=float)
        values = annual["mean"].to_numpy(dtype=float)
        slope, intercept = np.polyfit(years, values, 1)
        fitted = slope * years + intercept

        lowest_year = int(annual["mean"].idxmin())
        highest_year = int(annual["mean"].idxmax())
        direction = "increasing" if slope > 0 else "decreasing" if slope < 0 else "stable"

        return {
            "time_column": time_col,
            "target_column": target,
            "source_rows": source_rows,
            "valid_rows": int(len(working)),
            "daily_periods": int(len(daily)),
            "annual_periods": int(len(annual)),
            "date_range": {
                "start": working[time_col].iloc[0].isoformat(),
                "end": working[time_col].iloc[-1].isoformat(),
            },
            "data_quality": {
                "missing_time": missing_time,
                "missing_target": missing_target,
                "observed_years": int(len(annual)),
            },
            "summary": {
                "slope_per_year": _clean_number(slope),
                "warming_per_decade": _clean_number(slope * 10),
                "slope_per_decade": _clean_number(slope * 10),
                "total_change": _clean_number(slope * (years[-1] - years[0])),
                "r2": _clean_number(r2_score(values, fitted)),
                "trend_direction": direction,
                "coldest_year": lowest_year,
                "coldest_value": _clean_number(annual.loc[lowest_year, "mean"]),
                "warmest_year": highest_year,
                "warmest_value": _clean_number(annual.loc[highest_year, "mean"]),
                "lowest_year": lowest_year,
                "lowest_value": _clean_number(annual.loc[lowest_year, "mean"]),
                "highest_year": highest_year,
                "highest_value": _clean_number(annual.loc[highest_year, "mean"]),
            },
            "annual_series": [
                {
                    "year": int(year),
                    "mean": _clean_number(row["mean"]),
                    "std": _clean_number(row["std"]),
                    "min": _clean_number(row["min"]),
                    "max": _clean_number(row["max"]),
                    "count": int(row["count"]),
                    "trend": _clean_number(fitted[index]),
                }
                for index, (year, row) in enumerate(annual.iterrows())
            ],
        }

    def baseline_anomalies(
        self,
        df: pd.DataFrame,
        mapping: ColumnInference,
        request: AnalysisRequest,
    ) -> dict[str, Any]:
        time_col = request.time_column or mapping.time_column
        target = request.target_column or self._default_target(mapping)

        if not time_col:
            raise ValueError("Baseline anomalies require a mapped time column.")
        if not target:
            raise ValueError("Baseline anomalies require a numeric target variable.")
        if time_col not in df.columns:
            raise ValueError(f"Time column '{time_col}' not found.")
        if target not in df.columns:
            raise ValueError(f"Target column '{target}' not found.")

        working = df[[time_col, target]].copy()
        working[time_col] = pd.to_datetime(working[time_col], errors="coerce", utc=True)
        working[target] = pd.to_numeric(working[target], errors="coerce")

        source_rows = int(len(working))
        missing_time = int(working[time_col].isna().sum())
        missing_target = int(working[target].isna().sum())

        working = working.dropna(subset=[time_col, target]).sort_values(time_col)
        if len(working) < 3:
            raise ValueError("Baseline anomalies need at least 3 valid time/value rows.")

        baseline_start = request.options.get("baseline_start")
        baseline_end = request.options.get("baseline_end")
        if not baseline_start and not baseline_end:
            wmo_start = pd.Timestamp("1991-01-01", tz="UTC")
            wmo_end = pd.Timestamp("2020-12-31", tz="UTC")
            if working[time_col].iloc[0] <= wmo_start and working[time_col].iloc[-1] >= wmo_end:
                baseline_start = "1991-01-01"
                baseline_end = "2020-12-31"

        daily = (
            working.set_index(time_col)[target]
            .resample("D")
            .agg(["mean", "min", "max", "count"])
            .dropna(subset=["mean"])
        )
        if len(daily) < 3:
            raise ValueError("Baseline anomalies need at least 3 daily periods.")

        baseline = _baseline_monthly_means(daily, baseline_start, baseline_end)
        monthly_baseline = baseline["monthly_means"]
        if monthly_baseline.empty:
            raise ValueError("Baseline anomalies could not build a monthly baseline.")

        anomaly_df = daily.assign(
            year=daily.index.year,
            month=daily.index.month,
        ).copy()
        anomaly_df["monthly_baseline"] = anomaly_df["month"].map(monthly_baseline)
        anomaly_df["anomaly"] = anomaly_df["mean"] - anomaly_df["monthly_baseline"]
        anomaly_df = anomaly_df.dropna(subset=["anomaly"])
        if anomaly_df.empty:
            raise ValueError("Baseline anomalies could not match observations to baseline months.")

        annual = anomaly_df.groupby("year")["anomaly"].agg(["mean", "std", "min", "max", "count"])
        annual = annual.dropna(subset=["mean"])
        if annual.empty:
            raise ValueError("Baseline anomalies need at least one observed year.")

        most_negative_year = int(annual["mean"].idxmin())
        most_positive_year = int(annual["mean"].idxmax())

        return {
            "time_column": time_col,
            "target_column": target,
            "source_rows": source_rows,
            "valid_rows": int(len(working)),
            "daily_periods": int(len(daily)),
            "annual_periods": int(len(annual)),
            "date_range": {
                "start": working[time_col].iloc[0].isoformat(),
                "end": working[time_col].iloc[-1].isoformat(),
            },
            "data_quality": {
                "missing_time": missing_time,
                "missing_target": missing_target,
                "observed_years": int(len(annual)),
                "baseline_months": int(len(monthly_baseline)),
                "complete_12_month_baseline": int(len(monthly_baseline)) == 12,
            },
            "baseline": baseline["metadata"],
            "summary": {
                "baseline_mean": baseline["metadata"].get("mean"),
                "most_negative_year": most_negative_year,
                "most_negative_anomaly": _clean_number(annual.loc[most_negative_year, "mean"]),
                "most_positive_year": most_positive_year,
                "most_positive_anomaly": _clean_number(annual.loc[most_positive_year, "mean"]),
                "negative_years": int((annual["mean"] < 0).sum()),
                "positive_years": int((annual["mean"] >= 0).sum()),
            },
            "monthly_baseline": [
                {
                    "month": month,
                    "month_label": MONTH_LABELS[month],
                    "baseline": _clean_number(monthly_baseline.get(month)),
                }
                for month in range(1, 13)
            ],
            "annual_anomalies": [
                {
                    "year": int(year),
                    "anomaly": _clean_number(row["mean"]),
                    "std": _clean_number(row["std"]),
                    "min": _clean_number(row["min"]),
                    "max": _clean_number(row["max"]),
                    "count": int(row["count"]),
                }
                for year, row in annual.iterrows()
            ],
        }

    def extreme_events(
        self,
        df: pd.DataFrame,
        mapping: ColumnInference,
        request: AnalysisRequest,
    ) -> dict[str, Any]:
        time_col = request.time_column or mapping.time_column
        target = request.target_column or self._default_target(mapping)

        if not time_col:
            raise ValueError("Extreme events require a mapped time column.")
        if not target:
            raise ValueError("Extreme events require a numeric target variable.")
        if time_col not in df.columns:
            raise ValueError(f"Time column '{time_col}' not found.")
        if target not in df.columns:
            raise ValueError(f"Target column '{target}' not found.")

        high_quantile = _bounded_float(request.options.get("high_quantile"), 0.95, 0.5, 0.999)
        low_quantile = _bounded_float(request.options.get("low_quantile"), 0.05, 0.001, 0.5)
        if low_quantile >= high_quantile:
            raise ValueError("Low percentile must be lower than high percentile.")

        working = df[[time_col, target]].copy()
        working[time_col] = pd.to_datetime(working[time_col], errors="coerce", utc=True)
        working[target] = pd.to_numeric(working[target], errors="coerce")

        source_rows = int(len(working))
        missing_time = int(working[time_col].isna().sum())
        missing_target = int(working[target].isna().sum())

        working = working.dropna(subset=[time_col, target]).sort_values(time_col)
        if len(working) < 3:
            raise ValueError("Extreme events need at least 3 valid time/value rows.")

        daily = (
            working.set_index(time_col)[target]
            .resample("D")
            .agg(["mean", "min", "max", "count"])
            .dropna(subset=["mean"])
        )
        if len(daily) < 3:
            raise ValueError("Extreme events need at least 3 daily periods.")

        high_threshold = float(daily["max"].quantile(high_quantile))
        low_threshold = float(daily["min"].quantile(low_quantile))
        daily = daily.assign(
            year=daily.index.year,
            high_extreme=daily["max"] >= high_threshold,
            low_extreme=daily["min"] <= low_threshold,
        )

        annual = daily.groupby("year").agg(
            high_days=("high_extreme", "sum"),
            low_days=("low_extreme", "sum"),
            observed_days=("mean", "count"),
        )
        if annual.empty:
            raise ValueError("Extreme events need at least one observed year.")

        high_trend = _annual_count_trend(annual["high_days"])
        low_trend = _annual_count_trend(annual["low_days"])
        max_high_year = int(annual["high_days"].idxmax())
        max_low_year = int(annual["low_days"].idxmax())

        return {
            "time_column": time_col,
            "target_column": target,
            "source_rows": source_rows,
            "valid_rows": int(len(working)),
            "daily_periods": int(len(daily)),
            "annual_periods": int(len(annual)),
            "date_range": {
                "start": working[time_col].iloc[0].isoformat(),
                "end": working[time_col].iloc[-1].isoformat(),
            },
            "data_quality": {
                "missing_time": missing_time,
                "missing_target": missing_target,
                "observed_years": int(len(annual)),
            },
            "thresholds": {
                "high_quantile": high_quantile,
                "low_quantile": low_quantile,
                "high_threshold": _clean_number(high_threshold),
                "low_threshold": _clean_number(low_threshold),
            },
            "summary": {
                "high_threshold": _clean_number(high_threshold),
                "low_threshold": _clean_number(low_threshold),
                "high_trend_per_decade": high_trend["slope_per_decade"],
                "low_trend_per_decade": low_trend["slope_per_decade"],
                "high_r2": high_trend["r2"],
                "low_r2": low_trend["r2"],
                "high_total_days": int(annual["high_days"].sum()),
                "low_total_days": int(annual["low_days"].sum()),
                "max_high_year": max_high_year,
                "max_high_days": int(annual.loc[max_high_year, "high_days"]),
                "max_low_year": max_low_year,
                "max_low_days": int(annual.loc[max_low_year, "low_days"]),
            },
            "annual_extremes": [
                {
                    "year": int(year),
                    "high_days": int(row["high_days"]),
                    "low_days": int(row["low_days"]),
                    "observed_days": int(row["observed_days"]),
                    "high_trend": high_trend["fitted"].get(int(year)),
                    "low_trend": low_trend["fitted"].get(int(year)),
                }
                for year, row in annual.iterrows()
            ],
        }

    def decadal_distributions(
        self,
        df: pd.DataFrame,
        mapping: ColumnInference,
        request: AnalysisRequest,
    ) -> dict[str, Any]:
        time_col = request.time_column or mapping.time_column
        target = request.target_column or self._default_target(mapping)

        if not time_col:
            raise ValueError("Decadal distributions require a mapped time column.")
        if not target:
            raise ValueError("Decadal distributions require a numeric target variable.")
        if time_col not in df.columns:
            raise ValueError(f"Time column '{time_col}' not found.")
        if target not in df.columns:
            raise ValueError(f"Target column '{target}' not found.")

        bins = _bounded_int(request.options.get("bins"), 50, 10, 100)
        working = df[[time_col, target]].copy()
        working[time_col] = pd.to_datetime(working[time_col], errors="coerce", utc=True)
        working[target] = pd.to_numeric(working[target], errors="coerce")

        source_rows = int(len(working))
        missing_time = int(working[time_col].isna().sum())
        missing_target = int(working[target].isna().sum())

        working = working.dropna(subset=[time_col, target]).sort_values(time_col)
        if len(working) < 3:
            raise ValueError("Decadal distributions need at least 3 valid time/value rows.")

        daily = working.set_index(time_col)[target].resample("D").mean().dropna().to_frame("mean")
        if len(daily) < 3:
            raise ValueError("Decadal distributions need at least 3 daily periods.")

        daily["year"] = daily.index.year
        daily["decade"] = (daily["year"] // 10) * 10
        decades = sorted(int(decade) for decade in daily["decade"].dropna().unique())
        if not decades:
            raise ValueError("Decadal distributions could not infer decades from the time column.")

        values = daily["mean"].to_numpy(dtype=float)
        min_value = float(np.nanmin(values))
        max_value = float(np.nanmax(values))
        if min_value == max_value:
            min_value -= 0.5
            max_value += 0.5
        bin_edges = np.linspace(min_value, max_value, bins + 1)

        histograms: list[dict[str, Any]] = []
        stats: list[dict[str, Any]] = []
        for decade in decades:
            decade_values = daily.loc[daily["decade"] == decade, "mean"].dropna()
            if decade_values.empty:
                continue
            density, edges = np.histogram(decade_values.to_numpy(dtype=float), bins=bin_edges, density=True)
            step_x, step_y = _histogram_step_points(edges, density)
            summary = decade_values.describe(percentiles=[0.05, 0.25, 0.5, 0.75, 0.95])
            label = f"{decade}s"
            histograms.append(
                {
                    "decade": decade,
                    "label": label,
                    "count": int(len(decade_values)),
                    "bin_edges": [_clean_number(edge) for edge in edges],
                    "density": [_clean_number(value) for value in density],
                    "step_x": [_clean_number(value) for value in step_x],
                    "step_y": [_clean_number(value) for value in step_y],
                }
            )
            stats.append(
                {
                    "decade": decade,
                    "label": label,
                    "count": int(summary.get("count", 0)),
                    "mean": _clean_number(summary.get("mean")),
                    "std": _clean_number(summary.get("std")),
                    "min": _clean_number(summary.get("min")),
                    "q05": _clean_number(summary.get("5%")),
                    "q25": _clean_number(summary.get("25%")),
                    "median": _clean_number(summary.get("50%")),
                    "q75": _clean_number(summary.get("75%")),
                    "q95": _clean_number(summary.get("95%")),
                    "max": _clean_number(summary.get("max")),
                }
            )

        if not stats:
            raise ValueError("Decadal distributions could not calculate decade statistics.")

        first_decade = stats[0]
        last_decade = stats[-1]
        lowest_decade = min(stats, key=lambda item: float(item["mean"]))
        highest_decade = max(stats, key=lambda item: float(item["mean"]))

        return {
            "time_column": time_col,
            "target_column": target,
            "source_rows": source_rows,
            "valid_rows": int(len(working)),
            "daily_periods": int(len(daily)),
            "date_range": {
                "start": working[time_col].iloc[0].isoformat(),
                "end": working[time_col].iloc[-1].isoformat(),
            },
            "settings": {
                "bins": bins,
            },
            "data_quality": {
                "missing_time": missing_time,
                "missing_target": missing_target,
                "observed_decades": int(len(stats)),
            },
            "summary": {
                "first_decade": first_decade,
                "last_decade": last_decade,
                "lowest_mean_decade": lowest_decade,
                "highest_mean_decade": highest_decade,
                "mean_shift_first_to_last": _clean_number(
                    float(last_decade["mean"]) - float(first_decade["mean"])
                ),
            },
            "decadal_statistics": stats,
            "decadal_histograms": histograms,
        }

    def anomaly_detection(
        self,
        df: pd.DataFrame,
        mapping: ColumnInference,
        request: AnalysisRequest,
    ) -> dict[str, Any]:
        target = request.target_column or self._default_target(mapping)
        if not target:
            raise ValueError("Anomaly detection requires a target variable.")

        threshold = float(request.options.get("z_threshold", 2.0))
        time_col = request.time_column or mapping.time_column

        working_columns = [target] + ([time_col] if time_col else [])
        working = df[working_columns].copy()
        working[target] = pd.to_numeric(working[target], errors="coerce")
        working = working.dropna(subset=[target])
        if len(working) < 3:
            raise ValueError("Anomaly detection requires at least 3 numeric rows.")

        mean = float(working[target].mean())
        std = float(working[target].std(ddof=0))
        if std == 0:
            raise ValueError("Anomaly detection failed because standard deviation is zero.")

        working["z_score"] = (working[target] - mean) / std
        anomalies = working[working["z_score"].abs() >= threshold]

        def _row_payload(row: pd.Series) -> dict[str, Any]:
            payload: dict[str, Any] = {
                "value": float(row[target]),
                "z_score": float(row["z_score"]),
            }
            if time_col:
                ts = pd.to_datetime(row[time_col], errors="coerce")
                payload["time"] = ts.isoformat() if pd.notna(ts) else str(row[time_col])
            return payload

        return {
            "target_column": target,
            "z_threshold": threshold,
            "mean": mean,
            "std": std,
            "anomaly_count": int(len(anomalies)),
            "anomalies": [_row_payload(row) for _, row in anomalies.head(500).iterrows()],
        }

    def random_forest_regression(
        self,
        df: pd.DataFrame,
        mapping: ColumnInference,
        request: AnalysisRequest,
    ) -> dict[str, Any]:
        target = request.target_column or self._default_target(mapping)
        if not target:
            raise ValueError("Random forest requires a target column.")

        numeric_cols = self._numeric_columns(df)
        features = request.feature_columns or [col for col in mapping.climate_variables if col != target]
        features = [col for col in features if col in numeric_cols and col != target]
        if not features:
            raise ValueError("Random forest needs numeric feature columns.")

        model_df = df[features + [target]].dropna().copy()
        if len(model_df) < 30:
            raise ValueError("Random forest needs at least 30 complete rows.")

        X = model_df[features]
        y = pd.to_numeric(model_df[target], errors="coerce")
        valid = y.notna()
        X = X[valid]
        y = y[valid]

        X_train, X_test, y_train, y_test = train_test_split(
            X,
            y,
            test_size=0.2,
            random_state=42,
        )

        model = RandomForestRegressor(
            n_estimators=int(request.options.get("n_estimators", 200)),
            random_state=42,
            n_jobs=-1,
        )
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)

        return {
            "target_column": target,
            "feature_columns": features,
            "feature_importance": {
                feature: float(importance)
                for feature, importance in zip(features, model.feature_importances_)
            },
            "r2": float(r2_score(y_test, y_pred)),
            "rmse": float(np.sqrt(mean_squared_error(y_test, y_pred))),
            "test_points": int(len(y_test)),
        }

    def time_series_forecasting(
        self,
        df: pd.DataFrame,
        mapping: ColumnInference,
        request: AnalysisRequest,
    ) -> dict[str, Any]:
        time_col = request.time_column or mapping.time_column
        target = request.target_column or self._default_target(mapping)

        if not time_col:
            raise ValueError("Forecasting requires a mapped time column.")
        if not target:
            raise ValueError("Forecasting requires a target variable.")

        lags = int(request.options.get("lags", 6))
        horizon = int(request.options.get("horizon", 12))

        working = df[[time_col, target]].copy()
        working[time_col] = pd.to_datetime(working[time_col], errors="coerce", utc=True)
        working[target] = pd.to_numeric(working[target], errors="coerce")
        working = working.dropna().sort_values(time_col)

        if len(working) <= lags + 5:
            raise ValueError("Not enough historical data for forecasting. Add more rows or reduce lags.")

        series = working[target].reset_index(drop=True)
        feature_df = pd.DataFrame({"target": series})
        for lag in range(1, lags + 1):
            feature_df[f"lag_{lag}"] = feature_df["target"].shift(lag)
        feature_df = feature_df.dropna()

        X = feature_df.drop(columns=["target"])
        y = feature_df["target"]

        model = LinearRegression()
        model.fit(X, y)

        history = series.tolist()
        forecasts: list[float] = []
        for _ in range(horizon):
            lag_values = [history[-lag] for lag in range(1, lags + 1)]
            next_val = float(model.predict(np.array(lag_values).reshape(1, -1))[0])
            history.append(next_val)
            forecasts.append(next_val)

        inferred_freq = pd.infer_freq(working[time_col].head(500))
        last_time = working[time_col].iloc[-1]

        if inferred_freq:
            future_times = pd.date_range(last_time, periods=horizon + 1, freq=inferred_freq)[1:]
            forecast_points = [
                {"time": ts.isoformat(), "forecast": float(value)}
                for ts, value in zip(future_times, forecasts)
            ]
        else:
            forecast_points = [
                {"step": i + 1, "forecast": float(value)}
                for i, value in enumerate(forecasts)
            ]

        return {
            "time_column": time_col,
            "target_column": target,
            "lags": lags,
            "horizon": horizon,
            "forecast": forecast_points,
            "model_coefficients": {
                f"lag_{idx + 1}": float(coef) for idx, coef in enumerate(model.coef_)
            },
            "model_intercept": float(model.intercept_),
        }

    @staticmethod
    def _numeric_columns(df: pd.DataFrame) -> list[str]:
        return list(df.select_dtypes(include=[np.number]).columns)

    @staticmethod
    def _default_target(mapping: ColumnInference) -> str | None:
        return mapping.climate_variables[0] if mapping.climate_variables else None

    @staticmethod
    def _resolve_trend_target(
        df: pd.DataFrame,
        mapping: ColumnInference,
        request: AnalysisRequest,
    ) -> str:
        if request.target_column:
            return request.target_column

        if request.analysis_type == "temperature_trend":
            target = _match_variable(mapping.climate_variables, {"temp", "temperature"})
            if target:
                return target

        if request.analysis_type == "precipitation_trend":
            target = _match_variable(mapping.climate_variables, {"precip", "rain"})
            if target:
                return target

        target = AnalysisEngine._default_target(mapping)
        if target:
            return target

        numeric_columns = AnalysisEngine._numeric_columns(df)
        if not numeric_columns:
            raise ValueError("No numeric climate variable available for trend detection.")
        return numeric_columns[0]


def _normalize_frequency(value: str) -> str:
    normalized = value.strip().upper()
    aliases = {
        "DAILY": "D",
        "DAY": "D",
        "D": "D",
        "MONTHLY": "ME",
        "MONTH": "ME",
        "M": "ME",
        "ME": "ME",
        "YEARLY": "YE",
        "YEAR": "YE",
        "Y": "YE",
        "YE": "YE",
    }
    if normalized not in aliases:
        raise ValueError("aggregation_frequency must be one of: D, ME, YE.")
    return aliases[normalized]


def _bounded_float(value: Any, default: float, minimum: float, maximum: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    return min(max(parsed, minimum), maximum)


def _bounded_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return min(max(parsed, minimum), maximum)


def _clean_number(value: Any) -> float | int | None:
    if value is None or pd.isna(value):
        return None
    parsed = float(value)
    if parsed.is_integer():
        return int(parsed)
    return parsed


def _histogram_step_points(edges: np.ndarray, density: np.ndarray) -> tuple[list[float], list[float]]:
    step_x: list[float] = []
    step_y: list[float] = []
    for index, value in enumerate(density):
        step_x.extend([float(edges[index]), float(edges[index + 1])])
        step_y.extend([float(value), float(value)])
    return step_x, step_y


def _monthly_summary(aggregated: pd.DataFrame) -> list[dict[str, Any]]:
    summary = (
        aggregated.assign(month=aggregated.index.month)
        .groupby("month")["mean"]
        .agg(["mean", "std", "count"])
        .reset_index()
    )
    return [
        {
            "month": int(row["month"]),
            "mean": _clean_number(row["mean"]),
            "std": _clean_number(row["std"]),
            "count": int(row["count"]),
        }
        for _, row in summary.iterrows()
    ]


def _seasonal_summary(aggregated: pd.DataFrame) -> list[dict[str, Any]]:
    season_order = {"winter": 0, "spring": 1, "summer": 2, "autumn": 3}
    summary = (
        aggregated.assign(season=[_month_to_season(month) for month in aggregated.index.month])
        .groupby("season")["mean"]
        .agg(["mean", "std", "count"])
        .reset_index()
    )
    summary["order"] = summary["season"].map(season_order)
    summary = summary.sort_values("order")
    return [
        {
            "season": str(row["season"]),
            "mean": _clean_number(row["mean"]),
            "std": _clean_number(row["std"]),
            "count": int(row["count"]),
        }
        for _, row in summary.iterrows()
    ]


def _annual_summary(aggregated: pd.DataFrame) -> dict[str, Any]:
    annual = aggregated.assign(year=aggregated.index.year).groupby("year")["mean"].mean()
    annual_points = [
        {"year": int(year), "mean": _clean_number(value)}
        for year, value in annual.items()
    ]

    if len(annual) < 3:
        return {
            "points": annual_points,
            "slope_per_year": None,
            "slope_per_decade": None,
            "total_change": None,
            "r2": None,
            "lowest_year": None,
            "highest_year": None,
        }

    years = annual.index.to_numpy(dtype=float)
    values = annual.to_numpy(dtype=float)
    slope, intercept = np.polyfit(years, values, 1)
    fitted = slope * years + intercept

    lowest_year = int(annual.idxmin())
    highest_year = int(annual.idxmax())
    return {
        "points": annual_points,
        "slope_per_year": float(slope),
        "slope_per_decade": float(slope * 10),
        "total_change": float(slope * (years[-1] - years[0])),
        "r2": float(r2_score(values, fitted)),
        "lowest_year": {
            "year": lowest_year,
            "mean": _clean_number(annual.loc[lowest_year]),
        },
        "highest_year": {
            "year": highest_year,
            "mean": _clean_number(annual.loc[highest_year]),
        },
    }


def _annual_count_trend(annual_counts: pd.Series) -> dict[str, Any]:
    annual_counts = annual_counts.sort_index()
    if len(annual_counts) < 3:
        return {
            "slope_per_year": None,
            "slope_per_decade": None,
            "r2": None,
            "fitted": {int(year): None for year in annual_counts.index},
        }

    years = annual_counts.index.to_numpy(dtype=float)
    values = annual_counts.to_numpy(dtype=float)
    slope, intercept = np.polyfit(years, values, 1)
    fitted = slope * years + intercept
    return {
        "slope_per_year": _clean_number(slope),
        "slope_per_decade": _clean_number(slope * 10),
        "r2": _clean_number(r2_score(values, fitted)),
        "fitted": {
            int(year): _clean_number(value)
            for year, value in zip(annual_counts.index, fitted)
        },
    }


def _baseline_monthly_means(
    aggregated: pd.DataFrame,
    baseline_start: Any,
    baseline_end: Any,
) -> dict[str, Any]:
    start = pd.to_datetime(baseline_start, errors="coerce", utc=True) if baseline_start else None
    end = pd.to_datetime(baseline_end, errors="coerce", utc=True) if baseline_end else None

    baseline_df = aggregated
    requested = bool(start is not None or end is not None)
    if start is not None:
        baseline_df = baseline_df[baseline_df.index >= start]
    if end is not None:
        baseline_df = baseline_df[baseline_df.index <= end]

    if baseline_df.empty:
        baseline_df = aggregated
        requested = False

    monthly_means = baseline_df.assign(month=baseline_df.index.month).groupby("month")["mean"].mean()
    return {
        "monthly_means": monthly_means,
        "metadata": {
            "start": baseline_df.index.min().isoformat(),
            "end": baseline_df.index.max().isoformat(),
            "requested_start": start.isoformat() if start is not None else None,
            "requested_end": end.isoformat() if end is not None else None,
            "used_requested_period": requested,
            "periods": int(len(baseline_df)),
            "mean": _clean_number(baseline_df["mean"].mean()),
            "observed_months": int(len(monthly_means)),
            "complete_12_month_profile": int(len(monthly_means)) == 12,
            "monthly_means": {
                str(int(month)): _clean_number(value)
                for month, value in monthly_means.items()
            },
        },
    }


def _annual_anomalies(
    aggregated: pd.DataFrame,
    monthly_baseline: pd.Series,
) -> list[dict[str, Any]]:
    anomaly_df = aggregated.assign(
        year=aggregated.index.year,
        month=aggregated.index.month,
    ).copy()
    anomaly_df["baseline"] = anomaly_df["month"].map(monthly_baseline)
    anomaly_df["anomaly"] = anomaly_df["mean"] - anomaly_df["baseline"]
    annual = anomaly_df.groupby("year")["anomaly"].mean()
    return [
        {"year": int(year), "anomaly": _clean_number(value)}
        for year, value in annual.items()
    ]


def _extreme_summary(
    aggregated: pd.DataFrame,
    high_quantile: float,
    low_quantile: float,
) -> dict[str, Any]:
    high_threshold = float(aggregated["max"].quantile(high_quantile))
    low_threshold = float(aggregated["min"].quantile(low_quantile))
    extreme_df = aggregated.assign(
        year=aggregated.index.year,
        high_extreme=aggregated["max"] >= high_threshold,
        low_extreme=aggregated["min"] <= low_threshold,
    )
    annual_high = extreme_df.groupby("year")["high_extreme"].sum()
    annual_low = extreme_df.groupby("year")["low_extreme"].sum()

    years = annual_high.index.to_numpy(dtype=float)
    high_trend = None
    low_trend = None
    if len(years) >= 3:
        high_trend = float(np.polyfit(years, annual_high.to_numpy(dtype=float), 1)[0] * 10)
        low_trend = float(np.polyfit(years, annual_low.to_numpy(dtype=float), 1)[0] * 10)

    return {
        "high_quantile": high_quantile,
        "low_quantile": low_quantile,
        "high_threshold": high_threshold,
        "low_threshold": low_threshold,
        "high_extremes_per_year": [
            {"year": int(year), "count": int(count)}
            for year, count in annual_high.items()
        ],
        "low_extremes_per_year": [
            {"year": int(year), "count": int(count)}
            for year, count in annual_low.items()
        ],
        "high_extreme_trend_per_decade": high_trend,
        "low_extreme_trend_per_decade": low_trend,
    }


def _decade_summary(aggregated: pd.DataFrame) -> list[dict[str, Any]]:
    summary = (
        aggregated.assign(decade=(aggregated.index.year // 10) * 10)
        .groupby("decade")["mean"]
        .agg(["mean", "std", "min", "max", "count"])
        .reset_index()
    )
    return [
        {
            "decade": int(row["decade"]),
            "mean": _clean_number(row["mean"]),
            "std": _clean_number(row["std"]),
            "min": _clean_number(row["min"]),
            "max": _clean_number(row["max"]),
            "count": int(row["count"]),
        }
        for _, row in summary.iterrows()
    ]


def _aggregated_preview(aggregated: pd.DataFrame, limit: int = 1000) -> list[dict[str, Any]]:
    if len(aggregated) > limit:
        indices = np.linspace(0, len(aggregated) - 1, num=limit, dtype=int)
        preview = aggregated.iloc[indices]
    else:
        preview = aggregated

    return [
        {
            "time": timestamp.isoformat(),
            "mean": _clean_number(row["mean"]),
            "min": _clean_number(row["min"]),
            "max": _clean_number(row["max"]),
            "range": _clean_number(row["range"]),
            "count": int(row["count"]),
        }
        for timestamp, row in preview.iterrows()
    ]


def _summary_row_payload(row: pd.Series | None) -> dict[str, Any]:
    if row is None:
        return {
            "mean": None,
            "std": None,
            "min": None,
            "max": None,
            "count": 0,
        }

    return {
        "mean": _clean_number(row.get("mean")),
        "std": _clean_number(row.get("std")),
        "min": _clean_number(row.get("min")),
        "max": _clean_number(row.get("max")),
        "count": 0 if pd.isna(row.get("count")) else int(row.get("count")),
    }


def _monthly_climatology_records(monthly: pd.DataFrame) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for month in range(1, 13):
        row = monthly.loc[month] if month in monthly.index else None
        records.append(
            {
                "month": month,
                "month_label": MONTH_LABELS[month],
                **_summary_row_payload(row),
            }
        )
    return records


def _seasonal_cycle_records(seasonal: pd.DataFrame) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for season in SEASON_ORDER:
        row = seasonal.loc[season] if season in seasonal.index else None
        records.append({"season": season, **_summary_row_payload(row)})
    return records


def _hour_record(hour: int, row: pd.Series | None) -> dict[str, Any]:
    if row is None:
        return {
            "hour": hour,
            "mean": None,
            "std": None,
            "min": None,
            "max": None,
            "count": 0,
        }

    return {
        "hour": hour,
        "mean": _clean_number(row.get("mean")),
        "std": _clean_number(row.get("std")),
        "min": _clean_number(row.get("min")),
        "max": _clean_number(row.get("max")),
        "count": 0 if pd.isna(row.get("count")) else int(row.get("count")),
    }


def _hourly_profile_records(hourly: pd.DataFrame) -> list[dict[str, Any]]:
    return [_hour_record(hour, hourly.loc[hour] if hour in hourly.index else None) for hour in range(24)]


def _seasonal_hourly_profile_records(seasonal: pd.DataFrame) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for season in SEASON_ORDER:
        for hour in range(24):
            row = seasonal.loc[(season, hour)] if (season, hour) in seasonal.index else None
            records.append({"season": season, **_hour_record(hour, row)})
    return records


def _seasonal_hour_peaks(seasonal: pd.DataFrame) -> list[dict[str, Any]]:
    peaks: list[dict[str, Any]] = []
    seasons = set(seasonal.index.get_level_values("season")) if len(seasonal.index) else set()
    for season in SEASON_ORDER:
        if season not in seasons:
            continue
        season_df = seasonal.xs(season, level="season").dropna(subset=["mean"])
        if season_df.empty:
            continue
        warmest_hour = int(season_df["mean"].idxmax())
        coolest_hour = int(season_df["mean"].idxmin())
        peaks.append(
            {
                "season": season,
                "warmest_hour": warmest_hour,
                "warmest_value": _clean_number(season_df.loc[warmest_hour, "mean"]),
                "coolest_hour": coolest_hour,
                "coolest_value": _clean_number(season_df.loc[coolest_hour, "mean"]),
                "diurnal_range": _clean_number(
                    float(season_df.loc[warmest_hour, "mean"])
                    - float(season_df.loc[coolest_hour, "mean"])
                ),
            }
        )
    return peaks



def _month_to_season(month: int) -> str:
    if month in (12, 1, 2):
        return "winter"
    if month in (3, 4, 5):
        return "spring"
    if month in (6, 7, 8):
        return "summer"
    return "autumn"



def _match_variable(variables: list[str], hints: set[str]) -> str | None:
    for variable in variables:
        lowered = variable.lower()
        if any(hint in lowered for hint in hints):
            return variable
    return None


analysis_engine = AnalysisEngine()
