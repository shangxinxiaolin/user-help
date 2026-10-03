-- Agent Service 的会话与消息表
-- 对应 app/db/models/conversation.py 和 message.py

CREATE DATABASE IF NOT EXISTS lingxi_agent
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE lingxi_agent;

-- 先创建会话表，因为消息表要引用它
CREATE TABLE conversations (
    id BIGINT NOT NULL AUTO_INCREMENT,
    user_id VARCHAR(64) NOT NULL,
    status ENUM('进行中', '已转人工', '已结束')
        NOT NULL DEFAULT '进行中',
    summary TEXT NULL,
    summary_upto_msg_id BIGINT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    KEY ix_conversations_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

CREATE TABLE messages (
    id BIGINT NOT NULL AUTO_INCREMENT,
    conversation_id BIGINT NOT NULL,
    role ENUM('user', 'assistant', 'tool') NOT NULL,
    content TEXT NULL,
    tool_calls JSON NULL,
    tool_call_id VARCHAR(64) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    KEY ix_messages_conversation_id (conversation_id),
    CONSTRAINT fk_messages_conversation
        FOREIGN KEY (conversation_id)
        REFERENCES conversations (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;