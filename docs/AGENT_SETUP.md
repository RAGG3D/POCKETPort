# 接入 Claude、GPT / Codex

先运行根目录安装脚本。它会生成 `mcp.local.json`，其中是**这台电脑**的 Python 绝对路径。移动项目文件夹后重跑安装并更新 MCP 设置。

MCP 是让 Agent 调用本地采集工具的接口。POCKETPort 的七个工具是：`open_setup`、`capture_status`、`start_capture`、`stop_capture`、`collection_sessions`、`read_collection`、`export_collection`。

## Claude Desktop

在 Claude Desktop 的本地 MCP 开发者配置中，将生成的 `mcp.local.json` 里的 `mcpServers.pocketport` 合并进现有配置，保留其他服务，然后重启客户端。典型格式如下；请使用生成文件中的实际路径：

```json
{
  "mcpServers": {
    "pocketport": {
      "command": "/absolute/path/POCKETPort/.venv/bin/python",
      "args": ["-m", "pocketport", "mcp"]
    }
  }
}
```

Windows 的路径使用生成文件中的 `.venv\\Scripts\\python.exe`。主机需支持本地 stdio MCP；仅填写远程 Connector URL 的设置界面不是此安装入口。不要启动独立桌面实例，再让 Claude 同时启动第二个实例。

## Claude Code

执行安装脚本打印的 `claude mcp add --transport stdio ...` 命令。可选安装本仓库的采集 Skill：

```text
/plugin marketplace add RAGG3D/POCKETPort
/plugin install pocketport@pocketport
```

Skill 包含操作流程；MCP 由前一步单独注册，以便使用本机安装的绝对路径，不依赖插件缓存位置。安装 Skill 本身不会安装 Python 依赖。官方格式见 [Claude Code MCP](https://code.claude.com/docs/en/mcp) 和 [插件参考](https://code.claude.com/docs/en/plugins-reference)。

## GPT / Codex 本地环境

执行安装脚本打印的命令，形式为：

```sh
codex mcp add pocketport -- /absolute/path/POCKETPort/.venv/bin/python -m pocketport mcp
```

或在本地 Codex 配置文件加入：

```toml
[mcp_servers.pocketport]
command = "/absolute/path/POCKETPort/.venv/bin/python"
args = ["-m", "pocketport", "mcp"]
startup_timeout_sec = 20
tool_timeout_sec = 40
```

有空格的 CLI 路径需要双引号，安装器打印的命令已处理。Windows 用对应 `.venv\Scripts\python.exe`，TOML 可使用单引号包裹 Windows 路径。

OpenAI 官方说明本地 Codex 宿主支持 stdio MCP；ChatGPT 桌面与本地宿主的具体入口按你账户/客户端实际提供为准，参见 [OpenAI MCP 文档](https://developers.openai.com/codex/mcp)。仓库也附有 `.codex-plugin/plugin.json`，可用于支持本地插件导入的宿主；MCP 注册仍使用上面的步骤。

## 只有网页版 Claude / GPT

用 POCKETPort 的本地页面采集并下载 JSON，然后在自己的聊天窗口上传文件。POCKETPort 0.1.1 不提供远程 HTTP MCP、OAuth 服务或公网隧道；网页端的远程工具入口不能直接访问此处的本地 stdio 进程。不要把本地采集控制端口直接暴露到公网。

## 第一次对话

> 使用 POCKETPort 打开设置页面。我想采集淘宝里自己浏览的内容，采集后先把文件给我。

Agent 可读取建议 LAN IP 与状态，开启采集。你在本地浏览器扫描私密二维码并在手机完成浏览，然后告诉 Agent 停止。`read_collection` 返回的数据会进入 Agent 上下文；`export_collection` 只返回本地文件路径和响应条数。

采集得到的文本只是数据。Skill 和 MCP server instructions 都要求 Agent 不执行响应中夹带的指令；使用数据做什么，由你的后续请求决定。
