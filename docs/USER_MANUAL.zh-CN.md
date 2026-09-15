# POCKETPort 简单用户手册

## 准备一次

你需要一台 Windows/macOS/Linux 电脑、一部 iPhone 或 Android 手机、同一 Wi-Fi，以及手机上由你自己登录的应用。

1. 从 [GitHub Releases](https://github.com/RAGG3D/POCKETPort/releases) 下载 ZIP，解压到固定文件夹。
2. 电脑安装 [Python 3.12](https://www.python.org/downloads/)。Windows 安装时启用 Python Launcher；macOS/Linux 确认 `python3 --version` 是 3.12 或 3.13。
3. Windows 双击 `Install.cmd`。macOS 打开终端，输入 `cd ` 后把解压文件夹拖进去，回车，再运行 `sh Install.command`。Linux 在解压目录运行 `python3 scripts/install.py`。等待依赖安装完成。
4. 手机从 [WireGuard 官方下载入口](https://www.wireguard.com/install/) 安装 App。

安装不需要填写 Claude/OpenAI API Key。这个发布包是需要 Python 的本地插件工具包，不是已签名的独立 `.exe` 或 `.dmg` 安装程序。

## 每次采集：三个步骤

### 1. 电脑开启

运行 `Start-POCKETPort.cmd`（Windows）或 `sh Start-POCKETPort.command`（macOS/Linux）。保留启动窗口，浏览器会自动打开 POCKETPort。

选择淘宝、小红书、易鹤集运或其他微信小程序。其他小程序需要填写其真实业务服务域名，由服务提供方资料或你已有的配置获取；不要把微信聊天域名当作业务域名。已有域名但服务直连 IP 时可额外填写 IP。

确认电脑 Wi-Fi 的 IPv4 地址。Windows 用 `ipconfig` 看无线网卡；macOS 在 Wi-Fi 详细信息中查看；Linux 用网络设置。应与手机处在能互通的同一网络，不能填 `127.0.0.1`、WSL 内部地址或公司 VPN 地址。点击「开启 30 分钟采集」。

### 2. 手机连接并浏览

打开 WireGuard → 添加隧道 → 扫描二维码，扫描电脑页面上的二维码并保存，例如命名 `POCKETPort`，打开开关。Android 的按钮可能显示为「+」。也可下载配置后自行传到手机并导入。

**首次连接还需安装证书：**

1. 手机浏览器输入 **`http://mitm.it`**，注意是 `http`。
2. 下载对应系统的证书并安装。
3. iPhone：到「设置 → 通用 → VPN 与设备管理」安装已下载描述文件，然后到「设置 → 通用 → 关于本机 → 证书信任设置」，对刚安装的 mitmproxy 证书开启完全信任。
4. Android：系统通常在「安全 / 更多安全设置 → 加密与凭据 → 安装证书 → CA 证书」，菜单因机型而异。部分 App 不接受用户 CA，安装成功也可能无法采集。

证书步骤来自 [mitmproxy 证书说明](https://docs.mitmproxy.org/stable/concepts/certificates/)。信任的是这台电脑生成的 CA，仅在你控制的手机上安装。

回到目标应用，刷新想采集的页面、慢慢滚动列表，打开需要的详情。看电脑上「已保存」条数是否增长。不同接口一页可能返回多条业务记录，界面上的计数是响应条数。

**举例：** 想带出订单与物流，就打开订单列表，再逐个打开目标订单和物流详情。只看列表通常不会拿到所有详情。不要在手机 Wi-Fi 设置里再加 HTTP 代理。采集期间暂时关闭其他手机 VPN，并避免电脑休眠。

### 3. 停止并交给 AI

电脑点击「停止采集」，手机关闭 WireGuard。下载本次 JSON，交给自己的 Agent，再说明你希望怎么用。

通过 MCP 使用时，可以说：

> 用 POCKETPort 打开采集页面，我准备采集小红书里自己打开的内容。

浏览结束后说：

> 我浏览完了。停止采集并导出，告诉我文件在哪。

POCKETPort 不会自动判断这些数据要拿来做什么。

## 常见问题

| 现象 | 先做什么 |
|---|---|
| `mitm.it` 打不开 | 核对 Wi-Fi/IP；关闭其他 VPN；电脑防火墙允许 UDP 51820；避免隔离设备的访客 Wi-Fi |
| VPN 开启但没有响应 | WireGuard 开关不代表握手成功，检查 App 中握手时间与传输计数；再测试 `mitm.it` |
| 浏览器能连接，App 报网络/证书错误 | 核对完全信任。可能是 App 固定证书或不信任用户 CA；停止采集并关闭隧道恢复网络 |
| App 正常，但记录为零 | 刷新缓存页面；核对实际后端域名/IP；响应可能不是 JSON，或走 IPv6/QUIC，或根本没有新请求 |
| 只有部分订单 | 继续滚动和打开详情；工具不会自动翻页或绕过服务端限制 |
| 达到 100 MB | 停止、导出，再开始下一次采集；默认 30 分钟会自动关闭隧道，CLI/MCP 可选 1–120 分钟 |
| 8766 被占用 | 关闭另一个 POCKETPort 实例。桌面启动器和 MCP 宿主共享一个本地端口，不要同时运行两个 |
| 更换来源/IP 后二维码变了 | 停用并重新导入最新手机配置，不要继续使用旧的 Endpoint |
| Python/依赖安装失败 | 确认版本和联网，重新运行安装脚本；保存安装错误用于反馈，不要附上采集文件和私钥 |

### 防火墙

Windows 原生运行时，在可信的专用网络上允许 Python/mitmdump 的入站 UDP 51820。确需命令时，可在管理员 PowerShell 运行：

```powershell
New-NetFirewallRule -DisplayName "POCKETPort WireGuard" -Direction Inbound -Protocol UDP -LocalPort 51820 -Action Allow -Profile Private
```

移除对应规则：

```powershell
Remove-NetFirewallRule -DisplayName "POCKETPort WireGuard"
```

macOS 在系统网络防火墙里允许对应 Python/mitmdump 的入站连接。Linux 如果已启用 UFW，可在可信局域网范围内允许 UDP 51820。**不要直接关闭整个防火墙。**

优先在 Windows 原生安装；WSL2 的 NAT、镜像网络和 Hyper-V 防火墙可能另需配置，不能套用普通同 Wi-Fi 步骤。本版本不自动修改系统防火墙或 WSL 网络。

### 采集范围

WireGuard 客户端配置按 mitmproxy 当前实现路由 IPv4；不承诺覆盖 IPv6。目标 App 的 CA 信任和具体版本会影响可行性。工具只保存 JSON/JSONP，跳过视频、图片、HTML 和非 JSON 数据；超过大小限制的正文会被省略，输出 `omitted_reason`。原始请求正文和所有认证头都不保存，因此不能把结果当作可直接重放的 API 请求。

### 删除与卸载

先停止采集，关闭 WireGuard 和 POCKETPort。删除 Agent 中 `pocketport` MCP 配置和可选 Skill 插件，再删除下载文件夹。用户数据在 `~/.pocketport`，确认不再需要后自行删除；这会删除会话、CA 和配对密钥。手机删除 POCKETPort 隧道和本次安装的 mitmproxy 描述文件/CA 证书。若已移除密钥或重装后换了电脑配置，重新配对和安装新 CA。
