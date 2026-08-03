# 小黑盒签到

仅保留小黑盒（Xiaoheihe）本地 signer 签到相关代码。

## 文件

| 文件 | 说明 |
|------|------|
| `main.py` | 入口（青龙可直接 `task main.py`） |
| `xiaoheihe.py` | 签到封装（查签到状态 → 签到 → 回查） |
| `pure_signin.py` | 本地 hkey/_rnd 签名算法 |
| `notify.py` | 可选通知（Telegram / Gotify / ServerChan / wxpush） |
| `XIAOHEIHE_RND_HANDOFF.md` | 签名算法交接说明（加密） |

## 安装

```bash
pip install -r requirements.txt
```

## 配置

复制 `.env.example` 为 `.env` 或 `xiaoheihe.env`，至少填写：

```bash
XIAOHEIHE_KEY=...
XIAOHEIHE_COOKIE=pkey=...; x_xhh_tokenid=...;
```

也可直接设置环境变量（青龙面板同理）。

## 运行

```bash
python main.py
# 或
python xiaoheihe.py
# 或调试签名
python pure_signin.py "pkey=...; x_xhh_tokenid=..."
```

## 说明

- 签名在本地完成，请求只发往 `https://api.xiaoheihe.cn`
- 通知通道仅在配置了对应环境变量后才会推送
