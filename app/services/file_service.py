import csv
from pathlib import Path

from app.models.workbook import Sheet, Workbook


class FileServiceError(Exception):
    pass


SUPPORTED_EXTENSIONS = {".csv", ".xlsx"}


def load_workbook(path):
    file_path = Path(path)
    if not file_path.exists():
        raise FileServiceError("File does not exist.")

    suffix = file_path.suffix.lower()
    if suffix == ".csv":
        return _load_csv(file_path)
    if suffix == ".xlsx":
        return _load_xlsx(file_path)
    raise FileServiceError("Only .csv and .xlsx files are supported.")


def save_workbook(workbook, path):
    file_path = Path(path)
    suffix = file_path.suffix.lower()
    if suffix == ".csv":
        _save_csv(workbook, file_path)
        return
    if suffix == ".xlsx":
        _save_xlsx(workbook, file_path)
        return
    raise FileServiceError("Save path must end with .csv or .xlsx.")


def _load_csv(file_path):
    try:
        with file_path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = [[cell for cell in row] for row in csv.reader(handle)]
    except UnicodeDecodeError:
        with file_path.open("r", encoding="latin-1", newline="") as handle:
            rows = [[cell for cell in row] for row in csv.reader(handle)]
    except OSError as exc:
        raise FileServiceError(f"Could not read CSV file: {exc}") from exc

    if not rows:
        rows = [[""]]
    return Workbook(
        sheets=[Sheet(name=file_path.stem or "Sheet1", rows=rows)],
        file_type="csv",
        path=str(file_path),
    )


def _save_csv(workbook, file_path):
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with file_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerows(workbook.active_sheet.normalized_rows())
    except OSError as exc:
        raise FileServiceError(f"Could not save CSV file: {exc}") from exc


def _load_xlsx(file_path):
    try:
        from openpyxl import load_workbook as openpyxl_load_workbook
    except ImportError as exc:
        raise FileServiceError("openpyxl is required to open .xlsx files.") from exc

    try:
        source = openpyxl_load_workbook(file_path)
    except Exception as exc:
        raise FileServiceError(f"Could not read Excel file: {exc}") from exc

    sheets = []
    for worksheet in source.worksheets:
        rows = []
        for row in worksheet.iter_rows(values_only=True):
            rows.append(["" if value is None else str(value) for value in row])
        if not rows:
            rows = [[""]]
        sheets.append(Sheet(name=worksheet.title, rows=rows))

    if not sheets:
        sheets = [Sheet(name="Sheet1", rows=[[""]])]

    return Workbook(sheets=sheets, file_type="xlsx", path=str(file_path))


def _save_xlsx(workbook, file_path):
    try:
        from openpyxl import Workbook as OpenpyxlWorkbook
    except ImportError as exc:
        raise FileServiceError("openpyxl is required to save .xlsx files.") from exc

    target = OpenpyxlWorkbook()
    default = target.active
    target.remove(default)

    for sheet in workbook.sheets:
        worksheet = target.create_sheet(title=sheet.name[:31] or "Sheet")
        for row_index, row in enumerate(sheet.normalized_rows(), start=1):
            for column_index, value in enumerate(row, start=1):
                worksheet.cell(row=row_index, column=column_index, value=value)

    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        target.save(file_path)
    except OSError as exc:
        raise FileServiceError(f"Could not save Excel file: {exc}") from exc
