from pathlib import Path

from app.services.file_service import FileServiceError


SUPPORTED_MIME_EXTENSIONS = {
    "text/csv": ".csv",
    "application/csv": ".csv",
    "text/comma-separated-values": ".csv",
    "application/vnd.ms-excel": ".csv",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
}


def copy_android_content_uri(uri_text, target_root):
    try:
        from jnius import autoclass
    except ImportError as exc:
        raise FileServiceError("Android file access is unavailable in this build.") from exc

    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    Uri = autoclass("android.net.Uri")
    Channels = autoclass("java.nio.channels.Channels")
    ByteBuffer = autoclass("java.nio.ByteBuffer")
    FileOutputStream = autoclass("java.io.FileOutputStream")

    activity = PythonActivity.mActivity
    resolver = activity.getContentResolver()
    uri = Uri.parse(uri_text)
    destination = _destination_path(resolver, uri, target_root)

    input_stream = None
    output_stream = None
    input_channel = None
    output_channel = None

    try:
        input_stream = resolver.openInputStream(uri)
        if input_stream is None:
            raise FileServiceError("Selected file could not be opened.")

        output_stream = FileOutputStream(str(destination))
        input_channel = Channels.newChannel(input_stream)
        output_channel = Channels.newChannel(output_stream)
        buffer = ByteBuffer.allocate(64 * 1024)

        while input_channel.read(buffer) != -1:
            buffer.flip()
            while buffer.hasRemaining():
                output_channel.write(buffer)
            buffer.clear()
    except FileServiceError:
        raise
    except Exception as exc:
        raise FileServiceError(f"Could not copy selected file: {exc}") from exc
    finally:
        for stream in (output_channel, input_channel, output_stream, input_stream):
            if stream is not None:
                try:
                    stream.close()
                except Exception:
                    pass

    return str(destination)


def _destination_path(resolver, uri, target_root):
    imports_dir = Path(target_root) / "imports"
    imports_dir.mkdir(parents=True, exist_ok=True)

    name = _display_name(resolver, uri) or _fallback_name(resolver, uri)
    safe_name = _sanitize_filename(name)
    suffix = Path(safe_name).suffix.lower()
    if suffix not in {".csv", ".xlsx"}:
        inferred_suffix = SUPPORTED_MIME_EXTENSIONS.get(resolver.getType(uri) or "")
        if inferred_suffix:
            safe_name = f"{safe_name}{inferred_suffix}"

    destination = imports_dir / safe_name
    if not destination.exists():
        return destination

    stem = destination.stem
    suffix = destination.suffix
    for index in range(1, 1000):
        candidate = imports_dir / f"{stem}_{index}{suffix}"
        if not candidate.exists():
            return candidate

    raise FileServiceError("Could not create a local copy for the selected file.")


def _display_name(resolver, uri):
    from jnius import autoclass

    OpenableColumns = autoclass("android.provider.OpenableColumns")
    cursor = None
    try:
        cursor = resolver.query(uri, None, None, None, None)
        if cursor is not None and cursor.moveToFirst():
            index = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
            if index >= 0:
                return cursor.getString(index)
    except Exception:
        return None
    finally:
        if cursor is not None:
            cursor.close()
    return None


def _fallback_name(resolver, uri):
    segment = uri.getLastPathSegment() or "selected_file"
    suffix = SUPPORTED_MIME_EXTENSIONS.get(resolver.getType(uri) or "")
    if suffix and not segment.lower().endswith(suffix):
        return f"{segment}{suffix}"
    return segment


def _sanitize_filename(name):
    safe = "".join(char if char.isalnum() or char in "._- " else "_" for char in name)
    safe = safe.strip(" ._")
    return safe or "selected_file"
