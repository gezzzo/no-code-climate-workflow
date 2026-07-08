import {
  AnalysisRequest,
  AnalysisResponse,
  DatasetMetadata,
  DatasetPreview,
  DatasetSummary,
  MappingUpdateRequest,
  TemporalAggregationRequest,
  TransformationCreateRequest,
  TransformationsResponse,
  VisualizationRequest,
  VisualizationResponse,
} from "../types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `API request failed (${response.status})`);
  }
  return (await response.json()) as T;
}

export const api = {
  async health(): Promise<{ status: string }> {
    return request<{ status: string }>("/health");
  },

  async uploadDataset(file: File): Promise<DatasetMetadata> {
    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch(`${API_BASE_URL}/datasets/upload`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const detail = await response.text();
      throw new Error(detail || `Upload failed (${response.status})`);
    }

    return (await response.json()) as DatasetMetadata;
  },

  async importDatasetFromGithub(url: string): Promise<DatasetMetadata> {
    return request<DatasetMetadata>("/datasets/github-import", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ url }),
    });
  },

  async listDatasets(): Promise<DatasetSummary[]> {
    return request<DatasetSummary[]>("/datasets");
  },

  async getMetadata(datasetId: string): Promise<DatasetMetadata> {
    return request<DatasetMetadata>(`/datasets/${datasetId}`);
  },

  async getPreview(datasetId: string, limit = 100): Promise<DatasetPreview> {
    return request<DatasetPreview>(`/datasets/${datasetId}/preview?limit=${limit}`);
  },

  async updateMapping(datasetId: string, payload: MappingUpdateRequest): Promise<DatasetMetadata> {
    return request<DatasetMetadata>(`/datasets/${datasetId}/mapping`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
  },

  async getTransformations(datasetId: string): Promise<TransformationsResponse> {
    return request<TransformationsResponse>(`/datasets/${datasetId}/transformations`);
  },

  async createTransformation(
    datasetId: string,
    payload: TransformationCreateRequest,
  ): Promise<DatasetMetadata> {
    return request<DatasetMetadata>(`/datasets/${datasetId}/transformations`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
  },

  async deriveTemporalAggregation(
    datasetId: string,
    payload: TemporalAggregationRequest,
  ): Promise<DatasetMetadata> {
    return request<DatasetMetadata>(`/datasets/${datasetId}/derive/temporal-aggregation`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
  },

  async runAnalysis(datasetId: string, payload: AnalysisRequest): Promise<AnalysisResponse> {
    return request<AnalysisResponse>(`/datasets/${datasetId}/analysis`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
  },

  async buildVisualization(
    datasetId: string,
    payload: VisualizationRequest,
  ): Promise<VisualizationResponse> {
    return request<VisualizationResponse>(`/datasets/${datasetId}/visualize`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
  },

  async downloadDatasetCsv(datasetId: string): Promise<void> {
    await downloadFile(`${API_BASE_URL}/datasets/${datasetId}/export/dataset.csv`, `${datasetId}.csv`);
  },

  async downloadAnalysisCsv(datasetId: string, payload: AnalysisRequest): Promise<void> {
    await downloadFile(
      `${API_BASE_URL}/datasets/${datasetId}/analysis/export.csv`,
      `${datasetId}_${payload.analysis_type}.csv`,
      payload,
    );
  },

  async downloadAnalysisPdf(datasetId: string, payload: AnalysisRequest): Promise<void> {
    await downloadFile(
      `${API_BASE_URL}/datasets/${datasetId}/analysis/export.pdf`,
      `${datasetId}_${payload.analysis_type}.pdf`,
      payload,
    );
  },
};

async function downloadFile(url: string, filename: string, payload?: unknown): Promise<void> {
  const response = await fetch(url, {
    method: payload ? "POST" : "GET",
    headers: payload ? { "Content-Type": "application/json" } : undefined,
    body: payload ? JSON.stringify(payload) : undefined,
  });

  if (!response.ok) {
    throw new Error(`Download failed (${response.status})`);
  }

  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(objectUrl);
}
