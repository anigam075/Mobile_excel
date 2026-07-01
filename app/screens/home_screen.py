from pathlib import Path

from kivy.app import App
from kivy.metrics import dp
from kivy.utils import platform
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.filechooser import FileChooserIconView
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen


class HomeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.message_label = None
        self._build()

    def _build(self):
        root = BoxLayout(orientation="vertical", padding=dp(18), spacing=dp(14))

        title = Label(
            text="Mobile XL",
            font_size="28sp",
            bold=True,
            size_hint_y=None,
            height=dp(50),
            color=(0.09, 0.12, 0.16, 1),
        )
        subtitle = Label(
            text="Open, edit, and save CSV or Excel files.",
            font_size="15sp",
            size_hint_y=None,
            height=dp(34),
            color=(0.25, 0.29, 0.34, 1),
        )

        open_button = Button(
            text="Open CSV or Excel File",
            size_hint_y=None,
            height=dp(52),
            background_color=(0.12, 0.34, 0.56, 1),
        )
        open_button.bind(on_release=lambda *_: self.open_file_picker())

        new_button = Button(
            text="Create New CSV",
            size_hint_y=None,
            height=dp(52),
            background_color=(0.18, 0.45, 0.36, 1),
        )
        new_button.bind(on_release=lambda *_: App.get_running_app().create_blank_csv())

        self.message_label = Label(
            text="",
            font_size="14sp",
            halign="left",
            valign="top",
            color=(0.65, 0.15, 0.12, 1),
        )
        self.message_label.bind(size=self._sync_message_text_size)

        root.add_widget(title)
        root.add_widget(subtitle)
        root.add_widget(open_button)
        root.add_widget(new_button)
        root.add_widget(self.message_label)
        self.add_widget(root)

    def _sync_message_text_size(self, instance, size):
        instance.text_size = size

    def show_message(self, message):
        self.message_label.text = message

    def open_file_picker(self):
        if platform == "android":
            try:
                from plyer import filechooser

                filechooser.open_file(
                    on_selection=self._open_android_selection,
                    filters=[("Spreadsheet files", "*.csv", "*.xlsx")],
                )
                return
            except Exception as exc:
                self.show_message(f"Native file picker unavailable: {exc}")

        content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(8))
        chooser = FileChooserIconView(
            path=str(Path.home()),
            filters=["*.csv", "*.xlsx"],
            multiselect=False,
        )
        actions = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        cancel = Button(text="Cancel")
        open_file = Button(text="Open")
        actions.add_widget(cancel)
        actions.add_widget(open_file)
        content.add_widget(chooser)
        content.add_widget(actions)

        popup = Popup(title="Choose a CSV or Excel file", content=content, size_hint=(0.96, 0.9))
        cancel.bind(on_release=popup.dismiss)
        open_file.bind(on_release=lambda *_: self._open_selected_file(chooser, popup))
        popup.open()

    def _open_selected_file(self, chooser, popup):
        if not chooser.selection:
            self.show_message("Select a .csv or .xlsx file first.")
            return
        popup.dismiss()
        App.get_running_app().open_workbook(chooser.selection[0])

    def _open_android_selection(self, selection):
        if not selection:
            return
        App.get_running_app().open_workbook(selection[0])
