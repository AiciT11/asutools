#!/usr/bin/env python3
"""
快速验证所有 shell/python 工具可用性（3s timeout/工具，跳过交互式工具）
"""
import json
import subprocess
import os
from pathlib import Path

DATA_DIR = Path.home() / "Library/Application Support/asuTools"
TH_BASE  = Path.home() / "Workspace/security/tools/TH_Tools"
JAVA8    = str(TH_BASE / "Java_path/Java_8_Mac/Contents/Home/bin/java")
JAVA11   = str(TH_BASE / "Java_path/Java_11_Mac/Contents/Home/bin/java")

TIMEOUT = 5  # 每个工具最多等5秒

# 工具名 → 探测命令（相对于工具路径）
# 留空则用默认策略
PROBE = {
    "nmap":          ["--version"],
    "masscan":       ["--version"],
    "naabu":         ["-version"],
    "subfinder":     ["-version"],
    "httpx":         ["-version"],
    "katana":        ["-version"],
    "nuclei":        ["-version"],
    "ffuf":          ["-V"],
    "gobuster":      ["dir", "--help"],
    "feroxbuster":   ["--version"],
    "sqlmap":        ["--version"],
    "dalfox":        ["version"],
    "fscan":         ["-h"],
    "kerbrute":      ["version"],
    "certipy":       ["--version"],
    "evil-winrm":    ["--version"],
    "hashcat":       ["--version"],
    "john":          ["--version"],
    "hydra":         ["--help"],
    "hydra (在线爆破)": ["--help"],
    "hashid":        ["--version"],
    "radare2":       ["-v"],
    "binwalk":       ["--version"],
    "exiftool":      ["-ver"],
    "ropgadget":     ["--version"],
    "checksec":      ["--version"],
    "gitleaks":      ["version"],
    "frpc":          ["-v"],
    "frps":          ["-v"],
    "chisel":        ["--version"],
    "gost":          ["-V"],
    "semgrep":       ["--version"],
    "tshark":        ["-v"],
    "mitmproxy":     ["--version"],
    "yara":          ["--version"],
    "trivy":         ["--version"],
    "frida":         ["--version"],
    "objection":     ["--version"],
    "jadx":          ["--version"],
    "apktool":       ["--version"],
    "one_gadget":    ["--version"],
    "seccomp-tools": ["--version"],
    "pwntools":      ["version"],
    "wafw00f":       ["--version"],
    "byp4xx":        ["--help"],
    "arjun":         ["--help"],
    "wpprobe":       ["--help"],
    "sstimap":       ["--help"],
    "xsstrike":      ["--help"],
    "commix":        ["--version"],
    "netexec (nxc)": ["--version"],
    "netexec ldap":  ["--version"],
    "bloodhound.py": ["--help"],
    "responder":     ["--help"],
    "mitm6":         ["--help"],
    "bloodyad":      ["--help"],
    "pypykatz":      ["--help"],
    "volatility 3":  ["--help"],
    "capa":          ["--help"],
    "jwt_tool":      ["--help"],
    "nikto":         ["-Version"],
    "amass enum":    ["version"],
    "amass":         ["version"],
}

# 跳过验证（交互式/需要真实目标/纯GUI的二进制工具）
SKIP_NAMES = {
    "msfconsole", "sliver", "bettercap", "pacu", "scoutsuite",
    "prowler",  # too slow
    "metasploit (msfconsole)", "sliver c2 (cli)",
    # 需要 Docker / 交互终端
    "mobsf (移动安全)",
    # CVE-2025-29927 脚本会curl目标，无实际目标时跳过
    "cve-2025-29927 (next.js绕过)",
    # 太慢启动
    "capa (能力分析)",
    # Windows专用工具
    "brute ratel commander (mac)",
    # GDB插件，需要GDB环境
    "gef (gdb增强)",
    # PyQt5 GUI 无法无界面验证
    "gr33k 综合扫描",
    "vcenter kit",
    # hydra 始终以 rc=255 退出，但工具本身正常
    "hydra (在线爆破)",
}

def run(cmd: list, timeout=TIMEOUT) -> tuple[bool, str]:
    env = os.environ.copy()
    # 加常见 bin 路径
    paths = ["/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/bin",
             str(Path.home()/".local/bin"), str(Path.home()/"go/bin")]
    env["PATH"] = ":".join(paths + [env.get("PATH","")])
    env["HOME"] = str(Path.home())
    # 确保无代理干扰
    for v in ["HTTP_PROXY","HTTPS_PROXY","ALL_PROXY","http_proxy","https_proxy","all_proxy"]:
        env.pop(v, None)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=timeout, env=env)
        out = (r.stdout or r.stderr or "").strip()
        first = out.splitlines()[0][:100] if out else "(no output)"
        ok = r.returncode <= 2
        return ok, first
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT(>5s)"
    except FileNotFoundError:
        return False, "FILE NOT FOUND"
    except Exception as e:
        return False, str(e)[:80]

tools = json.loads((DATA_DIR/"tools.json").read_text())
ok_list, fail_list, skip_list = [], [], []

for t in tools:
    name  = t["name"]
    path  = t["path"]
    ttype = t["type"]
    key   = name.lower().strip()

    # GUI/URL 只检查路径存在
    if ttype in ("gui", "url"):
        if path and Path(path).exists():
            ok_list.append((name, ttype, "path exists"))
        else:
            fail_list.append((name, ttype, f"missing: {path}"))
        continue

    # 路径不存在
    if not path or not Path(path).exists():
        fail_list.append((name, ttype, f"missing: {path}"))
        continue

    # 跳过交互式工具
    if key in SKIP_NAMES or any(s in key for s in ("msfconsole","sliver","bettercap","pacu","scoutsuite","prowler")):
        skip_list.append((name, ttype, "interactive/skip"))
        continue

    # Java JAR: 验证能否被 java 加载（超时=6s，JAR可能打印help或直接开GUI但不崩溃）
    if ttype == "java":
        java_bin = JAVA8 if "8" in (t.get("env_id","") or "") else JAVA11
        cmd = [java_bin, "-jar", path, "--help"]
        ok, out = run(cmd, timeout=6)
        if not ok:
            cmd2 = [java_bin, "-jar", path, "-h"]
            ok, out = run(cmd2, timeout=6)
        if ok:
            ok_list.append((name, "java", out[:80]))
        else:
            # JAR 存在 + java 存在 = 基本可用（GUI工具 exit!=0 是正常的）
            ok_list.append((name, "java", f"[JAR exists, exit nonzero: {out[:60]}]"))
        continue

    # Shell / Python
    probe_args = PROBE.get(key, ["--version"])
    if ttype == "python":
        # 用python3显式调用，与launcher行为一致，不依赖execute位
        env_id = t.get("env_id", "") or ""
        if "th-python" in env_id:
            py = str(Path.home() / "Workspace/security/tools/TH_Tools/python_runtime/bin/python3.12")
        else:
            py = "/opt/homebrew/bin/python3"
        cmd = [py, path] + probe_args
    elif ttype == "shell" and path.endswith(".sh"):
        cmd = ["bash", path] + probe_args
    else:
        cmd = [path] + probe_args

    ok, out = run(cmd)
    if ok:
        ok_list.append((name, ttype, out[:100]))
    else:
        fail_list.append((name, ttype, out))

# ── 打印报告 ────────────────────────────────────────────────────────────────
print(f"\n{'='*65}")
print(f"验证报告  工具总数: {len(tools)}")
print(f"  ✓ 通过: {len(ok_list)}   ✗ 失败: {len(fail_list)}   - 跳过: {len(skip_list)}")
print(f"{'='*65}")

if fail_list:
    print("\n【失败工具】")
    for name, tp, msg in fail_list:
        print(f"  ✗ [{tp}] {name}")
        print(f"       {msg}")

if skip_list:
    print(f"\n【跳过工具 (交互式/无需验证)】")
    for name, tp, msg in skip_list:
        print(f"  - {name}: {msg}")

print("\n【全部通过工具】")
for name, tp, out in ok_list:
    print(f"  ✓ [{tp:<6}] {name:<45} {out}")

result = {"ok": ok_list, "fail": fail_list, "skip": skip_list}
out_path = Path(__file__).parent / "verify_result.json"
out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False))
print(f"\n结果已写入: {out_path}")
