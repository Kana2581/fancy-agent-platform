# Discord 斜杠命令配置指南

这份文档用于说明如何把 Discord 应用的斜杠命令（Slash Command）接到 Fancy Agent。

## 先说结论

Discord 接入和钉钉、Telegram 都不一样，它走的是 **Interactions（交互）** 机制，校验方式是 **Ed25519 签名**，不是 HMAC。最容易卡住的点是：

**Discord 会在你保存 Interactions Endpoint URL 时立刻发一个 PING 来验签，验不过就保存不了。**

所以正确顺序是先在 Fancy Agent 里填好 Public Key，再去 Discord 后台填 URL，否则验签必然失败。

实际顺序：

1. 在 Discord Developer Portal 创建应用，拿到 `Public Key`
2. 回到 Fancy Agent，新建 `Discord` 类型的 webhook，填入 `Public Key`
3. 拿到 Fancy Agent 生成的正式 Interactions Endpoint URL
4. 把这个 URL 填回 Discord 应用的 `Interactions Endpoint URL`（此时 Discord 发 PING 验签）
5. 注册一个斜杠命令
6. 在频道里用斜杠命令验证

## 前置条件

开始前请确认：

- Fancy Agent 后端已经部署完成
- 你的服务有**公网可访问地址**且支持 HTTPS
- 你有一个 Discord 应用（在 Developer Portal 创建）

## 完整操作步骤

### 1. 拿到 Public Key

进入 [Discord Developer Portal](https://discord.com/developers/applications)，选择（或新建）你的应用：

`General Information` → 找到 **Public Key**，复制它。

同时记下这两个值，后面注册命令要用：

- `Application ID`（General Information 里）
- `Bot Token`（Bot 页签里，若没有先添加 Bot）

### 2. 在 Fancy Agent 中创建 Discord webhook

进入 Fancy Agent 的入站 Webhook 页面，新建一条 webhook：

- `名称`：自定义，例如 `Discord 助手`
- `类型`：`Discord`
- `绑定 Agent`：选择希望被斜杠命令触发的 Agent
- `Discord Public Key`：填刚才复制的 Public Key

创建成功后，Fancy Agent 会生成一个正式的 Interactions Endpoint URL，格式类似：

```text
https://your-domain/api/v1/discord/interactions/<slug>
```

### 3. 把 URL 配回 Discord

回到 Discord Developer Portal 的应用页：

`General Information` → **Interactions Endpoint URL** → 填入上一步的 URL → 保存。

保存时 Discord 会立刻向该 URL 发一个 `type=1`（PING）请求做 Ed25519 验签。只要 Fancy Agent 里的 Public Key 填对了，验签就能通过，URL 保存成功。

> 如果保存时报错，几乎都是 Public Key 填错或服务未部署最新代码，详见下方常见问题。

### 4. 注册一个斜杠命令

用下面的命令注册一个名为 `ask` 的斜杠命令（替换占位值）：

```bash
APP_ID='<你的 Application ID>'
BOT_TOKEN='<你的 Bot Token>'

curl -X PUT "https://discord.com/api/v10/applications/$APP_ID/commands" \
  -H "Authorization: Bot $BOT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '[{
    "name": "ask",
    "description": "向绑定的 Agent 提问",
    "type": 1,
    "options": [{
      "name": "prompt",
      "description": "发给 Agent 的内容",
      "type": 3,
      "required": true
    }]
  }]'
```

> Fancy Agent 会从命令参数里按 `prompt` / `content` / `message` / `text` / `question` 的顺序取第一个匹配的作为输入，所以参数名用 `prompt` 最稳妥。

### 5. 验证是否接通

在已安装该应用的频道里输入：

```text
/ask prompt: 你好
```

正常流程是：

1. Discord 把交互回调给 Fancy Agent
2. Fancy Agent 用 Public Key 做 Ed25519 验签
3. Fancy Agent 先立即返回一个「思考中」的延迟响应（deferred），避免 Discord 3 秒超时
4. Agent 在后台执行完后，Fancy Agent 再异步编辑那条消息，填入最终回复

> Discord 单条消息上限 2000 字，超长回复会被截断并标注「回复过长，已截断」。

频道、服务器（guild）、用户三者组合决定会话归属，不同用户之间不会串扰。

## 常见问题

### 1. 保存 Interactions Endpoint URL 时报验证失败

这是 Ed25519 验签没过，常见原因：

- Fancy Agent 里填的 Public Key 不对（复制错、带了空格换行）
- URL 填错，没指向 Fancy Agent 的 Discord 端点
- 服务端没部署到最新代码

排查：重新从 Developer Portal 复制 Public Key，更新 Fancy Agent 里的 webhook，再保存 URL。

### 2. 斜杠命令在频道里看不到

- 全局命令注册后可能要等几分钟到一小时才在所有服务器生效
- 确认应用已被安装/邀请到该服务器，且有使用斜杠命令的权限

### 3. 命令有响应但一直显示「思考中」

说明验签和延迟响应都成功了，但后台 Agent 执行失败或超时。检查：

- 绑定的 Agent 配置是否正常（模型 api_key、工具等）
- 后端日志里该次执行的报错

### 4. “内部 Secret” 要不要配到 Discord

不用。Discord 通道只需要：

- Fancy Agent 中保存 `Public Key`
- Discord 后台配置 Fancy Agent 生成的 Interactions Endpoint URL

创建时弹窗显示的内部 secret 对 Discord 通道无用。

## 一句话记忆版

**先在 Fancy Agent 填好 Public Key，再把生成的 URL 配回 Discord（这一步会立即验签），最后注册斜杠命令。**
