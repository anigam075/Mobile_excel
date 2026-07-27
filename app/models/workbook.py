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

    def get_range(self, start_row, end_row, start_column, end_column):
        values = {}
        for row_index in range(max(0, start_row), min(end_row, len(self.rows))):
            row = self.rows[row_index]
            for column_index in range(max(0, start_column), min(end_column, len(row))):
                value = row[column_index]
                if value:
                    values[(row_index, column_index)] = value
        return values

    def iter_rows(self):
        width = self.column_count
        for row in self.rows:
            yield row + [""] * (width - len(row))

    def set_cell(self, row_index, column_index, value):
        self.ensure_cell(row_index, column_index)
        self.rows[row_index][column_index] = "" if value is None else str(value)

    def add_row(self):
        self.rows.append([""] * self.column_count)

    def insert_row_after(self, row_index):
        insert_at = min(max(row_index + 1, 0), len(self.rows))
        self.rows.insert(insert_at, [""] * self.column_count)

    def add_cell_below(self, row_index, column_index):
        self._ensure_column(column_index)
        if row_index >= len(self.rows):
            self.ensure_cell(row_index, column_index)
        self.rows.append([""] * self.column_count)
        insert_at = min(row_index + 1, len(self.rows) - 1)
        for index in range(len(self.rows) - 1, insert_at, -1):
            self.rows[index][column_index] = self.rows[index - 1][column_index]
        self.rows[insert_at][column_index] = ""

    def delete_cell(self, row_index, column_index):
        self._ensure_column(column_index)
        if row_index >= len(self.rows):
            return
        for index in range(row_index, len(self.rows) - 1):
            self.rows[index][column_index] = self.rows[index + 1][column_index]
        self.rows[-1][column_index] = ""

    def delete_row(self, row_index):
        if 0 <= row_index < len(self.rows):
            del self.rows[row_index]
        if not self.rows:
            self.rows.append([""])

    def _ensure_column(self, column_index):
        if not self.rows:
            self.rows.append([])
        for row_index in range(len(self.rows)):
            self.ensure_cell(row_index, column_index)


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

    def insert_row_after(self, row_index):
        self.active_sheet.insert_row_after(row_index)
        self.dirty = True

    def add_cell_below(self, row_index, column_index):
        self.active_sheet.add_cell_below(row_index, column_index)
        self.dirty = True

    def delete_cell(self, row_index, column_index):
        self.active_sheet.delete_cell(row_index, column_index)
        self.dirty = True

    def delete_row(self, row_index):
        self.active_sheet.delete_row(row_index)
        self.dirty = True
