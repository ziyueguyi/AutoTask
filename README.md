## 本项目是自动化脚本库，暂时只适配青龙使用，请释放你的时间，让脚本来代替你的工作。

<center> <font face="黑体" size=5>目前支持</font></center>

### **app应用**

| 应用名称       | cookie | 账密 | 秘钥 | 是否可用 | 功能                             |
|----------------|--------|------|------|----------|----------------------------------|
| 小黑盒         | ✅     | ❌   | ❌   | ❌       | 每日自动签                        |

### **mini应用**

| 应用名称       | cookie | 账密 | 秘钥 | 是否可用 | 功能                |
|----------------|--------|------|------|----------|---------------------|
| 微信小程序     | ✅     | ❌   | ❌   | ✅       | 每日任务自动完成     |

### **web应用**

| 应用名称                                     | cookie | 账密 | 秘钥 | 是否可用 | 功能                              |
|--------------------------------------------|--------|------|------|----------|-----------------------------------|
| [吾爱破解](https://www.52pojie.cn/)          | ✅     | ❌   | ❌   | ❌       | ~~每日签到~~（签到算法换了，暂未处理） |
| 药丸                                        | ✅     | ❌   | ❌   | ❌       | 每日自动签到                         |
| [阿里云盘](https://www.aliyundrive.com/)     | ❌     | ❌   | ✅   | ✅       | 每日签到得奖励                        |
| [百度贴吧](https://tieba.baidu.com)          | ✅     | ❌   | ❌   | ✅       | 每日自动签到及关注贴吧签到              |
| [恩山论坛](https://www.right.com.cn/)        | ✅     | ❌   | ❌   | ❌       | 每日模拟登录获得+1恩山币（积分）        |
| [好游快报](https://www.3839.com/)            | ✅     | ❌   | ❌   | ❌       | ~~每日爆米花浇水~~                    |
| [交易猫](https://www.jiaoyimao.com/)         | ✅     | ❌   | ❌   | ❌       | ~~每日签到得积分~~                    |
| [科学刀论坛](https://www.kxdao.net/)         | ✅     | ❌   | ❌   | ❌       | ~~每日签到~~                         |
| [夸克网盘](https://pan.quark.cn/)            | ✅     | ❌   | ❌   | ✅       | 每日签到抽奖得空间容量                 |
| [稀土掘金](https://invites.fun/)             | ✅     | ❌   | ❌   | ❌       | 每日签到                             |
| [天翼网盘](https://juejin.cn/)               | ✅     | ❌   | ❌   | ✅       | 每日签到抽奖得空间容量                 |
| [百度网盘](https://pan.baidu.com/disk/main/) | ✅     | ❌   | ❌   | ✅       | 每日签到                             |
| [麦当劳](https://open.mcd.cn/mcp/doc)         | ❌     | ❌   | ✅   | ✅       | 查询并一键领取优惠券；Token：[申请文档](https://open.mcd.cn/mcp/doc) |
| [美团天天神券](https://h5.waimai.meituan.com/) | ❌     | ❌   | ✅   | ✅       | 签到领豆、兑必中符、抢红包；Token 从 H5 Cookie 获取 |
| [天机爻](https://tianjiyao.com/)               | ✅     | ✅   | ❌   | ✅       | 每日签到领积分 + 每日一签查询推送 |
### 青龙

#### 依赖管理

点击青龙面板的依赖管理——>新建依赖——>选择Python3、自动拆分选择是、复制以下的依赖填到名称里——>点击确定，等待安装完成，已经有的依赖就不用安装了。

<details open>
<summary>Python3依赖</summary>

```tex
curl_cffi
fake_useragent
```

</details>

![image-20230413142448646](https://fastly.jsdelivr.net/gh/HeiDaotu/img-bucket/img/202304131425904.png)

#### 环境变量

脚本通过 `ImportSet("前缀")` 绑定青龙变量，统一为 `{前缀}_{功能}`。以百度为例：

```python
self.import_set = self.import_set.ImportSet("BD")
```

| 变量名 | 说明 |
|--------|------|
| `BD_account` | 账号 Cookie，多账号用 `&` 或换行分隔 |
| `BD_notify` | 通知开关，填 `1` 开启 |
| `BD_switch_delay` | 随机延迟开关，填 `1` 开启 |
| `BD_功能名` | 后续功能按此前缀扩展 |
| `ALI_account` | 阿里云盘账号，可直接填 `refresh_token`，或 `{"refresh_token":"xxx"}`，支持多账号 |
| `ALI_notify` | 阿里云盘通知开关，填 `1` 开启 |
| `ALI_switch_delay` | 阿里云盘随机延迟开关，填 `1` 开启 |
| `MCD_account` | 麦当劳账号，可直接填 token，或 `{"token":"xxx"}`，支持多账号；Token 申请见 [open.mcd.cn/mcp/doc](https://open.mcd.cn/mcp/doc) |
| `MCD_notify` | 麦当劳通知开关，填 `1` 开启 |
| `MCD_switch_delay` | 麦当劳随机延迟开关，填 `1` 开启 |
| `QUARK_account` | 夸克网盘 Cookie 字符串，多账号用换行 / `&` / `&&` 分隔 |
| `QUARK_notify` | 夸克网盘通知开关，填 `1` 开启 |
| `QUARK_switch_delay` | 夸克网盘随机延迟开关，填 `1` 开启 |
| `MT_account` | 美团天天神券 token / 整段 Cookie / JSON；多账号用 `&&` 或换行（Cookie 内含 `&` 勿用单 `&` 分隔） |
| `MT_notify` | 美团通知开关，填 `1` 开启 |
| `MT_latitude` / `MT_longitude` | 默认经纬度（去小数点），账号 JSON 可覆盖 |
| `MT_propId` | 兑换必中符类型，默认 `5` |
| `MT_exchangeCoinNumber` / `MT_setexchangedou` | 兑换豆数 / 攒够才兑，默认 `1800` |
| `MT_grab_big` | 填 `1` 开启大额红包监测 |
| `TJY_account` | 天机爻账号 JSON：`{"email":"邮箱","password":"密码"}`，可选加 `cookie`；多账号用 `&&` 或换行 |
| `TJY_notify` | 天机爻通知开关，填 `1` 开启 |

通知渠道（`PUSH_KEY`、`DD_BOT_TOKEN`、`TG_BOT_TOKEN` 等）仍在青龙面板单独配置。

##### 阿里云盘 `refresh_token` 获取方法

1. 浏览器访问 [阿里云盘网页版](https://www.aliyundrive.com) 并登录  
2. 按 `F12` 打开开发者工具 → **Console（控制台）**  
3. 执行：

```js
JSON.parse(localStorage.token).refresh_token
```

4. 复制输出的字符串，写入青龙环境变量 `ALI_account`（可直接填纯字符串，多账号用 `&` 或换行分隔）

也可在 **Application → Local Storage → https://www.aliyundrive.com → token** 中手动复制 `refresh_token`。

##### 夸克网盘 Cookie 获取方法

1. 浏览器访问 [夸克网盘网页版](https://pan.quark.cn) 并登录  
2. 按 `F12` 打开开发者工具 → **Application**（或 **应用**）标签页  
3. 左侧找到 **Cookies** → `https://pan.quark.cn`  
4. 复制全部 Cookie，整理成一行字符串（`name=value`，多项用 `; ` 分隔）  
5. 写入青龙环境变量 `QUARK_account`，例如：

```text
__puus=xxx; __pus=yyy; __kps=zzz; __ktd=aaa; __uid=bbb
```

也可在 Network 里随便点开一个 `pan.quark.cn` / `drive-m.quark.cn` 请求，从 Request Headers 的 `Cookie` 整段复制。

多账号用换行或 `&&` 分隔。不要填 Python 字典，要填上面这种 Cookie 字符串。

##### 美团天天神券 Token 获取方法（H5）

主站 `www.meituan.com` 经常无法登录，请用外卖 H5：

1. 浏览器打开 [美团外卖 H5](https://h5.waimai.meituan.com/) 并登录（可用手机模式 / 模拟移动 UA）
2. 按 `F12` → **Network** → 刷新页面
3. 点开任意 `i.waimai.meituan.com` 请求（如 `openh5/account/center`）
4. 在 Request Headers 的 `Cookie` 中找到 `token=...;`，**只复制 token 值**（不要带 `token=` 和分号）
5. 写入青龙环境变量 `MT_account`

也可直接把整段 Cookie 贴进 `MT_account`，脚本会自动解析其中的 `token`。

任务结束推送会包含神券红包的 **标题、效期、满减**。

单账号 JSON 示例（可带经纬度）：

```text
{"token":"AgHAxxxx","wm_latitude":"30657401","wm_longitude":"104065827"}
```

经纬度去掉小数点；默认可用成都样例 `30657401` / `104065827`。建议 cron 对准神券场次，例如 `5 11,17,21 * * *`。

##### 天机爻账号配置

青龙变量 `TJY_account` 一般只填账密即可：

```text
{"email":"你的邮箱","password":"你的密码"}
```

若登录被 Cloudflare 拦，再补浏览器 Cookie：

```text
{"email":"你的邮箱","password":"你的密码","cookie":"cf_clearance=xxx; ..."}
```

多账号用 `&&` 或换行分隔。建议 cron：`10 8 * * *`。

#### 订阅管理

我们需要把仓库的脚本添加到订阅里，这样可以获取脚本，同样可以不定时获取到最新的脚本(取决于你是否禁用)。

点击青龙面板的订阅管理——>创建订阅

直接在名称这输入：`ql repo git@github.com:ziyueguyi/AutoTask.git "" "initialize|notify|public" "initialize" "main"`
，就会自动输入到其他的空栏。

- **名称：** 随便写，自己看得懂就行，或者直接写`WFRobert脚本库`
- **类型：** 公开仓库
- **链接：** `git@github.com:ziyueguyi/AutoTask.git`
- **定时类型：** crontab
- **定时规则：** 随意，或者写`0 0 5 * * ? `，每天5点自动拉取仓库。
- **黑名单：**`initialize|notify`
- **依赖文件：**`initialize`

其他值默认，点击确定即可。

最后点击订阅管理里面新增的这条信息，点击`运行`即可，这时候我们就可以在定时任务中看到拉取下来的脚本了，如果不想自动更新，自己禁用该订阅管理就行了。

### 特别声明:

本仓库发布的项目中涉及的任何解锁和解密分析脚本，仅用于测试和学习研究，禁止用于商业用途，不能保证其准确性，完整性和有效性，请根据情况自行判断。
