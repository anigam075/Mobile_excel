from pathlib import Path

from kivy.app import App
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp
from kivy.utils import platform
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
        self.root_layout = None
        self.header_panel = None
        self.toolbar = None
        self.title_row = None
        self.action_row = None
        self.back_button = None
        self.save_button = None
        self.save_as_button = None
        self.add_row_button = None
        self.add_cell_button = None
        self.delete_cell_button = None
        self.delete_row_button = None
        self.edit_bar = None
        self.apply_button = None
        self.bottom_panel = None
        self.actions_scroll = None
        self.row_actions = None
        self.spreadsheet_scroll = None
        self._keyboard_height = 0
        self._cell_width = dp(128)
        self._row_header_width = dp(54)
        self._cell_height = dp(42)
        self._cell_font = "14sp"
        self._last_metrics = None
        self._build()

    def _build(self):
        root = BoxLayout(orientation="vertical", spacing=dp(4), padding=(0, 0, 0, 0))
        self.root_layout = root
        self._paint_background(root, (0.04, 0.05, 0.07, 1))

        self.header_panel = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            height=dp(92),
            spacing=dp(6),
            padding=(dp(8), dp(8), dp(8), dp(6)),
        )
        self._paint_background(self.header_panel, (0.06, 0.08, 0.12, 1))

        self.title_row = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(8))
        self.back_button = Button(text="<", size_hint_x=None, width=dp(46))
        self._style_button(self.back_button, (0.16, 0.2, 0.28, 1))
        self.back_button.bind(on_release=lambda *_: self._go_home())
        self.title_label = Label(
            text="No file",
            halign="left",
            valign="middle",
            color=(0.88, 0.92, 0.98, 1),
            shorten=True,
            shorten_from="right",
        )
        self.title_label.bind(size=lambda instance, size: setattr(instance, "text_size", size))
        self.title_row.add_widget(self.back_button)
        self.title_row.add_widget(self.title_label)

        self.toolbar = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(8))
        self.save_button = Button(text="Save", size_hint_x=None, width=dp(74))
        self._style_button(self.save_button, (0.11, 0.45, 0.7, 1))
        self.save_button.bind(on_release=lambda *_: self._save())
        self.save_as_button = Button(text="Save As", size_hint_x=None, width=dp(92))
        self._style_button(self.save_as_button, (0.22, 0.38, 0.72, 1))
        self.save_as_button.bind(on_release=lambda *_: self._open_save_as_popup())
        self.toolbar.add_widget(Label())
        self.toolbar.add_widget(self.save_button)
        self.toolbar.add_widget(self.save_as_button)
        self.header_panel.add_widget(self.title_row)
        self.header_panel.add_widget(self.toolbar)

        self.sheet_bar = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6), padding=(dp(6), 0))

        self.spreadsheet_scroll = ScrollView(do_scroll_x=True, do_scroll_y=True, bar_width=dp(6))
        self.grid = GridLayout(cols=1, spacing=1, size_hint=(None, None))
        self.grid.bind(minimum_width=self.grid.setter("width"), minimum_height=self.grid.setter("height"))
        self.spreadsheet_scroll.add_widget(self.grid)

        self.edit_bar = BoxLayout(size_hint_y=None, height=dp(58), spacing=dp(6), padding=(dp(6), dp(5)))
        self.cell_ref = Label(text="A1", size_hint_x=None, width=dp(58), color=(0.88, 0.92, 0.98, 1))
        self.editor_input = TextInput(multiline=False, font_size="16sp")
        self.apply_button = Button(text="Apply", size_hint_x=None, width=dp(74))
        self._style_button(self.apply_button, (0.05, 0.52, 0.45, 1))
        self.apply_button.bind(on_release=lambda *_: self._apply_edit())
        self.edit_bar.add_widget(self.cell_ref)
        self.edit_bar.add_widget(self.editor_input)
        self.edit_bar.add_widget(self.apply_button)

        self.actions_scroll = ScrollView(
            do_scroll_x=True,
            do_scroll_y=False,
            size_hint_y=None,
            height=dp(46),
            bar_width=dp(3),
        )
        self.row_actions = BoxLayout(size_hint=(None, 1), height=dp(46), spacing=dp(6), padding=(dp(6), 0))
        self.row_actions.bind(minimum_width=self.row_actions.setter("width"))
        self.add_row_button = Button(text="Add Row", size_hint_x=None, width=dp(104))
        self._style_button(self.add_row_button, (0.26, 0.39, 0.82, 1))
        self.add_row_button.bind(on_release=lambda *_: self._add_row())
        self.add_cell_button = Button(text="Add Cell", size_hint_x=None, width=dp(112))
        self._style_button(self.add_cell_button, (0.38, 0.33, 0.82, 1))
        self.add_cell_button.bind(on_release=lambda *_: self._add_cell())
        self.delete_cell_button = Button(text="Delete Cell", size_hint_x=None, width=dp(126))
        self._style_button(self.delete_cell_button, (0.78, 0.32, 0.22, 1))
        self.delete_cell_button.bind(on_release=lambda *_: self._delete_cell())
        self.delete_row_button = Button(text="Delete Row", size_hint_x=None, width=dp(124))
        self._style_button(self.delete_row_button, (0.7, 0.22, 0.34, 1))
        self.delete_row_button.bind(on_release=lambda *_: self._delete_row())
        self.status_label = Label(text="", size_hint_x=None, width=dp(132), color=(0.58, 0.88, 0.72, 1))
        self.row_actions.add_widget(self.add_row_button)
        self.row_actions.add_widget(self.add_cell_button)
        self.row_actions.add_widget(self.delete_cell_button)
        self.row_actions.add_widget(self.delete_row_button)
        self.row_actions.add_widget(self.status_label)
        self.actions_scroll.add_widget(self.row_actions)

        self.bottom_panel = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            height=dp(110),
            spacing=dp(4),
            padding=(0, 0, 0, 0),
        )
        self._paint_background(self.bottom_panel, (0.06, 0.07, 0.1, 1))
        self.bottom_panel.add_widget(self.edit_bar)
        self.bottom_panel.add_widget(self.actions_scroll)

        root.add_widget(self.header_panel)
        root.add_widget(self.sheet_bar)
        root.add_widget(self.spreadsheet_scroll)
        root.add_widget(self.bottom_panel)
        self.add_widget(root)
        self.bind(size=lambda *_: self._sync_responsive_layout())
        self.editor_input.bind(focus=self._on_editor_focus)
        try:
            Window.softinput_mode = "resize"
            Window.bind(keyboard_height=self._on_keyboard_height)
        except Exception:
            pass
        self._sync_responsive_layout()

    def _style_button(self, button, color, text_color=(1, 1, 1, 1)):
        button.background_normal = ""
        button.background_down = ""
        button.background_color = color
        button.color = text_color
        button.bold = True

    def _paint_background(self, widget, color):
        with widget.canvas.before:
            Color(*color)
            rect = Rectangle(pos=widget.pos, size=widget.size)
        widget.bind(pos=lambda instance, *_: setattr(rect, "pos", instance.pos))
        widget.bind(size=lambda instance, *_: setattr(rect, "size", instance.size))

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
            label = Label(text=self.workbook.active_sheet.name, color=(0.86, 0.9, 0.96, 1))
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
        cell_width = self._cell_width
        row_header_width = self._row_header_width
        cell_height = self._cell_height

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
                    font_size=self._cell_font,
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
            color=(0.82, 0.88, 0.95, 1),
        )

    def _sync_responsive_layout(self):
        width = self.width or dp(360)
        height = self.height or dp(640)
        narrow = width < dp(380)
        wide = width > dp(600)
        short = height < dp(680)
        very_short = height < dp(580)

        safe_top = dp(30) if platform == "android" else 0
        safe_bottom = dp(34) if platform == "android" else 0
        keyboard_padding = 0
        if self.editor_input and self.editor_input.focus:
            keyboard_padding = self._keyboard_height or min(dp(360), height * 0.46)
        side_padding = dp(4) if narrow else dp(6)
        if self.root_layout:
            self.root_layout.padding = (
                side_padding,
                safe_top,
                side_padding,
                max(safe_bottom, keyboard_padding + dp(8)),
            )
            self.root_layout.spacing = dp(2) if short else dp(4)

        if narrow:
            header_height = dp(124)
            title_row_height = dp(44)
            toolbar_height = dp(42)
            control_height = dp(52)
            action_height = dp(44)
            self.back_button.width = dp(40)
            self.save_button.width = dp(62)
            self.save_as_button.width = dp(82)
            self.cell_ref.width = dp(48)
            self.apply_button.width = dp(64)
            cols_visible = 2
            row_header_width = dp(42)
            button_font = "13sp"
            title_font = "15sp"
            cell_font = "13sp"
        elif wide:
            header_height = dp(132)
            title_row_height = dp(48)
            toolbar_height = dp(46)
            control_height = dp(62)
            action_height = dp(50)
            self.back_button.width = dp(52)
            self.save_button.width = dp(82)
            self.save_as_button.width = dp(104)
            self.cell_ref.width = dp(64)
            self.apply_button.width = dp(86)
            cols_visible = 4
            row_header_width = dp(58)
            button_font = "15sp"
            title_font = "17sp"
            cell_font = "14sp"
        else:
            header_height = dp(128)
            title_row_height = dp(46)
            toolbar_height = dp(44)
            control_height = dp(58)
            action_height = dp(46)
            self.back_button.width = dp(46)
            self.save_button.width = dp(74)
            self.save_as_button.width = dp(92)
            self.cell_ref.width = dp(58)
            self.apply_button.width = dp(74)
            cols_visible = 3
            row_header_width = dp(54)
            button_font = "14sp"
            title_font = "16sp"
            cell_font = "14sp"

        if very_short:
            header_height = max(dp(112), header_height - dp(8))
            title_row_height = max(dp(40), title_row_height - dp(4))
            toolbar_height = max(dp(38), toolbar_height - dp(4))
            control_height = max(dp(48), control_height - dp(4))
            action_height = max(dp(40), action_height - dp(4))
        elif short:
            header_height = max(dp(116), header_height - dp(4))
            title_row_height = max(dp(42), title_row_height - dp(2))
            toolbar_height = max(dp(40), toolbar_height - dp(2))
            control_height = max(dp(50), control_height - dp(2))

        self.back_button.font_size = button_font
        self.save_button.font_size = button_font
        self.save_as_button.font_size = button_font
        self.add_row_button.font_size = button_font
        self.add_cell_button.font_size = button_font
        self.apply_button.font_size = button_font
        self.title_label.font_size = title_font
        self.cell_ref.font_size = title_font
        self.editor_input.font_size = "15sp" if narrow else "16sp"
        self.status_label.font_size = "12sp" if narrow else "13sp"

        self.header_panel.height = header_height
        self.header_panel.padding = (dp(6), dp(8), dp(6), dp(6)) if narrow else (dp(8), dp(10), dp(8), dp(8))
        self.title_row.height = title_row_height
        self.toolbar.height = toolbar_height
        self.toolbar.padding = (0, 0, 0, 0)
        self.edit_bar.height = control_height
        self.edit_bar.padding = (dp(4), dp(4), dp(4), dp(4)) if narrow else (dp(6), dp(5), dp(6), dp(5))
        self.actions_scroll.height = action_height
        self.row_actions.height = action_height
        self.row_actions.padding = (dp(4), 0, dp(4), 0) if narrow else (dp(6), 0, dp(6), 0)
        self.bottom_panel.height = control_height + action_height + self.bottom_panel.spacing + dp(2)
        self.sheet_bar.height = dp(36) if short else (dp(40) if narrow else dp(44))

        action_button_width = dp(98) if narrow else dp(116)
        self.add_row_button.width = action_button_width
        self.add_cell_button.width = action_button_width + dp(8)
        self.delete_cell_button.width = action_button_width + dp(18)
        self.delete_row_button.width = action_button_width + dp(14)
        self.status_label.width = dp(116) if narrow else dp(132)

        usable_width = max(width - row_header_width - side_padding * 2 - dp(10), dp(160))
        cell_width = max(dp(92), min(dp(150), usable_width / cols_visible))
        if narrow and cols_visible == 2:
            cell_width = max(dp(86), min(dp(132), usable_width / cols_visible))

        cell_height = dp(36) if very_short else (dp(38) if short or narrow else dp(42))
        metrics = (cell_width, row_header_width, cell_height, cell_font)
        if metrics == self._last_metrics:
            return

        self._cell_width, self._row_header_width, self._cell_height, self._cell_font = metrics
        self._last_metrics = metrics
        if self.workbook:
            selected = self.selected
            self._render_grid()
            self._select_cell(*selected)

    def _on_keyboard_height(self, _window, height):
        self._keyboard_height = max(0, height)
        self._sync_responsive_layout()

    def _on_editor_focus(self, _instance, focused):
        if focused and self.spreadsheet_scroll:
            self.spreadsheet_scroll.scroll_y = 1
        self._sync_responsive_layout()

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
        row_index, column_index = self.selected
        self.workbook.insert_row_after(row_index)
        self._render_grid()
        self._select_cell(row_index + 1, min(column_index, self.workbook.active_sheet.column_count - 1))
        self.refresh_title()
        self.status_label.text = "Row added"

    def _add_cell(self):
        if not self.workbook:
            return
        row_index, column_index = self.selected
        self.workbook.add_cell_below(row_index, column_index)
        self._render_grid()
        self._select_cell(row_index + 1, column_index)
        self.refresh_title()
        self.status_label.text = "Cell added"

    def _delete_cell(self):
        if not self.workbook:
            return
        row_index, column_index = self.selected
        self.workbook.delete_cell(row_index, column_index)
        self._render_grid()
        self._select_cell(min(row_index, self.workbook.active_sheet.row_count - 1), column_index)
        self.refresh_title()
        self.status_label.text = "Cell deleted"

    def _delete_row(self):
        if not self.workbook:
            return
        row_index, column_index = self.selected
        self.workbook.delete_row(row_index)
        next_row = min(row_index, self.workbook.active_sheet.row_count - 1)
        next_col = min(column_index, self.workbook.active_sheet.column_count - 1)
        self.selected = (next_row, next_col)
        self._render_grid()
        self._select_cell(next_row, next_col)
        self.refresh_title()
        self.status_label.text = "Row deleted"

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
