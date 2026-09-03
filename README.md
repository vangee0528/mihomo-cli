# mihomo-cli

<p align="center">
  <strong>基于纯 Bash 的轻量级 Mihomo / Clash 终端可视化节点与连接管理器</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Language-Bash_4.0+-4EAA25?logo=gnu-bash&logoColor=white" alt="Bash">
  <img src="https://img.shields.io/badge/Kernel-Mihomo_%2F_Clash.Meta-3B82F6" alt="Mihomo">
  <img src="https://img.shields.io/badge/Dependencies-curl_%7C_jq-orange" alt="Dependencies">
  <img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License">
</p>

---

## 简介 (Introduction)

`mihomo-cli` 是一个面向 Linux / macOS 终端用户的轻量级管理工具。无需安装 Python、Node.js 或编译大型二进制程序，仅通过系统内置的 `curl` 与 `jq`，直接与 Mihomo (Clash Meta) 的 External Controller（默认 `127.0.0.1:9090`）通信。

它提供了类似桌面客户端的**全屏终端可视化（TUI）交互界面**，支持通过上下方向键选择节点、回车一键切换、一键并发测速扫描以及代理模式切换，特别适用于 **无桌面 Linux 服务器**、**SSH 远程开发会话** 及 **极客终端环境**。

---

## 界面预览 (UI Preview)

```text
⚡ Mihomo CLI v1.0.0  ● 运行中 (Mihomo v1.19.14)     RULE 规则模式 
  接口: http://127.0.0.1:9090  端口: 7890  连接数: 5  流量: ↑ 12.4 MB  ↓ 156.8 MB
  策略组: [🚀 节点选择]  当前在用节点: 🇯🇵 日本 01
  排序: ⚡ 延迟升序  (共 28 个节点)
───────────────────────────────────────────────────────────────────────────────
 >    [ ] 🇭🇰 香港 01   [Trojan]     98 ms
      [ ] 🇭🇰 香港 02   [Trojan]    105 ms
      [ ] 🇨🇳 台湾 01   [Trojan]    142 ms
      [ ] 🇸🇬 新加坡 01 [Trojan]    185 ms
   *  [✓] 🇯🇵 日本 01   [Trojan]    210 ms
      [ ] 🇯🇵 日本 02   [Trojan]    218 ms
      [ ] 🇺🇸 美国 01   [Trojan]    320 ms
      [ ] DIRECT       [Direct]    340 ms
───────────────────────────────────────────────────────────────────────────────
  ✔ 批量测速完成！已按延迟升序自动排序
  [↑/↓/j/k] 移动  [Enter] 切换节点  [t] 测速全部  [p] 测速当前  [s] 排序  [m] 模式
  [g] 策略组  [c] 断开旧连接  [/] 搜索  [r] 刷新  [q] 退出
```

---

## 核心特性 (Features)

- **零运行环境与免编译**：纯原生 Bash 编写，仅依赖基础的 `curl` 与 `jq`，启动时间小于 10ms，磁盘占用仅 30KB。
- **流畅终端可视化（TUI）**：支持 `↑ / ↓` 或 `j / k` 导航，`Enter` 选中即切换，支持平滑滚动与分页。
- **毫秒级全节点并发测速**：按 `t` 键调用内核底层接口并行测速全部节点，并自动按延迟升序重排，可用优质节点一目了然。
- **连接状态与路由模式切换**：一键循环切换 **Rule（规则分流）**、**Global（全局代理）**、**Direct（完全直连）**。
- **智能连接断开**：切换节点或手动触发时，自动终止现有长连接，杜绝旧 TCP 保持连接不走新节点的问题。
- **实时关键字搜索过滤**：按 `/` 输入关键字即时筛选节点列表，按 `Esc` 恢复全量。
- **终端代理环境变量助手**：提供 `env on/off` 命令，一键使终端的 `git`、`curl`、`wget` 等走代理。
- **双模运行支持**：既支持交互式全屏操作，也支持命令行子命令（如 `status`、`list`、`test`、`set`），方便脚本化集成。

---

## 依赖要求 (Prerequisites)

请确保系统已安装以下基本命令行工具（大多数 Linux 发行版已默认内置）：

```bash
# Debian / Ubuntu
sudo apt update && sudo apt install -y bash curl jq

# CentOS / RHEL / Fedora
sudo dnf install -y bash curl jq

# Arch Linux
sudo pacman -S bash curl jq
```

---

## 快速安装 (Installation)

### 方式一：克隆仓库并运行安装脚本（推荐）

```bash
git clone https://github.com/vangee0528/mihomo-cli.git
cd mihomo-cli
chmod +x install.sh
./install.sh
```

该脚本会自动将 `mihomo-cli` 软链接至 `~/.local/bin/mihomo-cli`。

> **提示**：请确保 `~/.local/bin` 已包含在您的 `$PATH` 中。如果未添加，可将以下内容写入 `~/.bashrc` 或 `~/.zshrc`：
> ```bash
> export PATH="$HOME/.local/bin:$PATH"
> ```

### 方式二：单文件手动下载安装

如果您只需单个脚本文件，可直接下载到系统可执行路径：

```bash
curl -fsSL https://raw.githubusercontent.com/vangee0528/mihomo-cli/main/mihomo-cli -o ~/.local/bin/mihomo-cli
chmod +x ~/.local/bin/mihomo-cli
```

---

## 使用指南 (Usage)

### 1. 交互式可视化界面

直接在终端执行主命令即可进入交互界面：

```bash
mihomo-cli
```

#### 交互式快捷键映射

| 按键 | 说明 |
| :--- | :--- |
| `↑` / `k` | 向上移动选中行 |
| `↓` / `j` | 向下移动选中行 |
| `PageUp` / `PageDown` | 快速上下翻页 |
| `Home` / `End` | 跳转至列表首行 / 尾行 |
| `Enter` / `Space` | **切换为当前选中的节点**（自动断开旧长连接） |
| `t` | **并发测速扫描全部节点**，完成后自动按延迟升序排列 |
| `p` | 单独测试当前选中的单个节点延迟 |
| `s` | 循环切换排序规则（配置默认顺序 $\rightarrow$ 延迟升序 $\rightarrow$ 节点名称） |
| `m` | **切换代理模式**（Rule 规则 $\rightarrow$ Global 全局 $\rightarrow$ Direct 直连） |
| `g` | 切换选中的策略组（如在 `🚀 节点选择`、`GLOBAL` 等策略组间切换） |
| `c` | 手动断开当前所有活跃代理连接（强制刷新路由） |
| `/` | 关键字搜索过滤（输入关键字后按回车应用） |
| `Esc` | 清除搜索过滤并恢复完整列表 |
| `r` | 重新拉取数据并刷新界面 |
| `q` | 退出程序并干净恢复终端屏幕 |

---

### 2. 命令行快捷指令（非交互模式）

适合在自动化脚本或无需全屏界面的终端中使用：

```bash
# 查看代理运行状态、端口、连接数及流量统计
mihomo-cli status

# 列出当前策略组的所有节点及最新延迟
mihomo-cli list

# 并发测速当前组内所有节点并按延迟升序输出
mihomo-cli test

# 查询当前代理出口的公网 IP 及地理位置
mihomo-cli ip

# 直接切换指定节点
mihomo-cli set "🇭🇰 香港 01"

# 查看或修改代理运行模式
mihomo-cli mode             # 查看当前模式
mihomo-cli mode rule        # 切换为规则分流模式
mihomo-cli mode global      # 切换为全局代理模式
mihomo-cli mode direct      # 切换为完全直连模式（相当于临时旁路代理）

# 断开当前所有活跃连接
mihomo-cli close-conns

# 开启或关闭当前终端的环境变量代理
eval $(mihomo-cli env on)   # 终端所有支持命令自动走 7890 代理
eval $(mihomo-cli env off)  # 取消终端代理
```

---

## 配置与环境变量 (Configuration)

工具默认适配本地标准设置，如果您的环境存在自定义端口、密码或远程控制器，可通过全局参数或环境变量进行配置：

| 选项参数 | 对应环境变量 | 默认值 | 说明 |
| :--- | :--- | :--- | :--- |
| `-c`, `--controller` | `MIHOMO_API` | `http://127.0.0.1:9090` | Mihomo External Controller API 地址 |
| `-s`, `--secret` | `MIHOMO_SECRET` | *(空)* | 控制器鉴权密钥 (Secret) |
| `-g`, `--group` | `MIHOMO_GROUP` | *(自动检测)* | 目标操作的策略组名称 |
| `--timeout` | `MIHOMO_TIMEOUT` | `2500` | 测速超时时间（毫秒） |

#### 自定义配置使用示例：

```bash
# 通过命令行参数连接远程控制器
mihomo-cli -c http://192.168.1.100:9090 -s my_secret_token

# 或通过环境变量持久化配置 (可加入 ~/.bashrc)
export MIHOMO_API="http://127.0.0.1:9090"
export MIHOMO_SECRET="your_secret"
```

---

## 开源许可证 (License)

本项目基于 [MIT License](LICENSE) 开源发布。
