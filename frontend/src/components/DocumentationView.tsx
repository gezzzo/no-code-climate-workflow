const workflowSteps = [
  "Upload a climate dataset in Dataset Manager using drag-and-drop.",
  "Review parsed columns and sample rows in Data Explorer.",
  "Map time, latitude, longitude, and climate variables in Column Mapping.",
  "Create derived variables in Transform Variables (unit conversion, math, rolling, daily/monthly aggregates).",
  "Run analysis in Analysis Tools (statistics, trends, ML).",
  "Build charts/maps in Visualization Panel.",
  "Export CSV, PDF, and PNG outputs for reports and collaboration.",
];

const analysisItems = [
  {
    title: "Descriptive Statistics",
    description: "Quickly inspect mean, standard deviation, min/max, and percentiles.",
  },
  {
    title: "Trend Detection",
    description: "Measure long-term increase/decrease of climate variables over time.",
  },
  {
    title: "Correlation",
    description: "Evaluate relationships between numeric variables such as temperature and humidity.",
  },
  {
    title: "Linear Regression",
    description: "Use interpretable baseline modeling with coefficients.",
  },
  {
    title: "Seasonal Patterns",
    description: "Compare monthly and seasonal behavior (winter/spring/summer/autumn).",
  },
  {
    title: "Anomaly Detection",
    description: "Find unusual climate values with z-score thresholding.",
  },
  {
    title: "Random Forest Regression",
    description: "Capture non-linear relationships for better predictive performance.",
  },
  {
    title: "Time-Series Forecasting",
    description: "Generate short-term forecasts from historical climate records.",
  },
];

const visualizationItems = [
  "Time Series: evolution of one variable over time.",
  "Scatter Plot: relationship between two numeric variables.",
  "Heatmap: spatial bins (lat/lon) or variable correlations.",
  "Geographic Map: points plotted over world map with lat/lon.",
  "Anomaly Graph: baseline series with highlighted outliers.",
];

const troubleshootingItems = [
  {
    problem: "Upload fails",
    fix: "Check file extension and file integrity, then retry upload.",
  },
  {
    problem: "Trend/seasonal/forecast errors",
    fix: "Confirm that a valid parseable time column is mapped.",
  },
  {
    problem: "Map looks empty",
    fix: "Verify lat/lon mapping and value ranges (lat -90..90, lon -180..180).",
  },
  {
    problem: "GRIB parsing errors",
    fix: "Ensure backend dependencies for cfgrib and ecCodes are installed.",
  },
  {
    problem: "Weak model performance",
    fix: "Increase clean data rows, reduce noisy features, and test shorter forecast horizons.",
  },
];

export function DocumentationView() {
  return (
    <section className="docs-layout">
      <div className="panel docs-hero">
        <h2>User and Research Documentation</h2>
        <p>
          This platform is designed for climate researchers who want to upload, analyze, and visualize climate
          datasets without writing code.
        </p>
      </div>

      <div className="panel docs-section">
        <h3>Quick Workflow</h3>
        <ol>
          {workflowSteps.map((step) => (
            <li key={step}>{step}</li>
          ))}
        </ol>
      </div>

      <div className="panel docs-section">
        <h3>Supported File Formats</h3>
        <div className="docs-tags">
          <span>CSV</span>
          <span>Excel (.xlsx)</span>
          <span>NetCDF (.nc)</span>
          <span>GRIB (.grb/.grib/.grib2)</span>
          <span>GeoTIFF (.tif/.tiff)</span>
        </div>
      </div>

      <div className="panel docs-section">
        <h3>Analysis Methods</h3>
        <div className="docs-grid">
          {analysisItems.map((item) => (
            <article key={item.title} className="docs-card">
              <h4>{item.title}</h4>
              <p>{item.description}</p>
            </article>
          ))}
        </div>
      </div>

      <div className="panel docs-section">
        <h3>Visualization Options</h3>
        <ul>
          {visualizationItems.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </div>

      <div className="panel docs-section">
        <h3>Troubleshooting</h3>
        <div className="docs-grid">
          {troubleshootingItems.map((item) => (
            <article key={item.problem} className="docs-card">
              <h4>{item.problem}</h4>
              <p>{item.fix}</p>
            </article>
          ))}
        </div>
      </div>

      <div className="panel docs-section">
        <h3>Research Best Practices</h3>
        <ul>
          <li>Keep clear variable names (`time`, `latitude`, `longitude`, `temperature`, `precipitation`).</li>
          <li>Use consistent units across datasets before comparing results.</li>
          <li>Export results with dates and dataset version notes for reproducibility.</li>
          <li>Validate high-stakes findings with domain review and independent checks.</li>
        </ul>
      </div>
    </section>
  );
}
