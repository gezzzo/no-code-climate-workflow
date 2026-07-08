from __future__ import annotations

from io import BytesIO
from typing import Any

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


class ExportService:
    def analysis_to_csv(self, analysis_type: str, result: dict[str, Any]) -> bytes:
        frame = self._result_to_dataframe(result)
        if frame.empty:
            frame = pd.DataFrame([{"analysis_type": analysis_type, "result": str(result)}])
        return frame.to_csv(index=False).encode("utf-8")

    def analysis_to_pdf(
        self,
        dataset_name: str,
        analysis_type: str,
        result: dict[str, Any],
    ) -> bytes:
        buffer = BytesIO()
        document = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = [
            Paragraph("Climate Data Analysis Report", styles["Title"]),
            Spacer(1, 10),
            Paragraph(f"Dataset: {dataset_name}", styles["Normal"]),
            Paragraph(f"Analysis: {analysis_type}", styles["Normal"]),
            Spacer(1, 14),
        ]

        frame = self._result_to_dataframe(result)
        if frame.empty:
            story.append(Paragraph(str(result), styles["Code"]))
        else:
            max_rows = min(30, len(frame))
            sliced = frame.head(max_rows)
            table_data = [list(sliced.columns)] + sliced.astype(str).values.tolist()
            table = Table(table_data, repeatRows=1)
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111827")),
                        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#9ca3af")),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
                    ]
                )
            )
            story.append(table)
            if len(frame) > max_rows:
                story.append(Spacer(1, 10))
                story.append(
                    Paragraph(
                        f"Showing first {max_rows} rows out of {len(frame)} rows in analysis output.",
                        styles["Italic"],
                    )
                )

        document.build(story)
        return buffer.getvalue()

    @staticmethod
    def _result_to_dataframe(result: dict[str, Any]) -> pd.DataFrame:
        for key in ("summary", "monthly_pattern", "seasonal_pattern", "anomalies", "forecast"):
            value = result.get(key)
            if isinstance(value, list) and value and isinstance(value[0], dict):
                return pd.DataFrame(value)

        if "matrix" in result and isinstance(result["matrix"], dict):
            matrix = result["matrix"]
            return pd.DataFrame(matrix).reset_index().rename(columns={"index": "column"})

        return pd.json_normalize(result, sep=".")


export_service = ExportService()
