# -claude-fix- Local development entry point that uses Python only.
import sys

from src.ai_workspace_account_manager.app import launch_browser_url, main


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].startswith(("http://", "https://")):
        raise SystemExit(launch_browser_url(sys.argv[1]))
    main()
