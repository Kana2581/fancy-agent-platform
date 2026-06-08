# Telegram Bot Webhook 配置指南

这份文档用于说明如何把 Telegram 机器人接到 Fancy Agent 的入站 Webhook。

## 先说结论

Telegram 接入和钉钉不同，没有「拿 AppSecret」这一步，最容易卡住的点是：

**Telegram 的 webhook 是你主动用 `setWebhook` API 注册的，不是在某个后台页面里填的。**

实际顺序应该是：

1. 在 Telegram 里找 BotFather 创建机器人，拿到 `Bot Token`
2. 回到 Fancy Agent，新建 `Telegram Bot` 类型的 webhook，填入 `Bot Token`
3. 拿到 Fancy Agent 生成的正式 webhook URL 和内部 `secret`
4. 用 `setWebhook` API 把这个 URL 和 secret 注册给 Telegram
5. 给机器人发消息验证

## 前置条件

开始前请确认：

- Fancy Agent 后端已经部署完成
- 你的服务有**公网可访问地址**（Telegram 服务器要能访问到）
- 服务支持 HTTPS（Telegram 的 `setWebhook` 默认要求 HTTPS）

## 完整操作步骤

### 1. 用 BotFather 创建机器人

在 Telegram 里搜索 `@BotFather`，发送：

```text
/newbot
```

按提示设置机器人名称和用户名，创建成功后 BotFather 会返回一个 token，格式类似：

```text
123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ
```

这就是 `Bot Token`，保存好，下一步要用。

### 2. 在 Fancy Agent 中创建 Telegram webhook

进入 Fancy Agent 的入站 Webhook 页面，新建一条 webhook：

- `名称`：自定义，例如 `Telegram 助手`
- `类型`：`Telegram Bot`
- `绑定 Agent`：选择希望被 Telegram 触发的 Agent
- `Telegram Bot Token`：填刚才从 BotFather 拿到的 token

创建成功后，Fancy Agent 会生成：

- 一个正式的 webhook URL，格式类似：

  ```text
  https://your-domain/api/v1/telegram/webhooks/<slug>
  ```

- 一个内部 `secret`（弹窗里只显示一次，请复制保存）

这个 `secret` 会作为 Telegram 回调时携带的校验令牌。

### 3. 用 setWebhook 注册地址

在任意能联网的终端执行下面的命令，把占位值替换成你自己的：

```bash
BOT_TOKEN='123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ'
WEBHOOK_URL='https://your-domain/api/v1/telegram/webhooks/<slug>'
SECRET_TOKEN='<Fancy Agent 生成的 secret>'

curl -X POST "https://api.telegram.org/bot$BOT_TOKEN/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "'"$WEBHOOK_URL"'",
    "secret_token": "'"$SECRET_TOKEN"'",
    "allowed_updates": ["message"],
    "drop_pending_updates": true
  }'
```

返回 `{"ok":true,"result":true,"description":"Webhook was set"}` 即注册成功。

> `secret_token` 必须和 Fancy Agent 里的内部 secret 完全一致。Telegram 每次回调会把它放在 `x-telegram-bot-api-secret-token` 请求头里，Fancy Agent 用它校验来源。

### 4. 验证是否接通

直接私聊你的机器人，或把它拉进群里发消息。

正常流程是：

1. Telegram 把消息回调给 Fancy Agent
2. Fancy Agent 校验 `x-telegram-bot-api-secret-token`
3. Fancy Agent 调用绑定的 Agent 执行
4. Fancy Agent 通过 `sendMessage` API 把回复发回对话

群聊和私聊、以及群里的不同话题（message thread）会各自维护独立会话，互不串扰。

## 常见问题

### 1. setWebhook 返回 ok 但机器人没反应

优先检查：

- webhook URL 是否真的公网可访问（用浏览器或 curl 直接访问应有响应）
- `secret_token` 是否和 Fancy Agent 里的 secret 一致
- webhook 是否绑定了正确的 Agent

可以用下面的命令查看当前 webhook 状态和最近的错误：

```bash
curl "https://api.telegram.org/bot$BOT_TOKEN/getWebhookInfo"
```

`last_error_message` 字段会告诉你 Telegram 回调失败的原因。

### 2. setWebhook 报 HTTPS / SSL 错误

Telegram 要求 webhook 地址是有效 HTTPS。自签证书不被接受，需要正规 CA 签发的证书（如 Let's Encrypt）。

### 3. 私聊能用，群里不行

把机器人加进群后，默认它只能看到 `@机器人` 或回复它的消息（隐私模式）。如需让它接收群里所有消息，在 BotFather 里对该机器人关闭 `Group Privacy`。

### 4. 想换绑定的 Agent

直接在 Fancy Agent 的 webhook 编辑里改绑定 Agent 即可，URL 和 secret 不变，无需重新 `setWebhook`。

## 一句话记忆版

**BotFather 拿 token → Fancy Agent 建 Telegram webhook 拿 URL 和 secret → 用 `setWebhook` 把两者注册给 Telegram。**
