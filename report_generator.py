import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from db import get_report_history
from src.config import settings


def generate_pdf(filename: str, report_data: list, out_path: str):
    doc = SimpleDocTemplate(out_path)
    styles = getSampleStyleSheet()
    story = [Paragraph(f"📄 Отчёт: {filename}", styles["Title"]), Spacer(1, 12)]

    for item in report_data:
        story.append(Paragraph(f"🔹 Раздел: {item['section']}", styles["Heading2"]))
        story.append(Paragraph(f"✔ Соответствие: {item['match']}", styles["Normal"]))
        story.append(Paragraph(f"💬 Комментарий: {item['comments']}", styles["Normal"]))
        story.append(Spacer(1, 12))

    doc.build(story)


def export_audit_history(
    export_format: str,
    filters: Optional[dict[str, Any]] = None,
    out_dir: Optional[Path] = None,
) -> str:
    """Экспортирует историю отчетов (audit history) в указанный формат.

    Args:
        export_format: Формат экспорта: 'txt' или 'json'.
        filters: Словарь фильтров: start_date, end_date, doc_type, user_id, limit, offset.
        out_dir: Директория вывода; по умолчанию settings.reports_dir.

    Returns:
        Путь к созданному файлу.
    """
    fmt = export_format.lower()
    if fmt not in {"txt", "json"}:
        raise ValueError("Unsupported export format. Use 'txt' or 'json'.")

    f = filters or {}
    start_date = f.get("start_date")
    end_date = f.get("end_date")
    doc_type = f.get("doc_type")
    user_id = f.get("user_id")
    limit = int(f.get("limit", 10000))
    offset = int(f.get("offset", 0))

    # Получаем историю с учетом фильтров
    history, total = get_report_history(
        start_date=start_date,
        end_date=end_date,
        doc_type=doc_type,
        user_id=user_id,
        limit=limit,
        offset=offset,
    )

    # Определяем выходную директорию и имя файла
    out_path = Path(out_dir) if out_dir else settings.reports_dir
    out_path.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"audit_history_{timestamp}.{fmt}"
    full_path = out_path / filename

    if fmt == "json":
        with open(full_path, "w", encoding="utf-8") as f_out:
            json.dump(
                {
                    "exported_at": datetime.now().isoformat(),
                    "total": total,
                    "items": history,
                },
                f_out,
                ensure_ascii=False,
                indent=2,
            )
    else:
        # Человекочитаемый TXT отчет
        lines: list[str] = []
        lines.append(f"Exported at: {datetime.now().isoformat()}")
        lines.append(f"Total items: {total}")
        lines.append("")
        for item in history:
            lines.append(f"ID: {item.get('id')}")
            lines.append(f"Filename: {item.get('filename')}")
            lines.append(f"Checked at: {item.get('checked_at')}")
            lines.append(f"Created at: {item.get('created_at')}")
            lines.append(f"User ID: {item.get('user_id')}")
            lines.append(f"Doc Type: {item.get('doc_type')}")
            # Краткое резюме результатов
            results = item.get("result") or []
            lines.append(f"Results count: {len(results)}")
            lines.append("-")
        content = "\n".join(lines)
        with open(full_path, "w", encoding="utf-8") as f_out:
            f_out.write(content)

    return str(full_path)
