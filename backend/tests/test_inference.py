import pandas as pd

from app.services.inference import infer_column_roles


def test_infer_column_roles_detects_time_and_geo() -> None:
    df = pd.DataFrame(
        {
            "timestamp": ["2024-01-01", "2024-01-02"],
            "latitude": [45.0, 45.1],
            "longitude": [9.1, 9.2],
            "temperature": [13.2, 13.4],
        }
    )

    result = infer_column_roles(df)

    assert result["time_column"] == "timestamp"
    assert result["latitude_column"] == "latitude"
    assert result["longitude_column"] == "longitude"
    assert "temperature" in result["climate_variables"]
