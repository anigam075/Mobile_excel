import math
from collections import OrderedDict

from kivy.clock import Clock
from kivy.core.text import Label as CoreLabel
from kivy.graphics import Color, Line, Rectangle
from kivy.metrics import dp, sp
from kivy.uix.widget import Widget

from app.models.workbook import column_name


def calculate_visible_range(
    row_count,
    column_count,
    cell_width,
    row_header_width,
    cell_height,
    content_width,
    content_height,
    viewport_width,
    viewport_height,
    scroll_x,
    scroll_y,
    overscan=2,
):
    horizontal_range = max(0, content_width - viewport_width)
    vertical_range = max(0, content_height - viewport_height)
    visible_left = max(0, min(1, scroll_x)) * horizontal_range
    visible_bottom = max(0, min(1, scroll_y)) * vertical_range
    visible_top = max(0, content_height - visible_bottom - viewport_height)

    first_grid_row = math.floor(visible_top / cell_height)
    last_grid_row = math.ceil((visible_top + viewport_height) / cell_height)
    start_row = max(0, first_grid_row - 1 - overscan)
    end_row = min(row_count, last_grid_row - 1 + overscan)

    first_column = math.floor((visible_left - row_header_width) / cell_width)
    last_column = math.ceil(
        (visible_left + viewport_width - row_header_width) / cell_width
    )
    start_column = max(0, first_column - overscan)
    end_column = min(column_count, last_column + overscan)
    return start_row, end_row, start_column, end_column, visible_left, visible_top


class VirtualSpreadsheet(Widget):
    def __init__(self, on_cell_selected=None, **kwargs):
        super().__init__(size_hint=(None, None), **kwargs)
        self.sheet = None
        self.scroll_view = None
        self.on_cell_selected = on_cell_selected
        self.selected = (0, 0)
        self.freeze_top_row = False
        self.cell_width = dp(128)
        self.row_header_width = dp(54)
        self.cell_height = dp(42)
        self.cell_font_size = sp(14)
        self._texture_cache = OrderedDict()
        self._redraw_trigger = Clock.create_trigger(self._redraw, 0)
        self.bind(pos=lambda *_: self.schedule_redraw())

    def attach_scroll_view(self, scroll_view):
        if self.scroll_view is not None:
            self.scroll_view.unbind(
                scroll_x=self._on_scroll,
                scroll_y=self._on_scroll,
                size=self._on_scroll,
            )
        self.scroll_view = scroll_view
        scroll_view.bind(
            scroll_x=self._on_scroll,
            scroll_y=self._on_scroll,
            size=self._on_scroll,
        )
        self.schedule_redraw()

    def set_sheet(self, sheet, reset_scroll=False):
        self.sheet = sheet
        self.selected = (0, 0)
        self.freeze_top_row = bool(getattr(sheet, "freeze_top_row", False))
        self.refresh_dimensions()
        if reset_scroll and self.scroll_view is not None:
            self.scroll_view.scroll_x = 0
            self.scroll_view.scroll_y = 1
        self.schedule_redraw()

    def set_freeze_top_row(self, enabled):
        self.freeze_top_row = bool(enabled)
        self.schedule_redraw()

    def set_metrics(self, cell_width, row_header_width, cell_height, font_size):
        changed = (
            self.cell_width != cell_width
            or self.row_header_width != row_header_width
            or self.cell_height != cell_height
            or self.cell_font_size != font_size
        )
        self.cell_width = cell_width
        self.row_header_width = row_header_width
        self.cell_height = cell_height
        self.cell_font_size = font_size
        if changed:
            self._texture_cache.clear()
            self.refresh_dimensions()
            self.schedule_redraw()

    def refresh_dimensions(self):
        rows = self.sheet.row_count if self.sheet is not None else 1
        columns = self.sheet.column_count if self.sheet is not None else 1
        self.size = (
            self.row_header_width + columns * self.cell_width,
            (rows + 1) * self.cell_height,
        )

    def select_cell(self, row_index, column_index):
        if self.sheet is None:
            return
        self.selected = (
            min(max(row_index, 0), self.sheet.row_count - 1),
            min(max(column_index, 0), self.sheet.column_count - 1),
        )
        self.schedule_redraw()

    def ensure_cell_visible(self, row_index, column_index, align_top=False):
        if self.sheet is None or self.scroll_view is None:
            return

        horizontal_range = max(0, self.width - self.scroll_view.width)
        vertical_range = max(0, self.height - self.scroll_view.height)
        _, _, _, _, visible_left, visible_top = self.visible_range()

        cell_left = self.row_header_width + column_index * self.cell_width
        cell_right = cell_left + self.cell_width
        desired_left = visible_left
        if cell_left < visible_left + self.row_header_width:
            desired_left = max(0, cell_left - self.row_header_width)
        elif cell_right > visible_left + self.scroll_view.width:
            desired_left = min(horizontal_range, cell_right - self.scroll_view.width)
        if horizontal_range:
            self.scroll_view.scroll_x = desired_left / horizontal_range

        if self.freeze_top_row and row_index == 0:
            self.schedule_redraw()
            return

        sticky_height = self.cell_height * (2 if self.freeze_top_row else 1)
        cell_top = (row_index + 1) * self.cell_height
        cell_bottom = cell_top + self.cell_height
        desired_top = visible_top
        if align_top or cell_top < visible_top + sticky_height:
            desired_top = max(0, cell_top - sticky_height)
        elif cell_bottom > visible_top + self.scroll_view.height:
            desired_top = min(vertical_range, cell_bottom - self.scroll_view.height)
        if vertical_range:
            self.scroll_view.scroll_y = 1 - desired_top / vertical_range
        self.schedule_redraw()

    def refresh_data(self):
        self.refresh_dimensions()
        self.schedule_redraw()

    def schedule_redraw(self):
        self._redraw_trigger()

    def visible_range(self):
        if self.sheet is None or self.scroll_view is None:
            return 0, 0, 0, 0, 0, 0
        return calculate_visible_range(
            self.sheet.row_count,
            self.sheet.column_count,
            self.cell_width,
            self.row_header_width,
            self.cell_height,
            self.width,
            self.height,
            self.scroll_view.width,
            self.scroll_view.height,
            self.scroll_view.scroll_x,
            self.scroll_view.scroll_y,
        )

    def _on_scroll(self, *_args):
        self.schedule_redraw()

    def _redraw(self, *_args):
        self.canvas.clear()
        if self.sheet is None or self.scroll_view is None:
            return

        (
            start_row,
            end_row,
            start_column,
            end_column,
            visible_left,
            visible_top,
        ) = self.visible_range()
        values = self.sheet.get_range(
            start_row,
            end_row,
            start_column,
            end_column,
        )
        frozen_values = {}
        show_frozen_row = self.freeze_top_row and visible_top > 0.5
        if show_frozen_row:
            if start_row == 0:
                frozen_values = values
            else:
                frozen_values = self.sheet.get_range(
                    0,
                    1,
                    start_column,
                    end_column,
                )

        with self.canvas:
            for row_index in range(start_row, end_row):
                y = self.y + self.height - (row_index + 2) * self.cell_height
                for column_index in range(start_column, end_column):
                    x = self.x + self.row_header_width + column_index * self.cell_width
                    selected = (row_index, column_index) == self.selected
                    background = (0.76, 0.88, 1, 1) if selected else (0.97, 0.98, 1, 1)
                    self._draw_cell(
                        x,
                        y,
                        self.cell_width,
                        self.cell_height,
                        background,
                        values.get((row_index, column_index), ""),
                        (0.07, 0.1, 0.15, 1),
                        False,
                    )

            fixed_x = self.x + visible_left
            fixed_y = self.y + self.height - visible_top - self.cell_height
            header_color = (0.08, 0.12, 0.19, 1)
            for column_index in range(start_column, end_column):
                x = self.x + self.row_header_width + column_index * self.cell_width
                self._draw_cell(
                    x,
                    fixed_y,
                    self.cell_width,
                    self.cell_height,
                    header_color,
                    column_name(column_index),
                    (0.84, 0.9, 0.98, 1),
                    True,
                )

            for row_index in range(start_row, end_row):
                y = self.y + self.height - (row_index + 2) * self.cell_height
                self._draw_cell(
                    fixed_x,
                    y,
                    self.row_header_width,
                    self.cell_height,
                    header_color,
                    str(row_index + 1),
                    (0.84, 0.9, 0.98, 1),
                    True,
                )

            if show_frozen_row:
                frozen_y = fixed_y - self.cell_height
                for column_index in range(start_column, end_column):
                    x = self.x + self.row_header_width + column_index * self.cell_width
                    selected = (0, column_index) == self.selected
                    background = (0.7, 0.86, 1, 1) if selected else (0.9, 0.95, 1, 1)
                    self._draw_cell(
                        x,
                        frozen_y,
                        self.cell_width,
                        self.cell_height,
                        background,
                        frozen_values.get((0, column_index), ""),
                        (0.06, 0.09, 0.14, 1),
                        True,
                    )
                self._draw_cell(
                    fixed_x,
                    frozen_y,
                    self.row_header_width,
                    self.cell_height,
                    (0.1, 0.3, 0.42, 1),
                    "1",
                    (0.9, 0.96, 1, 1),
                    True,
                )

            self._draw_cell(
                fixed_x,
                fixed_y,
                self.row_header_width,
                self.cell_height,
                (0.05, 0.08, 0.13, 1),
                "",
                (1, 1, 1, 1),
                True,
            )

    def _draw_cell(self, x, y, width, height, background, text, text_color, bold):
        Color(*background)
        Rectangle(pos=(x, y), size=(width, height))
        Color(0.28, 0.32, 0.39, 0.75)
        Line(rectangle=(x, y, width, height), width=0.55)
        if not text:
            return

        texture = self._text_texture(text, width, height, text_color, bold)
        Color(1, 1, 1, 1)
        Rectangle(pos=(x + dp(5), y), size=(width - dp(10), height), texture=texture)

    def _text_texture(self, text, width, height, color, bold):
        key = (str(text), round(width, 1), round(height, 1), color, bold, self.cell_font_size)
        texture = self._texture_cache.get(key)
        if texture is not None:
            self._texture_cache.move_to_end(key)
            return texture

        label = CoreLabel(
            text=str(text),
            font_size=self.cell_font_size,
            bold=bold,
            color=color,
            text_size=(max(dp(10), width - dp(10)), height),
            halign="center" if bold else "left",
            valign="middle",
            shorten=True,
            shorten_from="right",
        )
        label.refresh()
        texture = label.texture
        self._texture_cache[key] = texture
        while len(self._texture_cache) > 768:
            self._texture_cache.popitem(last=False)
        return texture

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos) and self.scroll_view is not None:
            touch.ud[f"mobilexl_{id(self)}"] = (
                touch.pos,
                self.scroll_view.scroll_x,
                self.scroll_view.scroll_y,
            )
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        key = f"mobilexl_{id(self)}"
        started = touch.ud.pop(key, None)
        handled = super().on_touch_up(touch)
        if started is None or not self.collide_point(*touch.pos) or self.sheet is None:
            return handled

        start_pos, start_scroll_x, start_scroll_y = started
        moved = abs(touch.x - start_pos[0]) > dp(8) or abs(touch.y - start_pos[1]) > dp(8)
        scrolled = (
            abs(self.scroll_view.scroll_x - start_scroll_x) > 0.002
            or abs(self.scroll_view.scroll_y - start_scroll_y) > 0.002
        )
        if moved or scrolled:
            return handled

        cell = self.cell_at_local_position(
            touch.x - self.x,
            self.height - (touch.y - self.y),
        )
        if cell is None:
            return handled
        row_index, column_index = cell
        self.select_cell(row_index, column_index)
        if self.on_cell_selected is not None:
            self.on_cell_selected(row_index, column_index)
        return True

    def cell_at_local_position(self, local_x, local_top):
        if self.sheet is None or self.scroll_view is None:
            return None
        _, _, _, _, visible_left, visible_top = self.visible_range()
        if (
            visible_left <= local_x <= visible_left + self.row_header_width
            or visible_top <= local_top <= visible_top + self.cell_height
        ):
            return None

        column_index = math.floor((local_x - self.row_header_width) / self.cell_width)
        frozen_row_top = visible_top + self.cell_height
        frozen_row_bottom = frozen_row_top + self.cell_height
        if (
            self.freeze_top_row
            and visible_top > 0.5
            and frozen_row_top <= local_top <= frozen_row_bottom
        ):
            row_index = 0
        else:
            row_index = math.floor(local_top / self.cell_height) - 1
        if 0 <= row_index < self.sheet.row_count and 0 <= column_index < self.sheet.column_count:
            return row_index, column_index
        return None
