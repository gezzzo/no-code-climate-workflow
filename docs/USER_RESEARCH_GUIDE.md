# User and Research Guide

This guide explains how climate researchers and students can use the platform end-to-end without coding.

## Who This Is For

- Climate scientists
- Environmental researchers
- Students using climate datasets
- Teams that need quick statistical and spatial climate analysis

## What You Can Do

- Upload climate datasets with drag-and-drop
- Automatically detect file format and infer column roles
- Map columns manually (time, latitude, longitude, variables)
- Run built-in statistics and machine learning analyses
- Build interactive charts and maps
- Export datasets and reports as CSV, PDF, and PNG

## Supported File Formats

- CSV (`.csv`)
- Excel (`.xlsx`)
- NetCDF (`.nc`)
- GRIB (`.grb`, `.grib`, `.grib2`)
- GeoTIFF (`.tif`, `.tiff`)

## Dashboard Sections

- `Dataset Manager`: Upload/select datasets
- `Data Explorer`: Preview table rows and columns
- `Column Mapping`: Confirm or edit time/lat/lon/variables
- `Analysis Tools`: Run statistical or ML analyses
- `Visualization Panel`: Build charts and geographic views
- `Results Export`: Download CSV/PDF outputs

## Standard Workflow

1. Open the app (`http://localhost:5173`).
2. In `Dataset Manager`, drag and drop your file.
3. Wait for automatic format detection and parsing.
4. Review first rows in `Data Explorer`.
5. In `Column Mapping`, verify:
   - Time column
   - Latitude column
   - Longitude column
   - Climate variable columns (temperature, precipitation, etc.)
6. In `Transform Variables`, create derived variables when needed (for example `t2m` Kelvin -> `t2m_c` Celsius).
7. Click `Save Mapping` if you changed anything.
8. In `Analysis Tools`, select analysis type and run.
9. In `Visualization Panel`, choose chart/map and build visualization.
10. Export results from `Results Export` or `Export PNG` in visualization panel.

## Analysis Types and When to Use Them

### 1) Descriptive Statistics
Use for quick data quality checks and variable summaries.

Outputs include mean, standard deviation, min/max, and percentiles.

### 2) Trend Detection
Use to measure long-term increase/decrease in a climate variable over time.

Best for temperature or precipitation series with a proper time column.

### 3) Correlation
Use to test relationships between numeric variables (e.g., temperature vs humidity).

### 4) Linear Regression
Use when you want an interpretable baseline model and coefficient values.

### 5) Temperature / Precipitation Trend
Shortcut analyses that prioritize likely temperature/precipitation columns.

### 6) Seasonal Patterns
Use to compare monthly and seasonal averages (winter/spring/summer/autumn).

### 7) Anomaly Detection
Use z-score based detection for unusual values or extreme events.

Recommended initial threshold: `z = 2.0`.

### 8) Random Forest Regression
Use for non-linear relationships when linear models underperform.

### 9) Time-Series Forecasting
Use to extrapolate future values from historical series.

Start with short horizons first, then increase if performance is reasonable.

## Derived Variables (Prepare Stage)

Use `Transform Variables` to create new climate columns without modifying original uploaded data.

Supported operations:

- Kelvin -> Celsius / Fahrenheit
- Celsius -> Kelvin
- m/s -> km/h / mph
- Pa -> hPa
- Multiply / Divide / Add / Subtract by constant
- Rolling mean
- Aggregation by day / month

The platform stores each transformation as a recipe and applies it dynamically during preview, analysis, visualization, and export.

## Visualization Guide

### Time Series
Best for tracking one variable over time.

### Scatter Plot
Best for comparing two numeric variables and spotting relationships.

### Heatmap
- If latitude/longitude is mapped: spatial intensity grid
- Otherwise: variable correlation heatmap

### Geographic Map
Plots data points on a world map using latitude/longitude.

### Anomaly Graph
Displays normal series values plus highlighted anomaly points.

## Recommended Data Preparation

- Include clear column names (`time`, `latitude`, `longitude`, `temperature`, `precipitation`).
- Keep one timestamp per row for tabular time series.
- Use consistent units across files (for example Celsius or Kelvin, not mixed).
- Remove obviously invalid values before upload when possible.
- For large files, start with a representative subset to validate workflow quickly.

## Example Research Workflows

### Workflow A: Temperature Trend by Region

1. Upload a dataset with `time`, `latitude`, `longitude`, `temperature`.
2. Map columns in `Column Mapping`.
3. Run `temperature_trend`.
4. Build `time_series` visualization.
5. Build `map` visualization to inspect spatial pattern.
6. Export analysis PDF for reporting.

### Workflow B: Precipitation Extremes Study

1. Upload precipitation dataset.
2. Map `time` and precipitation variable.
3. Run `anomaly_detection` with `z_threshold = 2.0` (or 2.5).
4. Build `anomaly_graph`.
5. Export CSV of results for external validation.

### Workflow C: Forecasting Short-Term Climate Variable

1. Upload historical time series.
2. Map `time` and target variable.
3. Run `time_series_forecasting` with a small horizon.
4. Compare forecast to recent known values.
5. Refine horizon/lag settings if needed.

## Exporting Results

- `Export Dataset CSV`: full normalized table
- `Export Analysis CSV`: analysis output table
- `Export PDF Report`: report summary for publications or meetings
- `Export PNG`: chart image from visualization panel

## Interpretation Notes

- Correlation does not imply causation.
- Forecast quality depends on historical data quality and coverage.
- Trend significance should be confirmed with domain/statistical review when used for publication.
- For mission-critical studies, validate results with independent scripts/tools.

## Troubleshooting

### Upload fails

- Confirm file extension is supported.
- Re-save file (especially Excel/NetCDF) and retry.
- Check backend logs for parser-specific errors.

### Time-based analyses fail

- Ensure a valid time column is mapped.
- Confirm the time column has parseable dates/timestamps.

### Map is empty

- Ensure latitude and longitude are mapped correctly.
- Confirm coordinates are in valid ranges (`lat: -90..90`, `lon: -180..180`).

### GRIB parsing issues

- Verify `cfgrib` and `ecCodes` dependencies are installed in backend environment.

### Forecasting or ML errors

- Increase number of complete rows.
- Remove rows with missing target/feature values.
- Start with fewer features.

## Good Practices for Research Teams

- Save exported CSV/PDF with clear experiment names and dates.
- Keep a small run log: dataset version, mapping, analysis type, parameters.
- Re-run key analyses when new data arrives to keep comparisons consistent.
- Use the same preprocessing and mapping rules across collaborators.

## Suggested Citation/Method Reporting Template

When reporting results externally, include:

- Dataset source and version
- Platform workflow (upload -> mapping -> analysis type)
- Selected variables and parameters
- Export date and timezone
- Any preprocessing steps done before upload

---

If you are new to this platform, start with `Descriptive statistics` and `Time series` first, then move to trend, anomaly, and forecasting analyses.
