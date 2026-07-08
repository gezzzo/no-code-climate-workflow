import { useEffect, useMemo, useState } from "react";

import { api } from "./api/client";
import { AnalysisTools } from "./components/AnalysisTools";
import { ColumnMappingPanel } from "./components/ColumnMappingPanel";
import { DataExplorer } from "./components/DataExplorer";
import { DatasetManager } from "./components/DatasetManager";
import { DocumentationView } from "./components/DocumentationView";
import { PrepareWorkflowBuilder } from "./components/PrepareWorkflowBuilder";
import { VisualizationPanel } from "./components/VisualizationPanel";
import { WorkflowStrip, WorkspaceStage } from "./components/WorkflowStrip";
import {
  AnalysisRequest,
  AnalysisResponse,
  DatasetMetadata,
  DatasetPreview,
  DatasetSummary,
  MappingUpdateRequest,
  VisualizationResponse,
} from "./types";

// ── Workspace Stages ──────────────────────────────────────────────────────────
const WORKSPACE_STAGES: Array<{ key: WorkspaceStage; label: string }> = [
  { key: "ingest", label: "Ingest" },
  { key: "prepare", label: "Prepare" },
  { key: "analyze", label: "Analyze" },
  { key: "visualize", label: "Visualize" },
];

// ── Dashboard (existing app content) ─────────────────────────────────────────
function Dashboard() {
  const [activeView, setActiveView] = useState<"dashboard" | "documentation">("dashboard");
  const [activeStage, setActiveStage] = useState<WorkspaceStage>("ingest");

  const [datasets, setDatasets] = useState<DatasetSummary[]>([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState<string | null>(null);
  const [metadata, setMetadata] = useState<DatasetMetadata | null>(null);
  const [preview, setPreview] = useState<DatasetPreview | null>(null);

  const [uploading, setUploading] = useState(false);
  const [importingFromGithub, setImportingFromGithub] = useState(false);
  const [savingMapping, setSavingMapping] = useState(false);
  const [runningAnalysis, setRunningAnalysis] = useState(false);
  const [buildingVisualization, setBuildingVisualization] = useState(false);
  const [applyingTransformation, setApplyingTransformation] = useState(false);
  const [derivingDataset, setDerivingDataset] = useState(false);

  const [analysisResult, setAnalysisResult] = useState<AnalysisResponse | null>(null);
  const [visualization, setVisualization] = useState<VisualizationResponse | null>(null);
  const [lastAnalysisRequest, setLastAnalysisRequest] = useState<AnalysisRequest | null>(null);

  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void refreshDatasets();
  }, []);

  const columns = useMemo(() => metadata?.columns ?? [], [metadata]);
  const hasDataset = Boolean(selectedDatasetId);
  const hasMapping = useMemo(() => {
    const mapping = metadata?.mapping;
    if (!mapping) return false;
    return Boolean(
      mapping.time_column ||
        mapping.latitude_column ||
        mapping.longitude_column ||
        mapping.climate_variables.length > 0,
    );
  }, [metadata]);
  const hasAnalysis = Boolean(analysisResult);
  const hasVisualization = Boolean(visualization);

  const refreshDatasets = async (): Promise<void> => {
    try {
      const list = await api.listDatasets();
      setDatasets(list);
      if (!selectedDatasetId && list.length > 0) {
        await loadDataset(list[0].dataset_id);
      }
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  const loadDataset = async (datasetId: string): Promise<void> => {
    try {
      setError(null);
      setSelectedDatasetId(datasetId);
      const [nextMetadata, nextPreview] = await Promise.all([
        api.getMetadata(datasetId),
        api.getPreview(datasetId, 100),
      ]);
      setMetadata(nextMetadata);
      setPreview(nextPreview);
      setAnalysisResult(null);
      setVisualization(null);
      setLastAnalysisRequest(null);
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  const uploadDataset = async (file: File): Promise<void> => {
    try {
      setUploading(true);
      setError(null);
      const created = await api.uploadDataset(file);
      await refreshDatasets();
      await loadDataset(created.dataset_id);
      setActiveStage("prepare");
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setUploading(false);
    }
  };

  const importDatasetFromGithub = async (url: string): Promise<void> => {
    try {
      setImportingFromGithub(true);
      setError(null);
      const created = await api.importDatasetFromGithub(url);
      await refreshDatasets();
      await loadDataset(created.dataset_id);
      setActiveStage("prepare");
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setImportingFromGithub(false);
    }
  };

  const saveMapping = async (payload: MappingUpdateRequest): Promise<void> => {
    if (!selectedDatasetId) return;
    try {
      setSavingMapping(true);
      setError(null);
      const updated = await api.updateMapping(selectedDatasetId, payload);
      setMetadata(updated);
      setActiveStage("prepare");
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSavingMapping(false);
    }
  };

  const applyTransformation = async (
    payload: Parameters<typeof api.createTransformation>[1],
  ): Promise<void> => {
    if (!selectedDatasetId) return;
    try {
      setApplyingTransformation(true);
      setError(null);
      const updated = await api.createTransformation(selectedDatasetId, payload);
      const updatedPreview = await api.getPreview(selectedDatasetId, 100);
      setMetadata(updated);
      setPreview(updatedPreview);
      setAnalysisResult(null);
      setVisualization(null);
      setLastAnalysisRequest(null);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setApplyingTransformation(false);
    }
  };

  const deriveTemporalAggregation = async (
    payload: Parameters<typeof api.deriveTemporalAggregation>[1],
  ): Promise<void> => {
    if (!selectedDatasetId) return;
    try {
      setDerivingDataset(true);
      setError(null);
      const created = await api.deriveTemporalAggregation(selectedDatasetId, payload);
      await refreshDatasets();
      await loadDataset(created.dataset_id);
      setActiveStage("prepare");
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setDerivingDataset(false);
    }
  };

  const runAnalysis = async (payload: AnalysisRequest): Promise<void> => {
    if (!selectedDatasetId) return;
    try {
      setRunningAnalysis(true);
      setError(null);
      const result = await api.runAnalysis(selectedDatasetId, payload);
      setAnalysisResult(result);
      setLastAnalysisRequest(payload);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setRunningAnalysis(false);
    }
  };

  const buildVisualization = async (
    payload: Parameters<typeof api.buildVisualization>[1],
  ): Promise<void> => {
    if (!selectedDatasetId) return;
    try {
      setBuildingVisualization(true);
      setError(null);
      const result = await api.buildVisualization(selectedDatasetId, payload);
      setVisualization(result);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setBuildingVisualization(false);
    }
  };

  const exportDatasetCsv = async (): Promise<void> => {
    if (!selectedDatasetId) return;
    try {
      await api.downloadDatasetCsv(selectedDatasetId);
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  const exportAnalysisCsv = async (): Promise<void> => {
    if (!selectedDatasetId || !lastAnalysisRequest) return;
    try {
      await api.downloadAnalysisCsv(selectedDatasetId, lastAnalysisRequest);
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  const exportAnalysisPdf = async (): Promise<void> => {
    if (!selectedDatasetId || !lastAnalysisRequest) return;
    try {
      await api.downloadAnalysisPdf(selectedDatasetId, lastAnalysisRequest);
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  return (
    <div className="app-shell">
      <div className="workspace-layout">
        <aside className="workspace-sidebar">
          <div className="sidebar-brand">
            <span className="brand-mark" aria-hidden="true">CD</span>
            <div>
              <h1>Climate Studio</h1>
              <p>Visual climate analytics workbench</p>
            </div>
          </div>

          <div className="sidebar-section">
            <button
              type="button"
              className={`side-nav-btn ${activeView === "dashboard" ? "side-nav-btn-active" : ""}`}
              onClick={() => setActiveView("dashboard")}
            >
              Data Workbench
            </button>
            <button
              type="button"
              className={`side-nav-btn ${activeView === "documentation" ? "side-nav-btn-active" : ""}`}
              onClick={() => setActiveView("documentation")}
            >
              User Documentation
            </button>
          </div>

          <div className="sidebar-section">
            <h2>Pipeline Stages</h2>
            <div className="side-stage-list">
              {WORKSPACE_STAGES.map((stage) => (
                <button
                  key={stage.key}
                  type="button"
                  className={`side-stage-btn ${activeStage === stage.key ? "side-stage-btn-active" : ""}`}
                  onClick={() => {
                    setActiveView("dashboard");
                    setActiveStage(stage.key);
                  }}
                >
                  {stage.label}
                </button>
              ))}
            </div>
          </div>

          <div className="sidebar-section sidebar-stats">
            <h2>Workspace Status</h2>
            <dl>
              <div>
                <dt>Datasets</dt>
                <dd>{datasets.length}</dd>
              </div>
              <div>
                <dt>Selected</dt>
                <dd>{metadata?.name ?? "None"}</dd>
              </div>
              <div>
                <dt>Rows</dt>
                <dd>{metadata ? metadata.row_count.toLocaleString() : "0"}</dd>
              </div>
              <div>
                <dt>Mapped vars</dt>
                <dd>{metadata?.mapping.climate_variables.length ?? 0}</dd>
              </div>
            </dl>
          </div>
        </aside>

        <div className="workspace-main">
          <header className="workspace-header panel">
            <div>
              <h2>{activeView === "dashboard" ? "Research Workbench" : "User and Research Documentation"}</h2>
              <p>
                {activeView === "dashboard"
                  ? "Build climate workflows visually with staged ingestion, analysis, and visualization."
                  : "Read usage guidance, workflows, and troubleshooting inside the platform."}
              </p>
            </div>
            <div className="header-actions">
              <button type="button" className="secondary-btn" onClick={() => void refreshDatasets()}>
                Refresh Datasets
              </button>
              <button type="button" className="secondary-btn" onClick={() => setActiveView("documentation")}>
                Open Docs
              </button>
            </div>
          </header>

          {error ? <div className="error-banner">{error}</div> : null}

          {activeView === "documentation" ? (
            <main>
              <DocumentationView />
            </main>
          ) : (
            <>
              <WorkflowStrip
                activeStage={activeStage}
                onStageChange={setActiveStage}
                hasDataset={hasDataset}
                hasMapping={hasMapping}
                hasAnalysis={hasAnalysis}
                hasVisualization={hasVisualization}
              />

              <section className="insight-strip">
                <article className="panel insight-card">
                  <span>Active dataset format</span>
                  <strong>{metadata?.source_format?.toUpperCase() ?? "-"}</strong>
                </article>
                <article className="panel insight-card">
                  <span>Inference status</span>
                  <strong>{hasMapping ? "Columns mapped" : "Needs mapping"}</strong>
                </article>
                <article className="panel insight-card">
                  <span>Last analysis</span>
                  <strong>{analysisResult?.analysis_type ?? "Not run"}</strong>
                </article>
                <article className="panel insight-card">
                  <span>Visualization</span>
                  <strong>{visualization?.visualization_type ?? "Not generated"}</strong>
                </article>
              </section>

              <main className="workspace-grid">
                <div className="workspace-column workspace-column-side">
                  <DatasetManager
                    datasets={datasets}
                    selectedDatasetId={selectedDatasetId}
                    uploading={uploading}
                    importingFromGithub={importingFromGithub}
                    onSelectDataset={(datasetId) => { void loadDataset(datasetId); }}
                    onUpload={uploadDataset}
                    onImportFromGithub={importDatasetFromGithub}
                  />

                  <section className="panel export-panel">
                    <div className="panel-header">
                      <h2>Results Export</h2>
                    </div>
                    <p>Download processed datasets and analysis reports.</p>
                    <div className="button-row">
                      <button type="button" className="secondary-btn" onClick={() => void exportDatasetCsv()}>
                        Export Dataset CSV
                      </button>
                      <button
                        type="button"
                        className="secondary-btn"
                        disabled={!lastAnalysisRequest}
                        onClick={() => void exportAnalysisCsv()}
                      >
                        Export Analysis CSV
                      </button>
                      <button
                        type="button"
                        className="secondary-btn"
                        disabled={!lastAnalysisRequest}
                        onClick={() => void exportAnalysisPdf()}
                      >
                        Export PDF Report
                      </button>
                    </div>
                  </section>
                </div>

                <div className="workspace-column workspace-column-main">
                  {activeStage === "ingest" ? <DataExplorer preview={preview} /> : null}

                  {activeStage === "prepare" ? (
                    <>
                      <ColumnMappingPanel
                        columns={columns}
                        mapping={metadata?.mapping ?? null}
                        saving={savingMapping}
                        onSave={saveMapping}
                      />
                      <PrepareWorkflowBuilder
                        datasetName={metadata?.name ?? null}
                        sourceFormat={metadata?.source_format ?? null}
                        rowCount={metadata?.row_count ?? 0}
                        datasetId={selectedDatasetId}
                        columns={columns}
                        mapping={metadata?.mapping ?? null}
                        transformations={metadata?.transformations ?? []}
                        preview={preview}
                        applying={applyingTransformation}
                        deriving={derivingDataset}
                        onApplyTransformation={applyTransformation}
                        onDeriveTemporalAggregation={deriveTemporalAggregation}
                      />
                      <DataExplorer preview={preview} />
                    </>
                  ) : null}

                  {activeStage === "analyze" ? (
                    <>
                      <AnalysisTools
                        columns={columns}
                        defaultTimeColumn={metadata?.mapping.time_column ?? null}
                        defaultVariables={metadata?.mapping.climate_variables ?? []}
                        running={runningAnalysis}
                        result={analysisResult}
                        onRun={runAnalysis}
                      />
                      <ColumnMappingPanel
                        columns={columns}
                        mapping={metadata?.mapping ?? null}
                        saving={savingMapping}
                        onSave={saveMapping}
                      />
                    </>
                  ) : null}

                  {activeStage === "visualize" ? (
                    <>
                      <VisualizationPanel
                        columns={columns}
                        defaultTimeColumn={metadata?.mapping.time_column ?? null}
                        defaultVariables={metadata?.mapping.climate_variables ?? []}
                        loading={buildingVisualization}
                        response={visualization}
                        onBuild={buildVisualization}
                      />
                      <AnalysisTools
                        columns={columns}
                        defaultTimeColumn={metadata?.mapping.time_column ?? null}
                        defaultVariables={metadata?.mapping.climate_variables ?? []}
                        running={runningAnalysis}
                        result={analysisResult}
                        onRun={runAnalysis}
                      />
                    </>
                  ) : null}
                </div>
              </main>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Root App ──────────────────────────────────────────────────────────────────
export default function App() {
  return <Dashboard />;
}

function getErrorMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  return "Unexpected error";
}
