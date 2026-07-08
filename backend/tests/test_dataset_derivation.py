import pandas as pd

from app.schemas import ColumnInference, TemporalAggregationRequest
from app.services.dataset_store import LocalDatasetStore


def test_create_dataset_from_dataframe_infers_mapping(tmp_path) -> None:
    store = LocalDatasetStore(tmp_path)
    metadata = store.create_dataset_from_dataframe(
        pd.DataFrame(
            {
                "timestamp": ["2024-01-01", "2024-01-02"],
                "temperature": [13.2, 13.4],
            }
        ),
        filename="observations.csv",
        source_format="csv",
    )

    assert metadata.mapping.time_column == "timestamp"
    assert "temperature" in metadata.mapping.climate_variables


def test_temporal_aggregation_creates_derived_daily_dataset(tmp_path) -> None:
    store = LocalDatasetStore(tmp_path)
    source_df = pd.DataFrame(
        {
            "observed_at": pd.date_range("2024-01-01", periods=48, freq="h"),
            "air_value": list(range(24)) + list(range(10, 34)),
            "water_value": [2.0] * 24 + [4.0] * 24,
            "station": ["A"] * 48,
        }
    )
    source = store.create_dataset_from_dataframe(
        source_df,
        filename="hourly_observations",
        source_format="csv",
        mapping=ColumnInference(
            time_column="observed_at",
            climate_variables=["air_value", "water_value"],
            column_types={
                "observed_at": "time",
                "air_value": "numeric",
                "water_value": "numeric",
                "station": "text",
            },
        ),
    )

    derived = store.derive_temporal_aggregation(
        source.dataset_id,
        TemporalAggregationRequest(
            time_column="observed_at",
            value_columns=["air_value", "water_value", "station"],
            frequency="D",
            aggregations=["mean", "min", "max", "range"],
            output_name="daily_observations",
        ),
    )
    derived_df = store.load_dataframe(derived.dataset_id)

    assert derived.name == "daily_observations"
    assert derived.source_format == "derived"
    assert derived.row_count == 2
    assert derived.mapping.time_column == "period_start"
    assert "station_mean" not in derived.columns
    assert {
        "period_start",
        "air_value_mean",
        "air_value_min",
        "air_value_max",
        "air_value_range",
        "water_value_mean",
    }.issubset(set(derived.columns))
    assert derived.parser_metadata["parent_dataset_id"] == source.dataset_id
    assert derived_df.loc[0, "air_value_mean"] == 11.5
    assert derived_df.loc[0, "air_value_range"] == 23
    assert derived_df.loc[1, "air_value_min"] == 10
    assert derived_df.loc[1, "water_value_mean"] == 4.0
