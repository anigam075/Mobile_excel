from pathlib import Path

from kivy.app import App
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp, sp
from kivy.utils import platform
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput

from app.models.workbook import column_name
from app.services.background_worker import run_in_background
from app.widgets.style import apply_rounded_button_style
from app.widgets.virtual_spreadsheet import VirtualSpreadsheet


class EditorScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.workbook = None
        self.selected = (0, 0)
        self._mutation_task = None
        self._save_in_progress = False
        self._last_metrics = None
        self._build()

    def _build(self):
        self.root_layout = BoxLayout(orientation="vertical", spacing=dp(4))
        self._paint_background(self.root_layout, (0.035, 0.045, 0.065, 1))

        self.header_panel = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=dp(6),
            padding=(dp(8), dp(8), dp(8), dp(6)),
        )
        self._paint_background(self.header_panel, (0.055, 0.075, 0.115, 1))

        self.title_row = BoxLayout(size_hint_y=None, spacing=dp(8))
        self.back_button = Button(text="<", size_hint_x=None)
        self._style_button(self.back_button, (0.14, 0.19, 0.29, 1))
        self.back_button.bind(on_release=lambda *_: self._go_home())
        self.title_label = Label(
            text="No file",
            halign="left",
            valign="middle",
            color=(0.91, 0.94, 0.99, 1),
            shorten=True,
            shorten_from="right",
        )
        self.title_label.bind(size=lambda instance, size: setattr(instance, "text_size", size))
        self.title_row.add_widget(self.back_button)
        self.title_row.add_widget(self.title_label)

        self.toolbar = BoxLayout(size_hint_y=None, spacing=dp(8))
        self.save_button = Button(text="Save", size_hint_x=None)
        self._style_button(self.save_button, (0.05, 0.48, 0.78, 1))
        self.save_button.bind(on_release=lambda *_: self._save())
        self.save_as_button = Button(text="Save As", size_hint_x=None)
        self._style_button(self.save_as_button, (0.24, 0.39, 0.77, 1))
        self.save_as_button.bind(on_release=lambda *_: self._open_save_as_popup())
        self.toolbar.add_widget(Label())
        self.toolbar.add_widget(self.save_button)
        self.toolbar.add_widget(self.save_as_button)
        self.header_panel.add_widget(self.title_row)
        self.header_panel.add_widget(self.toolbar)

        self.sheet_bar = BoxLayout(size_hint_y=None, spacing=dp(6), padding=(dp(6), 0))

        self.spreadsheet_scroll = ScrollView(
            do_scroll_x=True,
            do_scroll_y=True,
            bar_width=dp(5),
            scroll_type=["bars", "content"],
        )
        self.spreadsheet = VirtualSpreadsheet(on_cell_selected=self._select_cell)
        self.spreadsheet_scroll.add_widget(self.spreadsheet)
        self.spreadsheet.attach_scroll_view(self.spreadsheet_scroll)

        self.edit_bar = BoxLayout(size_hint_y=None, spacing=dp(6), padding=(dp(6), dp(5)))
        self.cell_ref = Label(text="A1", size_hint_x=None, color=(0.88, 0.92, 0.98, 1))
        self.editor_input = TextInput(multiline=False, font_size=sp(16))
        self.editor_input.bind(on_text_validate=lambda *_: self._apply_edit())
        self.editor_input.bind(focus=self._on_editor_focus)
        self.apply_button = Button(text="Apply", size_hint_x=None)
        self._style_button(self.apply_button, (0.02, 0.56, 0.48, 1))
        self.apply_button.bind(on_release=lambda *_: self._apply_edit())
        self.edit_bar.add_widget(self.cell_ref)
        self.edit_bar.add_widget(self.editor_input)
        self.edit_bar.add_widget(self.apply_button)

        self.actions_scroll = ScrollView(
            do_scroll_x=True,
            do_scroll_y=False,
            size_hint_y=None,
            bar_width=dp(3),
        )
        self.row_actions = BoxLayout(size_hint=(None, 1), spacing=dp(6), padding=(dp(6), 0))
        self.row_actions.bind(minimum_width=self.row_actions.setter("width"))
        self.add_row_button = Button(text="Add Row", size_hint_x=None)
        self._style_button(self.add_row_button, (0.25, 0.4, 0.84, 1))
        self.add_row_button.bind(on_release=lambda *_: self._add_row())
        self.add_cell_button = Button(text="Add Cell", size_hint_x=None)
        self._style_button(self.add_cell_button, (0.41, 0.33, 0.84, 1))
        self.add_cell_button.bind(on_release=lambda *_: self._add_cell())
        self.delete_cell_button = Button(text="Delete Cell", size_hint_x=None)
        self._style_button(self.delete_cell_button, (0.82, 0.31, 0.2, 1))
        self.delete_cell_button.bind(on_release=lambda *_: self._delete_cell())
        self.delete_row_button = Button(text="Delete Row", size_hint_x=None)
        self._style_button(self.delete_row_button, (0.72, 0.2, 0.34, 1))
        self.delete_row_button.bind(on_release=lambda *_: self._delete_row())
        self.status_label = Label(
            text="",
            size_hint_x=None,
            color=(0.56, 0.9, 0.72, 1),
            shorten=True,
        )
        for widget in (
            self.add_row_button,
            self.add_cell_button,
            self.delete_cell_button,
            self.delete_row_button,
            self.status_label,
        ):
            self.row_actions.add_widget(widget)
        self.actions_scroll.add_widget(self.row_actions)

        self.bottom_panel = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=dp(4),
        )
        self._paint_background(self.bottom_panel, (0.055, 0.065, 0.1, 1))
        self.bottom_panel.add_widget(self.edit_bar)
        self.bottom_panel.add_widget(self.actions_scroll)

        self.root_layout.add_widget(self.header_panel)
        self.root_layout.add_widget(self.sheet_bar)
        self.root_layout.add_widget(self.spreadsheet_scroll)
        self.root_layout.add_widget(self.bottom_panel)
        self.add_widget(self.root_layout)
        self.bind(size=lambda *_: self._sync_responsive_layout())
        self._sync_responsive_layout()

    def _style_button(self, button, color, text_color=(1, 1, 1, 1)):
        apply_rounded_button_style(button, color, text_color)

    def _paint_background(self, widget, color):
        with widget.canvas.before:
            Color(*color)
            rectangle = Rectangle(pos=widget.pos, size=widget.size)
        widget.bind(pos=lambda instance, *_: setattr(rectangle, "pos", instance.pos))
        widget.bind(size=lambda instance, *_: setattr(rectangle, "size", instance.size))

    def set_workbook(self, workbook):
        self.workbook = workbook
        self.selected = (0, 0)
        self.refresh_title()
        self._refresh_sheet_bar()
        self.spreadsheet.set_sheet(workbook.active_sheet, reset_scroll=True)
        self._select_cell(0, 0)
        self.status_label.text = ""

    def refresh_title(self):
        if not self.workbook:
            self.title_label.text = "No file"
            return
        dirty = "*" if self.workbook.dirty else ""
        self.title_label.text = f"{self.workbook.display_name}{dirty}"

    def _refresh_sheet_bar(self):
        self.sheet_bar.clear_widgets()
        if not self.workbook:
            return
        if len(self.workbook.sheets) <= 1:
            self.sheet_bar.add_widget(
                Label(text=self.workbook.active_sheet.name, color=(0.86, 0.9, 0.96, 1))
            )
            return

        spinner = Spinner(
            text=self.workbook.active_sheet.name,
            values=[sheet.name for sheet in self.workbook.sheets],
            size_hint=(1, None),
            height=dp(40),
        )
        spinner.bind(text=self._on_sheet_selected)
        self.sheet_bar.add_widget(spinner)

    def _on_sheet_selected(self, _spinner, text):
        for index, sheet in enumerate(self.workbook.sheets):
            if sheet.name == text:
                self.workbook.set_active_sheet(index)
                self.selected = (0, 0)
                self.spreadsheet.set_sheet(sheet, reset_scroll=True)
                self._select_cell(0, 0)
                return

    def _sync_responsive_layout(self):
        width = self.width or dp(360)
        height = self.height or dp(640)
        narrow = width < dp(380)
        wide = width > dp(600)
        short = height < dp(680)

        side_padding = dp(4) if narrow else dp(6)
        safe_top = dp(30) if platform == "android" else 0
        safe_bottom = dp(6) if self.editor_input.focus else (dp(28) if platform == "android" else 0)
        self.root_layout.padding = (side_padding, safe_top, side_padding, safe_bottom)
        self.root_layout.spacing = dp(2) if short else dp(4)

        if narrow:
            header_height, title_height, toolbar_height = dp(116), dp(42), dp(40)
            control_height, action_height = dp(50), dp(42)
            self.back_button.width, self.save_button.width, self.save_as_button.width = dp(40), dp(62), dp(82)
            self.cell_ref.width, self.apply_button.width = dp(48), dp(64)
            row_header_width, visible_columns = dp(42), 2
            button_font, title_font, cell_font = sp(13), sp(15), sp(13)
        elif wide:
            header_height, title_height, toolbar_height = dp(128), dp(46), dp(44)
            control_height, action_height = dp(60), dp(48)
            self.back_button.width, self.save_button.width, self.save_as_button.width = dp(52), dp(82), dp(104)
            self.cell_ref.width, self.apply_button.width = dp(64), dp(86)
            row_header_width, visible_columns = dp(58), 4
            button_font, title_font, cell_font = sp(15), sp(17), sp(14)
        else:
            header_height, title_height, toolbar_height = dp(122), dp(44), dp(42)
            control_height, action_height = dp(56), dp(44)
            self.back_button.width, self.save_button.width, self.save_as_button.width = dp(46), dp(74), dp(92)
            self.cell_ref.width, self.apply_button.width = dp(58), dp(74)
            row_header_width, visible_columns = dp(54), 3
            button_font, title_font, cell_font = sp(14), sp(16), sp(14)

        if short:
            header_height = max(dp(108), header_height - dp(8))
            control_height = max(dp(48), control_height - dp(4))
            action_height = max(dp(40), action_height - dp(4))

        for button in (
            self.back_button,
            self.save_button,
            self.save_as_button,
            self.add_row_button,
            self.add_cell_button,
            self.delete_cell_button,
            self.delete_row_button,
            self.apply_button,
        ):
            button.font_size = button_font
        self.title_label.font_size = title_font
        self.cell_ref.font_size = title_font
        self.editor_input.font_size = sp(15) if narrow else sp(16)
        self.status_label.font_size = sp(12) if narrow else sp(13)

        self.header_panel.height = header_height
        self.title_row.height = title_height
        self.toolbar.height = toolbar_height
        self.sheet_bar.height = dp(36) if short else dp(42)
        self.edit_bar.height = control_height
        self.actions_scroll.height = action_height
        self.row_actions.height = action_height
        self.bottom_panel.height = control_height + action_height + dp(6)

        action_width = dp(98) if narrow else dp(116)
        self.add_row_button.width = action_width
        self.add_cell_button.width = action_width + dp(8)
        self.delete_cell_button.width = action_width + dp(18)
        self.delete_row_button.width = action_width + dp(14)
        self.status_label.width = dp(116) if narrow else dp(132)

        usable_width = max(width - row_header_width - side_padding * 2 - dp(10), dp(160))
        cell_width = max(dp(88), min(dp(150), usable_width / visible_columns))
        cell_height = dp(36) if short or narrow else dp(42)
        metrics = (cell_width, row_header_width, cell_height, cell_font)
        if metrics != self._last_metrics:
            self._last_metrics = metrics
            self.spreadsheet.set_metrics(*metrics)

    def _on_editor_focus(self, _instance, _focused):
        self._sync_responsive_layout()

    def _select_cell(self, row_index, column_index):
        if not self.workbook:
            return
        self.selected = (row_index, column_index)
        self.spreadsheet.select_cell(row_index, column_index)
        self.cell_ref.text = f"{column_name(column_index)}{row_index + 1}"
        self.editor_input.text = self.workbook.active_sheet.get_cell(row_index, column_index)

    def _apply_edit(self):
        if not self.workbook or self._is_busy():
            return
        row_index, column_index = self.selected
        self.workbook.set_cell(row_index, column_index, self.editor_input.text)
        self.spreadsheet.refresh_data()
        self.refresh_title()
        self.status_label.text = "Edited"

    def _add_row(self):
        row_index, column_index = self.selected
        self._run_mutation(
            lambda: self.workbook.insert_row_after(row_index),
            lambda: (row_index + 1, min(column_index, self.workbook.active_sheet.column_count - 1)),
            "Row added",
        )

    def _add_cell(self):
        row_index, column_index = self.selected
        self._run_mutation(
            lambda: self.workbook.add_cell_below(row_index, column_index),
            lambda: (row_index + 1, column_index),
            "Cell added",
        )

    def _delete_cell(self):
        row_index, column_index = self.selected
        self._run_mutation(
            lambda: self.workbook.delete_cell(row_index, column_index),
            lambda: (min(row_index, self.workbook.active_sheet.row_count - 1), column_index),
            "Cell deleted",
        )

    def _delete_row(self):
        row_index, column_index = self.selected
        self._run_mutation(
            lambda: self.workbook.delete_row(row_index),
            lambda: (
                min(row_index, self.workbook.active_sheet.row_count - 1),
                min(column_index, self.workbook.active_sheet.column_count - 1),
            ),
            "Row deleted",
        )

    def _run_mutation(self, operation, next_selection, success_message):
        if not self.workbook or self._is_busy():
            return
        self._set_action_state(True, "Working...")
        self._mutation_task = run_in_background(
            lambda _cancel_event: operation(),
            lambda _result: self._finish_mutation(next_selection(), success_message),
            self._mutation_failed,
        )

    def _finish_mutation(self, selection, message):
        self._mutation_task = None
        self.spreadsheet.refresh_data()
        self._select_cell(*selection)
        self.refresh_title()
        self._set_action_state(False, message)

    def _mutation_failed(self, error):
        self._mutation_task = None
        self._set_action_state(False, f"{type(error).__name__}: {error}")

    def _is_busy(self):
        return self._mutation_task is not None or self._save_in_progress

    def _set_action_state(self, disabled, message):
        for button in (
            self.add_row_button,
            self.add_cell_button,
            self.delete_cell_button,
            self.delete_row_button,
            self.apply_button,
        ):
            button.disabled = disabled
        self.status_label.text = message

    def _save(self):
        if self._is_busy():
            return
        self._save_in_progress = True
        self._set_action_state(True, "Saving...")
        self.save_button.disabled = True
        self.save_as_button.disabled = True
        App.get_running_app().save_current_workbook_async(
            self._on_save_complete,
            on_progress=self._on_save_progress,
        )

    def _open_save_as_popup(self):
        default_name = self.workbook.display_name if self.workbook else "Untitled.csv"
        content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(8))
        hint = Label(
            text="Enter a full path ending in .csv or .xlsx",
            size_hint_y=None,
            height=dp(34),
            color=(0.12, 0.16, 0.2, 1),
        )
        initial_path = str(Path(App.get_running_app().user_data_dir) / default_name)
        self.save_as_input = TextInput(text=initial_path, multiline=False, size_hint_y=None, height=dp(44))
        actions = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        cancel = Button(text="Cancel")
        save = Button(text="Save")
        actions.add_widget(cancel)
        actions.add_widget(save)
        content.add_widget(hint)
        content.add_widget(self.save_as_input)
        content.add_widget(actions)
        popup = Popup(title="Save As", content=content, size_hint=(0.94, None), height=dp(210))
        cancel.bind(on_release=popup.dismiss)
        save.bind(on_release=lambda *_: self._save_as(popup))
        popup.open()

    def _save_as(self, popup):
        if self._is_busy():
            return
        path = self.save_as_input.text.strip()
        self._save_in_progress = True
        self._set_action_state(True, "Saving...")
        self.save_button.disabled = True
        self.save_as_button.disabled = True

        def completed(success, message):
            self._on_save_complete(success, message)
            if success:
                popup.dismiss()

        App.get_running_app().save_current_workbook_async(
            completed,
            path,
            self._on_save_progress,
        )

    def _on_save_progress(self, _current, _total, message):
        self.status_label.text = message

    def _on_save_complete(self, success, message):
        self._save_in_progress = False
        self.save_button.disabled = False
        self.save_as_button.disabled = False
        self._set_action_state(False, message)
        if success:
            self.refresh_title()
        elif "Save As" in message:
            self._open_save_as_popup()

    def _go_home(self):
        if not self._is_busy():
            App.get_running_app().manager.current = "home"
