# Runtime 持久化任务交接

更新时间：2026-10-05

## 1. 接手目标与当前停止点

项目名：灵犀客服。架构为 Python Agent Service + Java Business Service。

> 状态更新（A 阶段基础接线已完成）：原停止点已修复——`app/main.py` 与 `app/api/agent.py` 已改为请求执行时读取 `app.state.graph`，生命周期测试 `tests/api/test_lifespan.py` 通过。A 阶段基础接线不再阻塞，下一步进入 B 阶段（只读业务链）。以下第 4、5 节已按现状改写为「已解决」与「后续任务」。

工作目录：`D:\mewhelp-user-help`；Python 服务目录：`D:\mewhelp-user-help\agent-service`。请使用此英文路径，Java protobuf 插件曾在中文路径下失败。

仓库：<https://github.com/shangxinxiaolin/user-help>。当前存在未提交修改和未跟踪文件，不要覆盖用户手写内容，不要未经授权提交、推送或创建 PR。

## 2. 必须遵守的协作规则

- 每次最多写入一个文件，包括代码、测试和文档。完成该文件后汇报检查结果，等待用户确认才能写下一个文件；不要通过多次工具调用在同一轮修改多个文件。
- 规则已写入 `docs/PYTHON_AGENT_SERVICE_SPEC.md` 的“16.1 开发协作规则”。
- 用户偏好亲自手写，要求分小步讲解；“生成代码”默认只展示代码，“写入/你来写/修复”才执行对应修改，“检查”先读取最新文件并给出反馈。
- 分阶段实施，验收后等待明确确认再推进。当前阶段交付回复按规格以“当前停在阶段闸门，等待你的确认”结束。
- 不在文档中加入“原项目”等来源措辞。不记录实际密钥或密码；不要读取或复制 `.env` 的秘密值到交接内容。
- 使用 `uv run` 调用项目解释器和 pytest；系统 Python 不一定安装项目依赖。

## 3. 已完成的代码

### 会话 Repository

`app/db/repositories/conversation.py` 新增：

```python
async def get_conversation_for_user(
    self, conversation_id: int, user_id: str,
) -> Conversation | None:
    # WHERE id = conversation_id AND user_id = user_id
    ...
```

本人会话返回 ORM 对象，他人或不存在的会话统一返回 `None`。仓储测试覆盖这三种情形。

### Graph 日志节点

`app/graph/nodes/logging.py` 定义 `make_log_node(repository=None)`：

- 无 Repository 时返回空状态更新。
- 有 Repository 时要求状态包含 `conversation_id`，否则抛 `ValueError`。
- 使用 `resolve_answer(state)` 提取回答，通过 `append_message(role="assistant")` 写库，返回 `{}`。

`app/graph/build.py` 接收 `model`、`repository`、`checkpointer`，流程为 `START → chat → log → END`，编译时传入 `checkpointer`。

### Runtime

`app/graph/runtime.py`：

- `ConversationNotFound`：会话不存在或不属于用户时统一抛出。
- `_ensure_conversation(repository, user_id, conversation_id)`：无 ID 时创建会话，有 ID 时按用户归属查询。
- `run_turn(..., repository=None)`：注入仓储时要求非空 `user_id`，取得 `ensured_id`，写入本轮用户消息，再执行 Graph。
- 有 `ensured_id` 时传入 `config={"configurable": {"thread_id": str(ensured_id)}}`。
- 无 ID 时不传 config；这条路径只适合当前无 Checkpointer 的过渡调用。
- Repository 仍可选，现有 API 尚未注入它，因此不能宣称 API 已做会话归属校验或消息落库。

### SQLite Checkpointer

`app/db/checkpointer.py`：

```python
@asynccontextmanager
async def open_checkpointer(
    db_path: str,
) -> AsyncGenerator[AsyncSqliteSaver, None]:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    async with AsyncSqliteSaver.from_conn_string(db_path) as saver:
        yield saver
```

已使用 `AsyncGenerator` 标注，避免当前 Pylance 对装饰器配合 `AsyncIterator` 的弃用提示。SQLite 连接必须覆盖 Graph 使用期间，退出上下文自动关闭。

`tests/db/test_checkpointer.py` 使用 `tmp_path`：第一轮调用后关闭连接，再打开同一个 SQLite 文件和重建 Graph，以同一 `thread_id="42"` 调用第二轮，断言恢复后四条消息的类型、内容和顺序。该测试已经通过。

## 4. 已解决：main.py 接线（原阻塞记录）

交接时读取到的 `app/main.py` 状态：

- lifespan 已定义并传给 `FastAPI(lifespan=lifespan)`。
- 注入 `model` 时跳过 Checkpointer；否则打开配置路径并赋值 `app.state.graph`。
- 创建应用时也设置了默认 `app.state.graph = build_graph(model)`。
- **第 37 行仍调用 `create_agent_router(graph)`，但局部 `graph` 已被删除，导致 `create_app()` 执行时 NameError。**
- **第 47 行 `/api/chat` 内也仍使用 `graph=graph`。**
- `app/api/agent.py` 仍是 `create_agent_router(graph: Any)`，内部闭包持有构造时的 Graph。即使恢复旧局部变量，它也不会跟随 lifespan 替换后的 `app.state.graph`。

目标：两个接口在请求执行时读取启动后的 `app.state.graph`，而不是捕获启动前的旧对象。

注意：lifespan 参数 `app` 与外层局部变量是不同作用域的名字，但正常启动时指向同一个应用实例，这本身不是错误。空白行也不会改变 Python 缩进结构，真正需要修的是未定义变量及对象引用时机。

## 5. 后续任务（对齐新设计，每步都需用户确认）

A 阶段基础接线已完成，后续按 `docs/SPEC.md` 12.6 分阶段推进：

- **B 只读业务链**：Python 工具 → gRPC → Java 查询订单；生成 gRPC Stub，`query_order` 改调 Java `OrderService`。
- **C 可靠退款**：确认状态 + Java 持久化退款与幂等。
- **D 政策依据与评测**：小范围政策 RAG、引用与低置信度处理。
- **E 统一产品入口**：经确认后增加 Java 鉴权与 Agent HTTP/SSE 转发。

各模块设计与选型理由见 `docs/design/`（01–10 篇）。要点：

- 上下文管理采用三层分层（原文/截短/摘要），摘要按用量触发（见设计 06）。
- 数据飞轮三入口（证据弱 / useful=false / 用户反馈）汇入低置信度问题池（见设计 08）。
- 主题分类器用于飞轮统计、排补知识优先级（见设计 09）。

已知缺口（A 阶段遗留）：`app/graph/nodes/chat.py` 目前只取最后一个 HumanMessage 构建 Prompt，未将全部历史传给模型，属于上下文管理模块（设计 06）落地内容。

## 6. 环境与存储约定

- Python 3.12.14，FastAPI、LangGraph、SQLAlchemy asyncio。
- `conversation_id: int`，`user_id: str`；Checkpointer 使用 `thread_id=str(conversation_id)`。
- MySQL Docker 映射 `127.0.0.1:3307` → 容器 `3306`；业务库 `lingxi_agent`，隔离验证库 `lingxi_agent_test`。
- `app/db/base.py` 提供 Engine 与 async_sessionmaker。导入时创建 Engine 不等于立即连接数据库。
- `app/core/config.py`：`checkpointer_db_path="data/checkpoints.sqlite"`，可由 `.env` 中 `CHECKPOINTER_DB_PATH` 覆盖。
- 此路径相对于启动工作目录，通常从 `agent-service` 启动。
- MySQL 存产品会话/消息；SQLite 存 LangGraph 状态，两者不是同一事务。
- 用户消息当前在调用 Graph 前独立 commit，模型失败时用户消息仍会保留。
- 请求中的 user_id 目前是开发契约，不是已经认证的身份；不要把归属查询当成身份认证。
- `.gitignore` 忽略 `.env`、SQLite 文件等运行产物。

## 7. 验证记录及可用命令

此前全量测试曾达到 `40 passed`（在 main.py 此次未完成编辑之前）。之后：

- thread_id 调整后 `tests/graph/test_runtime.py`：`6 passed`。
- `tests/db/test_checkpointer.py`：`1 passed`（关闭再打开后恢复）。
- **main.py 当前编辑后没有全量通过记录；当前代码不能正常导入，不能声称全量仍通过。**

从 `D:\mewhelp-user-help\agent-service` 执行：

```powershell
uv run pytest tests/graph/test_runtime.py
uv run pytest tests/db/test_checkpointer.py
uv run pytest tests/api/test_chat.py tests/api/test_agent.py
uv run pytest
git diff --check
```

按改动范围选择测试，先修应用导入，再跑 API 和全量。

## 8. 交接时工作区文件

已修改且未提交：

- `app/db/repositories/conversation.py`
- `app/graph/build.py`
- `app/graph/runtime.py`
- `app/main.py`
- `docs/PYTHON_AGENT_SERVICE_SPEC.md`
- `tests/db/test_conversation_repository.py`
- `tests/graph/test_build.py`
- `tests/graph/test_runtime.py`

新增且尚未跟踪：

- `app/db/checkpointer.py`
- `app/graph/nodes/logging.py`
- `tests/db/test_checkpointer.py`
- `tests/graph/test_logging.py`
- 本交接文档。

接手时先重新读取最新代码与 git status，用户可能继续手写。当前最优先的是 main.py 的接线错误，不是重新实现已经通过的仓储或 Checkpointer。
