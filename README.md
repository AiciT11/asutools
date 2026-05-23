<div align="center">

# asutools

**渗透测试工具箱 · Security Toolbox for macOS**

[![Python](https://img.shields.io/badge/Python-3.12+-blue)](https://python.org)
[![PyQt6](https://img.shields.io/badge/PyQt6-6.x-green)](https://pypi.org/project/PyQt6/)
[![macOS](https://img.shields.io/badge/macOS-Apple%20Silicon-black)](https://apple.com)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

</div>

## 特性

- **227个工具** 覆盖完整渗透测试链路（外网打点→内网渗透→域渗透→后渗透）
- **36个分类** 精细划分：端口扫描、漏洞利用、横向移动、域渗透、C2等
- **代理控制** 工具箱左上角输入框，一键切换直连/代理（支持HTTP/SOCKS5）
- **iTerm2优先** 工具启动自动在iTerm2新窗口，fallback Terminal.app
- **工具详情弹窗** 双击/右键查看工具说明、基础命令、使用示例
- **Java绝对路径** 自动选择Java 8/11/17启动不同JAR工具
- **完全离线** 工具配置本地存储，无需联网

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/lsdogXG/asutools.git
cd asutools
```

### 2. 安装（自动安装工具+配置）

```bash
bash install.sh
```

### 3. 启动

```bash
# 添加到 ~/.zshrc（安装脚本会提示）
asu
# 或直接运行
bash launch.sh
```

## 截图

> 截图待添加

## 工具分类

| 分类 | 代表工具 |
|------|---------|
| 端口扫描 | nmap, masscan, rustscan, naabu |
| 子域名/资产 | subfinder, amass, OneForAll |
| 指纹识别 | httpx, whatweb, wafw00f |
| 目录爆破 | ffuf, gobuster, feroxbuster, dirsearch |
| 漏洞扫描 | nuclei, xray, afrog |
| SQLi | sqlmap |
| XSS | dalfox, XSStrike |
| Java中间件 | Shiro/Fastjson/Log4j/Nacos/WebLogic利用工具 |
| 反序列化 | ysoserial, JNDIExploit |
| CVE EXP | 2024-2025高危漏洞PoC集 |
| Webshell | 冰蝎v3/v4, 哥斯拉, 天蝎 |
| 内网扫描 | fscan, 0x7e, nxc |
| 横向移动 | netexec, evil-winrm, GoGoGo |
| 域渗透 | BloodHound.py, certipy-ad, kerbrute, responder |
| 内网隧道 | frp, chisel, gost, ligolo-ng, Neo-reGeorg |
| C2 | Sliver, Metasploit, vshell, AdaptixC2 |
| 提权 | PwnKit, DirtyPipe, GodPotato, JuicyPotatoNG |
| 密码攻击 | hashcat, john, hydra |
| 移动安全 | frida, objection, jadx, apktool, MobSF |
| 逆向工程 | Ghidra, radare2, JD-GUI |
| PWN | pwntools, ROPgadget, seccomp-tools, GEF |
| 云安全 | ScoutSuite, Prowler, Pacu |
| 流量分析 | Wireshark, tshark, mitmproxy |
| 取证溯源 | Volatility3, Velociraptor, YARA, capa |

## 系统要求

- macOS (Apple Silicon / Intel)
- Python 3.12+
- Homebrew
- Go 1.21+ (部分工具)
- iTerm2 (推荐)

## 声明

本工具箱仅用于授权渗透测试、CTF竞赛和安全研究。使用者须遵守当地法律法规，禁止用于非法用途。

## License

MIT License — 仅限启动器代码。各工具遵循其原始License。
