from __future__ import annotations

import json
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import BinaryIO
from uuid import uuid4

import numpy as np
import pandas as pd
from fastapi import UploadFile

from app.core.config import settings
from app.schemas import (
    ColumnInference,
    DatasetMetadata,
    DatasetPreview,
    DatasetSummary,
    TemporalAggregationRequest,
    TransformationCreateRequest,
    TransformationsResponse,
)
from app.services.file_parser import detect_format, parse_file
from app.services.inference import infer_column_roles
from app.services.transformations import (
    apply_transformation_recipe,
    apply_transformation_recipes,
    build_transformation_recipe,
    suggest_transformations,
)


def _coerce_mapping(mapping: ColumnInference | dict[str, object]) -> ColumnInference:
    if isinstance(mapping, ColumnInference):
        return mapping
    return ColumnInference.model_validate(mapping)


class LocalDatasetStore:
    def __init__(self, storage_dir: Path) -> None:
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def create_dataset(self, upload_file: UploadFile) -> DatasetMetadata:
        return self.create_dataset_from_stream(
            upload_file.file,
            upload_file.filename or "",
        )

    def create_dataset_from_path(
        self,
        source_path: Path,
        filename: str,
        source_metadata: dict[str, object] | None = None,
    ) -> DatasetMetadata:
        with source_path.open("rb") as source_stream:
            return self.create_dataset_from_stream(source_stream, filename, source_metadata)

    def create_dataset_from_stream(
        self,
        source_stream: BinaryIO,
        filename: str,
        source_metadata: dict[str, object] | None = None,
    ) -> DatasetMetadata:
        dataset_id = uuid4().hex
        dataset_dir = self.storage_dir / dataset_id
        dataset_dir.mkdir(parents=True, exist_ok=False)

        source_format = detect_format(filename)
        original_path = dataset_dir / f"source{Path(filename).suffix.lower()}"

        with original_path.open("wb") as dest:
            shutil.copyfileobj(source_stream, dest)

        parsed = parse_file(original_path, source_format)
        parser_metadata = dict(parsed.parser_metadata)
        if source_metadata:
            parser_metadata.update(source_metadata)
        inferred_mapping = _coerce_mapping(infer_column_roles(parsed.dataframe))

        parquet_path = dataset_dir / "data.parquet"
        parsed.dataframe.to_parquet(parquet_path, index=False)

        metadata: dict[str, object] = {
            "dataset_id": dataset_id,
            "name": filename or dataset_id,
            "source_format": parsed.source_format,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "row_count": int(len(parsed.dataframe)),
            "columns": list(parsed.dataframe.columns),
            "parser_metadata": parser_metadata,
            "mapping": inferred_mapping.model_dump(),
            "transformations": [],
            "derived_columns": [],
        }
        self._write_metadata(dataset_id, metadata)
        return DatasetMetadata.model_validate(metadata)

    def create_dataset_from_dataframe(
        self,
        dataframe: pd.DataFrame,
        filename: str,
        source_format: str,
        parser_metadata: dict[str, object] | None = None,
        mapping: ColumnInference | None = None,
        derived_columns: list[str] | None = None,
    ) -> DatasetMetadata:
        dataset_id = uuid4().hex
        dataset_dir = self.storage_dir / dataset_id
        dataset_dir.mkdir(parents=True, exist_ok=False)

        normalized = dataframe.reset_index(drop=True).copy()
        inferred_mapping = _coerce_mapping(mapping or infer_column_roles(normalized))

        parquet_path = dataset_dir / "data.parquet"
        normalized.to_parquet(parquet_path, index=False)

        metadata: dict[str, object] = {
            "dataset_id": dataset_id,
            "name": filename or dataset_id,
            "source_format": source_format,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "row_count": int(len(normalized)),
            "columns": list(normalized.columns),
            "parser_metadata": parser_metadata or {},
            "mapping": inferred_mapping.model_dump(),
            "transformations": [],
            "derived_columns": derived_columns or [],
        }
        self._write_metadata(dataset_id, metadata)
        return DatasetMetadata.model_validate(metadata)

    def list_datasets(self) -> list[DatasetSummary]:
        summaries: list[DatasetSummary] = []
        for dataset_dir in sorted(self.storage_dir.glob("*")):
            metadata_path = dataset_dir / "metadata.json"
            if not metadata_path.exists():
                continue
            metadata = self._read_metadata(dataset_dir.name)
            summaries.append(
                DatasetSummary.model_validate(
                    {
                        "dataset_id": metadata["dataset_id"],
                        "name": metadata["name"],
                        "source_format": metadata["source_format"],
                        "created_at": metadata["created_at"],
                        "row_count": metadata["row_count"],
                        "columns": metadata["columns"],
                    }
                )
            )

        return sorted(summaries, key=lambda item: item.created_at, reverse=True)

    def get_metadata(self, dataset_id: str) -> DatasetMetadata:
        metadata = self._read_metadata(dataset_id)
        return DatasetMetadata.model_validate(metadata)

    def get_transformations(self, dataset_id: str) -> TransformationsResponse:
        metadata = self.get_metadata(dataset_id)
        suggestions = [
            suggestion
            for suggestion in suggest_transformations(metadata)
            if suggestion.suggested_output not in set(metadata.columns)
        ]
        return TransformationsResponse(
            dataset_id=dataset_id,
            transformations=metadata.transformations,
            suggestions=suggestions,
        )

    def add_transformation(
        self,
        dataset_id: str,
        payload: TransformationCreateRequest,
    ) -> DatasetMetadata:
        with self._lock:
            metadata = self.get_metadata(dataset_id)
            current_df = self.load_dataframe(dataset_id, include_transformations=True)

            if payload.source_variable not in current_df.columns:
                raise ValueError(
                    f"Source variable '{payload.source_variable}' not found in dataset columns."
                )
            if payload.output_variable in current_df.columns:
                raise ValueError(
                    f"Output variable '{payload.output_variable}' already exists. Use another name."
                )

            recipe = build_transformation_recipe(payload, metadata.mapping)

            apply_transformation_recipe(current_df.copy(), recipe, metadata.mapping)

            transformations = [*metadata.transformations, recipe]
            derived_columns = [item.output_variable for item in transformations]

            mapping = metadata.mapping.model_copy(deep=True)
            mapping.column_types[recipe.output_variable] = "derived_numeric"
            if recipe.output_variable not in mapping.climate_variables:
                mapping.climate_variables.append(recipe.output_variable)

            base_columns = [col for col in metadata.columns if col not in derived_columns]
            columns = list(dict.fromkeys(base_columns + derived_columns))

            updated = metadata.model_copy(
                update={
                    "columns": columns,
                    "derived_columns": derived_columns,
                    "transformations": transformations,
                    "mapping": mapping,
                }
            )
            self._write_metadata(dataset_id, updated.model_dump(mode="json"))

        return self.get_metadata(dataset_id)

    def derive_temporal_aggregation(
        self,
        dataset_id: str,
        payload: TemporalAggregationRequest,
    ) -> DatasetMetadata:
        with self._lock:
            metadata = self.get_metadata(dataset_id)
            df = self.load_dataframe(dataset_id, include_transformations=True)

            time_column = (payload.time_column or metadata.mapping.time_column or "").strip()
            if not time_column:
                raise ValueError("Temporal aggregation requires a time column.")
            if time_column not in df.columns:
                raise ValueError(f"Time column '{time_column}' not found.")

            numeric_columns = list(df.select_dtypes(include=[np.number]).columns)
            default_values = metadata.mapping.climate_variables or numeric_columns
            value_columns = payload.value_columns or default_values
            value_columns = [
                column
                for column in value_columns
                if column in df.columns and column != time_column
            ]
            numeric_value_columns: list[str] = []
            for column in value_columns:
                converted = pd.to_numeric(df[column], errors="coerce")
                if converted.notna().any():
                    numeric_value_columns.append(column)
            value_columns = numeric_value_columns
            if not value_columns:
                raise ValueError("Temporal aggregation requires at least one numeric value column.")

            aggregations = list(dict.fromkeys(payload.aggregations))
            if not aggregations:
                raise ValueError("Select at least one aggregation.")

            working = df[[time_column, *value_columns]].copy()
            working[time_column] = pd.to_datetime(working[time_column], errors="coerce", utc=True)
            working = working.dropna(subset=[time_column])
            if working.empty:
                raise ValueError(f"Column '{time_column}' does not contain parseable datetimes.")

            for column in value_columns:
                working[column] = pd.to_numeric(working[column], errors="coerce")
            working = working.sort_values(time_column).set_index(time_column)

            resampler = working[value_columns].resample(payload.frequency)
            aggregation_frames: list[pd.DataFrame] = []
            for aggregation in aggregations:
                if aggregation == "range":
                    part = resampler.max() - resampler.min()
                else:
                    method = getattr(resampler, aggregation)
                    part = method()
                part = part.rename(columns={column: f"{column}_{aggregation}" for column in part.columns})
                aggregation_frames.append(part)

            aggregated = pd.concat(aggregation_frames, axis=1).dropna(how="all")
            if aggregated.empty:
                raise ValueError("Temporal aggregation produced no rows.")

            flattened_columns = list(aggregated.columns)
            output_df = aggregated.reset_index().rename(columns={time_column: "period_start"})
            output_df["period_start"] = output_df["period_start"].dt.tz_convert(None)

            mapping = ColumnInference(
                time_column="period_start",
                latitude_column=None,
                longitude_column=None,
                climate_variables=flattened_columns,
                column_types={
                    "period_start": "time",
                    **{column: "numeric" for column in flattened_columns},
                },
            )
            frequency_label = {
                "D": "daily",
                "ME": "monthly",
                "YE": "yearly",
            }.get(payload.frequency, payload.frequency.lower())
            output_name = (
                payload.output_name.strip()
                if payload.output_name and payload.output_name.strip()
                else f"{Path(metadata.name).stem}_{frequency_label}"
            )

            return self.create_dataset_from_dataframe(
                output_df,
                output_name,
                source_format="derived",
                parser_metadata={
                    "source": "temporal_aggregation",
                    "parent_dataset_id": dataset_id,
                    "parent_dataset_name": metadata.name,
                    "time_column": time_column,
                    "value_columns": value_columns,
                    "frequency": payload.frequency,
                    "aggregations": aggregations,
                    "input_rows": int(len(df)),
                    "valid_time_rows": int(len(working)),
                },
                mapping=mapping,
                derived_columns=flattened_columns,
            )

    def get_preview(self, dataset_id: str, limit: int, offset: int = 0) -> DatasetPreview:
        metadata = self.get_metadata(dataset_id)
        df = self.load_dataframe(dataset_id)
        preview_df = df.iloc[offset : offset + limit]
        rows = preview_df.replace({np.nan: None}).to_dict(orient="records")
        return DatasetPreview(
            dataset_id=dataset_id,
            columns=list(df.columns),
            rows=rows,
            row_count=metadata.row_count,
            derived_columns=metadata.derived_columns,
        )

    def load_dataframe(self, dataset_id: str, include_transformations: bool = True) -> pd.DataFrame:
        df = self._load_base_dataframe(dataset_id)
        if not include_transformations:
            return df

        metadata = self.get_metadata(dataset_id)
        if not metadata.transformations:
            return df

        return apply_transformation_recipes(df, metadata.transformations, metadata.mapping)

    def update_mapping(self, dataset_id: str, mapping: ColumnInference) -> DatasetMetadata:
        with self._lock:
            metadata = self._read_metadata(dataset_id)
            metadata["mapping"] = mapping.model_dump()
            self._write_metadata(dataset_id, metadata)
        return DatasetMetadata.model_validate(metadata)

    def export_csv(self, dataset_id: str) -> bytes:
        df = self.load_dataframe(dataset_id)
        return df.to_csv(index=False).encode("utf-8")

    def _load_base_dataframe(self, dataset_id: str) -> pd.DataFrame:
        path = self.storage_dir / dataset_id / "data.parquet"
        if not path.exists():
            raise FileNotFoundError(f"Dataset '{dataset_id}' not found")
        return pd.read_parquet(path)

    def _read_metadata(self, dataset_id: str) -> dict:
        metadata_path = self.storage_dir / dataset_id / "metadata.json"
        if not metadata_path.exists():
            raise FileNotFoundError(f"Dataset metadata for '{dataset_id}' not found")
        loaded = json.loads(metadata_path.read_text(encoding="utf-8"))
        return self._normalize_metadata(loaded)

    @staticmethod
    def _normalize_metadata(metadata: dict) -> dict:
        metadata.setdefault("parser_metadata", {})
        metadata.setdefault("transformations", [])
        metadata.setdefault("derived_columns", [])

        mapping = metadata.setdefault("mapping", {})
        mapping.setdefault("time_column", None)
        mapping.setdefault("latitude_column", None)
        mapping.setdefault("longitude_column", None)
        mapping.setdefault("climate_variables", [])
        mapping.setdefault("column_types", {})

        transformation_outputs = [
            recipe.get("output_variable")
            for recipe in metadata.get("transformations", [])
            if isinstance(recipe, dict) and recipe.get("output_variable")
        ]
        derived_columns = [
            column
            for column in metadata.get("derived_columns", [])
            if isinstance(column, str)
        ]
        metadata["derived_columns"] = list(dict.fromkeys(derived_columns + transformation_outputs))

        columns = [column for column in metadata.get("columns", []) if isinstance(column, str)]
        metadata["columns"] = list(dict.fromkeys(columns + metadata["derived_columns"]))

        climate_variables = [
            variable for variable in mapping.get("climate_variables", []) if isinstance(variable, str)
        ]
        column_types = {
            str(key): str(value)
            for key, value in mapping.get("column_types", {}).items()
        }

        for derived in metadata["derived_columns"]:
            if derived not in climate_variables:
                climate_variables.append(derived)
            column_types.setdefault(derived, "derived_numeric")

        mapping["climate_variables"] = climate_variables
        mapping["column_types"] = column_types
        return metadata

    def _write_metadata(self, dataset_id: str, metadata: dict) -> None:
        dataset_dir = self.storage_dir / dataset_id
        metadata_path = dataset_dir / "metadata.json"
        with tempfile.NamedTemporaryFile("w", delete=False, dir=dataset_dir, encoding="utf-8") as tmp:
            json.dump(metadata, tmp, ensure_ascii=True, indent=2)
            temp_path = Path(tmp.name)
        temp_path.replace(metadata_path)


store = LocalDatasetStore(settings.storage_dir)
