export type WorkspaceStage = "ingest" | "prepare" | "analyze" | "visualize";

interface Props {
  activeStage: WorkspaceStage;
  onStageChange: (stage: WorkspaceStage) => void;
  hasDataset: boolean;
  hasMapping: boolean;
  hasAnalysis: boolean;
  hasVisualization: boolean;
}

const STAGE_CONFIG: Array<{
  key: WorkspaceStage;
  title: string;
  description: string;
}> = [
  {
    key: "ingest",
    title: "Ingest Data",
    description: "Upload and parse climate sources",
  },
  {
    key: "prepare",
    title: "Prepare Mapping",
    description: "Map time, spatial, and climate columns",
  },
  {
    key: "analyze",
    title: "Run Analysis",
    description: "Climate statistics and diagnostics",
  },
  {
    key: "visualize",
    title: "Visualize + Export",
    description: "Charts, maps, and report outputs",
  },
];

export function WorkflowStrip({
  activeStage,
  onStageChange,
  hasDataset,
  hasMapping,
  hasAnalysis,
  hasVisualization,
}: Props) {
  const completionMap: Record<WorkspaceStage, boolean> = {
    ingest: hasDataset,
    prepare: hasMapping,
    analyze: hasAnalysis,
    visualize: hasVisualization,
  };

  return (
    <section className="panel workflow-panel">
      <div className="panel-header">
        <h2>Workflow Canvas</h2>
      </div>
      <div className="workflow-track" role="tablist" aria-label="Workflow stages">
        {STAGE_CONFIG.map((stage, idx) => {
          const complete = completionMap[stage.key];
          const active = activeStage === stage.key;
          const statusLabel = complete ? "Complete" : "Pending";

          return (
            <button
              key={stage.key}
              type="button"
              className={`workflow-node ${active ? "workflow-node-active" : ""}`}
              onClick={() => onStageChange(stage.key)}
              role="tab"
              aria-selected={active}
            >
              <span className={`workflow-index ${complete ? "workflow-index-complete" : ""}`}>
                {idx + 1}
              </span>
              <span className="workflow-meta">
                <strong>{stage.title}</strong>
                <small>{stage.description}</small>
              </span>
              <span className={`workflow-status ${complete ? "workflow-status-complete" : ""}`}>{statusLabel}</span>
            </button>
          );
        })}
      </div>
    </section>
  );
}
