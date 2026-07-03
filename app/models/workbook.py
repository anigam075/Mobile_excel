from dataclasses import dataclass, field
from pathlib import Path


def column_name(index):
    if index < 0:
        raise ValueError("Column index must be zero or greater.")

    name = ""
    number = index + 1
    while number:
        number, remainder = divmod(number - 1, 26)
        name = chr(65 + remainder) + name
    return name


@dataclass
class Sheet:
    name: str
    rows: list[list[str]] = field(default_factory=list)

    @property
    def row_count(self):
        return max(len(self.rows), 1)

    @property
    def column_count(self):
        max_width = max((len(row) for row in self.rows), default=0)
        return max(max_width, 1)

    def normalized_rows(self):
        width = self.column_count
        return [row + [""] * (width - len(row)) for row in self.rows]

    def ensure_cell(self, row_index, column_index):
        while len(self.rows) <= row_index:
            self.rows.append([])
        row = self.rows[row_index]
        while len(row) <= column_index:
            row.append("")

    def get_cell(self, row_index, column_index):
        if row_index >= len(self.rows):
            return ""
        row = self.rows[row_index]
        if column_index >= len(row):
            return ""
        return row[column_index]

    def set_cell(self, row_index, column_index, value):
        self.ensure_cell(row_index, column_index)
        self.rows[row_index][column_index] = "" if value is None else str(value)

    def add_row(self):
        self.rows.append([""] * self.column_count)

    def add_column(self):
        if not self.rows:
            self.rows.append([""])
            return
        for row in self.rows:
            row.append("")

    def clear_cell(self, row_index, column_index):
        self.set_cell(row_index, column_index, "")

    def delete_row(self, row_index):
        if 0 <= row_index < len(self.rows):
            del self.rows[row_index]
        if not self.rows:
            self.rows.append([""])


@dataclass
class Workbook:
    sheets: list[Sheet]
    file_type: str = "csv"
    path: str | None = None
    active_sheet_index: int = 0
    dirty: bool = False

    @property
    def display_name(self):
        if self.path:
            return Path(self.path).name
        return "Untitled.csv"

    @property
    def active_sheet(self):
        return self.sheets[self.active_sheet_index]

    def set_active_sheet(self, index):
        if index < 0 or index >= len(self.sheets):
            raise IndexError("Sheet index out of range.")
        self.active_sheet_index = index

    def set_cell(self, row_index, column_index, value):
        self.active_sheet.set_cell(row_index, column_index, value)
        self.dirty = True

    def add_row(self):
        self.active_sheet.add_row()
        self.dirty = True

    def add_column(self):
        self.active_sheet.add_column()
        self.dirty = True

    def clear_cell(self, row_index, column_index):
        self.active_sheet.clear_cell(row_index, column_index)
        self.dirty = True

    def delete_row(self, row_index):
        self.active_sheet.delete_row(row_index)
        self.dirty = True
