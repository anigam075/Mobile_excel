import csv
import tempfile
import threading
import unittest
from pathlib import Path

from app.models.workbook import Sheet, Workbook
from app.services.file_service import OperationCancelled, load_workbook, save_workbook
from app.services.workbook_store import StoredWorkbook


class LargeFileImportTests(unittest.TestCase):
    def test_cancelled_import_removes_partial_store(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "cancel.csv"
            source.write_text("A,B\n1,2\n", encoding="utf-8")
            cancelled = threading.Event()
            cancelled.set()

            with self.assertRaises(OperationCancelled):
                load_workbook(source, storage_dir=directory, cancel_event=cancelled)

            stores = Path(directory) / "workbooks"
            self.assertEqual(list(stores.glob("*.sqlite3")), [])

    def test_cancelled_save_keeps_existing_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "existing.csv"
            destination.write_text("original\n", encoding="utf-8")
            workbook = Workbook(sheets=[Sheet(name="Data", rows=[["replacement"]])])
            cancelled = threading.Event()
            cancelled.set()

            with self.assertRaises(OperationCancelled):
                save_workbook(workbook, destination, cancel_event=cancelled)

            self.assertEqual(destination.read_text(encoding="utf-8"), "original\n")
            self.assertEqual(list(Path(directory).glob("*.tmp.csv")), [])

    def test_large_csv_uses_disk_backed_ranges(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "large.csv"
            with source.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                for row_index in range(1000):
                    writer.writerow([f"R{row_index}C{column}" for column in range(50)])

            workbook = load_workbook(source, storage_dir=directory)
            try:
                self.assertIsInstance(workbook, StoredWorkbook)
                self.assertEqual(workbook.active_sheet.row_count, 1000)
                self.assertEqual(workbook.active_sheet.column_count, 50)
                self.assertEqual(
                    workbook.active_sheet.get_range(998, 1000, 48, 50),
                    {
                        (998, 48): "R998C48",
                        (998, 49): "R998C49",
                        (999, 48): "R999C48",
                        (999, 49): "R999C49",
                    },
                )

                exported = Path(directory) / "exported.csv"
                save_workbook(workbook, exported)
                with exported.open("r", encoding="utf-8", newline="") as handle:
                    rows = csv.reader(handle)
                    first = next(rows)
                    for last in rows:
                        pass
                self.assertEqual(first[0], "R0C0")
                self.assertEqual(last[-1], "R999C49")
            finally:
                workbook.close(remove=True)


if __name__ == "__main__":
    unittest.main()
