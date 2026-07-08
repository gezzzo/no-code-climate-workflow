import { DatasetPreview } from "../types";

interface Props {
  preview: DatasetPreview | null;
}

export function DataExplorer({ preview }: Props) {
  const derivedColumns = preview?.derived_columns ?? [];

  return (
    <section className="panel data-explorer">
      <div className="panel-header">
        <h2>Data Explorer</h2>
      </div>

      {!preview ? (
        <p className="muted">Upload and select a dataset to preview rows and inferred columns.</p>
      ) : (
        <>
          <p className="meta">Previewing first {preview.rows.length} rows of {preview.row_count.toLocaleString()}</p>
          {derivedColumns.length > 0 ? (
            <p className="meta">
              Derived variables: <strong>{derivedColumns.join(", ")}</strong>
            </p>
          ) : null}
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  {preview.columns.map((column) => (
                    <th
                      key={column}
                      className={derivedColumns.includes(column) ? "derived-column-cell" : undefined}
                    >
                      {column}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {preview.rows.map((row, idx) => (
                  <tr key={idx}>
                    {preview.columns.map((column) => (
                      <td
                        key={`${idx}-${column}`}
                        className={derivedColumns.includes(column) ? "derived-column-cell" : undefined}
                      >
                        {formatCell(row[column])}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  );
}

function formatCell(value: unknown): string {
  if (value === null || value === undefined) {
    return "";
  }
  if (typeof value === "object") {
    return JSON.stringify(value);
  }
  return String(value);
}
