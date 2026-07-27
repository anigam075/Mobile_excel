import os
import unittest

os.environ.setdefault("KIVY_NO_FILELOG", "1")

from kivy.uix.scrollview import ScrollView

from app.widgets.virtual_spreadsheet import VirtualSpreadsheet
from app.widgets.virtual_spreadsheet import calculate_visible_range


class RecordingSheet:
    row_count = 5000
    column_count = 200

    def __init__(self):
        self.requested_range = None

    def get_range(self, start_row, end_row, start_column, end_column):
        self.requested_range = (start_row, end_row, start_column, end_column)
        return {}


class VirtualSpreadsheetRangeTests(unittest.TestCase):
    def test_widget_draws_only_a_bounded_viewport(self):
        sheet = RecordingSheet()
        scroll = ScrollView(size=(400, 640))
        spreadsheet = VirtualSpreadsheet()
        scroll.add_widget(spreadsheet)
        spreadsheet.attach_scroll_view(scroll)
        spreadsheet.set_metrics(100, 50, 40, 14)
        spreadsheet.set_sheet(sheet, reset_scroll=True)

        spreadsheet._redraw()

        start_row, end_row, start_column, end_column = sheet.requested_range
        self.assertLessEqual(end_row - start_row, 18)
        self.assertLessEqual(end_column - start_column, 6)
        self.assertLess(len(spreadsheet.canvas.children), 1000)

    def test_large_sheet_only_requests_top_left_viewport(self):
        visible = calculate_visible_range(
            row_count=5000,
            column_count=200,
            cell_width=100,
            row_header_width=50,
            cell_height=40,
            content_width=20050,
            content_height=200040,
            viewport_width=400,
            viewport_height=640,
            scroll_x=0,
            scroll_y=1,
        )

        start_row, end_row, start_column, end_column, _, _ = visible
        self.assertEqual(start_row, 0)
        self.assertEqual(start_column, 0)
        self.assertLessEqual(end_row - start_row, 18)
        self.assertLessEqual(end_column - start_column, 6)

    def test_bottom_right_viewport_stays_inside_sheet(self):
        visible = calculate_visible_range(
            row_count=5000,
            column_count=200,
            cell_width=100,
            row_header_width=50,
            cell_height=40,
            content_width=20050,
            content_height=200040,
            viewport_width=400,
            viewport_height=640,
            scroll_x=1,
            scroll_y=0,
        )

        start_row, end_row, start_column, end_column, _, _ = visible
        self.assertGreater(start_row, 4980)
        self.assertEqual(end_row, 5000)
        self.assertGreater(start_column, 190)
        self.assertEqual(end_column, 200)


if __name__ == "__main__":
    unittest.main()
