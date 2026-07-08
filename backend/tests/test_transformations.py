import pandas as pd

from app.schemas import ColumnInference, TransformationCreateRequest
from app.services.transformations import (
    apply_transformation_recipe,
    build_transformation_recipe,
)


def test_kelvin_to_celsius_transformation() -> None:
    df = pd.DataFrame({"t2m": [273.15, 280.15, 290.15]})
    mapping = ColumnInference(
        time_column=None,
        latitude_column=None,
        longitude_column=None,
        climate_variables=["t2m"],
        column_types={"t2m": "numeric"},
    )

    recipe = build_transformation_recipe(
        TransformationCreateRequest(
            source_variable="t2m",
            operation="kelvin_to_celsius",
            output_variable="t2m_c",
        ),
        mapping,
    )

    transformed = apply_transformation_recipe(df, recipe, mapping)

    assert transformed["t2m_c"].round(2).tolist() == [0.0, 7.0, 17.0]


def test_rolling_mean_transformation_with_time_column() -> None:
    df = pd.DataFrame(
        {
            "time": pd.date_range("2024-01-01", periods=4, freq="D"),
            "temp": [10.0, 12.0, 14.0, 16.0],
        }
    )
    mapping = ColumnInference(
        time_column="time",
        latitude_column=None,
        longitude_column=None,
        climate_variables=["temp"],
        column_types={"time": "time", "temp": "numeric"},
    )

    recipe = build_transformation_recipe(
        TransformationCreateRequest(
            source_variable="temp",
            operation="rolling_mean",
            output_variable="temp_roll",
            parameters={"window": 2},
        ),
        mapping,
    )

    transformed = apply_transformation_recipe(df, recipe, mapping)

    assert transformed["temp_roll"].round(2).tolist() == [10.0, 11.0, 13.0, 15.0]
