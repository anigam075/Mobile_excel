from kivy.clock import Clock
from kivy.core.text import Label as CoreLabel
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.uix.widget import Widget


def calculate_thumb_geometry(
    track_length,
    viewport_length,
    content_length,
    minimum_length,
):
    if track_length <= 0 or content_length <= viewport_length:
        return 0, 0
    ratio = max(0, min(1, viewport_length / content_length))
    thumb_length = min(track_length, max(minimum_length, track_length * ratio))
    return thumb_length, max(0, track_length - thumb_length)


def clamp_scroll_value(value):
    return max(0, min(1, value))


class FastScroller(Widget):
    def __init__(
        self,
        scroll_view,
        content_widget,
        orientation="vertical",
        label_provider=None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        if orientation not in ("vertical", "horizontal"):
            raise ValueError("orientation must be vertical or horizontal")
        self.scroll_view = scroll_view
        self.content_widget = content_widget
        self.orientation = orientation
        self.label_provider = label_provider
        self.active = False
        self._drag_offset = 0
        self._thumb_position = 0
        self._thumb_length = 0
        self._travel = 0
        self._visible = False
        self._redraw_trigger = Clock.create_trigger(self._redraw, 0)

        scroll_view.bind(
            scroll_x=self._schedule_redraw,
            scroll_y=self._schedule_redraw,
            size=self._schedule_redraw,
        )
        content_widget.bind(size=self._schedule_redraw)
        self.bind(pos=self._schedule_redraw, size=self._schedule_redraw)
        self._schedule_redraw()

    def _schedule_redraw(self, *_args):
        self._redraw_trigger()

    def _axis_metrics(self):
        padding = dp(7)
        if self.orientation == "vertical":
            return (
                self.y + padding,
                max(0, self.height - padding * 2),
                self.scroll_view.height,
                self.content_widget.height,
                self.scroll_view.scroll_y,
            )
        return (
            self.x + padding,
            max(0, self.width - padding * 2),
            self.scroll_view.width,
            self.content_widget.width,
            self.scroll_view.scroll_x,
        )

    def _update_geometry(self):
        track_start, track_length, viewport_length, content_length, value = self._axis_metrics()
        thumb_length, travel = calculate_thumb_geometry(
            track_length,
            viewport_length,
            content_length,
            dp(52),
        )
        self._visible = thumb_length > 0
        self._thumb_length = thumb_length
        self._travel = travel
        self._thumb_position = track_start + clamp_scroll_value(value) * travel

    def _thumb_bounds(self, expanded=False):
        thickness = dp(18) if expanded else dp(5)
        if self.orientation == "vertical":
            return (
                self.right - thickness - dp(3),
                self._thumb_position,
                thickness,
                self._thumb_length,
            )
        return (
            self._thumb_position,
            self.y + dp(3),
            self._thumb_length,
            thickness,
        )

    def _redraw(self, *_args):
        self._update_geometry()
        self.canvas.clear()
        if not self._visible:
            return

        x, y, width, height = self._thumb_bounds(expanded=self.active)
        with self.canvas:
            Color(0.12, 0.72, 0.78, 0.96 if self.active else 0.62)
            RoundedRectangle(pos=(x, y), size=(width, height), radius=[dp(5)])
            if self.active and self.label_provider is not None:
                self._draw_preview(self.label_provider(self._scroll_value()))

    def _draw_preview(self, text):
        label = CoreLabel(
            text=str(text),
            font_size=sp(13),
            bold=True,
            color=(0.94, 0.98, 1, 1),
        )
        label.refresh()
        bubble_width = max(dp(70), label.texture.size[0] + dp(22))
        bubble_height = dp(38)
        if self.orientation == "vertical":
            x = self.x - bubble_width - dp(8)
            y = max(
                self.y,
                min(
                    self.top - bubble_height,
                    self._thumb_position + self._thumb_length / 2 - bubble_height / 2,
                ),
            )
        else:
            x = max(
                self.x,
                min(
                    self.right - bubble_width,
                    self._thumb_position + self._thumb_length / 2 - bubble_width / 2,
                ),
            )
            y = self.top + dp(8)

        Color(0.055, 0.075, 0.115, 0.96)
        RoundedRectangle(pos=(x, y), size=(bubble_width, bubble_height), radius=[dp(7)])
        Color(1, 1, 1, 1)
        RoundedRectangle(
            pos=(
                x + (bubble_width - label.texture.size[0]) / 2,
                y + (bubble_height - label.texture.size[1]) / 2,
            ),
            size=label.texture.size,
            texture=label.texture,
        )

    def _scroll_value(self):
        if self.orientation == "vertical":
            return self.scroll_view.scroll_y
        return self.scroll_view.scroll_x

    def _touch_axis(self, touch):
        return touch.y if self.orientation == "vertical" else touch.x

    def _touch_hits_thumb(self, touch):
        x, y, width, height = self._thumb_bounds(expanded=True)
        hit_padding = dp(7)
        return (
            x - hit_padding <= touch.x <= x + width + hit_padding
            and y - hit_padding <= touch.y <= y + height + hit_padding
        )

    def on_touch_down(self, touch):
        self._update_geometry()
        if (
            not self._visible
            or not self.collide_point(*touch.pos)
            or not self._touch_hits_thumb(touch)
        ):
            return False
        self.active = True
        self._drag_offset = self._touch_axis(touch) - self._thumb_position
        touch.grab(self)
        self._schedule_redraw()
        return True

    def on_touch_move(self, touch):
        if touch.grab_current is not self:
            return False
        track_start = self._axis_metrics()[0]
        value = 0 if self._travel <= 0 else (
            self._touch_axis(touch) - self._drag_offset - track_start
        ) / self._travel
        value = clamp_scroll_value(value)
        if self.orientation == "vertical":
            self.scroll_view.scroll_y = value
        else:
            self.scroll_view.scroll_x = value
        self._schedule_redraw()
        return True

    def on_touch_up(self, touch):
        if touch.grab_current is not self:
            return False
        touch.ungrab(self)
        self.active = False
        self._schedule_redraw()
        return True
