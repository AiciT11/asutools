#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DATA_DIR="$HOME/Library/Application Support/asuTools"

echo "=== asutools 安装脚本 ==="
echo ""

# ─────────────────────────────────────────────────────────────
# 1. 创建数据目录，复制配置文件（替换 ~ 为 $HOME）
# ─────────────────────────────────────────────────────────────
echo "── 初始化配置文件 ──"
mkdir -p "$DATA_DIR"
for f in tools.json categories.json environments.json; do
  if [ ! -f "$DATA_DIR/$f" ]; then
    sed "s|~|$HOME|g" "$SCRIPT_DIR/data/$f" > "$DATA_DIR/$f"
    echo "✓ 配置文件: $f"
  else
    echo "  跳过（已存在）: $f"
  fi
done

# ─────────────────────────────────────────────────────────────
# 2. 创建 .venv 并安装 asutools
# ─────────────────────────────────────────────────────────────
echo ""
echo "── 安装 asutools Python 包 ──"
if [ ! -d "$SCRIPT_DIR/.venv" ]; then
  python3 -m venv "$SCRIPT_DIR/.venv"
  echo "✓ 虚拟环境已创建: .venv"
fi
"$SCRIPT_DIR/.venv/bin/pip" install -e "$SCRIPT_DIR" -q
echo "✓ asutools 已安装至 .venv"

# ─────────────────────────────────────────────────────────────
# 3. 添加 asu 命令到 shell
# ─────────────────────────────────────────────────────────────
echo ""
echo "── shell 快捷命令 ──"
ASU_ALIAS="alias asu='$SCRIPT_DIR/.venv/bin/python -m asutools'"
if grep -qF "python -m asutools" "$HOME/.zshrc" 2>/dev/null; then
  echo "  跳过（已存在 asu alias）"
else
  echo "" >> "$HOME/.zshrc"
  echo "# asutools 启动器" >> "$HOME/.zshrc"
  echo "$ASU_ALIAS" >> "$HOME/.zshrc"
  echo "✓ 已添加 asu 命令到 ~/.zshrc"
fi
echo "  提示: 执行 'source ~/.zshrc' 后即可使用 'asu' 启动"

# ─────────────────────────────────────────────────────────────
# 4. Homebrew / Go / pip 工具安装（可选）
# ─────────────────────────────────────────────────────────────
echo ""
echo "=== 安装开源工具 ==="
read -p "是否自动安装所有开源工具? (brew/go/pip) [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then

  # ── 4a. Homebrew 工具 ──────────────────────────────────────
  if ! command -v brew &>/dev/null; then
    echo "未检测到 Homebrew，跳过 brew 安装。安装地址: https://brew.sh"
  else
    echo ""
    echo "── Homebrew 工具 ──"
    BREW_PKGS=(
      nmap masscan naabu subfinder httpx katana nuclei
      ffuf gobuster feroxbuster
      sqlmap dalfox
      hashcat john-jumbo hydra
      radare2 binwalk exiftool
      gitleaks
      frp chisel gost
      semgrep tshark mitmproxy
      yara trivy
      frida jadx apktool
      nikto amass sleuthkit
      bettercap sliver metasploit
      netexec bloodhound-python
      responder mitm6
      searchsploit
    )
    for pkg in "${BREW_PKGS[@]}"; do
      if brew list "$pkg" &>/dev/null 2>&1; then
        echo "  已安装: $pkg"
      else
        echo "  安装: $pkg"
        brew install "$pkg" 2>&1 | tail -1 || echo "  ⚠ $pkg 安装失败，继续..."
      fi
    done
    echo "✓ Homebrew 工具安装完毕"
  fi

  # ── 4b. Go 工具 ───────────────────────────────────────────
  if ! command -v go &>/dev/null; then
    echo "未检测到 Go，跳过 go install。安装地址: https://go.dev/dl"
  else
    echo ""
    echo "── Go 工具 ──"
    GO_PKGS=(
      "github.com/projectdiscovery/naabu/v2/cmd/naabu@latest"
      "github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest"
      "github.com/projectdiscovery/httpx/cmd/httpx@latest"
      "github.com/projectdiscovery/katana/cmd/katana@latest"
      "github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest"
      "github.com/jpillora/chisel@latest"
      "github.com/zyylhn/fscan@latest"
      "github.com/hahwul/dalfox/v2@latest"
      "github.com/ropnop/kerbrute@latest"
      "github.com/go-gost/gost/cmd/gost@latest"
    )
    for pkg in "${GO_PKGS[@]}"; do
      echo "  go install $pkg"
      go install "$pkg" 2>&1 || echo "  ⚠ $pkg 安装失败，继续..."
    done
    echo "✓ Go 工具安装完毕"
  fi

  # ── 4c. pip 工具（安装到 .venv）─────────────────────────────
  echo ""
  echo "── pip 工具（安装到 .venv）──"
  PIP_PKGS=(
    certipy-ad impacket pypykatz mitm6 volatility3 bloodhound
    semgrep objection scoutsuite pacu
  )
  "$SCRIPT_DIR/.venv/bin/pip" install "${PIP_PKGS[@]}" -q
  echo "✓ pip 工具安装完毕"

else
  echo "跳过工具安装。"
fi

# ─────────────────────────────────────────────────────────────
# 完成
# ─────────────────────────────────────────────────────────────
echo ""
echo "=== 安装完成 ==="
echo "  启动: source ~/.zshrc && asu"
echo "  或直接: bash $SCRIPT_DIR/launch.sh"
