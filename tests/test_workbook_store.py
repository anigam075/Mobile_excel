import tempfile
import unittest

from app.services.workbook_store import StoredWorkbook, WorkbookStore


class WorkbookStoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.store = WorkbookStore.create(self.temporary_directory.name)
        sheet_id = self.store.add_sheet("Data", 0)
        self.store.append_rows(sheet_id, [["A", "B"], ["1", "2"], ["3", "4"]], 0)
        self.workbook = StoredWorkbook(
            self.store,
            self.store.sheet_metadata(),
            file_type="csv",
        )

    def tearDown(self):
        self.workbook.close(remove=True)
        self.temporary_directory.cleanup()

    def test_reads_only_requested_range(self):
        values = self.workbook.active_sheet.get_range(1, 3, 0, 1)

        self.assertEqual(values, {(1, 0): "1", (2, 0): "3"})

    def test_selected_row_and_cell_operations_match_workbook_behavior(self):
        self.workbook.insert_row_after(0)
        self.assertEqual(self.workbook.active_sheet.get_cell(1, 0), "")
        self.assertEqual(self.workbook.active_sheet.get_cell(2, 0), "1")

        self.workbook.add_cell_below(1, 0)
        self.assertEqual(self.workbook.active_sheet.get_cell(2, 0), "")
        self.assertEqual(self.workbook.active_sheet.get_cell(3, 0), "1")

        self.workbook.delete_cell(2, 0)
        self.assertEqual(self.workbook.active_sheet.get_cell(2, 0), "1")
        self.assertEqual(self.workbook.active_sheet.get_cell(3, 0), "3")

        self.workbook.delete_row(2)
        self.assertEqual(self.workbook.active_sheet.get_cell(2, 0), "3")

    def test_iter_rows_preserves_blank_rows_and_width(self):
        self.workbook.insert_row_after(0)

        self.assertEqual(
            list(self.workbook.active_sheet.iter_rows()),
            [["A", "B"], ["", ""], ["1", "2"], ["3", "4"]],
        )


if __name__ == "__main__":
    unittest.main()
