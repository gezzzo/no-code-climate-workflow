from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import rasterio
import xarray as xr
from rasterio.warp import transform

from app.core.config import settings


SUPPORTED_FORMATS = {
    ".csv": "csv",
    ".xlsx": "xlsx",
    ".xls": "xlsx",
    ".nc": "netcdf",
    ".grb": "grib",
    ".grib": "grib",
    ".grib2": "grib",
    ".tif": "geotiff",
    ".tiff": "geotiff",
}


class UnsupportedFormatError(ValueError):
    pass


@dataclass
class ParsedDataset:
    source_format: str
    dataframe: pd.DataFrame
    parser_metadata: dict[str, Any]



def detect_format(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_FORMATS:
        supported = ", ".join(sorted(SUPPORTED_FORMATS))
        raise UnsupportedFormatError(
            f"Unsupported file format '{suffix}'. Supported extensions: {supported}"
        )
    return SUPPORTED_FORMATS[suffix]



def parse_file(file_path: Path, source_format: str) -> ParsedDataset:
    if source_format == "csv":
        df = pd.read_csv(file_path, low_memory=False)
        parser_metadata = {"source": "pandas.read_csv"}
    elif source_format == "xlsx":
        df = pd.read_excel(file_path)
        parser_metadata = {"source": "pandas.read_excel"}
    elif source_format == "netcdf":
        df, parser_metadata = _parse_xarray_dataset(file_path, source_format)
    elif source_format == "grib":
        df, parser_metadata = _parse_xarray_dataset(file_path, source_format)
    elif source_format == "geotiff":
        df, parser_metadata = _parse_geotiff(file_path)
    else:
        raise UnsupportedFormatError(f"Unsupported source format: {source_format}")

    df = _standardize_dataframe(df)
    df = _downsample_dataframe(df, settings.max_standardized_rows)
    parser_metadata["standardized_rows"] = int(len(df))

    return ParsedDataset(source_format=source_format, dataframe=df, parser_metadata=parser_metadata)



def _parse_xarray_dataset(file_path: Path, source_format: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    open_kwargs: dict[str, Any] = {}
    if source_format == "grib":
        open_kwargs["engine"] = "cfgrib"

    try:
        with xr.open_dataset(file_path, **open_kwargs) as ds:
            data_variables = list(ds.data_vars)
            if not data_variables:
                raise ValueError("No data variables found in dataset.")

            # Convert multidimensional climate arrays to a flat internal table.
            flat = ds[data_variables].to_dataframe().reset_index()
            metadata = {
                "source": "xarray.open_dataset",
                "variables": data_variables,
                "dimensions": {k: int(v) for k, v in ds.dims.items()},
                "coordinates": list(ds.coords),
                "attributes": {k: str(v) for k, v in ds.attrs.items()},
                "variable_attributes": {
                    variable: {key: str(value) for key, value in ds[variable].attrs.items()}
                    for variable in data_variables
                },
            }
    except Exception as exc:
        if source_format == "grib":
            raise ValueError(
                "Failed to parse GRIB file. Ensure cfgrib and ecCodes are installed and the file is valid."
            ) from exc
        raise

    return flat, metadata



def _parse_geotiff(file_path: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    with rasterio.open(file_path) as src:
        band = src.read(1, masked=True)
        valid_rows, valid_cols = np.where(~band.mask)
        if valid_rows.size == 0:
            raise ValueError("GeoTIFF contains no valid data pixels.")

        values = band[valid_rows, valid_cols].astype(float)

        max_points = min(settings.max_standardized_rows, 300_000)
        if len(values) > max_points:
            keep_indices = np.linspace(0, len(values) - 1, num=max_points, dtype=int)
            valid_rows = valid_rows[keep_indices]
            valid_cols = valid_cols[keep_indices]
            values = values[keep_indices]

        xs, ys = rasterio.transform.xy(src.transform, valid_rows, valid_cols)
        xs = np.asarray(xs)
        ys = np.asarray(ys)

        if src.crs and src.crs.to_epsg() != 4326:
            lon, lat = transform(src.crs, "EPSG:4326", xs.tolist(), ys.tolist())
        else:
            lon, lat = xs.tolist(), ys.tolist()

        df = pd.DataFrame(
            {
                "longitude": lon,
                "latitude": lat,
                "value": values,
            }
        )

        metadata = {
            "source": "rasterio",
            "bounds": list(src.bounds),
            "crs": str(src.crs) if src.crs else None,
            "width": int(src.width),
            "height": int(src.height),
            "count": int(src.count),
        }

    return df, metadata



def _standardize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    normalized.columns = [str(col).strip() for col in normalized.columns]

    for column in normalized.columns:
        if pd.api.types.is_object_dtype(normalized[column]):
            normalized[column] = normalized[column].apply(_safe_object_to_scalar)

    return normalized.reset_index(drop=True)



def _safe_object_to_scalar(value: Any) -> Any:
    if isinstance(value, (bytes, bytearray)):
        return value.decode("utf-8", errors="ignore")
    if isinstance(value, (list, dict, tuple, set)):
        return str(value)
    return value



def _downsample_dataframe(df: pd.DataFrame, max_rows: int) -> pd.DataFrame:
    if len(df) <= max_rows:
        return df

    indices = np.linspace(0, len(df) - 1, num=max_rows, dtype=int)
    return df.iloc[indices].reset_index(drop=True)
