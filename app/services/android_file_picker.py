_REQUEST_CODE = 42017
_ERROR_PREFIX = "__mobilexl_picker_error__:"
_callback = None
_bound = False


def open_android_file(on_selection):
    global _callback, _bound

    from android import activity, mActivity
    from jnius import autoclass, cast

    ActivityNotFoundException = autoclass("android.content.ActivityNotFoundException")
    Intent = autoclass("android.content.Intent")
    String = autoclass("java.lang.String")

    if not _bound:
        activity.bind(on_activity_result=_on_activity_result)
        _bound = True

    _callback = on_selection

    intent = Intent(Intent.ACTION_OPEN_DOCUMENT)
    intent.addCategory(Intent.CATEGORY_OPENABLE)
    intent.setType("*/*")
    intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
    intent.addFlags(Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION)

    chooser = Intent.createChooser(
        intent,
        cast("java.lang.CharSequence", String("Open CSV or Excel File")),
    )

    try:
        mActivity.startActivityForResult(chooser, _REQUEST_CODE)
    except ActivityNotFoundException:
        fallback = Intent(Intent.ACTION_GET_CONTENT)
        fallback.addCategory(Intent.CATEGORY_OPENABLE)
        fallback.setType("*/*")
        fallback.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        mActivity.startActivityForResult(fallback, _REQUEST_CODE)


def _on_activity_result(request_code, result_code, data):
    global _callback

    if request_code != _REQUEST_CODE:
        return

    callback = _callback
    _callback = None
    if callback is None:
        return

    try:
        selection = _selection_from_activity_result(result_code, data)
    except Exception as exc:
        selection = [f"{_ERROR_PREFIX}{type(exc).__name__}: {exc}"]

    _deliver_selection(callback, selection)


def _selection_from_activity_result(result_code, data):
    from jnius import autoclass

    Activity = autoclass("android.app.Activity")
    if result_code != Activity.RESULT_OK or data is None:
        return []

    uri = data.getData()
    if uri is None:
        clip_data = data.getClipData()
        if clip_data is not None and clip_data.getItemCount() > 0:
            uri = clip_data.getItemAt(0).getUri()

    if uri is None:
        return []

    _persist_read_permission(data, uri)
    return [uri.toString()]


def _deliver_selection(callback, selection):
    from kivy.clock import Clock

    Clock.schedule_once(lambda *_: callback(selection), 0)


def _persist_read_permission(data, uri):
    try:
        from android import mActivity
        from jnius import autoclass

        Intent = autoclass("android.content.Intent")
        flags = data.getFlags() & Intent.FLAG_GRANT_READ_URI_PERMISSION
        if flags:
            mActivity.getContentResolver().takePersistableUriPermission(uri, flags)
    except Exception:
        pass
