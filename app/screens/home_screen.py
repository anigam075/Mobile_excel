from pathlib import Path
from urllib.parse import unquote, urlparse

from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.utils import platform
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.filechooser import FileChooserIconView
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.progressbar import ProgressBar
from kivy.uix.screenmanager import Screen


PICKER_ERROR_PREFIX = "__mobilexl_picker_error__:"


class HomeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.message_label = None
        self.path_label = None
        self.local_path_label = None
        self.loading_label = None
        self.loading_bar = None
        self._build()

    def _build(self):
        root = BoxLayout(orientation="vertical", padding=dp(18), spacing=dp(14))

        title = Label(
            text="Mobile XL",
            font_size="28sp",
            bold=True,
            size_hint_y=None,
            height=dp(50),
            color=(0.88, 0.92, 0.98, 1),
        )
        subtitle = Label(
            text="Open, edit, and save CSV or Excel files.",
            font_size="15sp",
            size_hint_y=None,
            height=dp(34),
            color=(0.74, 0.78, 0.86, 1),
        )

        open_button = Button(
            text="Open CSV or Excel File",
            size_hint_y=None,
            height=dp(52),
            background_color=(0.12, 0.34, 0.56, 1),
        )
        open_button.bind(on_release=lambda *_: self.open_file_picker())

        self.path_label = Label(
            text="Selected file: none",
            font_size="13sp",
            size_hint_y=None,
            height=dp(62),
            halign="left",
            valign="top",
            color=(0.86, 0.9, 0.96, 1),
        )
        self.path_label.bind(size=self._sync_message_text_size)

        self.local_path_label = Label(
            text="Local file: none",
            font_size="13sp",
            size_hint_y=None,
            height=dp(62),
            halign="left",
            valign="top",
            color=(0.86, 0.9, 0.96, 1),
        )
        self.local_path_label.bind(size=self._sync_message_text_size)

        self.loading_label = Label(
            text="",
            font_size="14sp",
            size_hint_y=None,
            height=dp(26),
            color=(0.43, 0.72, 1, 1),
        )

        self.loading_bar = ProgressBar(max=1, value=0, size_hint_y=None, height=dp(6))
        self.loading_bar.opacity = 0

        self.message_label = Label(
            text="",
            font_size="14sp",
            halign="left",
            valign="top",
            color=(1, 0.42, 0.36, 1),
        )
        self.message_label.bind(size=self._sync_message_text_size)

        root.add_widget(title)
        root.add_widget(subtitle)
        root.add_widget(open_button)
        root.add_widget(self.path_label)
        root.add_widget(self.local_path_label)
        root.add_widget(self.loading_label)
        root.add_widget(self.loading_bar)
        root.add_widget(self.message_label)
        self.add_widget(root)

    def _sync_message_text_size(self, instance, size):
        instance.text_size = size

    def show_message(self, message):
        self.message_label.text = message

    def show_selected_path(self, path):
        self.path_label.text = f"Selected file:\n{path or 'none'}"

    def show_local_path(self, path):
        self.local_path_label.text = f"Local file:\n{path or 'none'}"

    def set_loading(self, is_loading, message="Loading file..."):
        self.loading_label.text = message if is_loading else ""
        self.loading_bar.opacity = 1 if is_loading else 0
        self.loading_bar.value = 0.6 if is_loading else 0

    def open_file_picker(self):
        self.show_message("")
        self.show_selected_path("Waiting for picker selection...")
        self.show_local_path("none")
        self.set_loading(False)

        if platform == "android":
            try:
                from app.services.android_file_picker import open_android_file

                open_android_file(self._open_android_selection)
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
        selected = chooser.selection[0]
        self.show_selected_path(selected)
        self.show_local_path(selected)
        self.show_message("")
        self.set_loading(True)
        popup.dismiss()
        Clock.schedule_once(lambda *_: self._open_resolved_workbook(selected), 0)

    def _open_android_selection(self, selection):
        if not selection:
            self.show_selected_path("No selection returned by picker.")
            self.show_local_path("none")
            self.set_loading(False)
            self.show_message("No file selected, or Android returned an empty picker result.")
            return
        selected = str(selection[0])

        self.show_selected_path(selected)
        self.show_local_path("Resolving Android file...")
        self.show_message("")
        self.set_loading(True)

        if selected.startswith(PICKER_ERROR_PREFIX):
            self.set_loading(False)
            self.show_message(selected.removeprefix(PICKER_ERROR_PREFIX))
            return

        Clock.schedule_once(lambda *_: self._resolve_and_open_android_selection(selected), 0)

    def _resolve_and_open_android_selection(self, selected):
        running_app = App.get_running_app()

        try:
            selected = self._resolve_android_selection(selected, running_app.user_data_dir)
        except Exception as exc:
            self.set_loading(False)
            self.show_local_path("none")
            self.show_message(f"{type(exc).__name__}: {exc}")
            return

        self.show_local_path(selected)
        self._open_resolved_workbook(selected)

    def _open_resolved_workbook(self, selected):
        try:
            success, message = App.get_running_app().open_workbook(selected)
        except Exception as exc:
            success = False
            message = f"{type(exc).__name__}: {exc}"

        self.set_loading(False)
        if not success:
            self.show_message(message)

    def _resolve_android_selection(self, selected, target_dir):
        if selected.startswith("content://"):
            from app.services.android_file_service import copy_android_content_uri

            return copy_android_content_uri(selected, target_dir)

        if selected.startswith("file://"):
            return unquote(urlparse(selected).path)

        return selected
