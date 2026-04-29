# -claude-fix- Local development entry point that uses Python only.
import re
import sys

from src.ai_workspace_account_manager.app import launch_browser_url, main


if __name__ == "__main__":
    # -claude-fix- Claude may pass the OAuth URL with extra quoting; handle it before opening the main UI.
    raw_args = " ".join(sys.argv[1:])
    match = re.search(r"https?://\\?\"?[^\\s\"]+", raw_args)
    if match:
        url = match.group(0).strip("\\\"'")
        raise SystemExit(launch_browser_url(url))
    main()
