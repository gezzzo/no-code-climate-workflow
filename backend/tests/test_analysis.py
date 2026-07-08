import pandas as pd

from app.schemas import AnalysisRequest, ColumnInference
from app.services.analysis import analysis_engine


def test_descriptive_stats_analysis_returns_summary() -> None:
    df = pd.DataFrame(
        {
            "time": pd.date_range("2024-01-01", periods=12, freq="D"),
            "temperature": [12.0, 12.5, 13.0, 13.2, 13.1, 13.6, 13.9, 14.2, 14.4, 14.6, 14.9, 15.1],
            "precipitation": [2.0, 1.0, 0.0, 0.5, 0.2, 0.3, 0.0, 0.1, 0.2, 0.0, 0.0, 0.4],
        }
    )

    mapping = ColumnInference(
        time_column="time",
        latitude_column=None,
        longitude_column=None,
        climate_variables=["temperature", "precipitation"],
        column_types={"time": "time", "temperature": "numeric", "precipitation": "numeric"},
    )
    request = AnalysisRequest(analysis_type="descriptive_stats")

    result = analysis_engine.run(df, mapping, request)

    assert result["summary"]
    assert result["summary"][0]["column"] in {"temperature", "precipitation"}


def test_climate_workflow_runs_on_generic_time_series_variable() -> None:
    dates = pd.date_range("2019-01-01", "2022-12-31", freq="D")
    values = [
        35.0 + (idx / 365.0) * 0.4 + 8.0 * ((date.dayofyear % 365) / 365.0)
        for idx, date in enumerate(dates)
    ]
    df = pd.DataFrame(
        {
            "observed_at": dates,
            "soil_moisture": values,
        }
    )
    mapping = ColumnInference(
        time_column="observed_at",
        climate_variables=["soil_moisture"],
        column_types={"observed_at": "time", "soil_moisture": "numeric"},
    )
    request = AnalysisRequest(
        analysis_type="climate_workflow",
        target_column="soil_moisture",
        time_column="observed_at",
        options={
            "aggregation_frequency": "D",
            "baseline_start": "2020-01-01",
            "baseline_end": "2021-12-31",
        },
    )

    result = analysis_engine.run(df, mapping, request)

    assert result["target_column"] == "soil_moisture"
    assert result["aggregated_periods"] == len(dates)
    assert len(result["monthly_climatology"]) == 12
    assert result["annual_trend"]["slope_per_decade"] is not None
    assert result["extremes"]["high_threshold"] > result["extremes"]["low_threshold"]
    assert result["anomalies"]["baseline"]["used_requested_period"] is True


def test_seasonal_patterns_returns_monthly_climatology_for_generic_variable() -> None:
    dates = pd.date_range("2022-01-01", "2023-12-01", freq="MS")
    values = [float(date.month * 2) for date in dates]
    df = pd.DataFrame(
        {
            "observed_at": dates,
            "soil_moisture": values,
        }
    )
    mapping = ColumnInference(
        time_column="observed_at",
        climate_variables=["soil_moisture"],
        column_types={"observed_at": "time", "soil_moisture": "numeric"},
    )
    request = AnalysisRequest(
        analysis_type="seasonal_patterns",
        target_column="soil_moisture",
        time_column="observed_at",
    )

    result = analysis_engine.run(df, mapping, request)

    assert result["target_column"] == "soil_moisture"
    assert result["data_quality"]["observed_months"] == 12
    assert len(result["monthly_climatology"]) == 12
    assert len(result["seasonal_cycle"]) == 4
    assert result["monthly_climatology"][0]["month_label"] == "Jan"
    assert result["monthly_climatology"][6]["mean"] == 14
    assert result["summary"]["warmest_month_label"] == "Dec"
    assert result["summary"]["coolest_month_label"] == "Jan"
    assert result["summary"]["seasonal_range"] == 22


def test_diurnal_cycle_runs_on_generic_sub_daily_time_series() -> None:
    timestamps = []
    values = []
    for month, base in [(1, 0.0), (4, 10.0), (7, 20.0), (10, 30.0)]:
        for hour in range(24):
            timestamps.append(pd.Timestamp(year=2024, month=month, day=15, hour=hour))
            values.append(base + hour)

    df = pd.DataFrame(
        {
            "observed_at": timestamps,
            "air_value": values,
        }
    )
    mapping = ColumnInference(
        time_column="observed_at",
        climate_variables=["air_value"],
        column_types={"observed_at": "time", "air_value": "numeric"},
    )
    request = AnalysisRequest(
        analysis_type="diurnal_cycle",
        target_column="air_value",
        time_column="observed_at",
    )

    result = analysis_engine.run(df, mapping, request)

    assert result["target_column"] == "air_value"
    assert result["data_quality"]["observed_hours"] == 24
    assert result["summary"]["warmest_hour"] == 23
    assert result["summary"]["coolest_hour"] == 0
    assert result["summary"]["diurnal_range"] == 23
    assert len(result["hourly_profile"]) == 24
    assert len(result["seasonal_hourly_profile"]) == 96
    assert result["hourly_profile"][23]["mean"] == 38
    assert result["season_definitions"]["winter"] == [12, 1, 2]


def test_annual_trend_signal_returns_generic_climate_change_summary() -> None:
    dates = pd.date_range("2019-01-01", "2023-12-31", freq="D")
    values = [20.0 + (date.year - 2019) * 0.25 + (date.dayofyear / 366.0) for date in dates]
    df = pd.DataFrame(
        {
            "observed_at": dates,
            "soil_moisture": values,
        }
    )
    mapping = ColumnInference(
        time_column="observed_at",
        climate_variables=["soil_moisture"],
        column_types={"observed_at": "time", "soil_moisture": "numeric"},
    )
    request = AnalysisRequest(
        analysis_type="annual_trend_signal",
        target_column="soil_moisture",
        time_column="observed_at",
    )

    result = analysis_engine.run(df, mapping, request)

    assert result["target_column"] == "soil_moisture"
    assert result["data_quality"]["observed_years"] == 5
    assert len(result["annual_series"]) == 5
    assert result["summary"]["trend_direction"] == "increasing"
    assert result["summary"]["warming_per_decade"] > 0
    assert result["summary"]["coldest_year"] == 2019
    assert result["summary"]["warmest_year"] == 2023


def test_baseline_anomalies_returns_annual_anomalies_for_generic_variable() -> None:
    dates = pd.date_range("2019-01-01", "2023-12-31", freq="D")
    values = [
        date.month * 10.0 + (date.year - 2019) * 0.5
        for date in dates
    ]
    df = pd.DataFrame(
        {
            "observed_at": dates,
            "soil_moisture": values,
        }
    )
    mapping = ColumnInference(
        time_column="observed_at",
        climate_variables=["soil_moisture"],
        column_types={"observed_at": "time", "soil_moisture": "numeric"},
    )
    request = AnalysisRequest(
        analysis_type="baseline_anomalies",
        target_column="soil_moisture",
        time_column="observed_at",
        options={
            "baseline_start": "2020-01-01",
            "baseline_end": "2021-12-31",
        },
    )

    result = analysis_engine.run(df, mapping, request)

    assert result["target_column"] == "soil_moisture"
    assert result["baseline"]["used_requested_period"] is True
    assert result["data_quality"]["baseline_months"] == 12
    assert len(result["annual_anomalies"]) == 5
    assert result["summary"]["most_negative_year"] == 2019
    assert result["summary"]["most_positive_year"] == 2023
    assert result["annual_anomalies"][0]["anomaly"] < 0
    assert result["annual_anomalies"][-1]["anomaly"] > 0


def test_extreme_events_counts_high_and_low_days_for_generic_variable() -> None:
    dates = pd.date_range("2019-01-01", "2023-12-31", freq="D")
    values = [
        (date.year - 2019) * 2.0 + (date.dayofyear / 366.0)
        for date in dates
    ]
    df = pd.DataFrame(
        {
            "observed_at": dates,
            "soil_moisture": values,
        }
    )
    mapping = ColumnInference(
        time_column="observed_at",
        climate_variables=["soil_moisture"],
        column_types={"observed_at": "time", "soil_moisture": "numeric"},
    )
    request = AnalysisRequest(
        analysis_type="extreme_events",
        target_column="soil_moisture",
        time_column="observed_at",
        options={"high_quantile": 0.8, "low_quantile": 0.2},
    )

    result = analysis_engine.run(df, mapping, request)

    assert result["target_column"] == "soil_moisture"
    assert result["thresholds"]["high_threshold"] > result["thresholds"]["low_threshold"]
    assert result["summary"]["high_trend_per_decade"] > 0
    assert result["summary"]["low_trend_per_decade"] < 0
    assert result["summary"]["max_high_year"] == 2023
    assert result["summary"]["max_low_year"] == 2019
    assert len(result["annual_extremes"]) == 5


def test_decadal_distributions_returns_histograms_and_stats_for_generic_variable() -> None:
    dates = pd.date_range("1990-01-01", "2019-12-31", freq="D")
    values = [
        (date.year // 10) * 10 - 1990 + (date.dayofyear / 366.0)
        for date in dates
    ]
    df = pd.DataFrame(
        {
            "observed_at": dates,
            "soil_moisture": values,
        }
    )
    mapping = ColumnInference(
        time_column="observed_at",
        climate_variables=["soil_moisture"],
        column_types={"observed_at": "time", "soil_moisture": "numeric"},
    )
    request = AnalysisRequest(
        analysis_type="decadal_distributions",
        target_column="soil_moisture",
        time_column="observed_at",
        options={"bins": 20},
    )

    result = analysis_engine.run(df, mapping, request)

    assert result["target_column"] == "soil_moisture"
    assert result["settings"]["bins"] == 20
    assert result["data_quality"]["observed_decades"] == 3
    assert len(result["decadal_histograms"]) == 3
    assert len(result["decadal_histograms"][0]["density"]) == 20
    assert len(result["decadal_histograms"][0]["bin_edges"]) == 21
    assert result["decadal_statistics"][0]["decade"] == 1990
    assert result["summary"]["mean_shift_first_to_last"] > 0
