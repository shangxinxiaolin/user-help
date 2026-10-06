# Runtime 持久化任务交接

更新时间：2026-10-06

## 1. 接手目标与当前停止点

项目名：灵犀客服。架构为 Python Agent Service + Java Business Service。

> 当前状态（静态代码核对）：Graph 的 checkpoint 封装、会话归属查询逻辑和日志节点已经存在并有针对性测试；但 repository 尚未从 HTTP 入口注入，A 阶段的 HTTP 端到端验收尚未完成。`app/main.py` 和 `app/api/agent.py` 仍需接通 repository，并补充 API 层验收。

工作目录：`D:\mewhelp-user-help`；Python 服务目录：`D:\mewhelp-user-help\agent-service`。请使用此英文路径，Java protobuf 插件曾在中文路径下失败。

仓库：<https://github.com/shangxinxiaolin/user-help>。接手任何新任务前先读取最新 `git status`、目标文件和 diff；不要覆盖用户手写内容，不要未经授权提交、推送或创建 PR。

## 2. 必须遵守的协作规则

- 默认每次只写一个文件并等待确认；用户明确授权批量修改时，在授权范围内批量处理后统一验收。文档修复授权不等于代码修改授权。
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

## 4. 尚未完成：HTTP 入口接线

当前代码核对结果：

- lifespan 已定义并传给 `FastAPI(lifespan=lifespan)`。
- 生产路径会在 lifespan 中创建带 SQLite checkpointer 的 Graph；应用创建时还会创建一个无 checkpointer 的默认 Graph，现有 Fake 模型测试依赖这一行为。
- `/api/chat` 和 `/api/agent` 当前调用 `run_turn` 时都没有传入 `ConversationRepository`。
- 因此 `run_turn` 中的会话归属校验和用户消息落库不会在真实 HTTP 请求中执行；Graph 日志节点也没有 repository，因而不会写入 assistant 消息。
- `app/api/agent.py` 的路由仍接收构造时传入的 `graph` 参数，但闭包实际读取 `raw_request.app.state.graph`；旧 Graph 引用问题已经规避，但 repository 接线仍未完成。

目标：保留请求执行时读取启动后 `app.state.graph` 的行为，并通过 FastAPI Depends 把同一 repository 接入路由、`run_turn` 和 Graph 日志节点。

注意：lifespan 参数 `app` 与外层局部变量是不同作用域的名字，但正常启动时指向同一个应用实例，这本身不是错误。接线时还要保留测试替换 repository 和 Graph 的能力，不能让 API 测试依赖真实 MySQL。

## 5. 后续任务（对齐新设计，每步都需用户确认）

A 阶段目前只完成了基础代码骨架和部分单元测试。先完成 A 阶段 HTTP 接线与验收，再按 `docs/SPEC.md` 12.6 推进：

- **A 收尾**：通过 FastAPI Depends 接通 repository；验证所属会话可续聊、他人会话被拒、用户和 assistant 消息落库，以及应用重启后的 checkpoint 恢复。
- **B 只读业务链**：Python 工具 → gRPC → Java 查询订单；生成 gRPC Stub，`query_order` 改调 Java `OrderService`。
- **C 可靠退款**：确认状态 + Java 持久化退款与幂等。
- **D 政策依据与评测**：小范围政策 RAG、引用与低置信度处理。
- **E 统一产品入口（目标已定、待实现）**：同一 Spring Boot 内新增 entry Gateway/BFF，与业务模块分层；Java → Python 内部 HTTP/SSE，Python → Java Business gRPC。客户端身份由 Java 验证，Python 验证内部上下文，不复制会话或 Graph 状态。具体实施以总规格 12.5 为准。

各模块设计与选型理由见 `docs/design/`（01–10 篇）。要点：

- 上下文管理采用三层分层（原文/截短/摘要），摘要按用量触发（见设计 06）。
- 数据飞轮三入口（证据弱 / useful=false / 用户反馈）汇入低置信度问题池（见设计 08）。
- 主题归类初版使用 LLM 打标，微调后置；设计 09 仅为可选方案。

已知缺口（A 阶段遗留）：`app/graph/nodes/chat.py` 目前只取最后一个 HumanMessage 构建 Prompt，未将全部历史传给模型，属于上下文管理模块（设计 06）落地内容。

## 6. 环境与存储约定

- Python 3.12.14，FastAPI、LangGraph、SQLAlchemy asyncio。
- `conversation_id: int`，`user_id: str`；Checkpointer 使用 `thread_id=str(conversation_id)`。
- MySQL Docker 映射 `127.0.0.1:3307` → 容器 `3306`；业务库 `lingxi_agent`，隔离验证库 `lingxi_agent_test`。
- `app/db/base.py` 提供 Engine 与 async_sessionmaker。导入时创建 Engine 不等于立即连接数据库。
- `app/core/config.py`：`checkpointer_db_path="data/checkpoints.sqlite"`，可由 `.env` 中 `CHECKPOINTER_DB_PATH` 覆盖。
- 此路径相对于启动工作目录，通常从 `agent-service` 启动。
- MySQL 存产品会话/消息；SQLite 存 LangGraph 状态，两者不是同一事务。
- 直接调用 runtime 并传入 repository 时，用户消息在 Graph 前独立 commit；当前 HTTP 未注入 repository，不会触发此写库行为。
- 请求中的 user_id 目前是开发契约，不是已经认证的身份；不要把归属查询当成身份认证。
- `.gitignore` 忽略 `.env`、SQLite 文件等运行产物。

## 7. 验证记录及可用命令

历史记录中曾执行过以下局部测试；本轮静态核对没有重新运行全量测试：

- thread_id 调整后 `tests/graph/test_runtime.py`：`6 passed`。
- `tests/db/test_checkpointer.py`：`1 passed`（关闭再打开后恢复）。
- **不能据此声称当前全量测试通过。** API 入口尚未接通 repository，相关端到端验收仍待补充。

从 `D:\mewhelp-user-help\agent-service` 执行：

```powershell
uv run pytest tests/graph/test_runtime.py
uv run pytest tests/db/test_checkpointer.py
uv run pytest tests/api/test_chat.py tests/api/test_agent.py
uv run pytest
git diff --check
```

按改动范围选择测试；完成 repository 接线后先跑 API 针对性测试，再跑全量。

## 8. 历史改动记录

以下文件曾在该轮开发中修改，不能据此判断当前工作区状态：

- `app/db/repositories/conversation.py`
- `app/graph/build.py`
- `app/graph/runtime.py`
- `app/main.py`
- `docs/PYTHON_AGENT_SERVICE_SPEC.md`
- `tests/db/test_conversation_repository.py`
- `tests/graph/test_build.py`
- `tests/graph/test_runtime.py`

以下文件曾在该轮开发中新增，当前是否已提交以最新 `git status` 为准：

- `app/db/checkpointer.py`
- `app/graph/nodes/logging.py`
- `tests/db/test_checkpointer.py`
- `tests/graph/test_logging.py`
- 本交接文档。

接手时先重新读取最新代码与 `git status`，用户可能继续手写。当前最优先的是完成 repository 的 HTTP 接线和 API 端到端验收，不是重新实现已经存在的仓储或 Checkpointer。
