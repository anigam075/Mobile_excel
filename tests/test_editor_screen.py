import os
import unittest

os.environ.setdefault("KIVY_NO_FILELOG", "1")

from app.models.workbook import Sheet, Workbook
from app.screens.editor_screen import EditorScreen


class EditorScreenTests(unittest.TestCase):
    def setUp(self):
        self.editor = EditorScreen(name="editor")

    def test_command_panel_is_above_the_spreadsheet(self):
        visual_order = list(reversed(self.editor.root_layout.children))

        self.assertLess(
            visual_order.index(self.editor.command_panel),
            visual_order.index(self.editor.spreadsheet_panel),
        )

    def test_spreadsheet_has_vertical_and_horizontal_fast_scrollers(self):
        self.assertIs(
            self.editor.vertical_fast_scroller.scroll_view,
            self.editor.spreadsheet_scroll,
        )
        self.assertEqual(self.editor.vertical_fast_scroller.orientation, "vertical")
        self.assertEqual(self.editor.horizontal_fast_scroller.orientation, "horizontal")
        self.assertEqual(self.editor.spreadsheet_scroll.bar_width, 0)

    def test_freeze_toggle_updates_active_sheet_without_dirtying_csv(self):
        workbook = Workbook(
            sheets=[Sheet(name="Data", rows=[["Heading"], ["Value"]])],
            file_type="csv",
        )
        self.editor.set_workbook(workbook)

        self.editor.freeze_button.state = "down"

        self.assertTrue(workbook.active_sheet.freeze_top_row)
        self.assertTrue(self.editor.spreadsheet.freeze_top_row)
        self.assertFalse(workbook.dirty)

    def test_freeze_toggle_marks_xlsx_dirty(self):
        workbook = Workbook(
            sheets=[Sheet(name="Data", rows=[["Heading"], ["Value"]])],
            file_type="xlsx",
        )
        self.editor.set_workbook(workbook)

        self.editor.freeze_button.state = "down"

        self.assertTrue(workbook.dirty)
        self.assertTrue(self.editor.title_label.text.endswith("*"))


if __name__ == "__main__":
    unittest.main()
