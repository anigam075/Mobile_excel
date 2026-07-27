import os
import traceback

os.environ.setdefault("KIVY_NO_FILELOG", "1")

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager

from app.screens.editor_screen import EditorScreen
from app.screens.home_screen import HomeScreen
from app.services.background_worker import run_in_background
from app.services.file_service import FileServiceError, load_workbook, save_workbook


class MobileXLApp(App):
    title = "Mobile XL"

    def build(self):
        try:
            Window.softinput_mode = "resize"
        except Exception:
            pass

        self.workbook = None
        self.current_path = None
        self._open_task = None
        self._save_task = None

        self.manager = ScreenManager()
        self.home_screen = HomeScreen(name="home")
        self.editor_screen = EditorScreen(name="editor")
        self.manager.add_widget(self.home_screen)
        self.manager.add_widget(self.editor_screen)
        return self.manager

    def open_workbook(self, path):
        try:
            workbook = load_workbook(path, storage_dir=self.user_data_dir)
        except FileServiceError as exc:
            return False, str(exc)
        except Exception as exc:
            return False, self._exception_message(exc)

        self._activate_workbook(workbook, path)
        return True, "File loaded successfully."

    def open_workbook_async(self, path, on_complete, on_progress=None):
        if self._open_task is not None:
            on_complete(False, "Another file is already loading.")
            return self._open_task

        def progress(current, total, message):
            if on_progress is not None:
                Clock.schedule_once(
                    lambda *_, values=(current, total, message): on_progress(*values),
                    0,
                )

        def work(cancel_event):
            return load_workbook(
                path,
                storage_dir=self.user_data_dir,
                progress_callback=progress,
                cancel_event=cancel_event,
            )

        def succeeded(workbook):
            self._open_task = None
            self._activate_workbook(workbook, path)
            on_complete(True, "File loaded successfully.")

        def failed(error):
            self._open_task = None
            self.manager.current = "home"
            on_complete(False, self._exception_message(error))

        self._open_task = run_in_background(work, succeeded, failed)
        return self._open_task

    def cancel_open(self):
        if self._open_task is not None:
            self._open_task.cancel()

    def save_current_workbook(self, path=None):
        if not self.workbook:
            return False, "No workbook is open."
        target_path = path or self.current_path
        if not target_path:
            return False, "Choose Save As for a new file."
        try:
            save_workbook(self.workbook, target_path)
        except FileServiceError as exc:
            return False, str(exc)
        self._finish_save(target_path)
        return True, "Saved."

    def save_current_workbook_async(self, on_complete, path=None, on_progress=None):
        if not self.workbook:
            on_complete(False, "No workbook is open.")
            return None
        if self._save_task is not None:
            on_complete(False, "A save is already running.")
            return self._save_task

        target_path = path or self.current_path
        if not target_path:
            on_complete(False, "Choose Save As for a new file.")
            return None

        def progress(current, total, message):
            if on_progress is not None:
                Clock.schedule_once(
                    lambda *_, values=(current, total, message): on_progress(*values),
                    0,
                )

        def work(cancel_event):
            save_workbook(
                self.workbook,
                target_path,
                progress_callback=progress,
                cancel_event=cancel_event,
            )
            return target_path

        def succeeded(saved_path):
            self._save_task = None
            self._finish_save(saved_path)
            on_complete(True, "Saved.")

        def failed(error):
            self._save_task = None
            on_complete(False, self._exception_message(error))

        self._save_task = run_in_background(work, succeeded, failed)
        return self._save_task

    def _activate_workbook(self, workbook, path):
        previous = self.workbook
        self.workbook = workbook
        self.current_path = path
        self.editor_screen.set_workbook(workbook)
        self.manager.current = "editor"
        if previous is not None and hasattr(previous, "close"):
            previous.close(remove=True)

    def _finish_save(self, target_path):
        self.current_path = target_path
        self.workbook.path = target_path
        self.workbook.dirty = False
        self.editor_screen.refresh_title()

    def _exception_message(self, error):
        if isinstance(error, FileServiceError):
            return str(error)
        return "".join(traceback.format_exception_only(type(error), error)).strip()

    def on_stop(self):
        if self.workbook is not None and hasattr(self.workbook, "close"):
            self.workbook.close(remove=True)


if __name__ == "__main__":
    MobileXLApp().run()
