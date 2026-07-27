from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp


def apply_rounded_button_style(button, color, text_color=(1, 1, 1, 1)):
    button.background_normal = ""
    button.background_down = ""
    button.background_color = (0, 0, 0, 0)
    button.color = text_color
    button.bold = True

    with button.canvas.before:
        fill = Color(*color)
        background = RoundedRectangle(
            pos=button.pos,
            size=button.size,
            radius=[dp(7)],
        )

    def update_geometry(instance, *_args):
        background.pos = instance.pos
        background.size = instance.size

    def update_color(instance, *_args):
        factor = 0.55 if instance.disabled else (0.82 if instance.state == "down" else 1)
        fill.rgba = (color[0] * factor, color[1] * factor, color[2] * factor, color[3])

    button.bind(pos=update_geometry, size=update_geometry)
    button.bind(state=update_color, disabled=update_color)
    update_color(button)
