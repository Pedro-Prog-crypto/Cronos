from cronos.supervisor import ui_command


def test_windows_prefers_python_webview_window_without_browser_address():
    assert ui_command(platform="nt", webview_available=True)[1:] == ["-m", "cronos.desktop"]


def test_browser_fallback_remains_for_missing_webview_and_non_windows():
    assert ui_command(platform="nt", webview_available=False)[1:] == ["-m", "cronos.browser", "--managed"]
    assert ui_command(platform="posix", webview_available=True)[1:] == ["-m", "cronos.browser", "--managed"]
