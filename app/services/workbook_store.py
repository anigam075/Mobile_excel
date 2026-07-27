import sqlite3
import threading
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4


@dataclass
class StoredSheet:
    store: "WorkbookStore"
    sheet_id: int
    name: str
    _row_count: int = 1
    _column_count: int = 1

    @property
    def row_count(self):
        return max(self._row_count, 1)

    @property
    def column_count(self):
        return max(self._column_count, 1)

    def get_cell(self, row_index, column_index):
        return self.store.get_cell(self.sheet_id, row_index, column_index)

    def get_range(self, start_row, end_row, start_column, end_column):
        return self.store.get_range(
            self.sheet_id,
            start_row,
            end_row,
            start_column,
            end_column,
        )

    def set_cell(self, row_index, column_index, value):
        self.store.set_cell(self.sheet_id, row_index, column_index, value)
        self._row_count = max(self._row_count, row_index + 1)
        self._column_count = max(self._column_count, column_index + 1)

    def insert_row_after(self, row_index):
        self.store.insert_row(self.sheet_id, row_index + 1, self.row_count)
        self._row_count += 1

    def add_row(self):
        self.insert_row_after(self.row_count - 1)

    def add_cell_below(self, row_index, column_index):
        self.store.insert_cell_down(
            self.sheet_id,
            row_index + 1,
            column_index,
            self.row_count,
        )
        self._row_count += 1
        self._column_count = max(self._column_count, column_index + 1)

    def delete_cell(self, row_index, column_index):
        self.store.delete_cell_up(
            self.sheet_id,
            row_index,
            column_index,
            self.row_count,
        )

    def delete_row(self, row_index):
        self.store.delete_row(self.sheet_id, row_index, self.row_count)
        self._row_count = max(1, self._row_count - 1)

    def iter_rows(self):
        return self.store.iter_rows(self.sheet_id, self.row_count, self.column_count)

    def normalized_rows(self):
        return list(self.iter_rows())


class StoredWorkbook:
    def __init__(self, store, sheets, file_type="csv", path=None):
        self.store = store
        self.sheets = sheets
        self.file_type = file_type
        self.path = path
        self.active_sheet_index = 0
        self.dirty = False

    @property
    def display_name(self):
        return Path(self.path).name if self.path else "Untitled.csv"

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

    def insert_row_after(self, row_index):
        self.active_sheet.insert_row_after(row_index)
        self.dirty = True

    def add_row(self):
        self.active_sheet.add_row()
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

    def close(self, remove=False):
        self.store.close(remove=remove)


class WorkbookStore:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._connection = sqlite3.connect(str(self.path), check_same_thread=False)
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.execute("PRAGMA synchronous=NORMAL")
        self._connection.execute("PRAGMA temp_store=MEMORY")
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS sheets (
                id INTEGER PRIMARY KEY,
                position INTEGER NOT NULL,
                name TEXT NOT NULL,
                row_count INTEGER NOT NULL,
                column_count INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS cells (
                sheet_id INTEGER NOT NULL,
                row_index INTEGER NOT NULL,
                column_index INTEGER NOT NULL,
                value TEXT NOT NULL,
                PRIMARY KEY (sheet_id, row_index, column_index)
            ) WITHOUT ROWID;
            """
        )

    @classmethod
    def create(cls, root):
        stores_dir = Path(root) / "workbooks"
        return cls(stores_dir / f"workbook_{uuid4().hex}.sqlite3")

    def add_sheet(self, name, position):
        with self._lock, self._connection:
            cursor = self._connection.execute(
                "INSERT INTO sheets(position, name, row_count, column_count) VALUES (?, ?, 1, 1)",
                (position, name),
            )
        return cursor.lastrowid

    def append_rows(self, sheet_id, rows, start_row):
        cells = []
        max_width = 1
        for row_offset, row in enumerate(rows):
            max_width = max(max_width, len(row))
            for column_index, value in enumerate(row):
                text = "" if value is None else str(value)
                if text:
                    cells.append((sheet_id, start_row + row_offset, column_index, text))

        row_count = max(1, start_row + len(rows))
        with self._lock, self._connection:
            if cells:
                self._connection.executemany(
                    "INSERT OR REPLACE INTO cells(sheet_id, row_index, column_index, value) "
                    "VALUES (?, ?, ?, ?)",
                    cells,
                )
            self._connection.execute(
                "UPDATE sheets SET row_count = MAX(row_count, ?), "
                "column_count = MAX(column_count, ?) WHERE id = ?",
                (row_count, max_width, sheet_id),
            )

    def sheet_metadata(self):
        with self._lock:
            rows = self._connection.execute(
                "SELECT id, name, row_count, column_count FROM sheets ORDER BY position"
            ).fetchall()
        return [
            StoredSheet(self, sheet_id, name, row_count, column_count)
            for sheet_id, name, row_count, column_count in rows
        ]

    def get_cell(self, sheet_id, row_index, column_index):
        with self._lock:
            row = self._connection.execute(
                "SELECT value FROM cells WHERE sheet_id = ? AND row_index = ? AND column_index = ?",
                (sheet_id, row_index, column_index),
            ).fetchone()
        return row[0] if row else ""

    def get_range(self, sheet_id, start_row, end_row, start_column, end_column):
        if end_row <= start_row or end_column <= start_column:
            return {}
        with self._lock:
            rows = self._connection.execute(
                "SELECT row_index, column_index, value FROM cells "
                "WHERE sheet_id = ? AND row_index >= ? AND row_index < ? "
                "AND column_index >= ? AND column_index < ?",
                (sheet_id, start_row, end_row, start_column, end_column),
            ).fetchall()
        return {(row_index, column_index): value for row_index, column_index, value in rows}

    def set_cell(self, sheet_id, row_index, column_index, value):
        text = "" if value is None else str(value)
        with self._lock, self._connection:
            if text:
                self._connection.execute(
                    "INSERT OR REPLACE INTO cells(sheet_id, row_index, column_index, value) "
                    "VALUES (?, ?, ?, ?)",
                    (sheet_id, row_index, column_index, text),
                )
            else:
                self._connection.execute(
                    "DELETE FROM cells WHERE sheet_id = ? AND row_index = ? AND column_index = ?",
                    (sheet_id, row_index, column_index),
                )
            self._connection.execute(
                "UPDATE sheets SET row_count = MAX(row_count, ?), "
                "column_count = MAX(column_count, ?) WHERE id = ?",
                (row_index + 1, column_index + 1, sheet_id),
            )

    def insert_row(self, sheet_id, insert_at, row_count):
        insert_at = min(max(insert_at, 0), row_count)
        with self._lock, self._connection:
            self._shift_rows(sheet_id, "row_index >= ?", (insert_at,), 1, row_count)
            self._connection.execute(
                "UPDATE sheets SET row_count = ? WHERE id = ?",
                (row_count + 1, sheet_id),
            )

    def delete_row(self, sheet_id, row_index, row_count):
        if row_index < 0 or row_index >= row_count:
            return
        with self._lock, self._connection:
            self._connection.execute(
                "DELETE FROM cells WHERE sheet_id = ? AND row_index = ?",
                (sheet_id, row_index),
            )
            self._shift_rows(
                sheet_id,
                "row_index > ?",
                (row_index,),
                -1,
                row_count,
            )
            self._connection.execute(
                "UPDATE sheets SET row_count = ? WHERE id = ?",
                (max(1, row_count - 1), sheet_id),
            )

    def insert_cell_down(self, sheet_id, insert_at, column_index, row_count):
        insert_at = min(max(insert_at, 0), row_count)
        with self._lock, self._connection:
            self._shift_rows(
                sheet_id,
                "column_index = ? AND row_index >= ?",
                (column_index, insert_at),
                1,
                row_count,
            )
            self._connection.execute(
                "UPDATE sheets SET row_count = ?, column_count = MAX(column_count, ?) WHERE id = ?",
                (row_count + 1, column_index + 1, sheet_id),
            )

    def delete_cell_up(self, sheet_id, row_index, column_index, row_count):
        if row_index < 0 or row_index >= row_count:
            return
        with self._lock, self._connection:
            self._connection.execute(
                "DELETE FROM cells WHERE sheet_id = ? AND row_index = ? AND column_index = ?",
                (sheet_id, row_index, column_index),
            )
            self._shift_rows(
                sheet_id,
                "column_index = ? AND row_index > ?",
                (column_index, row_index),
                -1,
                row_count,
            )

    def _shift_rows(self, sheet_id, condition, parameters, delta, row_count):
        offset = row_count + 2
        first_shift = offset if delta > 0 else offset
        second_shift = offset - delta
        self._connection.execute(
            f"UPDATE cells SET row_index = row_index + ? WHERE sheet_id = ? AND {condition}",
            (first_shift, sheet_id, *parameters),
        )
        shifted_condition = condition.replace("row_index", f"(row_index - {first_shift})")
        self._connection.execute(
            f"UPDATE cells SET row_index = row_index - ? WHERE sheet_id = ? AND {shifted_condition}",
            (second_shift, sheet_id, *parameters),
        )

    def iter_rows(self, sheet_id, row_count, column_count, fetch_size=2048):
        with self._lock:
            cursor = self._connection.execute(
                "SELECT row_index, column_index, value FROM cells "
                "WHERE sheet_id = ? ORDER BY row_index, column_index",
                (sheet_id,),
            )

        current_row = 0
        row_values = [""] * column_count
        while True:
            with self._lock:
                batch = cursor.fetchmany(fetch_size)
            if not batch:
                break
            for row_index, column_index, value in batch:
                while current_row < row_index:
                    yield row_values
                    current_row += 1
                    row_values = [""] * column_count
                if column_index < column_count:
                    row_values[column_index] = value

        while current_row < row_count:
            yield row_values
            current_row += 1
            row_values = [""] * column_count

    def close(self, remove=False):
        with self._lock:
            if self._connection is not None:
                self._connection.close()
                self._connection = None
        if remove:
            for candidate in (self.path, Path(f"{self.path}-wal"), Path(f"{self.path}-shm")):
                try:
                    candidate.unlink(missing_ok=True)
                except OSError:
                    pass
