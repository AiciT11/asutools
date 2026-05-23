"""Tool launcher: dispatch by tool.type, with env selection and proxy control."""
import shlex
import subprocess
import webbrowser
from pathlib import Path

from . import store


def _find_env(env_id: str) -> dict | None:
    if not env_id:
        return None
    for e in store.load_environments().get("environments", []):
        if e.get("id") == env_id:
            return e
    return None


def _default_env(env_type: str) -> dict | None:
    data = store.load_environments()
    eid = data.get("defaults", {}).get(env_type, "")
    return _find_env(eid)


def _python_bin(env: dict) -> str:
    p = Path(env["path"])
    if env["type"] == "python":
        return env["path"]
    if env["type"] in ("venv", "conda"):
        return str(p / "bin" / "python")
    return env["path"]


def _java_bin(env: dict) -> str:
    return str(Path(env["path"]) / "bin" / "java")


def _iterm_available() -> bool:
    return Path("/Applications/iTerm.app").exists()


def _escape_for_applescript(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _proxy_prefix() -> str:
    """返回 shell 代理设置前缀串，注入到每条终端命令前。
    有代理时 export，无代理时 unset 确保直连。"""
    proxy = store.load_settings().get("proxy", "").strip()
    vars_ = "HTTP_PROXY HTTPS_PROXY ALL_PROXY http_proxy https_proxy all_proxy"
    if proxy:
        exports = " ".join(
            f'{v}={shlex.quote(proxy)}'
            for v in vars_.split()
        )
        return f"export {exports} && "
    # 显式 unset，防止 shell 环境变量残留影响工具
    return f"unset {vars_} 2>/dev/null; "


def _run_in_terminal(cmd: str, cwd: str | None = None) -> None:
    """Run a shell command in a new terminal window (iTerm2 preferred, fallback Terminal.app)."""
    cd = f"cd {shlex.quote(cwd)} && " if cwd else ""
    full = f"{_proxy_prefix()}{cd}{cmd}"
    escaped = _escape_for_applescript(full)
    if _iterm_available():
        script = (
            'tell application "iTerm"\n'
            '  activate\n'
            '  create window with default profile\n'
            '  tell current session of current window\n'
            f'    write text "{escaped}"\n'
            '  end tell\n'
            'end tell'
        )
    else:
        script = (
            'tell application "Terminal"\n'
            '  activate\n'
            f'  do script "{escaped}"\n'
            'end tell'
        )
    subprocess.Popen(["osascript", "-e", script])


def launch(tool: dict) -> tuple[bool, str]:
    """Run a tool. Returns (ok, message)."""
    ttype = (tool.get("type") or "").lower()
    path = tool.get("path", "")
    args = tool.get("args", "") or ""

    if ttype == "url":
        if not path:
            return False, "缺少 URL"
        webbrowser.open(path)
        return True, f"已打开 {path}"

    if ttype == "gui":
        if not path:
            return False, "缺少路径"
        p = Path(path)
        if not p.exists():
            return False, f"路径不存在: {path}"
        if path.endswith(".app") or p.is_dir():
            subprocess.Popen(["open", path])
        elif path.endswith(".html") or path.endswith(".htm"):
            webbrowser.open(f"file://{p.resolve()}")
        else:
            subprocess.Popen(["open", path])
        return True, f"已启动 {p.name}"

    if ttype == "python":
        env = _find_env(tool.get("env_id", "")) or _default_env("python")
        if not env:
            return False, "找不到 Python 环境，请到设置中配置"
        py = _python_bin(env)
        if not Path(py).exists():
            return False, f"Python 不存在: {py}"
        cmd = f"{shlex.quote(py)} {shlex.quote(path)} {args}".strip()
        _run_in_terminal(cmd, cwd=str(Path(path).parent) if path else None)
        return True, f"在 Terminal 中运行 ({env['name']})"

    if ttype == "java":
        env = _find_env(tool.get("env_id", "")) or _default_env("java")
        if not env:
            return False, "找不到 Java 环境，请到设置中配置"
        java = _java_bin(env)
        if not Path(java).exists():
            return False, f"java 不存在: {java}"
        cmd = f"{shlex.quote(java)} -jar {shlex.quote(path)} {args}".strip()
        _run_in_terminal(cmd, cwd=str(Path(path).parent) if path else None)
        return True, f"在 Terminal 中运行 ({env['name']})"

    if ttype == "shell":
        if not path:
            return False, "缺少路径"
        if path.endswith(".sh"):
            cmd = f"bash {shlex.quote(path)} {args}".strip()
        else:
            cmd = f"{shlex.quote(path)} {args}".strip()
        _run_in_terminal(cmd, cwd=str(Path(path).parent) if path else None)
        return True, "在 Terminal 中运行"

    return False, f"未知类型: {ttype}"


def record_recent(tool_id: str) -> None:
    """Update last_used timestamp on a tool."""
    import time
    tools = store.load_tools()
    for t in tools:
        if t.get("id") == tool_id:
            t["last_used"] = int(time.time())
            break
    store.save_tools(tools)
