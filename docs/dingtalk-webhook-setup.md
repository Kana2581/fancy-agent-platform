# 钉钉 Bot Webhook 配置指南

这份文档用于说明如何把钉钉机器人接到 Fancy Agent 的入站 Webhook。

> 验证状态：该链路已在真实环境中完成联调，当前文档对应的是已明确跑通的接入方式。

## 先说结论

钉钉接入最容易卡住的点，不是公网地址，也不是 webhook 路径，而是：

**很多人一开始不知道 `AppSecret` 在哪里拿。**

实际顺序应该是：

1. 先在钉钉开放平台创建一个机器人应用
2. 在机器人配置里先随便填一个可保存的回调地址
3. 保存后进入「凭证与基础信息」，拿到 `AppSecret`
4. 回到 Fancy Agent，新建 `DingTalk Bot` 类型的 webhook，并填入这个 `AppSecret`
5. 拿到 Fancy Agent 生成的正式 webhook URL
6. 再回到钉钉后台，把机器人回调地址改成这个正式 URL

如果顺序反了，通常就会遇到 401，原因是 Fancy Agent 用错误的 secret 做签名校验。

## 前置条件

开始前请确认：

- Fancy Agent 后端已经部署完成
- 你的服务有公网可访问地址
- 钉钉可以访问这个地址
- 服务器时间准确，不能漂移太多

钉钉签名校验依赖时间戳，如果部署机时间偏差太大，回调会返回 401。

## 完整操作步骤

### 1. 在钉钉开放平台创建机器人应用

进入钉钉开放平台，创建一个机器人应用，开启消息接收相关能力。

如果后台要求你先填写一个回调地址才能继续保存，可以先填一个占位地址，例如：

```text
http://your-host.example.com/placeholder
```

这里只是为了先把机器人应用建出来，方便拿到凭证信息。后面会改成 Fancy Agent 的正式地址。

### 2. 拿到 AppSecret

机器人应用创建完成后，进入：

`凭证与基础信息`

找到：

- `AppKey`
- `AppSecret`

其中 Fancy Agent 钉钉 webhook 真正需要的是：

**`AppSecret`**

注意不要填错成这些值：

- 机器人 token
- Client Secret
- 其他应用的 secret
- 旧机器人对应的 secret

## 3. 在 Fancy Agent 中创建钉钉 webhook

进入 Fancy Agent 的入站 Webhook 页面，新建一条 webhook。

推荐这样填写：

- `名称`：自定义，例如 `钉钉群助手`
- `类型`：`DingTalk Bot`
- `绑定 Agent`：选择希望被钉钉触发的 Agent
- `DingTalk AppSecret`：填刚才在钉钉开放平台复制的 `AppSecret`

创建成功后，Fancy Agent 会生成一个正式的 webhook URL，格式类似：

```text
http://your-domain/api/v1/dingtalk/webhooks/<slug>
```

这个 URL 才是最终要填回钉钉后台的地址。

### 4. 把正式 webhook URL 配回钉钉

回到钉钉开放平台，进入机器人应用的消息接收配置，把之前的占位地址改成 Fancy Agent 生成的正式地址。

例如：

```text
http://your-domain/api/v1/dingtalk/webhooks/<slug>
```

保存并发布版本。

如果钉钉会立即发起校验请求，Fancy Agent 会根据 `AppSecret` 校验签名。只要 secret 一致，校验就能通过。

### 5. 验证是否接通

把机器人加入群聊，在群里 `@机器人` 发一句话。

正常流程是：

1. 钉钉把消息回调给 Fancy Agent
2. Fancy Agent 用 `AppSecret` 校验签名
3. Fancy Agent 调用绑定的 Agent 执行
4. Fancy Agent 通过钉钉回调里的 `sessionWebhook` 把回复发回群里

## 常见问题

### 1. 返回 401 Unauthorized

这几乎总是签名校验失败。

最常见原因：

- Fancy Agent 里填的不是正确的 `AppSecret`
- 钉钉后台已经换过 secret，但 Fancy Agent 里还是旧值
- 复制时带了空格或换行
- 服务器时间不准

排查建议：

1. 重新去钉钉后台复制一次 `AppSecret`
2. 删除 Fancy Agent 中原来的钉钉 webhook
3. 重新创建一条新的钉钉 webhook
4. 把新生成的 URL 再填回钉钉后台

### 2. URL 能访问，但钉钉保存失败

说明公网联通不一定有问题，但钉钉校验没过。

优先检查：

- `AppSecret` 是否正确
- 服务端是否已部署到最新代码
- 服务器时间是否准确

### 3. 群里发消息没反应

常见原因：

- 没有 `@机器人`
- webhook 绑定到了错误的 Agent
- Agent 执行太久，`sessionWebhook` 已过期

### 4. “内部 Secret” 要不要填到钉钉后台

不用。

钉钉通道只需要：

- Fancy Agent 中保存 `AppSecret`
- 钉钉后台配置 Fancy Agent 生成的 webhook URL

Fancy Agent 创建完成后弹窗里显示的内部 secret，不需要配置到钉钉。

## 推荐操作顺序

为了避免反复 401，推荐固定使用下面这套顺序：

1. 在钉钉开放平台创建机器人
2. 先完成应用初始化，拿到 `AppSecret`
3. 在 Fancy Agent 创建 `DingTalk Bot` webhook，并填入 `AppSecret`
4. 拿到 Fancy Agent 正式 webhook URL
5. 回钉钉后台把消息接收地址改成正式 URL
6. 发布并在群里实际测试

## 一句话记忆版

**先拿到钉钉 `AppSecret`，再创建 Fancy Agent 钉钉 webhook，最后把 Fancy Agent 生成的 URL 配回钉钉。**
