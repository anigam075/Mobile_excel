import os
import unittest

os.environ.setdefault("KIVY_NO_FILELOG", "1")

from kivy.metrics import dp
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget

from app.widgets.fast_scroller import FastScroller
from app.widgets.fast_scroller import calculate_thumb_geometry
from app.widgets.fast_scroller import clamp_scroll_value
from app.widgets.virtual_spreadsheet import VirtualSpreadsheet
from app.widgets.virtual_spreadsheet import calculate_visible_range


class RecordingSheet:
    row_count = 5000
    column_count = 200

    def __init__(self):
        self.requested_range = None
        self.requested_ranges = []

    def get_range(self, start_row, end_row, start_column, end_column):
        self.requested_range = (start_row, end_row, start_column, end_column)
        self.requested_ranges.append(self.requested_range)
        return {}


class FakeTouch:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.grab_current = None

    @property
    def pos(self):
        return self.x, self.y

    def grab(self, widget):
        self.grab_current = widget

    def ungrab(self, widget):
        if self.grab_current is widget:
            self.grab_current = None


class VirtualSpreadsheetRangeTests(unittest.TestCase):
    def test_fast_scroller_thumb_is_bounded_and_scales_with_content(self):
        thumb_length, travel = calculate_thumb_geometry(600, 600, 6000, 52)

        self.assertEqual(thumb_length, 60)
        self.assertEqual(travel, 540)
        self.assertEqual(calculate_thumb_geometry(600, 600, 500, 52), (0, 0))
        self.assertEqual(clamp_scroll_value(-1), 0)
        self.assertEqual(clamp_scroll_value(2), 1)

    def test_vertical_fast_scroller_drag_reaches_bottom(self):
        scroll = ScrollView(size=(400, 600), scroll_y=1)
        content = Widget(size_hint=(None, None), size=(1000, 6000))
        scroll.add_widget(content)
        scroller = FastScroller(
            scroll,
            content,
            orientation="vertical",
            pos=(0, 0),
            size=(30, 600),
        )
        scroller._update_geometry()
        touch = FakeTouch(25, scroller._thumb_position + scroller._thumb_length / 2)

        self.assertTrue(scroller.on_touch_down(touch))
        touch.y = dp(7) + scroller._thumb_length / 2
        self.assertTrue(scroller.on_touch_move(touch))
        self.assertEqual(scroll.scroll_y, 0)
        self.assertTrue(scroller.on_touch_up(touch))
        self.assertFalse(scroller.active)

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

    def test_frozen_top_row_is_queried_and_receives_touches_after_scroll(self):
        sheet = RecordingSheet()
        scroll = ScrollView(size=(400, 640))
        spreadsheet = VirtualSpreadsheet()
        scroll.add_widget(spreadsheet)
        spreadsheet.attach_scroll_view(scroll)
        spreadsheet.set_metrics(100, 50, 40, 14)
        spreadsheet.set_sheet(sheet)
        spreadsheet.set_freeze_top_row(True)
        scroll.scroll_y = 0

        spreadsheet._redraw()

        self.assertTrue(any(request[0:2] == (0, 1) for request in sheet.requested_ranges))
        _, _, _, _, visible_left, visible_top = spreadsheet.visible_range()
        selected = spreadsheet.cell_at_local_position(
            visible_left + spreadsheet.row_header_width + 10,
            visible_top + spreadsheet.cell_height + 10,
        )
        self.assertEqual(selected, (0, 0))

    def test_selected_cell_can_be_aligned_below_frozen_headers(self):
        sheet = RecordingSheet()
        scroll = ScrollView(size=(400, 640))
        spreadsheet = VirtualSpreadsheet()
        scroll.add_widget(spreadsheet)
        spreadsheet.attach_scroll_view(scroll)
        spreadsheet.set_metrics(100, 50, 40, 14)
        spreadsheet.set_sheet(sheet)
        spreadsheet.set_freeze_top_row(True)
        scroll.scroll_y = 0

        spreadsheet.ensure_cell_visible(2500, 5, align_top=True)

        _, _, _, _, _, visible_top = spreadsheet.visible_range()
        selected_cell_top = (2500 + 1) * spreadsheet.cell_height
        self.assertAlmostEqual(
            selected_cell_top - visible_top,
            spreadsheet.cell_height * 2,
            delta=1,
        )


if __name__ == "__main__":
    unittest.main()
