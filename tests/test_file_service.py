import tempfile
import unittest
from pathlib import Path

from app.models.workbook import Sheet, Workbook, column_name
from app.services.file_service import load_workbook, save_workbook


class WorkbookTests(unittest.TestCase):
    def test_column_name(self):
        self.assertEqual(column_name(0), "A")
        self.assertEqual(column_name(25), "Z")
        self.assertEqual(column_name(26), "AA")

    def test_csv_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.csv"
            workbook = Workbook(
                sheets=[Sheet(name="Sheet1", rows=[["Metric", "Amount"], ["", ""]])],
                file_type="csv",
            )
            workbook.set_cell(1, 0, "Revenue")
            workbook.set_cell(1, 1, "1200")

            save_workbook(workbook, path)
            loaded = load_workbook(path)

            self.assertEqual(loaded.active_sheet.get_cell(1, 0), "Revenue")
            self.assertEqual(loaded.active_sheet.get_cell(1, 1), "1200")

    def test_xlsx_round_trip(self):
        try:
            import openpyxl  # noqa: F401
        except ImportError:
            self.skipTest("openpyxl is not installed")

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.xlsx"
            workbook = Workbook(
                sheets=[Sheet(name="Data", rows=[["Metric", "Amount"], ["", ""]])],
                file_type="xlsx",
            )
            workbook.set_cell(1, 0, "Cost")
            workbook.set_cell(1, 1, "900")

            save_workbook(workbook, path)
            loaded = load_workbook(path)

            self.assertEqual(loaded.sheets[0].name, "Data")
            self.assertEqual(loaded.active_sheet.get_cell(1, 0), "Cost")
            self.assertEqual(loaded.active_sheet.get_cell(1, 1), "900")


if __name__ == "__main__":
    unittest.main()
