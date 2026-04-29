# AI Workspace Account Manager

一个通用的 Python 3 / Tkinter 桌面工具，用来把多个 AI 平台账号绑定到不同的 VS Code 工作空间。

## 功能

- 支持 OpenAI、Claude、Gemini、GLM、DeepSeek 五类平台。
- 每个 VS Code 工作空间都可以分别选择五个平台账号，允许为空。
- 每个平台行内都有启动、登录、切换账号按钮。
- 打开 VS Code 时会注入当前工作空间对应的账号环境变量，例如 `CLAUDE_CONFIG_DIR` 和 `CODEX_HOME`。
- 切换账号后会使用“工作空间 + 账号组合”隔离 VS Code user-data 目录，避免复用旧窗口环境。
- 支持中文和英文界面。
- 启动前会自动识别系统里是否存在对应 AI CLI，缺失时禁用该平台的启动和登录按钮。
- 程序逻辑使用 Python `subprocess` 启动 VS Code 和各平台 CLI，不依赖 PowerShell。

## 运行

需要 Python 3.10+。

```bash
python run.py
```

## 构建 exe

可选安装 PyInstaller：

```bash
python -m pip install -r requirements-dev.txt
python scripts/build.py
```

输出文件：

```text
dist/AIWorkspaceAccountManager/AIWorkspaceAccountManager.exe
```

## 配置

首次运行会在 exe 同目录生成 `config.json`。这个文件包含本地账号、工作空间和命令路径，不建议提交到 GitHub。

可以参考：

```text
config.example.json
```

关键字段：

- `settings.vscodeCommand`: VS Code 命令，例如 `code.cmd` 或完整路径。
- `settings.profileRoot`: VS Code 隔离 profile 保存目录。
- `providers[].command`: 对应平台 CLI 命令。
- `providers[].envVar`: 对应平台账号目录环境变量。
- `accounts[]`: 本地账号列表。
- `workspaces[]`: VS Code 工作空间列表。

## GitHub 发布建议

建议提交源码、脚本、README 和 `config.example.json`，不要提交 `config.json`、`dist/`、账号目录或 VS Code profile。

```bash
git init
git add .
git commit -m "Initial generic AI workspace account manager"
git remote add origin https://github.com/<user>/<repo>.git
git push -u origin main
```

## 隐私说明

这个项目的通用版默认不包含任何邮箱、账号 token、个人项目路径或登录状态。所有真实账号信息只保存在用户本地的 `config.json` 和账号目录中。
