from pathlib import Path

from kivy.app import App
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput

from app.models.workbook import column_name


class EditorScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.workbook = None
        self.selected = (0, 0)
        self.cell_buttons = {}
        self.title_label = None
        self.sheet_bar = None
        self.grid = None
        self.cell_ref = None
        self.editor_input = None
        self.status_label = None
        self.save_as_input = None
        self._build()

    def _build(self):
        root = BoxLayout(orientation="vertical", spacing=dp(4))

        toolbar = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(6), padding=(dp(6), dp(6)))
        back = Button(text="<", size_hint_x=None, width=dp(46))
        back.bind(on_release=lambda *_: self._go_home())
        self.title_label = Label(text="No file", halign="left", valign="middle", color=(0.08, 0.1, 0.13, 1))
        self.title_label.bind(size=lambda instance, size: setattr(instance, "text_size", size))
        save = Button(text="Save", size_hint_x=None, width=dp(74))
        save.bind(on_release=lambda *_: self._save())
        save_as = Button(text="Save As", size_hint_x=None, width=dp(92))
        save_as.bind(on_release=lambda *_: self._open_save_as_popup())
        toolbar.add_widget(back)
        toolbar.add_widget(self.title_label)
        toolbar.add_widget(save)
        toolbar.add_widget(save_as)

        self.sheet_bar = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6), padding=(dp(6), 0))

        scroll = ScrollView(do_scroll_x=True, do_scroll_y=True, bar_width=dp(8))
        self.grid = GridLayout(cols=1, spacing=1, size_hint=(None, None))
        self.grid.bind(minimum_width=self.grid.setter("width"), minimum_height=self.grid.setter("height"))
        scroll.add_widget(self.grid)

        edit_bar = BoxLayout(size_hint_y=None, height=dp(58), spacing=dp(6), padding=(dp(6), dp(5)))
        self.cell_ref = Label(text="A1", size_hint_x=None, width=dp(58), color=(0.08, 0.1, 0.13, 1))
        self.editor_input = TextInput(multiline=False, font_size="16sp")
        apply_button = Button(text="Apply", size_hint_x=None, width=dp(74))
        apply_button.bind(on_release=lambda *_: self._apply_edit())
        edit_bar.add_widget(self.cell_ref)
        edit_bar.add_widget(self.editor_input)
        edit_bar.add_widget(apply_button)

        row_actions = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(6), padding=(dp(6), 0))
        add_row = Button(text="Add Row")
        add_row.bind(on_release=lambda *_: self._add_row())
        add_col = Button(text="Add Column")
        add_col.bind(on_release=lambda *_: self._add_column())
        self.status_label = Label(text="", color=(0.18, 0.34, 0.28, 1))
        row_actions.add_widget(add_row)
        row_actions.add_widget(add_col)
        row_actions.add_widget(self.status_label)

        root.add_widget(toolbar)
        root.add_widget(self.sheet_bar)
        root.add_widget(scroll)
        root.add_widget(edit_bar)
        root.add_widget(row_actions)
        self.add_widget(root)

    def set_workbook(self, workbook):
        self.workbook = workbook
        self.selected = (0, 0)
        self.refresh_title()
        self._refresh_sheet_bar()
        self._render_grid()
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
            label = Label(text=self.workbook.active_sheet.name, color=(0.2, 0.24, 0.28, 1))
            self.sheet_bar.add_widget(label)
            return

        spinner = Spinner(
            text=self.workbook.active_sheet.name,
            values=[sheet.name for sheet in self.workbook.sheets],
            size_hint=(1, None),
            height=dp(40),
        )
        spinner.bind(text=self._on_sheet_selected)
        self.sheet_bar.add_widget(spinner)

    def _on_sheet_selected(self, spinner, text):
        for index, sheet in enumerate(self.workbook.sheets):
            if sheet.name == text:
                self.workbook.set_active_sheet(index)
                self.selected = (0, 0)
                self._render_grid()
                self._select_cell(0, 0)
                return

    def _render_grid(self):
        self.grid.clear_widgets()
        self.cell_buttons.clear()
        if not self.workbook:
            return

        sheet = self.workbook.active_sheet
        rows = sheet.row_count
        cols = sheet.column_count
        cell_width = dp(128)
        row_header_width = dp(54)
        cell_height = dp(42)

        self.grid.cols = cols + 1
        self.grid.width = row_header_width + cols * cell_width
        self.grid.height = (rows + 1) * cell_height

        self.grid.add_widget(self._header_cell("", row_header_width, cell_height))
        for column_index in range(cols):
            self.grid.add_widget(self._header_cell(column_name(column_index), cell_width, cell_height))

        for row_index in range(rows):
            self.grid.add_widget(self._header_cell(str(row_index + 1), row_header_width, cell_height))
            for column_index in range(cols):
                value = sheet.get_cell(row_index, column_index)
                button = Button(
                    text=value,
                    font_size="14sp",
                    halign="left",
                    valign="middle",
                    size_hint=(None, None),
                    size=(cell_width, cell_height),
                    background_normal="",
                    background_color=(1, 1, 1, 1),
                    color=(0.08, 0.1, 0.13, 1),
                    shorten=True,
                )
                button.bind(size=lambda instance, size: setattr(instance, "text_size", (size[0] - dp(10), size[1])))
                button.bind(on_release=lambda _, r=row_index, c=column_index: self._select_cell(r, c))
                self.cell_buttons[(row_index, column_index)] = button
                self.grid.add_widget(button)

    def _header_cell(self, text, width, height):
        return Label(
            text=text,
            bold=True,
            size_hint=(None, None),
            size=(width, height),
            color=(0.1, 0.14, 0.18, 1),
        )

    def _select_cell(self, row_index, column_index):
        if not self.workbook:
            return
        previous = self.cell_buttons.get(self.selected)
        if previous:
            previous.background_color = (1, 1, 1, 1)

        self.selected = (row_index, column_index)
        current = self.cell_buttons.get(self.selected)
        if current:
            current.background_color = (0.78, 0.89, 1, 1)

        self.cell_ref.text = f"{column_name(column_index)}{row_index + 1}"
        self.editor_input.text = self.workbook.active_sheet.get_cell(row_index, column_index)

    def _apply_edit(self):
        if not self.workbook:
            return
        row_index, column_index = self.selected
        self.workbook.set_cell(row_index, column_index, self.editor_input.text)
        button = self.cell_buttons.get(self.selected)
        if button:
            button.text = self.editor_input.text
        self.refresh_title()
        self.status_label.text = "Edited"

    def _add_row(self):
        if not self.workbook:
            return
        self.workbook.add_row()
        self._render_grid()
        self._select_cell(self.workbook.active_sheet.row_count - 1, 0)
        self.refresh_title()

    def _add_column(self):
        if not self.workbook:
            return
        self.workbook.add_column()
        self._render_grid()
        self._select_cell(0, self.workbook.active_sheet.column_count - 1)
        self.refresh_title()

    def _save(self):
        ok, message = App.get_running_app().save_current_workbook()
        self.status_label.text = message
        if not ok and "Save As" in message:
            self._open_save_as_popup()

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
        path = self.save_as_input.text.strip()
        ok, message = App.get_running_app().save_current_workbook(path)
        self.status_label.text = message
        if ok:
            popup.dismiss()

    def _go_home(self):
        App.get_running_app().manager.current = "home"
