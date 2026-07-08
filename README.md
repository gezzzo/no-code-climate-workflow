# Climate Data Analysis Tool

Full-stack Tool for climate researchers to upload, explore, analyze, and visualize climate datasets without writing code for my thesis

User-facing documentation: [docs/USER_RESEARCH_GUIDE.md](/docs/USER_RESEARCH_GUIDE.md)

## Supervisor : Prof. Ducco Roccuni
GitHub link: https://github.com/ducciorocchini


## Features

- In-app `Documentation` view for end users and researchers
- Single-user local workspace with file-backed dataset storage
- Drag-and-drop upload workflow
- Automatic format detection and parsing
- Supported formats:
  - CSV
  - Excel (`.xlsx`)
  - NetCDF (`.nc`)
  - GRIB (`.grb`, `.grib`, `.grib2`)
  - GeoTIFF (`.tif`, `.tiff`)
- Automatic schema inference:
  - Time column
  - Latitude / longitude
  - Candidate climate variables
- Manual column mapping override
- Derived Variables / Transform Variables module (recipe-based, non-destructive)
- Built-in analysis:
  - Descriptive statistics (mean, std, min, max, quantiles)
  - Trend detection
  - Correlation
  - Linear regression
  - Temperature/precipitation trend shortcuts
  - Seasonal patterns
  - Anomaly detection (z-score)
  - Random forest regression
  - Time-series forecasting
- Interactive visualizations:
  - Time series
  - Scatter
  - Heatmap
  - Geographic maps (Leaflet + geospatial layer)
  - Anomaly graph
- Export capabilities:
  - Dataset CSV
  - Analysis CSV
  - PDF report
  - PNG chart export (frontend)

## Architecture

### Frontend (`/frontend`)

- React + Vite + TypeScript
- Opens directly to the workbench; no homepage, login, or registration flow
- `react-dropzone` for drag-and-drop upload
- `react-plotly.js` for interactive charts
- `react-leaflet` for geographic map visualization
- Scientific dashboard sections:
  - Dataset Manager
  - Data Explorer
  - Column Mapping
  - Analysis Tools
  - Visualization Panel
  - Results Export

### Backend (`/backend`)

- FastAPI REST API
- Data parsing and normalization services
- Analysis engine with statistical + ML modules
- Export service for CSV and PDF
- Local dataset store (`storage/`) with metadata and parquet-backed normalized tables
- No database service is required; persisted metadata lives in JSON files beside each dataset

### Data Processing Layer

- `pandas` for tabular handling
- `xarray` / `netCDF4` / `cfgrib` for multidimensional climate datasets
- `rasterio` for GeoTIFF spatial extraction
- `numpy` and `scikit-learn` for numerical and ML operations

## Local Setup

### 1) Backend

```bash
cd /Users/mohammedmostafa/Projects/climate-tool-individual
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn app.main:app --reload --app-dir backend --port 8000
```

Backend API: `http://localhost:8000/api`

Note: GRIB parsing depends on `cfgrib` + `ecCodes` (included in requirements). If your OS blocks native dependencies, GRIB ingestion may need additional system packages.

### 2) Frontend

```bash
cd /Users/mohammedmostafa/Projects/climate-tool-individual/frontend
npm install
npm run dev
```

Frontend app: `http://localhost:5173`

If needed, set API URL:

```bash
export VITE_API_BASE_URL=http://localhost:8000/api
```

## Docker Deployment

```bash
cd /Users/mohammedmostafa/Projects/climate-tool-individual
docker compose up --build
```

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000/api`

## Backend Tests

```bash
cd /Users/mohammedmostafa/Projects/climate-tool-individual
source .venv/bin/activate
pip install -r backend/requirements-dev.txt
PYTHONPATH=backend pytest backend/tests
```

## API Overview

- `POST /api/datasets/upload`
- `POST /api/datasets/github-import`
- `GET /api/datasets`
- `GET /api/datasets/{dataset_id}`
- `GET /api/datasets/{dataset_id}/preview`
- `GET /api/datasets/{dataset_id}/mapping`
- `PUT /api/datasets/{dataset_id}/mapping`
- `POST /api/datasets/{dataset_id}/analysis`
- `GET /api/datasets/{dataset_id}/transformations`
- `POST /api/datasets/{dataset_id}/transformations`
- `POST /api/datasets/{dataset_id}/derive/temporal-aggregation`
- `POST /api/datasets/{dataset_id}/visualize`
- `GET /api/datasets/{dataset_id}/export/dataset.csv`
- `POST /api/datasets/{dataset_id}/analysis/export.csv`
- `POST /api/datasets/{dataset_id}/analysis/export.pdf`

## Scalability Notes

- Uploaded datasets are converted to parquet for efficient local reads.
- Very large multidimensional datasets are downsampled to a configurable cap (`MAX_STANDARDIZED_ROWS`).
- Map rendering is point-capped for responsive interaction.
- The service layer is modular and can be swapped to distributed engines (Dask/Spark/object storage) later.

## Optional Extensions

- Notebook-like analysis history
- Advanced geospatial layers (raster overlays / vector tiles)
- Project workspaces backed by local files
