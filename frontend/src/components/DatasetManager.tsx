import { useMemo, useState } from "react";
import type { FormEvent } from "react";
import { useDropzone } from "react-dropzone";

import { DatasetSummary } from "../types";

interface Props {
  datasets: DatasetSummary[];
  selectedDatasetId: string | null;
  uploading: boolean;
  importingFromGithub: boolean;
  onSelectDataset: (datasetId: string) => void;
  onUpload: (file: File) => Promise<void>;
  onImportFromGithub: (url: string) => Promise<void>;
}

export function DatasetManager({
  datasets,
  selectedDatasetId,
  uploading,
  importingFromGithub,
  onSelectDataset,
  onUpload,
  onImportFromGithub,
}: Props) {
  const [githubUrl, setGithubUrl] = useState("");
  const selected = useMemo(
    () => datasets.find((dataset) => dataset.dataset_id === selectedDatasetId),
    [datasets, selectedDatasetId],
  );
  const ingesting = uploading || importingFromGithub;

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    multiple: false,
    disabled: ingesting,
    onDropAccepted: async (files) => {
      if (files[0]) {
        await onUpload(files[0]);
      }
    },
  });

  const handleGithubImport = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmedUrl = githubUrl.trim();
    if (!trimmedUrl) return;

    await onImportFromGithub(trimmedUrl);
    setGithubUrl("");
  };

  return (
    <section className="panel dataset-manager">
      <div className="panel-header">
        <h2>Dataset Manager</h2>
      </div>

      <div {...getRootProps()} className={`dropzone ${isDragActive ? "dropzone-active" : ""}`}>
        <input {...getInputProps()} />
        <p>{uploading ? "Uploading..." : "Drag and drop climate files here or click to upload"}</p>
        <small>Supported: CSV, XLSX, NetCDF, GRIB, GeoTIFF</small>
      </div>

      <form className="github-import-form" onSubmit={(event) => void handleGithubImport(event)}>
        <label>
          <span>GitHub file URL</span>
          <input
            type="url"
            value={githubUrl}
            disabled={ingesting}
            placeholder="https://github.com/owner/repo/blob/main/data.csv"
            onChange={(event) => setGithubUrl(event.target.value)}
          />
        </label>
        <button
          type="submit"
          className="secondary-btn"
          disabled={ingesting || githubUrl.trim().length === 0}
        >
          {importingFromGithub ? "Importing..." : "Import from GitHub"}
        </button>
      </form>

      <div className="dataset-list">
        {datasets.length === 0 ? <p className="muted">No datasets uploaded yet.</p> : null}
        {datasets.map((dataset) => (
          <button
            key={dataset.dataset_id}
            type="button"
            className={`dataset-item ${dataset.dataset_id === selectedDatasetId ? "dataset-item-active" : ""}`}
            onClick={() => onSelectDataset(dataset.dataset_id)}
          >
            <span>{dataset.name}</span>
            <small>
              {dataset.source_format.toUpperCase()} | {dataset.row_count.toLocaleString()} rows
            </small>
          </button>
        ))}
      </div>

      {selected ? (
        <div className="dataset-details">
          <h3>Selected Dataset</h3>
          <p>
            <strong>Name:</strong> {selected.name}
          </p>
          <p>
            <strong>Format:</strong> {selected.source_format}
          </p>
          <p>
            <strong>Rows:</strong> {selected.row_count.toLocaleString()}
          </p>
        </div>
      ) : null}
    </section>
  );
}
