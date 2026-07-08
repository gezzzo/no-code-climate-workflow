from __future__ import annotations

from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.schemas import (
    AnalysisRequest,
    AnalysisResponse,
    ColumnInference,
    DatasetMetadata,
    DatasetPreview,
    DatasetSummary,
    GitHubImportRequest,
    MappingUpdateRequest,
    TemporalAggregationRequest,
    TransformationCreateRequest,
    TransformationsResponse,
    VisualizationRequest,
    VisualizationResponse,
)
from app.services.analysis import analysis_engine
from app.services.dataset_store import store
from app.services.exporter import export_service
from app.services.file_parser import UnsupportedFormatError
from app.services.github_importer import GitHubImportError, download_github_file
from app.services.visualization import visualization_builder

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.post("/upload", response_model=DatasetMetadata)
async def upload_dataset(file: UploadFile = File(...)) -> DatasetMetadata:
    try:
        return store.create_dataset(file)
    except UnsupportedFormatError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to process upload: {exc}") from exc


@router.post("/github-import", response_model=DatasetMetadata)
async def import_dataset_from_github(payload: GitHubImportRequest) -> DatasetMetadata:
    imported_path: Path | None = None
    try:
        imported = download_github_file(payload.url)
        imported_path = imported.path
        metadata = store.create_dataset_from_path(
            imported.path,
            imported.filename,
            {
                "import_source": "github",
                "github_url": imported.source_url,
                "github_raw_url": imported.raw_url,
                "github_repository": imported.repository,
                "github_ref": imported.ref,
                "github_path": imported.file_path,
                "github_bytes": imported.bytes_read,
            },
        )
        return metadata
    except (GitHubImportError, UnsupportedFormatError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to import GitHub file: {exc}") from exc
    finally:
        if imported_path:
            imported_path.unlink(missing_ok=True)


@router.get("", response_model=list[DatasetSummary])
async def list_datasets() -> list[DatasetSummary]:
    return store.list_datasets()


@router.get("/{dataset_id}", response_model=DatasetMetadata)
async def get_dataset_metadata(dataset_id: str) -> DatasetMetadata:
    try:
        return store.get_metadata(dataset_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{dataset_id}/preview", response_model=DatasetPreview)
async def get_dataset_preview(
    dataset_id: str,
    limit: int = Query(default=settings.preview_default_limit, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> DatasetPreview:
    try:
        return store.get_preview(dataset_id, limit=limit, offset=offset)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate preview: {exc}") from exc


@router.get("/{dataset_id}/mapping", response_model=ColumnInference)
async def get_mapping(dataset_id: str) -> ColumnInference:
    try:
        metadata = store.get_metadata(dataset_id)
        return metadata.mapping
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/{dataset_id}/mapping", response_model=DatasetMetadata)
async def update_mapping(dataset_id: str, payload: MappingUpdateRequest) -> DatasetMetadata:
    try:
        existing = store.get_metadata(dataset_id).mapping
        mapping = existing.model_copy(update=payload.model_dump())
        return store.update_mapping(dataset_id, mapping)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{dataset_id}/analysis", response_model=AnalysisResponse)
async def run_analysis(dataset_id: str, payload: AnalysisRequest) -> AnalysisResponse:
    try:
        metadata = store.get_metadata(dataset_id)
        df = store.load_dataframe(dataset_id)
        result = analysis_engine.run(df, metadata.mapping, payload)
        return AnalysisResponse(dataset_id=dataset_id, analysis_type=payload.analysis_type, result=result)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}") from exc


@router.get("/{dataset_id}/transformations", response_model=TransformationsResponse)
async def get_transformations(dataset_id: str) -> TransformationsResponse:
    try:
        return store.get_transformations(dataset_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{dataset_id}/transformations", response_model=DatasetMetadata)
async def create_transformation(dataset_id: str, payload: TransformationCreateRequest) -> DatasetMetadata:
    try:
        return store.add_transformation(dataset_id, payload)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{dataset_id}/derive/temporal-aggregation", response_model=DatasetMetadata)
async def derive_temporal_aggregation(
    dataset_id: str, payload: TemporalAggregationRequest
) -> DatasetMetadata:
    try:
        return store.derive_temporal_aggregation(dataset_id, payload)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{dataset_id}/visualize", response_model=VisualizationResponse)
async def build_visualization(dataset_id: str, payload: VisualizationRequest) -> VisualizationResponse:
    try:
        metadata = store.get_metadata(dataset_id)
        df = store.load_dataframe(dataset_id)
        figure = visualization_builder.build(df, metadata.mapping, payload)
        return VisualizationResponse(
            dataset_id=dataset_id,
            visualization_type=payload.visualization_type,
            figure=figure,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Visualization failed: {exc}") from exc


@router.get("/{dataset_id}/export/dataset.csv")
async def export_dataset_csv(dataset_id: str) -> StreamingResponse:
    try:
        csv_bytes = store.export_csv(dataset_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return StreamingResponse(
        BytesIO(csv_bytes),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={dataset_id}.csv"},
    )


@router.post("/{dataset_id}/analysis/export.csv")
async def export_analysis_csv(
    dataset_id: str, payload: AnalysisRequest
) -> StreamingResponse:
    try:
        metadata = store.get_metadata(dataset_id)
        df = store.load_dataframe(dataset_id)
        result = analysis_engine.run(df, metadata.mapping, payload)
        csv_bytes = export_service.analysis_to_csv(payload.analysis_type, result)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    filename = f"{dataset_id}_{payload.analysis_type}.csv"
    return StreamingResponse(
        BytesIO(csv_bytes),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/{dataset_id}/analysis/export.pdf")
async def export_analysis_pdf(
    dataset_id: str, payload: AnalysisRequest
) -> StreamingResponse:
    try:
        metadata = store.get_metadata(dataset_id)
        df = store.load_dataframe(dataset_id)
        result = analysis_engine.run(df, metadata.mapping, payload)
        pdf_bytes = export_service.analysis_to_pdf(
            dataset_name=metadata.name,
            analysis_type=payload.analysis_type,
            result=result,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    filename = f"{dataset_id}_{payload.analysis_type}.pdf"
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
