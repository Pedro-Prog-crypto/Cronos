from cronos.supervisor import ui_command


def test_windows_opens_in_default_browser_not_python_webview():
    assert ui_command(platform="nt", webview_available=True)[1:] == ["-m", "cronos.browser", "--managed"]


def test_browser_fallback_remains_for_missing_webview_and_non_windows():
    assert ui_command(platform="nt", webview_available=False)[1:] == ["-m", "cronos.browser", "--managed"]
    assert ui_command(platform="posix", webview_available=True)[1:] == ["-m", "cronos.browser", "--managed"]
