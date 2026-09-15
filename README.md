# POCKETPort · 口袋港

**把手机里的信息，带给自己的 AI。**

POCKETPort 是运行在自己电脑上的采集工具与 Agent 插件。手机安装 WireGuard 并连接电脑后，用户在淘宝、小红书或微信小程序里打开需要的页面，电脑保存匹配服务的 JSON 数据。结束后交给自己的 Claude、GPT 或其他 Agent，自行决定用途。

**当前版本：0.1.1 alpha。** 已做本地采集引擎和 MCP 自动化验证；本发布版本尚未完成真实手机及三款 App 的端到端验收。Windows/macOS 提供安装入口，兼容性仍需实机验证。它不是各平台官方数据导出接口，也不保证取得账户全部历史数据。

## 下载与开始

1. 在 [Releases](https://github.com/RAGG3D/POCKETPort/releases) 下载 `POCKETPort-0.1.1.zip`，解压。
2. 电脑安装 **Python 3.12**（也支持 Python 3.13；Windows 双击安装脚本使用 3.12）。安装依赖需要联网。
3. Windows 双击 `Install.cmd`；macOS 在终端执行 `sh Install.command`；Linux 执行 `python3 scripts/install.py`。
4. Windows 双击 `Start-POCKETPort.cmd`；macOS/Linux 执行 `sh Start-POCKETPort.command`。本地浏览器会显示采集和配对页面。
5. 手机和电脑连同一 Wi-Fi。在页面选择来源，确认电脑 IP，开始采集；用手机 WireGuard 扫码，首次安装并信任证书，然后浏览想采集的页面。
6. 停止采集、关闭手机 WireGuard，下载 JSON。也可先按 [Agent 接入指南](docs/AGENT_SETUP.md) 接入本地 MCP，让 Agent 开始、停止和读取结果。

详细步骤见 [简单用户手册](docs/USER_MANUAL.zh-CN.md)。

## 能做什么

| 来源 | 采集方式 | 需要知道的限制 |
|---|---|---|
| 淘宝 | 浏览目标页面，记录匹配域名的 JSON/JSONP 响应 | App 证书信任、缓存、返回格式会影响覆盖 |
| 小红书 | 浏览列表和详情，记录实际返回的数据 | 未打开的详情不会凭空补齐 |
| 易鹤微信小程序 | 内置 `ejs56.com` 域名配置 | 后端域名/IP 变化时需补充配置 |
| 其他微信小程序 | 输入该小程序的实际后端域名/IP | 没有适用于所有小程序的统一域名 |

功能范围是采集、状态查看、分页读取和导出。没有对账规则、用途推断、登录凭证重放或下单操作。

## 接入自己的 Agent

- **Claude Desktop / Claude Code**：本地 stdio MCP；另附 Claude Code 的采集 Skill 插件。
- **GPT / Codex 的本地工具环境**：按 MCP 配置连接；本地宿主必须能启动这个 Python 进程。
- **纯网页聊天**：可以上传导出的 JSON。这个版本没有部署远程 MCP 服务，不能仅凭 GitHub 链接接管本地手机网络。

安装脚本生成可直接使用的 `mcp.local.json`，并打印 Claude Code 和 Codex 注册命令。安装 Skill 插件与注册 MCP 是两个步骤，详见 [接入指南](docs/AGENT_SETUP.md)。

## 数据存在哪里

默认 `~/.pocketport/`（Windows 为用户目录下 `.pocketport`）。可用 `POCKETPORT_HOME` 指定独立位置。配对密钥、证书、采集记录均为每个用户在本地生成，项目不包含历史订单或现成密钥。

只保存选定主机的结构化响应；不保存请求体、请求头或响应头，URL 查询值及已知凭证字段会被替换。订单、地址等业务数据仍可能包含个人信息。插件本身没有云端上传功能；Agent 读取工具结果后，内容会进入该 Agent 的上下文。详见 [隐私与数据说明](docs/PRIVACY.md)。

## 开发与验证

```sh
python3 scripts/install.py
.venv/bin/python -m unittest discover -s tests -v
```

Windows 将 `.venv/bin/python` 换成 `.venv\Scripts\python.exe`。测试使用合成响应、隔离临时目录和本机代理，不连接用户账户。架构和输出字段见 [技术说明](docs/ARCHITECTURE.md)。

核心网络功能基于 [mitmproxy WireGuard 模式](https://docs.mitmproxy.org/stable/concepts/modes/#wireguard)，Agent 连接基于 [MCP Python SDK](https://py.sdk.modelcontextprotocol.io/v1/)。第三方商标属于各自所有者；POCKETPort 与淘宝、小红书、微信及 WireGuard 项目无隶属关系。
