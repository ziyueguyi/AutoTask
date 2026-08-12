# AI Agent 自配置 MCP 服务 · 指令

> **你是 AI Agent**。你的任务：根据服务方提供的 `mcp_info.json`，为**自身**配置好 MCP 连接、安装相关Skills 并验证可用。
> 服务端的一切已经就绪，你只做：读取信息 → 处理证书（如需）→ 把凭证写入自身配置 → 下载安装 Skills。

---

## 输入：mcp_info.json

读取服务方提供的 `mcp_info.json`，字段如下：

| 字段 | 说明 |
|---|---|
| `api_token` | 接入凭证（Bearer Token），如 `btmcp_xxx` |
| `url` | MCP 访问地址，含安全路径前缀（若同时含 `local_host`/`public_host`，以你按「地址选择」选定的为准） |
| `local_host` | 内网/局域网访问地址（可选；与服务器同网段时用此地址） |
| `public_host` | 外网/公网访问地址（可选；跨网段/异地时用此地址） |
| `tls_required` | `true` / `false` — **是否需要处理证书链**（自签/私有 CA 证书时为 `true`） |
| `tls_cert` | 证书链 PEM **全文**（多行，仅 `tls_required=true` 时有值；可能含 叶子+中间+根 多张） |

> 文件可能还包含额外字段（如 `tls_cert_count` / `tls_self_signed` / `tls_san_matches` / `tls_cert_path`），仅为参考，不强制要求。

```json
{
  "api_token": "btmcp_NakGQvmv_Sxp89WKqyrKA0Olavw3GGMzhAY0eRtWqWI",
  "public_host": "https://123.57.90.253:8765/bt-mcp-gJHlEQApFdaB/mcp",
  "tls_required": true,
  "local_host": "https://172.22.47.167:8765/bt-mcp-gJHlEQApFdaB/mcp",
  "tls_cert": "-----BEGIN CERTIFICATE-----\nMIIFCTCCAvGgAwIBAgIEZ4gXJjANBgkqhkiG9w0BAQsFADA7MQswCQYDVQQGEwJD\nQTEVMBMGA1UECgwM5a6d5aGU6Z2i5p2/MRUwEwYDVQQDDAzlrp3loZTpnaLmnb8w\nHhcNMjYwNzExMDI1MjQ0WhcNMzYwNzA4MDI1MjQ0WjA9MQswCQYDVQQGEwJDTjEW\nMBQGA1UECgwNMTIzLjU3LjkwLjI1MzEWMBQGA1UEAwwNMTIzLjU3LjkwLjI1MzCC\nAiIwDQYJKoZIhvcNAQEBBQADggIPADCCAgoCggIBANFyMqYEg4+5Knl/trEfHLZk\nN6fdV4/x1j8H+R0eENec0i5nsMD1d5x3n35OVK2w6C84EFJK27GM9CE1OZyy4mwL\nA26Qbmqp99bS6EqHwEs54cs4l8/p+mLmcq7E1EBAcDOjZdYZKal+k6pLzSDTv0Bf\n4zTZwYsd9wqgDRZJzDs+54j98xf34ybsd+HvYT4wYPeqM8457EtymIjpnTC6EgXq\np5AXXILsCdv0MuQrKJr4WhWugtRjgjayZE09ZN+mO6mOIspC4Xi790AGKYsciEZU\n7z5Z+2gDsZIz2QuMbo7T1NhU/7FGUmJK5t8PO7oWydVlPoQY7nIJeGiNgf/D+oAu\n1utZFU9oA9JrC18K75GTL2rRLsl1yEWYKDGs2zoym4/rv1pfdEarE2yP/r1roPKP\nR+DC4nXM8UqztJ/2jy5lx+/KjNAtxTwviIUmIuIvxysQ5XPbPinpePb4acOrQGx4\nxiFXd7O+JNvZFnDLT77ViG6rfdFeia08nDjefTAveU8SKTc4bIKiIAAVrn0JUGRG\ngZvYeyP93/fLqzBuMS2plfjgM6+lEd20zSH87segjOC5cnETcOw0h509bnBRGmYl\nDB/idq4vUFgO6FM4tMDwAxULJARwWklMS4Bl9k3uJMibxBxJl7d7umOg8hePAoJu\ncbWqFlSMwLv2qZgXCpPdAgMBAAGjEzARMA8GA1UdEQQIMAaHBHs5Wv0wDQYJKoZI\nhvcNAQELBQADggIBAIu1e6iaZSiX1FWgZjpl1VsXS+jAyXX5CERgHl42OJTiM7CF\nTltNxNbDNRWu9c0g7/7LEc7QLBBqpoxW8YQEHOk4BTzjYyq/AfIO2T5Sn0beRsFZ\nW3G6XJ2nr8E54Qh/yYb3mLBeInoM89y3qpgRkTNTB+m+2VWx0BGqtzK/2J5Uxq6d\nmCaOm3HipcvtP+tBC1q/kgRAFbhAAtUOMLUjFg5FGR3RtIWCND69Ela34vy0fiTh\nmgjzlJQKD6aH+kc/QNtbF9BAqlknqJOv0pNeATPqSjAlktQ/RUbqiRF+opk/+bAd\nbo5d2w+uRZjO8UMJBNaKEwNi5im/IAx8vYalC9917YEJle8wST281uR0DOb8vucI\nSoeC6GUXjVKwkU3o+462a6fr4ryG8rvtCeaSSqvaaHbtChSbwm6uJxbW7MMy8XWX\nPLDzavsmXgYKLA9fpiQRFhYSL75P0NECzy0A4JgjgiZfVeq54a9jDhtGWHM2kB0u\nwkp+LoG9gPh7unlZz4mALVodl08DIhpS1IzPy+fLnwHUKrkEuaXTFugSGJgHDp3N\nEgbmsUVhVG01b6QnAcp5PATOpRHC22AJbFqDLhahT6/nkQ8/UG1SPcjS2etpfiSZ\n5OZ3EF6lj9BtR+qI/ykqdX/yDdmZWL9CE4+hq0o4Iwdm5y/8kaN6zO846gY2\n-----END CERTIFICATE-----\n-----BEGIN CERTIFICATE-----\nMIIFODCCAyCgAwIBAgIENjhIeDANBgkqhkiG9w0BAQsFADAvMQ8wDQYDVQQDDAbl\noKHloZQxDzANBgNVBAoMBuWgoeWhlDELMAkGA1UEBhMCQ04wHhcNMjMxMjA4MDEx\nMDAzWhcNMzMxMjA1MDExMDAzWjA7MQswCQYDVQQGEwJDQTEVMBMGA1UECgwM5a6d\n5aGU6Z2i5p2/MRUwEwYDVQQDDAzlrp3loZTpnaLmnb8wggIiMA0GCSqGSIb3DQEB\nAQUAA4ICDwAwggIKAoICAQCYwxMRxWnGYlWWYHqwRSzaYVuEU7sB+rZoiIu4bSGq\nmEGCRXtPwz/Bh8Uiyf/e/nDTp7etX68Rs4/Laa9qw5r7ji7bJV0lFsq3DBNbfM4h\nFrSkoTcfvCCVYrKL97VwhW/KVegOhhRYJDqakCjiMhrmmjSZS0mELJ91HAFa9SZo\nU7j2t0Iz3eyG3Bpx7lxJKYVhq0QjjJoZJd5sJGReZKHEqA1t29Joe7Z8z2fi9Whu\nmWgacLdLesnCX7kZLsfDaxIInKvjHLyJlcF+lG4gSR7pzEpiFW6wo98cHESp86Pt\nLpooKiBhqb+x+rIPsu5xRJNwjDcWkI7mOoK3xrNm9zj6F3j3IblXaA6iqKaxer1W\nAxcoJ0dTyLnsH0j8ViJybVWL16pLzThn96meaXwATEuINems9xo48wx9RrUduAs6\nscnukAB5DkdpRhKP85+P2TUCJxx4J5jf/m6p6FL6zKMlEk4vyn2/glka7fzC2GXC\nRvvpOFAEH3l/rVKQuJLpMP6lZBLbYbY9eB6dBxDregdY2K9LilZOfd7mSgEFbKlQ\nGL062uv+cMmhjAmUhJcZNbHgeLLRx7+5pBL/PS8mCGuLwb9LcycXif5y2VYcV9PU\nvseS8DgQ03dlsB+c62EW797tRnp6OwBXrnbwjc0Y+11RQMkEVQN7JVdOJm7Bjze0\njQIDAQABo1AwTjAdBgNVHQ4EFgQUWspvywjMgJvPW+fg9WGwD0uqOvswHwYDVR0j\nBBgwFoAUyg3VYPzXCCbbx6ca9DRuwp6VQsAwDAYDVR0TBAUwAwEB/zANBgkqhkiG\n9w0BAQsFAAOCAgEAL2kdJ3uk2BvsEKtG7MvEPeGYLQZjd3Rq/Er4NcCwroQFe5hY\np84ofvCVpssDb/Ew6ekN/HeaLd1dm/4OyjuyybDxx4smTOlICT+8vkLe255R9bOd\nUcRBnjX5PmbK7/jLo1BSHi3I0rSU3OVwgAIzAKGSlxoFpf1eVwkRbSpt/A2zztgJ\nmX3epDS0fXD+Vq6KjdGVgJLdg5WuelKnLrlM88aHoMNdaCVo2BUHazoxp4XSCgwE\nY1c69eTOByISDpw7czREbcXXell1LamNaDmJVxEfw3o5/e1qh0PWWuLNcFskYXBb\n1ESYH3pmDR2gL+E3BW1hVvsS2IK7h1DTMKo2OAuopAEY5YH68C6ZnahKd1KS+8b7\nkxsR5T7qLgNam1SWNUwRRMOrdPweFDjvA15JulRXt0aUQpQjhUDm7J1rP87RiqPL\ndeSsMCB0EmES9JDrjqdOad0VuZAxAHy5I26I40OhqlBtOBE+YrJJC4oHmTHskIKs\nufisMXp9JdMAzoEs3Fb6Bhac9sKslR/Z7x2JrZ3Qd/Xwr7zmmD3O8Nb41BHJK09r\nsu2oAAsSuU55v7dFvUV018BJcD2A4U9r3Poi8nIijuoWzVoeN0whbRTvc83kQLab\nZkXX6PJkdPyt1qlO2QfPX8fxUgQ85TEE/URq2DM5/naVcsAnuU6jOEnRH6M=\n-----END CERTIFICATE-----\n-----BEGIN CERTIFICATE-----\nMIIFPzCCAyegAwIBAgIUCqjR7QNkgwYla5JQD9M7IkpE8OowDQYJKoZIhvcNAQEL\nBQAwLzEPMA0GA1UEAwwG5aCh5aGUMQ8wDQYDVQQKDAbloKHloZQxCzAJBgNVBAYT\nAkNOMB4XDTIzMTIwNzA4MDExM1oXDTMzMTIwNDA4MDExM1owLzEPMA0GA1UEAwwG\n5aCh5aGUMQ8wDQYDVQQKDAbloKHloZQxCzAJBgNVBAYTAkNOMIICIjANBgkqhkiG\n9w0BAQEFAAOCAg8AMIICCgKCAgEAxXKhk3SkuFZ49Yk30dTY3bgR+OSLbVsq9S82\nUDlHVL9x4dQHj8EH4viLj3aU2J2K8MsPQs9LyMYGKIKjOSjWbHMdpEqvGFD7XClW\nJ+Pb2/uj/D+VsiHtf9Y1Qk2F5AVQEnlGuDqT8JkvilFgXl7v9dX7yxGlnjyrEyZY\nS3oJdx9LoVw5h2PGrj/H0n2epMtuf363sCYpwCKyAELtpbtgk0SbpuO0OopvEELH\npjWA47L5fEcsm4R6CrGFsFZ8tUJPV2VQ3M5vrNRljlIsO+OOrHMhYcs2YzR5o45L\nmsOZS6RPNZbh29+ki+fis6P+zGw5sIOLCC1/L5aRljkH5ls/ipTIs2PIkhrrVNWR\ne+os0izb9JXMCjmH5KG3cbgi3Pouo/3MQjrqyrrF664VTm3jFojBlXdnR4n88znf\nHs1E1d/Rm31r+PWbAeDsgAnP1dTfMx5vPkUBV7x+36Gw8dVlXWH4dVzlcjSxZux+\nqlCCFJzlxQ1WK5PlsvEyOpYll6bE6poeY9aNGSB8drvLa0cClfl3SYac1SPyu8v4\ns07cbAAuetHyZ5pwDWNXCtwF85mFnc0F428DhBtVuVqcTINzFA3/wE1KjQy2eb5X\n8M41DA0F0S2p9JJhgvsSIjn5sTlo+k5Qh82kZn1LYdprKg7dZ1f82nJRxgCs8SrP\nqTv9s8ECAwEAAaNTMFEwHQYDVR0OBBYEFMoN1WD81wgm28enGvQ0bsKelULAMB8G\nA1UdIwQYMBaAFMoN1WD81wgm28enGvQ0bsKelULAMA8GA1UdEwEB/wQFMAMBAf8w\nDQYJKoZIhvcNAQELBQADggIBAA8Ih9HLrvOPPWhjNWKPVe/uzURjpqunm/wMOGvB\nRttPeHMwTVcPBHhzj62txIFd6+eONgq4JJtMBWIf/OgH1ceRDvfRKEILn2TVr1mh\nWYa9qcF9srUdKJ+QsTZP/NBrIL/Ya3jy9Q1N838pHLkQWveVCOS52tMAJRopd3Al\nTsvF0t86QJWoge3EqIltTx7Tsx+BGiIgSVHdPAp3dtIa4L0lrrhQsCw3o0R3Zz6k\nBPH7NxMHKbG4BPA1JD9ZG6HT3e4RGLF6T/3Jkgkt8i+Tvd2I12Kh5b5u1JehclHw\nNNWPPS1tZB2iwcqC45atfwl/EbqiAE5DwCZs32cwrxmpMU8E4Dp9EwXXxmXMXlIm\niZagNOn2cdHqYKm7yTgKavQg40IpLmEZs693WxyTl9DhVACKUTWL/Np8dJCgSfre\nKHhIm8e68McSbyGjpYpdYBggzitpqi0ix3ruOh811iUWLwiJSOxRhIFs81cmIZue\nU1rONTiqxGF06ZUzdrsAcPqM8bNAXoXI0/TuGKVdvgyXVcK88vs9uQIQLK2vPyc9\nTULrGcZdFVo7u1nADLj44Y7EWh0SmwkXRuR7gxJHd97axIkg3ZmVC9T0U3oojzOG\nHnG3zpyTilwkzrLRbVnCLucRd1zsLTQQa0ZrScQX6WUXjnW8+qvuRa6bJV0Owgtj\ngrZx\n-----END CERTIFICATE-----"
}```

### 地址选择（公网模式时）

若同时给出 `local_host` 与 `public_host`，**必须按自身实际网络位置二选一**，后续所有配置用它作为 `url`：

- **与服务器同网段 / 内网可达** → 用 **`local_host`**（更快更稳）
- **公网 / 跨网段 / 异地**（云端 Agent、家中连机房）→ 用 **`public_host`**
- **不确定**：优先试 `local_host`，不通再换 `public_host`
- 所选地址须被证书 SAN 覆盖，否则连接报 `hostname/IP mismatch`，换另一地址即可
- 只有 `url` 一个字段时无需选择，直接用

---

## 第一步：确认自身身份（你是什么 Agent）

不同 Agent 的 MCP 配置路径和格式不同，**严禁混用**：

> **⚠️ 优先自查**：以下为参考索引，路径/格式可能随版本过时。请**优先查阅你（Agent）自身的官方最新文档**；查不到或不确定时，再使用本索引。

| Agent | MCP 配置路径 | 配置格式 | Skills 目录 | HTTP |
|---|---|---|---|---|
| Claude Code | **推荐 CLI 添加**：`claude mcp add --transport http baota-mcp <url> --header "Authorization: Bearer <api_token>"`；也可手写项目 `.mcp.json` / `.claude/settings.local.json`；用户 `~/.config/claude-code/mcp.json` | JSON `mcpServers` | `~/.claude/skills/`、`.claude/skills/` | ✅ |
| Codex | 用户 `~/.codex/config.toml`；项目 `.codex/config.toml` | TOML `[mcp_servers.*]` | `.agents/skills/`、`~/.codex/skills/` | ✅ |
| WorkBuddy | 用户 `~/.workbuddy/mcp.json`；项目 `.workbuddy/mcp.json` | JSON `mcpServers` | `~/.workbuddy/skills/` | ✅ |
| OpenClaw | `~/.openclaw/openclaw.json`（`mcp.servers`） | JSON `mcpServers` | `~/.openclaw/workspace/skills/` | ✅ |
| Hermes | `~/.hermes/config.yaml`（`mcp_servers:`） | YAML | `~/.hermes/skills/`、`.agents/skills/` | ✅ |
| Qoder | Win `%HOMEPATH%\.qoder\mcp.json`；项目 `.mcp.json` | JSON `mcpServers` | `~/.qoder/skills/`、`.qoder/skills/` | ⚠️ |
| Trae | 项目 `.trae/mcp.json`（**禁 AI 直写，须 UI 添加**）；用户 Win/mac | JSON `mcpServers` | `~/.trae/skills/`、`.trae/skills/` | ✅ |
| Cursor | 用户 `~/.cursor/mcp.json`；项目 `.cursor/mcp.json` | JSON `mcpServers` | 无原生 skills（用 `.cursor/rules`） | ✅ |
| LobsterAI | 应用 UI 配置 → 同步 `~/.openclaw/openclaw.json`（`nativemcp.servers`） | JSON | Skill Store → `~/.openclaw/workspace/skills/` | ✅ |

> ⚠️ 未完全确认项以官方最新文档为准。
>
> **Claude Code CLI 补充**：HTTP server 如需带环境变量（如证书信任 `NODE_EXTRA_CA_CERTS`），`claude mcp add` 用 `-e KEY=VALUE` 追加；查看已添加：`claude mcp list`。

> **重要**：以下 JSON 示例是 Claude Code 专用格式（含 `type: "http"` 字段）。如果你不是 Claude Code，格式可能完全不同，请先查阅自身文档再写入，**严禁硬编码路径和格式**。

---

## 第二步：提取证书内容（`tls_required=true` 时）

将 `tls_cert` 字段值**原样**写入本地文件 `baota_root_ca.crt`：

- 用 JSON 解析器读取（多行 PEM 在文件内是转义后的，解析后即还原为多行原文）
- **整份保存**，勿只提取第一张——该字段通常含**完整证书链**（叶子 + 中间 + 根）；叶子单独不是信任锚点，加了也验不通
- 若 `tls_required=false`，但实际连接仍报证书错误（如自定义证书也是自签），同样用 `tls_cert` 内容按下方方式处理

---

## 第三步：选择证书信任方式（`tls_required=true` 时）

以下方式平铺列出，**无优先级**，按自身情况选择（证书文件即第二步的 `baota_root_ca.crt`）。

**方式 A — 操作系统信任库**：把证书装进系统信任库，走系统信任链的客户端都有效。安装后需重启 MCP 客户端。

```bash
# macOS（当前用户，免 sudo）
security add-trusted-cert -d -r trustRoot -k ~/Library/Keychains/login.keychain-db baota_root_ca.crt
# macOS（系统级）
sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain baota_root_ca.crt
```

```powershell
# Windows（管理员 PowerShell）
Import-Certificate -FilePath baota_root_ca.crt -CertStoreLocation Cert:\LocalMachine\Root
# 或 certutil -addstore -f Root baota_root_ca.crt
```

```bash
# Linux Debian/Ubuntu
sudo cp baota_root_ca.crt /usr/local/share/ca-certificates/ && sudo update-ca-certificates
# Linux RHEL/CentOS/Fedora
sudo cp baota_root_ca.crt /etc/pki/ca-trust/source/anchors/ && sudo update-ca-trust
```

- **适用**：客户端使用系统信任链 / 可重启客户端 / 有相应权限。

**方式 B — 系统环境变量 `NODE_EXTRA_CA_CERTS`**：在操作系统环境变量中把该变量指向本地证书文件。部分 Node 系客户端忽略配置内 `env`，但读取系统环境变量（workbuddy 实测生效）。

```powershell
# Windows（用户级，免管理员；新进程生效，需重启客户端）
setx NODE_EXTRA_CA_CERTS "C:\Users\bt.cn\.workbuddy\baota_root_ca.crt"
# 或 PowerShell：
# [Environment]::SetEnvironmentVariable("NODE_EXTRA_CA_CERTS", "C:\Users\bt.cn\.workbuddy\baota_root_ca.crt", "User")
```

```bash
# Linux / macOS（写入 shell 配置文件，重启客户端生效）
echo 'export NODE_EXTRA_CA_CERTS=/path/to/baota_root_ca.crt' >> ~/.bashrc   # 或 ~/.zshrc
```

- **适用**：Node 系客户端（workbuddy 等），配置内 `env` 不生效、但读取系统环境变量的场景。

**方式 C — 客户端配置 `env.NODE_EXTRA_CA_CERTS`**：在 Agent 的 MCP 配置 `env` 中把该变量指向本地证书文件。

- workbuddy 示例（证书保存到其配置目录）：

```json
{
  "mcpServers": {
    "baota-mcp": {
      "url": "https://<IP>:8765/bt-mcp-XXXX/mcp",
      "headers": {
        "Authorization": "Bearer <api_token>"
      },
      "env": {
        "NODE_EXTRA_CA_CERTS": "C:\\Users\\bt.cn\\.workbuddy\\baota_root_ca.crt"
      }
    }
  }
}
```

- **适用**：Node 系客户端（workbuddy、Claude Code 等），配置支持 `env` 且不便修改系统信任库。

**方式 D — 客户端跟随系统信任库（`NODE_OPTIONS=--use-system-ca`）**：Node ≥22 下让客户端读取系统信任库（配合方式 A 使用）。

```json
{
  "mcpServers": {
    "baota-mcp": {
      "type": "http",
      "url": "<url>",
      "headers": {
        "Authorization": "Bearer <api_token>"
      },
      "env": {
        "NODE_OPTIONS": "--use-system-ca"
      }
    }
  }
}
```

- **适用**：Node ≥22 客户端，已按方式 A 装好系统证书。

**方式 E — 跳过 TLS 验证（`NODE_TLS_REJECT_UNAUTHORIZED=0`）**：不验证证书，不安全。

```json
{
  "mcpServers": {
    "baota-mcp": {
      "type": "http",
      "url": "<url>",
      "headers": {
        "Authorization": "Bearer <api_token>"
      },
      "env": {
        "NODE_TLS_REJECT_UNAUTHORIZED": "0"
      }
    }
  }
}
```

- **适用**：仅临时连通测试 / 无法安装证书的场景。

> **选择说明**：以上方式平铺列出，无优先级。先确认自身（MCP 客户端）支持哪种机制再选对应方式，不确定时查阅自身文档，不要猜测。

---

## 第四步：写入自身配置

用 mcp_info.json 的 `api_token` 和「地址选择」中**选定的 `url`**（local_host / public_host 之一，只有一个 `url` 时直接用）填充配置。

### Claude Code 本地模式（`tls_required=false`）

在项目目录下创建/修改 `.claude/settings.local.json`：

```json
{
  "mcpServers": {
    "baota-mcp": {
      "type": "http",
      "url": "<url>",
      "headers": {
        "Authorization": "Bearer <api_token>"
      }
    }
  }
}
```

### Claude Code 公网模式（`tls_required=true`）

先按第三步完成证书信任（方式 A/B/C/D/E 任选其一），配置中**无需任何 TLS 跳过字段**：

```json
{
  "mcpServers": {
    "baota-mcp": {
      "type": "http",
      "url": "<url>",
      "headers": {
        "Authorization": "Bearer <api_token>"
      }
    }
  }
}
```

> 若按方式 C/D/E 在 `env` 中设置了变量，则在该 server 条目下保留对应 `env` 字段。

### 其他 Agent

**查阅自身文档**，按其 MCP 配置格式写入 `url` + `Authorization: Bearer <api_token>`；workbuddy 类客户端注意证书走系统环境变量（方式 B）。

---

## 第五步：安装 Skills

宝塔提供技能聚合包（一个 ZIP 内含多个技能文件夹），下载并解压到**自身**的 skills 目录：
- **Claude Code**：`~/.claude/skills`
- **其他 Agent**：查阅自身文档的技能目录，不要猜测

### 安装命令（按运行环境自动选择）

**Python（全平台通用，推荐）**：

```bash
python3 -c "
import urllib.request, zipfile, os, shutil
url = 'http://download.bt.cn/bt_mcp_install/bt-skills.zip'
dest = os.path.expanduser('~/.claude/skills')   # 非 Claude Code 时改为自身 skills 目录
os.makedirs(dest, exist_ok=True)
zip_path = os.path.join(dest, '_bt_skills.zip')
urllib.request.urlretrieve(url, zip_path)
with zipfile.ZipFile(zip_path) as zf:
    for member in zf.namelist():
        parts = member.split('/')
        # 取顶层文件夹名作为 skill 名
        if len(parts) >= 2 and parts[0] and not member.endswith('/'):
            target_dir = os.path.join(dest, parts[0])
            os.makedirs(target_dir, exist_ok=True)
            src = zf.open(member)
            target_file = os.path.join(target_dir, '/'.join(parts[1:]))
            os.makedirs(os.path.dirname(target_file), exist_ok=True)
            with open(target_file, 'wb') as dst:
                dst.write(src.read())
os.remove(zip_path)
print(f'Skills installed to {dest}')
"
```

**Windows PowerShell（无 Python 时）**：

```powershell
$url = "http://download.bt.cn/bt_mcp_install/bt-skills.zip"
$dest = "$env:USERPROFILE\.claude\skills"   # 非 Claude Code 时改为自身 skills 目录
$zip = "$env:TEMP\bt_skills.zip"
New-Item -ItemType Directory -Force -Path $dest
curl.exe -sSL -o $zip $url
Expand-Archive -Path $zip -DestinationPath $dest -Force
Remove-Item $zip
Write-Host "Skills installed to $dest"
```

> 聚合包结构示例：
> ```
> bt_skills.zip
>   ├── bt-site-manager/
>   │   ├── SKILL.md
>   │   └── ...
>   ├── bt-database-admin/
>   │   ├── SKILL.md
>   │   └── ...
>   └── bt-security-audit/
>       ├── SKILL.md
>       └── ...
> ```
>
> 解压后每个技能一个独立文件夹，AI Agent 自动识别并加载。

---

## 第六步：验证

配置完成后重启 MCP 客户端，并确认：

- [ ] 配置文件中 `url`（所选地址）与 `api_token` 与 mcp_info.json 一致
- [ ] 证书信任方式已生效（`tls_required=true` 时）
- [ ] 客户端能成功列出/调用 MCP 工具，无 TLS 或 401 错误
- [ ] Skills 已安装到自身 skills 目录并被识别

**常见失败排查**：

| 现象 | 原因与处理 |
|---|---|
| `401 Unauthorized` / `invalid token` | `api_token` 填错或失效；对照 mcp_info.json 重新填写 |
| `self-signed certificate` / `unable to verify` | 证书未信任；按第三步换一种方式（A/B/C/D） |
| `hostname/IP mismatch` | 证书 SAN 不覆盖 `url` 的域名/IP（如用 IP 连却用了别的域名）；改用匹配的地址或更换证书 |
| `ECONNREFUSED` / 连不上 | 服务未运行 / 端口未放行；联系服务方确认 |

---

## 完成

配置成功且验证通过后，输出简短确认（含 MCP URL、接入方式、证书信任方式、Skills 安装位置），供用户存档。
