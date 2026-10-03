from langchain_core.prompts import ChatPromptTemplate


AGENT_SYSTEM_PROMPT = """
你是灵犀客服，一个专业、准确、友好的电商客服助手。

你的职责：
1. 理解用户的问题。
2. 基于已提供的信息回答问题。
3. 信息不足时，明确说明缺少什么信息。
4. 不要编造订单、物流、退款或售后信息。
5. 需要查询业务数据时，等待后续工具调用。
6. 回答要简洁、清晰、符合客服语气。
"""



def build_chat_prompt() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages(
        [
            ("system", AGENT_SYSTEM_PROMPT),
            ("human", "{message}"),
        ]
    )