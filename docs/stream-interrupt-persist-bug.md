# 前端打断流式生成时，部分 AI 消息未落库的 Bug 复盘

## 背景

前端新增了"停止生成"按钮：用户点击后通过 `AbortController.abort()` 中断 fetch，
希望服务端已经产出的 AI 文本能以完整一条消息的形式保存进数据库，下一轮对话可继续。

实现思路（`backend/app/services/chat_service.py`）：

1. 在 `agent.astream()` 流内按 `msg.id` 把 `AIMessageChunk` 累进 `chunk_buffer`
2. `updates["model"]` 到达 ⇒ 整条消息落地，把对应 id 的 buffer pop 掉（已完整）
3. 用 `try/finally` 包住整段流，`finally` 里把 buffer 里残留的 chunk 合并成一条
   `AIMessage`，塞进 `MessageProcessor`，再调 `_persist` 写库

逻辑看着对，但实测：**客户端 abort 后，这条中断的 AI 消息不会出现在数据库里。**

---

## 根因：`CancelledError` 会毒化 `finally` 里的 `await`

FastAPI `StreamingResponse` 对客户端断开的处理路径是：

1. `listen_for_disconnect` 协程探测到 TCP 连接关闭
2. **取消**整个流式响应 Task
3. `CancelledError` 向下传播到正在 `yield` 的业务 async generator
4. 触发 `finally` 块

关键陷阱：**一个任务被取消后，它后续发起的每一个 `await` 都会立刻再次抛
`CancelledError`**。这是 asyncio 的设计（保证取消语义不被忽略），不是 bug。

对应到我们的 `finally`：

```python
finally:
    if chunk_buffer:
        self._flush_interrupted_chunks(chunk_buffer, processor)  # 纯同步，OK
    await self._persist(processor)  # ← 这里开始有 await 就炸
```

`_persist` 的内部是：

```python
async with get_db_session() as db:            # __aenter__ 有 await  ← CancelledError
    mapper = ChatMessageMapper(db)
    await mapper._bulk_create_entities(...)    # 根本走不到
```

所以现象是："buffer 合并走到了、processor 里有消息了、日志打到了`_persist`入口了，
但 `INSERT` 一行都没发出去。"

---

## 修法：`asyncio.shield` 把持久化挡在取消链路外

```python
import asyncio

finally:
    if chunk_buffer:
        self._flush_interrupted_chunks(chunk_buffer, processor)
    await asyncio.shield(self._persist(processor))
```

`asyncio.shield(coro)` 的语义：

- 内部用一个独立 Task 跑 `coro`
- 外层 `await shield(...)` **本身仍会被取消**（抛 `CancelledError`）
- 但被 shield 包住的 inner Task **不会**被取消，会继续跑完

对我们来说完美匹配：
- 写库继续跑到 COMMIT，数据保住 ✔
- 外层 generator 本来就要结束，抛不抛 `CancelledError` 无所谓 ✔
- 不需要拿 `_persist` 的返回值（None），丢掉外层 await 结果没有副作用 ✔

---

## 相关知识点速记

### 1. `CancelledError` vs `GeneratorExit`

| 触发方式 | 抛出异常 | 能否 `await` |
| --- | --- | --- |
| `task.cancel()` | `asyncio.CancelledError`（继承自 `BaseException`，Python 3.8+） | 后续 `await` 立刻再抛 |
| `agen.aclose()` | `GeneratorExit`（继承自 `BaseException`） | 允许一次非 yield 的 `await`；若再 `yield` 会 `RuntimeError` |

FastAPI StreamingResponse 客户端断开走的是**前者**（task cancel），这是区分本 bug
和"async generator 关闭协议"的关键。

### 2. `asyncio.shield` 的正确理解

- **它不是让协程免疫取消**，而是让"被 shield 的协程在单独的 Task 里跑、不随外层取消"
- 外层 `await shield(inner)` 仍会被取消
- 要真的拿到 inner 结果，需要把 Task 保存下来并在别处 await：
  ```python
  t = asyncio.ensure_future(self._persist(processor))
  try:
      await asyncio.shield(t)
  except asyncio.CancelledError:
      await t   # 再取一次结果，不会再被取消
  ```
  本项目不需要结果，所以省略。

### 3. 何时该用 shield、何时不该

**该用：** 副作用已经准备好、不写出去会导致数据不一致
- 收尾写库、提交事务、释放锁、发最终通知
- 本 bug 属于此类

**不该用：** 业务主逻辑
- shield 整条请求处理 = 客户端取消但服务端还在烧 CPU，资源泄漏
- 取消本来就是为了及时回收资源，shield 滥用会让取消失效

### 4. async generator 的 `finally` 还有一个坑

规范上，async generator 的 `finally` 里**不能再 `yield`**，否则 `RuntimeError:
async generator ignored GeneratorExit`。我们这里 `finally` 只有 `await`（非 yield），
所以合法——但换到别的场景要小心。

### 5. LangChain 流式 chunk 合并的官方姿势

```python
from langchain_core.messages.utils import message_chunk_to_message
merged = message_chunk_to_message(sum(chunks[1:], chunks[0]))
```

`AIMessageChunk` 实现了 `__add__`，`sum([c1, c2, c3], c0)` 就是
`c0 + c1 + c2 + c3`，累计得到一个完整 chunk；再用 `message_chunk_to_message`
转成可持久化的 `AIMessage`。

**注意**：打断时 `tool_call_chunks` 里的 JSON args 大概率残缺（例如只有 `{"qu`），
合成的 `tool_calls` 会是无效的。这种消息留着会让下一轮 LLM 找不到对应
`ToolMessage` 而直接报错，所以我们在 flush 时显式剥离：

```python
merged.tool_calls = []
merged.tool_call_chunks = []
merged.invalid_tool_calls = []
```

### 6. FastAPI/Starlette 客户端断开的检测链路

```
TCP FIN
  → Starlette ServerErrorMiddleware / StreamingResponse
  → asyncio.Task.cancel()
  → await 点抛 CancelledError
  → 逐层 finally 执行
```

想在业务里显式感知断开，可以：
- `await request.is_disconnected()` 轮询
- 或者就依赖 `CancelledError`——本项目选这条

---

## 验证清单

- [ ] 触发较长的流式回复，中途点停止按钮
- [ ] 检查数据库 `chat_message` 表：应出现一条 `role=ai` 的中断消息，`content`
      是已输出的文本前缀
- [ ] 检查 `parent_id` 链：新消息挂在正确的 user message 下
- [ ] 接着在同一 session 继续对话：下一轮不应因"工具调用无对应 ToolMessage"而报错
- [ ] 正常结束的对话行为不回归（`finally` 里 shield 也会跑，但 `chunk_buffer`
      已被清空，`_flush_interrupted_chunks` 无副作用）

---

## 一句话总结

> Task 被取消后，它的新 `await` 都会立即再次抛 `CancelledError`。
> 凡是"客户端断开后还必须完成的副作用"，用 `asyncio.shield` 隔离。
