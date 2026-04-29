# -claude-fix- Python/Tkinter implementation that detects missing AI CLIs before launch.
from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from tkinter import END, BOTH, LEFT, RIGHT, X, Y, StringVar, Tk, Toplevel, filedialog, messagebox
from tkinter import ttk


APP_NAME = "AI Workspace Account Manager"
NONE_VALUE = "__none__"


TEXT = {
    "zh": {
        "title": "AI 工作空间账号管理器",
        "workspace": "工作空间",
        "path": "路径",
        "add_workspace": "添加工作空间",
        "open_vscode": "打开 VS Code",
        "save": "保存映射",
        "launch": "启动",
        "login": "登录",
        "switch": "切换账号",
        "refresh": "刷新状态",
        "accounts": "账号管理",
        "states": "账号状态",
        "provider": "平台",
        "account": "账号",
        "email": "邮箱",
        "add_account": "添加账号",
        "delete_account": "删除账号",
        "default": "默认",
        "none": "空",
        "cli_ok": "CLI 可用",
        "cli_missing": "CLI 缺失",
        "saved": "已保存配置。",
        "no_cli": "该平台 CLI 不存在，请先安装或在 config.json 配置 command。",
        "no_vscode": "未找到 VS Code，请在 config.json 配置 settings.vscodeCommand。",
        "subtitle": "账号登录一次长期保存，工作空间自动切换专属环境",
        "login_hint": "将打开该账号的专属浏览器窗口；请在里面登录对应邮箱，登录态会保存在账号目录。",
        "switch_hint": "已切换账号。已打开的 VS Code 不会自动换环境，请重新打开对应工作空间。",
        "lang": "English",
    },
    "en": {
        "title": "AI Workspace Account Manager",
        "workspace": "Workspace",
        "path": "Path",
        "add_workspace": "Add workspace",
        "open_vscode": "Open VS Code",
        "save": "Save mapping",
        "launch": "Launch",
        "login": "Login",
        "switch": "Switch account",
        "refresh": "Refresh status",
        "accounts": "Account management",
        "states": "Account status",
        "provider": "Provider",
        "account": "Account",
        "email": "Email",
        "add_account": "Add account",
        "delete_account": "Delete account",
        "default": "Default",
        "none": "None",
        "cli_ok": "CLI OK",
        "cli_missing": "CLI missing",
        "saved": "Config saved.",
        "no_cli": "This provider CLI is missing. Install it or set command in config.json.",
        "no_vscode": "VS Code was not found. Set settings.vscodeCommand in config.json.",
        "subtitle": "Login once, keep sessions, and auto-switch accounts per workspace",
        "login_hint": "A dedicated browser window will open for this account. Sign in with the matching email; the session stays in the account folder.",
        "switch_hint": "Account switched. Existing VS Code windows keep their old environment; reopen the workspace.",
        "lang": "中文",
    },
}


def app_dir() -> Path:
    # -claude-fix- Store runtime config beside the executable, or at repo root during development.
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def expand_path(value: str) -> str:
    return os.path.expanduser(os.path.expandvars(value or ""))


def default_config() -> dict:
    account_root = str(Path.home() / ".ai-workspace-account-manager" / "accounts")
    profile_root = str(Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "AIWorkspaceAccountManager" / "vscode-profiles")
    providers = [
        {
            "id": "openai",
            "name": "OpenAI",
            "command": "codex",
            "envVar": "CODEX_HOME",
            "accountsRoot": str(Path(account_root) / "openai"),
            "statusArgs": "login status",
            "loginArgs": "login",
        },
        {
            "id": "claude",
            "name": "Claude",
            "command": "claude",
            "envVar": "CLAUDE_CONFIG_DIR",
            "accountsRoot": str(Path(account_root) / "claude"),
            "statusArgs": "auth status --text",
            "loginArgs": "auth login --claudeai --email {email}",
        },
        {
            "id": "gemini",
            "name": "Gemini",
            "command": "gemini",
            "envVar": "GEMINI_CONFIG_DIR",
            "accountsRoot": str(Path(account_root) / "gemini"),
            "statusArgs": "--version",
            "loginArgs": "",
        },
        {
            "id": "glm",
            "name": "GLM",
            "command": "",
            "envVar": "GLM_CONFIG_DIR",
            "accountsRoot": str(Path(account_root) / "glm"),
            "statusArgs": "",
            "loginArgs": "",
        },
        {
            "id": "deepseek",
            "name": "DeepSeek",
            "command": "",
            "envVar": "DEEPSEEK_CONFIG_DIR",
            "accountsRoot": str(Path(account_root) / "deepseek"),
            "statusArgs": "",
            "loginArgs": "",
        },
    ]
    return {
        "settings": {
            "language": "zh",
            "vscodeCommand": "code",
            "profileRoot": profile_root,
            "accountRoot": account_root,
        },
        "providers": providers,
        "accounts": [],
        "workspaces": [],
        "defaults": {p["id"]: "" for p in providers},
    }


def normalize_config(config: dict) -> dict:
    defaults = default_config()
    # -claude-fix- Migrate legacy desktop config while preserving accounts and workspace mappings.
    legacy_language = config.get("language")
    config.setdefault("settings", {})
    had_settings_language = bool(config["settings"].get("language"))
    for key, value in defaults["settings"].items():
        config["settings"].setdefault(key, value)
    if legacy_language and not had_settings_language:
        config["settings"]["language"] = legacy_language
    config.setdefault("providers", defaults["providers"])
    config.setdefault("accounts", [])
    config.setdefault("workspaces", [])
    config.setdefault("defaults", {})
    existing_provider_ids = {p["id"] for p in config["providers"]}
    for provider in defaults["providers"]:
        if provider["id"] not in existing_provider_ids:
            config["providers"].append(provider)
    for provider in config["providers"]:
        # -claude-fix- Reuse legacy zh/en provider labels instead of falling back to raw provider ids.
        provider.setdefault("name", provider.get("zh") or provider.get("en") or provider["id"])
        provider.setdefault("command", "")
        provider.setdefault("envVar", "")
        provider.setdefault("accountsRoot", str(Path(config["settings"]["accountRoot"]) / provider["id"]))
        provider.setdefault("statusArgs", "")
        provider.setdefault("loginArgs", "")
        config["defaults"].setdefault(provider["id"], "")
    for account in config["accounts"]:
        provider = provider_by_id(config, account.get("provider", ""))
        if provider and not account.get("configDir"):
            account["configDir"] = str(Path(expand_path(provider["accountsRoot"])) / account["id"])
    for workspace in config["workspaces"]:
        workspace.setdefault("mappings", {})
        for provider in config["providers"]:
            workspace["mappings"].setdefault(provider["id"], "")
    return config


def provider_by_id(config: dict, provider_id: str) -> dict | None:
    for provider in config.get("providers", []):
        if provider.get("id") == provider_id:
            return provider
    return None


def resolve_command(command: str) -> str:
    # -claude-fix- Detect AI CLI availability before enabling launch/login buttons.
    command = expand_path(command)
    if not command:
        return ""
    path = Path(command)
    if path.exists():
        return str(path)
    found = shutil.which(command)
    return found or ""


def split_args(args: str) -> list[str]:
    if not args:
        return []
    return shlex.split(args, posix=False)


def detached_flags() -> int:
    if os.name != "nt":
        return 0
    return getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)


def hidden_process_flags() -> int:
    if os.name != "nt":
        return 0
    # -claude-fix- Hide provider login helper consoles; the browser window is the intended login UI.
    return detached_flags() | getattr(subprocess, "CREATE_NO_WINDOW", 0)


def hidden_startupinfo() -> subprocess.STARTUPINFO | None:
    if os.name != "nt":
        return None
    startupinfo = subprocess.STARTUPINFO()
    # -claude-fix- Ensure cmd/bat login wrappers stay hidden even when Windows creates a shell host.
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = 0
    return startupinfo


def find_browser_executable() -> str:
    candidates = [
        os.environ.get("PROGRAMFILES", "") + r"\Microsoft\Edge\Application\msedge.exe",
        os.environ.get("PROGRAMFILES(X86)", "") + r"\Microsoft\Edge\Application\msedge.exe",
        os.environ.get("PROGRAMFILES", "") + r"\Google\Chrome\Application\chrome.exe",
        os.environ.get("PROGRAMFILES(X86)", "") + r"\Google\Chrome\Application\chrome.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    return shutil.which("msedge") or shutil.which("chrome") or ""


def launch_browser_url(url: str) -> int:
    browser = os.environ.get("AIAM_BROWSER_EXE") or find_browser_executable()
    profile = os.environ.get("AIAM_BROWSER_PROFILE_DIR")
    if not browser or not profile:
        return 1
    Path(profile).mkdir(parents=True, exist_ok=True)
    # -claude-fix- Let the packaged Python app act as a no-console OAuth browser launcher.
    subprocess.Popen([browser, f"--user-data-dir={profile}", "--no-first-run", "--new-window", url], creationflags=detached_flags())
    return 0


def account_browser_launcher(account: dict) -> dict[str, str]:
    config_dir = Path(expand_path(account.get("configDir", "")))
    browser = find_browser_executable()
    if os.name != "nt" or not browser or not config_dir:
        return {}
    browser_profile = config_dir / "browser-profile"
    browser_profile.mkdir(parents=True, exist_ok=True)
    env = {
        "AIAM_BROWSER_EXE": browser,
        "AIAM_BROWSER_PROFILE_DIR": str(browser_profile),
    }
    if getattr(sys, "frozen", False):
        env["BROWSER"] = sys.executable
        return env
    wrapper = config_dir / "open-claude-login.cmd"
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    launcher = str(pythonw if pythonw.exists() else Path(sys.executable))
    run_script = Path(__file__).resolve().parents[2] / "run.py"
    # -claude-fix- Development fallback avoids PowerShell while preserving each account's browser login state.
    wrapper.write_text(
        "\r\n".join(
            [
                "@echo off",
                f'start "" "{launcher}" "{run_script}" %*',
                "exit /b 0",
                "",
            ]
        ),
        encoding="ascii",
    )
    env["BROWSER"] = str(wrapper)
    return env


class AccountManagerApp:
    def __init__(self) -> None:
        self.root = Tk()
        self.config_path = app_dir() / "config.json"
        self.config = self.load_config()
        self.provider_boxes: dict[str, ttk.Combobox] = {}
        self.provider_cli_labels: dict[str, ttk.Label] = {}
        self.launch_buttons: dict[str, ttk.Button] = {}
        self.login_buttons: dict[str, ttk.Button] = {}
        self.switch_buttons: dict[str, ttk.Button] = {}
        self.refreshing = False
        self.workspace_var = StringVar()
        self.path_var = StringVar()
        self.account_provider_var = StringVar()
        self.account_id_var = StringVar()
        self.account_email_var = StringVar()
        self.log_var = StringVar()
        self.build_ui()
        self.apply_language()
        self.refresh_all()

    def t(self, key: str) -> str:
        lang = self.config.get("settings", {}).get("language", "zh")
        return TEXT.get(lang, TEXT["zh"]).get(key, key)

    def load_config(self) -> dict:
        if self.config_path.exists():
            data = json.loads(self.config_path.read_text(encoding="utf-8"))
        else:
            data = default_config()
        data = normalize_config(data)
        self.save_config(data)
        return data

    def save_config(self, config: dict | None = None) -> None:
        # -claude-fix- Keep real account data local in config.json, which is ignored by Git.
        payload = self.config if config is None else config
        self.config_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def build_ui(self) -> None:
        self.root.title(APP_NAME)
        self.root.geometry("1440x900")
        self.root.minsize(1320, 780)

        style = ttk.Style()
        if "clam" in style.theme_names():
            style.theme_use("clam")
        # -claude-fix- Use a softer anime-inspired palette while keeping the desktop tool readable.
        self.root.configure(bg="#f8f4ff")
        style.configure(".", background="#f8f4ff", foreground="#34284f", font=("Microsoft YaHei UI", 9))
        style.configure("TFrame", background="#f8f4ff")
        style.configure("TLabelframe", background="#f8f4ff", foreground="#6d5bb8")
        style.configure("TLabelframe.Label", background="#f8f4ff", foreground="#6d5bb8", font=("Microsoft YaHei UI", 10, "bold"))
        style.configure("TLabel", background="#f8f4ff", foreground="#34284f")
        style.configure("Hero.TLabel", background="#f8f4ff", foreground="#7b62d9", font=("Microsoft YaHei UI", 17, "bold"))
        style.configure("Subtle.TLabel", background="#f8f4ff", foreground="#8b7ab8")
        style.configure("TButton", padding=(10, 5), background="#efe7ff", foreground="#34284f")
        style.map("TButton", background=[("active", "#e3d6ff")])
        style.configure("Accent.TButton", padding=(12, 6), background="#dcd0ff", foreground="#2f2550")
        style.configure("Treeview", background="#fffaff", fieldbackground="#fffaff", foreground="#34284f", rowheight=24)
        style.configure("Treeview.Heading", background="#eadfff", foreground="#5b4a9c", font=("Microsoft YaHei UI", 9, "bold"))

        top = ttk.Frame(self.root, padding=16)
        top.pack(fill=X)
        title_group = ttk.Frame(top)
        title_group.pack(side=LEFT)
        self.title_label = ttk.Label(title_group, style="Hero.TLabel")
        self.title_label.pack(side=LEFT)
        self.subtitle_label = ttk.Label(title_group, style="Subtle.TLabel")
        self.subtitle_label.pack(anchor="w")
        self.lang_button = ttk.Button(top, command=self.toggle_language)
        self.lang_button.pack(side=RIGHT)

        workspace = ttk.Frame(self.root, padding=(16, 0, 16, 8))
        workspace.pack(fill=X)
        self.workspace_label = ttk.Label(workspace, width=14)
        self.workspace_label.pack(side=LEFT)
        self.workspace_box = ttk.Combobox(workspace, textvariable=self.workspace_var, state="readonly", width=50)
        self.workspace_box.bind("<<ComboboxSelected>>", lambda _event: self.refresh_workspace_selection())
        self.workspace_box.pack(side=LEFT, padx=(0, 12))
        self.add_workspace_button = ttk.Button(workspace, command=self.add_workspace)
        self.add_workspace_button.pack(side=LEFT, padx=4)
        self.open_vscode_button = ttk.Button(workspace, command=self.open_vscode, style="Accent.TButton")
        self.open_vscode_button.pack(side=LEFT, padx=4)
        self.save_button = ttk.Button(workspace, command=self.save_workspace_mappings)
        self.save_button.pack(side=LEFT, padx=4)
        self.refresh_button = ttk.Button(workspace, command=self.refresh_status_grid)
        self.refresh_button.pack(side=LEFT, padx=4)

        path_frame = ttk.Frame(self.root, padding=(16, 0, 16, 8))
        path_frame.pack(fill=X)
        self.path_label = ttk.Label(path_frame, width=14)
        self.path_label.pack(side=LEFT)
        self.path_entry = ttk.Entry(path_frame, textvariable=self.path_var, state="readonly")
        self.path_entry.pack(side=LEFT, fill=X, expand=True)

        provider_frame = ttk.Frame(self.root, padding=(16, 4, 16, 16))
        provider_frame.pack(fill=X)
        for row, provider in enumerate(self.config["providers"]):
            ttk.Label(provider_frame, text=provider["name"], width=14).grid(row=row, column=0, sticky="w", pady=4)
            var = StringVar()
            # -claude-fix- Widen account selectors so long account ids and emails remain visible.
            box = ttk.Combobox(provider_frame, textvariable=var, state="readonly", width=64)
            box.provider_id = provider["id"]  # type: ignore[attr-defined]
            box.bind("<<ComboboxSelected>>", self.provider_selection_changed)
            box.grid(row=row, column=1, sticky="w", padx=(0, 10), pady=4)
            self.provider_boxes[provider["id"]] = box

            cli_label = ttk.Label(provider_frame, width=12)
            cli_label.grid(row=row, column=2, sticky="w", padx=(0, 10), pady=4)
            self.provider_cli_labels[provider["id"]] = cli_label

            launch = ttk.Button(provider_frame, command=lambda p=provider["id"]: self.launch_provider(p, False))
            launch.grid(row=row, column=3, padx=4, pady=4)
            self.launch_buttons[provider["id"]] = launch

            login = ttk.Button(provider_frame, command=lambda p=provider["id"]: self.launch_provider(p, True))
            login.grid(row=row, column=4, padx=4, pady=4)
            self.login_buttons[provider["id"]] = login

            switch = ttk.Button(provider_frame, command=lambda p=provider["id"]: self.switch_provider_account(p))
            switch.grid(row=row, column=5, padx=4, pady=4)
            self.switch_buttons[provider["id"]] = switch

        bottom = ttk.PanedWindow(self.root, orient="horizontal")
        bottom.pack(fill=BOTH, expand=True, padx=16, pady=(0, 16))
        account_panel = ttk.LabelFrame(bottom)
        status_panel = ttk.LabelFrame(bottom)
        bottom.add(account_panel, weight=1)
        bottom.add(status_panel, weight=1)
        self.account_panel = account_panel
        self.status_panel = status_panel

        self.accounts_tree = ttk.Treeview(account_panel, columns=("provider", "account", "email", "config"), show="headings", height=9)
        for col, width in (("provider", 110), ("account", 180), ("email", 260), ("config", 520)):
            self.accounts_tree.heading(col, text=col)
            self.accounts_tree.column(col, width=width, stretch=True)
        self.accounts_tree.pack(fill=BOTH, expand=True, padx=10, pady=10)

        account_inputs = ttk.Frame(account_panel, padding=10)
        account_inputs.pack(fill=X)
        self.account_provider_box = ttk.Combobox(account_inputs, textvariable=self.account_provider_var, state="readonly", width=12)
        self.account_provider_box.pack(side=LEFT, padx=(0, 8))
        ttk.Entry(account_inputs, textvariable=self.account_id_var, width=26).pack(side=LEFT, padx=(0, 8))
        ttk.Entry(account_inputs, textvariable=self.account_email_var, width=42).pack(side=LEFT, padx=(0, 8))
        self.add_account_button = ttk.Button(account_inputs, command=self.add_account)
        self.add_account_button.pack(side=LEFT, padx=4)
        self.delete_account_button = ttk.Button(account_inputs, command=self.delete_account)
        self.delete_account_button.pack(side=LEFT, padx=4)

        self.status_tree = ttk.Treeview(status_panel, columns=("provider", "account", "email", "cli", "status"), show="headings", height=9)
        for col, width in (("provider", 110), ("account", 180), ("email", 260), ("cli", 120), ("status", 260)):
            self.status_tree.heading(col, text=col)
            self.status_tree.column(col, width=width, stretch=True)
        self.status_tree.pack(fill=BOTH, expand=True, padx=10, pady=10)
        self.log_entry = ttk.Entry(status_panel, textvariable=self.log_var, state="readonly")
        self.log_entry.pack(fill=X, padx=10, pady=(0, 10))

    def apply_language(self) -> None:
        self.root.title(self.t("title"))
        self.title_label.configure(text=self.t("title"))
        self.subtitle_label.configure(text=self.t("subtitle"))
        self.lang_button.configure(text=self.t("lang"))
        self.workspace_label.configure(text=self.t("workspace"))
        self.path_label.configure(text=self.t("path"))
        self.add_workspace_button.configure(text=self.t("add_workspace"))
        self.open_vscode_button.configure(text=self.t("open_vscode"))
        self.save_button.configure(text=self.t("save"))
        self.refresh_button.configure(text=self.t("refresh"))
        self.account_panel.configure(text=self.t("accounts"))
        self.status_panel.configure(text=self.t("states"))
        self.add_account_button.configure(text=self.t("add_account"))
        self.delete_account_button.configure(text=self.t("delete_account"))
        for provider in self.config["providers"]:
            provider_id = provider["id"]
            self.launch_buttons[provider_id].configure(text=self.t("launch"))
            self.login_buttons[provider_id].configure(text=self.t("login"))
            self.switch_buttons[provider_id].configure(text=self.t("switch"))

    def toggle_language(self) -> None:
        self.config["settings"]["language"] = "en" if self.config["settings"].get("language") == "zh" else "zh"
        self.save_config()
        self.apply_language()
        self.refresh_all()

    def refresh_all(self) -> None:
        self.refreshing = True
        names = [w["name"] for w in sorted(self.config["workspaces"], key=lambda x: x["name"])]
        self.workspace_box["values"] = names
        if names and self.workspace_var.get() not in names:
            self.workspace_var.set(names[0])
        providers = [p["id"] for p in self.config["providers"]]
        self.account_provider_box["values"] = providers
        if providers and self.account_provider_var.get() not in providers:
            self.account_provider_var.set(providers[0])
        self.refreshing = False
        self.refresh_cli_controls()
        self.refresh_workspace_selection()
        self.refresh_accounts_grid()
        self.refresh_status_grid()

    def selected_workspace(self) -> dict | None:
        name = self.workspace_var.get()
        for workspace in self.config["workspaces"]:
            if workspace["name"] == name:
                return workspace
        return None

    def refresh_workspace_selection(self) -> None:
        workspace = self.selected_workspace()
        if not workspace:
            self.path_var.set("")
            return
        self.path_var.set(workspace["path"])
        self.refreshing = True
        try:
            for provider in self.config["providers"]:
                provider_id = provider["id"]
                values = [f"({self.t('default')}: {self.config['defaults'].get(provider_id, '')})", f"({self.t('none')})"]
                values.extend([f"{a['id']} <{a['email']}>" for a in self.config["accounts"] if a["provider"] == provider_id])
                box = self.provider_boxes[provider_id]
                box["values"] = values
                selected = workspace["mappings"].get(provider_id, "")
                self.select_provider_value(provider_id, selected)
        finally:
            self.refreshing = False

    def select_provider_value(self, provider_id: str, account_id: str) -> None:
        box = self.provider_boxes[provider_id]
        values = list(box["values"])
        index = 0
        if account_id == NONE_VALUE:
            index = 1
        elif account_id:
            for i, value in enumerate(values):
                if value.startswith(account_id + " "):
                    index = i
                    break
        if values:
            box.current(index)

    def provider_selection_changed(self, event) -> None:
        if self.refreshing:
            return
        box = event.widget
        provider_id = getattr(box, "provider_id", "")
        workspace = self.selected_workspace()
        if not workspace or not provider_id:
            return
        self.sync_single_mapping(workspace, provider_id)
        self.save_config()
        self.log(f"{provider_id} -> {workspace['mappings'].get(provider_id, '') or self.t('default')}")

    def sync_workspace_mappings(self, workspace: dict) -> None:
        for provider in self.config["providers"]:
            self.sync_single_mapping(workspace, provider["id"])

    def sync_single_mapping(self, workspace: dict, provider_id: str) -> None:
        box = self.provider_boxes[provider_id]
        index = box.current()
        value = box.get()
        if index == 0:
            workspace["mappings"][provider_id] = ""
        elif index == 1:
            workspace["mappings"][provider_id] = NONE_VALUE
        elif value:
            workspace["mappings"][provider_id] = value.split(" ", 1)[0]

    def save_workspace_mappings(self) -> None:
        workspace = self.selected_workspace()
        if not workspace:
            return
        self.sync_workspace_mappings(workspace)
        self.save_config()
        self.log(self.t("saved"))

    def refresh_cli_controls(self) -> None:
        for provider in self.config["providers"]:
            provider_id = provider["id"]
            available = bool(resolve_command(provider.get("command", "")))
            self.provider_cli_labels[provider_id].configure(text=self.t("cli_ok") if available else self.t("cli_missing"))
            state = "normal" if available else "disabled"
            self.launch_buttons[provider_id].configure(state=state)
            self.login_buttons[provider_id].configure(state=state)

    def effective_account(self, workspace: dict, provider_id: str) -> dict | None:
        account_id = workspace["mappings"].get(provider_id, "")
        if account_id == NONE_VALUE:
            return None
        if not account_id:
            account_id = self.config["defaults"].get(provider_id, "")
        for account in self.config["accounts"]:
            if account["provider"] == provider_id and account["id"] == account_id:
                return account
        return None

    def build_workspace_env(self, workspace: dict) -> dict[str, str]:
        env = os.environ.copy()
        for provider in self.config["providers"]:
            account = self.effective_account(workspace, provider["id"])
            if not account or not provider.get("envVar"):
                continue
            config_dir = expand_path(account["configDir"])
            Path(config_dir).mkdir(parents=True, exist_ok=True)
            env[provider["envVar"]] = config_dir
            env.update(account_browser_launcher(account))
        return env

    def workspace_profile_key(self, workspace: dict) -> str:
        parts = []
        for provider in self.config["providers"]:
            account = self.effective_account(workspace, provider["id"])
            parts.append(f"{provider['id']}-{account['id'] if account else 'none'}")
        return "_".join(parts)

    def open_vscode(self) -> None:
        workspace = self.selected_workspace()
        if not workspace:
            return
        self.sync_workspace_mappings(workspace)
        self.save_config()
        vscode = resolve_command(self.config["settings"].get("vscodeCommand", "code"))
        if not vscode:
            messagebox.showwarning(APP_NAME, self.t("no_vscode"))
            return
        target = workspace["path"] if Path(workspace["path"]).exists() else workspace["cwd"]
        profile_root = Path(expand_path(self.config["settings"]["profileRoot"]))
        profile_dir = profile_root / safe_path_segment(workspace["id"] + "-" + self.workspace_profile_key(workspace))
        profile_dir.mkdir(parents=True, exist_ok=True)
        env = self.build_workspace_env(workspace)
        # -claude-fix- Start VS Code directly with subprocess and the selected account environment.
        subprocess.Popen(
            [vscode, "--new-window", "--user-data-dir", str(profile_dir), target],
            cwd=workspace.get("cwd") or app_dir(),
            env=env,
            creationflags=detached_flags(),
        )

    def launch_provider(self, provider_id: str, login: bool) -> None:
        workspace = self.selected_workspace()
        provider = provider_by_id(self.config, provider_id)
        if not workspace or not provider:
            return
        command = resolve_command(provider.get("command", ""))
        if not command:
            messagebox.showwarning(APP_NAME, self.t("no_cli"))
            return
        self.sync_workspace_mappings(workspace)
        account = self.effective_account(workspace, provider_id)
        if not account:
            messagebox.showwarning(APP_NAME, f"{provider_id}: {self.t('none')}")
            return
        args = provider.get("loginArgs" if login else "", "") if login else ""
        args = args.replace("{email}", account.get("email", ""))
        env = os.environ.copy()
        if provider.get("envVar"):
            config_dir = expand_path(account["configDir"])
            Path(config_dir).mkdir(parents=True, exist_ok=True)
            env[provider["envVar"]] = config_dir
            env.update(account_browser_launcher(account))
        if login:
            self.log(f"{provider_id} login -> {account['id']} <{account.get('email', '')}>. {self.t('login_hint')}")
        # -claude-fix- Start provider CLIs directly with subprocess, keeping missing CLIs blocked by prior detection.
        subprocess.Popen(
            [command] + split_args(args),
            cwd=workspace.get("cwd") or app_dir(),
            env=env,
            creationflags=hidden_process_flags() if login else detached_flags(),
            startupinfo=hidden_startupinfo() if login else None,
        )

    def switch_provider_account(self, provider_id: str) -> None:
        workspace = self.selected_workspace()
        if not workspace:
            return
        accounts = [a for a in self.config["accounts"] if a["provider"] == provider_id]
        if not accounts:
            messagebox.showwarning(APP_NAME, f"{provider_id}: {self.t('none')}")
            return
        current = workspace["mappings"].get(provider_id, "") or self.config["defaults"].get(provider_id, "")
        if current == NONE_VALUE:
            current = ""
        current_index = next((i for i, a in enumerate(accounts) if a["id"] == current), -1)
        next_account = accounts[(current_index + 1) % len(accounts)]
        workspace["mappings"][provider_id] = next_account["id"]
        self.select_provider_value(provider_id, next_account["id"])
        self.save_config()
        self.log(f"{provider_id} -> {next_account['id']} <{next_account['email']}>. {self.t('switch_hint')}")

    def add_workspace(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("VS Code workspace", "*.code-workspace"), ("All files", "*.*")])
        if not path:
            return
        workspace_path = Path(path)
        workspace_id = safe_path_segment(workspace_path.stem.lower().replace(" ", "-"))
        workspace = {
            "id": workspace_id,
            "name": workspace_path.stem,
            "path": str(workspace_path),
            "cwd": str(workspace_path.parent),
            "mappings": {p["id"]: "" for p in self.config["providers"]},
        }
        if not any(w["id"] == workspace_id for w in self.config["workspaces"]):
            self.config["workspaces"].append(workspace)
        self.save_config()
        self.refresh_all()
        self.workspace_var.set(workspace["name"])
        self.refresh_workspace_selection()

    def add_account(self) -> None:
        provider_id = self.account_provider_var.get()
        account_id = self.account_id_var.get().strip()
        email = self.account_email_var.get().strip()
        if not provider_id or not account_id or not email:
            return
        if any(a["provider"] == provider_id and a["id"] == account_id for a in self.config["accounts"]):
            messagebox.showwarning(APP_NAME, "Account exists.")
            return
        provider = provider_by_id(self.config, provider_id)
        if not provider:
            return
        account = {
            "provider": provider_id,
            "id": account_id,
            "email": email,
            "configDir": str(Path(expand_path(provider["accountsRoot"])) / account_id),
        }
        self.config["accounts"].append(account)
        if not self.config["defaults"].get(provider_id):
            self.config["defaults"][provider_id] = account_id
        self.save_config()
        self.account_id_var.set("")
        self.account_email_var.set("")
        self.refresh_all()

    def delete_account(self) -> None:
        selected = self.accounts_tree.selection()
        if not selected:
            return
        values = self.accounts_tree.item(selected[0], "values")
        provider_id, account_id = values[0], values[1]
        self.config["accounts"] = [a for a in self.config["accounts"] if not (a["provider"] == provider_id and a["id"] == account_id)]
        if self.config["defaults"].get(provider_id) == account_id:
            self.config["defaults"][provider_id] = ""
        self.save_config()
        self.refresh_all()

    def refresh_accounts_grid(self) -> None:
        self.accounts_tree.delete(*self.accounts_tree.get_children())
        for account in self.config["accounts"]:
            self.accounts_tree.insert("", END, values=(account["provider"], account["id"], account["email"], account.get("configDir", "")))

    def refresh_status_grid(self) -> None:
        self.status_tree.delete(*self.status_tree.get_children())
        for account in self.config["accounts"]:
            provider = provider_by_id(self.config, account["provider"])
            if not provider:
                continue
            command = resolve_command(provider.get("command", ""))
            cli = self.t("cli_ok") if command else self.t("cli_missing")
            status = self.account_status(provider, account, command) if command else self.t("cli_missing")
            self.status_tree.insert("", END, values=(account["provider"], account["id"], account["email"], cli, status))
        self.refresh_cli_controls()
        self.log("Status refreshed.")

    def account_status(self, provider: dict, account: dict, command: str) -> str:
        status_args = provider.get("statusArgs", "")
        if not status_args:
            return TEXT[self.config["settings"].get("language", "zh")]["unknown"]
        env = os.environ.copy()
        if provider.get("envVar"):
            env[provider["envVar"]] = expand_path(account.get("configDir", ""))
        try:
            result = subprocess.run(
                [command] + split_args(status_args),
                cwd=str(app_dir()),
                env=env,
                capture_output=True,
                text=True,
                timeout=10,
            )
            output = (result.stdout or "") + (result.stderr or "")
            if provider["id"] == "claude":
                return self.t("cli_ok") if "Email:" in output or "Login method:" in output else self.t("unknown")
            if provider["id"] == "openai":
                return self.t("cli_ok") if output.strip().lower().startswith("logged in") else self.t("unknown")
            if provider["id"] == "gemini":
                return self.t("cli_ok")
            return self.t("unknown")
        except Exception as exc:
            return str(exc)[:80]

    def log(self, message: str) -> None:
        self.log_var.set(message)

    def run(self) -> None:
        self.root.mainloop()


def safe_path_segment(value: str) -> str:
    invalid = '<>:"/\\|?*'
    for char in invalid:
        value = value.replace(char, "_")
    return value or "workspace"


def main() -> None:
    AccountManagerApp().run()


if __name__ == "__main__":
    main()
