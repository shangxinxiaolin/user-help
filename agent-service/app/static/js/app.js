document.addEventListener("DOMContentLoaded", () => {
  // Global State
  let currentUserId = "u1";
  let activeConversationId = null;
  let isStreaming = false;

  // DOM Elements
  const userInput = document.getElementById("current-user-input");
  const navItems = document.querySelectorAll(".nav-item");
  const tabPanes = document.querySelectorAll(".tab-pane");

  const btnNewChat = document.getElementById("btn-new-chat");
  const btnClearChat = document.getElementById("btn-clear-chat");
  const convListContainer = document.getElementById("conversation-list");
  const messagesContainer = document.getElementById("messages-container");
  const chatInput = document.getElementById("chat-input");
  const btnSend = document.getElementById("btn-send");
  const activeChatTitle = document.getElementById("active-chat-title");
  const activeIntentTag = document.getElementById("active-intent-tag");
  const quickChips = document.querySelectorAll(".quick-chip");

  const kbChunksList = document.getElementById("kb-chunks-list");
  const kbSearchInput = document.getElementById("kb-search-input");
  const btnSearchKb = document.getElementById("btn-search-kb");
  const modalAddChunk = document.getElementById("modal-add-chunk");
  const btnOpenAddChunk = document.getElementById("btn-open-add-chunk");
  const formAddChunk = document.getElementById("form-add-chunk");

  const reviewTableBody = document.getElementById("review-table-body");
  const reviewCountBadge = document.getElementById("review-count-badge");

  const btnRefreshMetrics = document.getElementById("btn-refresh-metrics");

  // Tab Navigation
  navItems.forEach(item => {
    item.addEventListener("click", () => {
      navItems.forEach(i => i.classList.remove("active"));
      tabPanes.forEach(p => p.classList.remove("active"));

      item.classList.add("active");
      const tabId = item.getAttribute("data-tab");
      document.getElementById(tabId).classList.add("active");

      if (tabId === "tab-kb") loadKnowledgeChunks();
      if (tabId === "tab-review") loadReviewQueue();
      if (tabId === "tab-observability") loadObservability();
    });
  });

  // User ID Change
  userInput.addEventListener("change", () => {
    const val = userInput.value.trim();
    if (val) {
      currentUserId = val;
      loadConversations();
    }
  });

  // Quick Chips
  quickChips.forEach(chip => {
    chip.addEventListener("click", () => {
      chatInput.value = chip.getAttribute("data-text");
      chatInput.focus();
    });
  });

  // New Chat
  btnNewChat.addEventListener("click", () => {
    activeConversationId = null;
    activeChatTitle.textContent = "会话 #新会话";
    activeIntentTag.style.display = "none";
    messagesContainer.innerHTML = `
      <div class="message assistant">
        <div class="avatar">🤖</div>
        <div class="bubble">
          <div class="content">新会话已开启，有什么可以帮您？</div>
        </div>
      </div>
    `;
    document.querySelectorAll(".conv-item").forEach(i => i.classList.remove("active"));
  });

  btnClearChat.addEventListener("click", () => {
    messagesContainer.innerHTML = "";
  });

  // Send Message
  btnSend.addEventListener("click", sendMessage);
  chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  async function sendMessage() {
    const text = chatInput.value.trim();
    if (!text || isStreaming) return;

    chatInput.value = "";
    appendUserMessage(text);

    isStreaming = true;
    btnSend.disabled = true;

    // Create assistant bubble placeholder
    const assistantMsgObj = appendAssistantMessage("");
    const contentElem = assistantMsgObj.querySelector(".content");

    try {
      const response = await fetch("/api/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: text,
          user_id: currentUserId,
          conversation_id: activeConversationId,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let fullAnswer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop(); // keep last incomplete chunk

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.slice(6));
              handleSseEvent(data, assistantMsgObj, contentElem, (ans) => {
                fullAnswer = ans;
              });
            } catch (e) {
              console.error("Parse error:", e);
            }
          }
        }
      }

      // Add feedback buttons
      if (fullAnswer && activeConversationId) {
        attachFeedbackButtons(assistantMsgObj, text);
      }

      loadConversations();
    } catch (err) {
      contentElem.innerHTML += `<br><span style="color:var(--danger);">[连接异常]: ${err.message}</span>`;
    } finally {
      isStreaming = false;
      btnSend.disabled = false;
      chatInput.focus();
    }
  }

  function handleSseEvent(data, msgObj, contentElem, onAnswer) {
    if (data.event === "start") {
      if (data.conversation_id) {
        activeConversationId = data.conversation_id;
        activeChatTitle.textContent = `会话 #${activeConversationId}`;
      }
    } else if (data.event === "token") {
      contentElem.textContent += data.delta;
      onAnswer(contentElem.textContent);
      scrollToBottom();
    } else if (data.event === "tool_start") {
      const pill = document.createElement("div");
      pill.className = "tool-pill";
      pill.innerHTML = `<span>⚡</span> <span>执行业务工具: <strong>${data.tool}</strong>...</span>`;
      msgObj.querySelector(".bubble").insertBefore(pill, contentElem);
      scrollToBottom();
    } else if (data.event === "action_required") {
      renderActionCard(msgObj, data.action);
    } else if (data.event === "done") {
      if (data.answer && !contentElem.textContent) {
        contentElem.textContent = data.answer;
        onAnswer(data.answer);
      }
      if (data.citations && data.citations.length > 0) {
        renderCitations(msgObj, data.citations);
      }
      scrollToBottom();
    } else if (data.event === "error") {
      contentElem.innerHTML += `<br><span style="color:var(--danger);">${data.message}</span>`;
    }
  }

  function renderActionCard(msgObj, action) {
    const card = document.createElement("div");
    card.className = "action-card";
    card.innerHTML = `
      <h4>⚠️ 需要您的确认授权</h4>
      <p>${action.message || "是否确认执行此操作？"}</p>
      <div class="action-card-buttons">
        <button class="btn-primary-sm btn-confirm">✅ 确认提交</button>
        <button class="btn-outline-sm btn-cancel">❌ 取消</button>
      </div>
    `;

    card.querySelector(".btn-confirm").addEventListener("click", async () => {
      card.querySelector(".action-card-buttons").innerHTML = "<em>正在提交中...</em>";
      await resumeAction(true);
    });

    card.querySelector(".btn-cancel").addEventListener("click", async () => {
      card.querySelector(".action-card-buttons").innerHTML = "<em>已取消操作</em>";
      await resumeAction(false);
    });

    msgObj.querySelector(".bubble").appendChild(card);
    scrollToBottom();
  }

  async function resumeAction(confirmed) {
    try {
      const res = await fetch("/api/actions/resume", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          conversation_id: activeConversationId,
          user_id: currentUserId,
          confirmed: confirmed,
          message: confirmed ? "我确认提交" : "我取消操作",
        }),
      });
      const data = await res.json();
      if (data.answer) {
        appendAssistantMessage(data.answer);
      }
      loadConversations();
    } catch (e) {
      appendAssistantMessage(`操作处理失败: ${e.message}`);
    }
  }

  function renderCitations(msgObj, citations) {
    const box = document.createElement("div");
    box.className = "citations-box";
    const titles = citations.map(c => `【${c.title}】`).join(" ");
    box.innerHTML = `<strong>📖 参考政策依据：</strong>${titles}`;
    msgObj.querySelector(".bubble").appendChild(box);
  }

  function attachFeedbackButtons(msgObj, question) {
    const meta = document.createElement("div");
    meta.className = "message-meta";
    meta.innerHTML = `
      <span>回答是否对您有帮助？</span>
      <button class="feedback-btn btn-thumb-up" title="有帮助">👍</button>
      <button class="feedback-btn btn-thumb-down" title="未解决/答非所问">👎</button>
    `;

    meta.querySelector(".btn-thumb-up").addEventListener("click", () => {
      sendFeedback(question, true);
      meta.innerHTML = `<span style="color:var(--success);">感谢您的正面评价！</span>`;
    });

    meta.querySelector(".btn-thumb-down").addEventListener("click", () => {
      sendFeedback(question, false);
      meta.innerHTML = `<span style="color:var(--warning);">已反馈，问题将自动汇入飞轮待审池！</span>`;
    });

    msgObj.querySelector(".bubble").appendChild(meta);
  }

  async function sendFeedback(question, helpful) {
    try {
      await fetch("/api/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          conversation_id: activeConversationId || 1,
          user_id: currentUserId,
          question: question,
          helpful: helpful,
        }),
      });
      loadReviewQueue();
    } catch (e) {
      console.error(e);
    }
  }

  function appendUserMessage(text) {
    const div = document.createElement("div");
    div.className = "message user";
    div.innerHTML = `
      <div class="avatar">👤</div>
      <div class="bubble"><div class="content">${escapeHtml(text)}</div></div>
    `;
    messagesContainer.appendChild(div);
    scrollToBottom();
  }

  function appendAssistantMessage(text) {
    const div = document.createElement("div");
    div.className = "message assistant";
    div.innerHTML = `
      <div class="avatar">🤖</div>
      <div class="bubble"><div class="content">${escapeHtml(text)}</div></div>
    `;
    messagesContainer.appendChild(div);
    scrollToBottom();
    return div;
  }

  function scrollToBottom() {
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  function escapeHtml(str) {
    if (!str) return "";
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  // Load Conversations List
  async function loadConversations() {
    try {
      const res = await fetch(`/api/conversations?user_id=${encodeURIComponent(currentUserId)}`);
      if (!res.ok) return;
      const convs = await res.json();
      convListContainer.innerHTML = "";
      convs.forEach(c => {
        const item = document.createElement("div");
        item.className = `conv-item ${c.id === activeConversationId ? 'active' : ''}`;
        item.innerHTML = `
          <strong>会话 #${c.id}</strong>
          <span class="conv-item-id">${c.summary || c.status}</span>
        `;
        item.addEventListener("click", () => loadConversationDetail(c.id));
        convListContainer.appendChild(item);
      });
    } catch (e) {
      console.error("Failed to load conversations:", e);
    }
  }

  async function loadConversationDetail(convId) {
    activeConversationId = convId;
    activeChatTitle.textContent = `会话 #${convId}`;
    loadConversations();
    try {
      const res = await fetch(`/api/conversations/${convId}?user_id=${encodeURIComponent(currentUserId)}`);
      if (!res.ok) return;
      const data = await res.json();
      messagesContainer.innerHTML = "";
      data.messages.forEach(m => {
        if (m.role === "user") {
          appendUserMessage(m.content);
        } else if (m.role === "assistant") {
          appendAssistantMessage(m.content);
        }
      });
      scrollToBottom();
    } catch (e) {
      console.error(e);
    }
  }

  // Knowledge Base Tab
  async function loadKnowledgeChunks(searchQuery = "") {
    try {
      let chunks = [];
      if (searchQuery.trim()) {
        const res = await fetch("/api/kb/search", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query: searchQuery.trim(), top_k: 10 }),
        });
        chunks = await res.json();
      } else {
        const res = await fetch("/api/kb/chunks");
        chunks = await res.json();
      }

      kbChunksList.innerHTML = "";
      chunks.forEach(c => {
        const card = document.createElement("div");
        card.className = "card";
        card.innerHTML = `
          <div class="card-header">
            <span class="card-title">${c.title}</span>
            <div>
              ${c.is_key_clause ? '<span class="card-badge" style="background:#fef3c7;color:#b45309;">核心条款</span>' : ''}
              <span class="card-badge">${c.category || '通用'}</span>
            </div>
          </div>
          <p class="card-content">${c.content}</p>
        `;
        kbChunksList.appendChild(card);
      });
    } catch (e) {
      console.error(e);
    }
  }

  btnSearchKb.addEventListener("click", () => {
    loadKnowledgeChunks(kbSearchInput.value);
  });

  // Modal Add Chunk
  btnOpenAddChunk.addEventListener("click", () => modalAddChunk.classList.add("active"));
  document.querySelectorAll(".modal-close").forEach(b => {
    b.addEventListener("click", () => modalAddChunk.classList.remove("active"));
  });

  formAddChunk.addEventListener("submit", async (e) => {
    e.preventDefault();
    const title = document.getElementById("chunk-title").value.trim();
    const category = document.getElementById("chunk-category").value;
    const isKey = document.getElementById("chunk-is-key").checked;
    const content = document.getElementById("chunk-content").value.trim();

    try {
      await fetch("/api/kb/chunks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: title,
          category: category,
          is_key_clause: isKey,
          content: content,
        }),
      });
      modalAddChunk.classList.remove("active");
      formAddChunk.reset();
      loadKnowledgeChunks();
    } catch (err) {
      alert("添加失败: " + err.message);
    }
  });

  // Review Queue Tab
  async function loadReviewQueue() {
    try {
      const res = await fetch("/api/review/queue");
      if (!res.ok) return;
      const items = await res.json();
      reviewCountBadge.textContent = items.filter(i => i.status === "pending").length;
      reviewTableBody.innerHTML = "";

      if (items.length === 0) {
        reviewTableBody.innerHTML = `<tr><td colspan="6" style="text-align:center;color:var(--text-muted);">暂无待审核问题</td></tr>`;
        return;
      }

      items.forEach(item => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td>${item.id}</td>
          <td><strong>${item.normalized_question}</strong></td>
          <td><span class="card-badge" style="background:#fee2e2;color:#b91c1c;">${item.occurrence_count} 次</span></td>
          <td>${item.ai_suggested_answer || '无建议答复'}</td>
          <td><span class="card-badge">${item.status}</span></td>
          <td>
            ${item.status === 'pending' ? `
              <button class="btn-success-sm btn-approve" data-id="${item.id}">通过入库</button>
              <button class="btn-danger-sm btn-reject" data-id="${item.id}">驳回</button>
            ` : '已处理'}
          </td>
        `;

        const btnApprove = tr.querySelector(".btn-approve");
        if (btnApprove) {
          btnApprove.addEventListener("click", () => updateReviewStatus(item.id, "approved", item.ai_suggested_answer));
        }
        const btnReject = tr.querySelector(".btn-reject");
        if (btnReject) {
          btnReject.addEventListener("click", () => updateReviewStatus(item.id, "rejected"));
        }

        reviewTableBody.appendChild(tr);
      });
    } catch (e) {
      console.error(e);
    }
  }

  async function updateReviewStatus(id, status, answer = null) {
    try {
      await fetch(`/api/review/queue/${id}/status`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          status: status,
          reviewed_answer: answer,
          reviewed_by: "admin",
        }),
      });
      loadReviewQueue();
    } catch (e) {
      alert("操作失败: " + e.message);
    }
  }

  // Observability Tab
  async function loadObservability() {
    try {
      const [rMetrics, rCosts] = await Promise.all([
        fetch("/api/observability/metrics"),
        fetch("/api/observability/costs"),
      ]);

      if (rMetrics.ok) {
        const m = await rMetrics.json();
        document.getElementById("metric-turns").textContent = m.total_turns;
        document.getElementById("metric-calls").textContent = m.total_calls;
        document.getElementById("metric-tokens").textContent = m.total_input_tokens + m.total_output_tokens;
        document.getElementById("metric-cost").textContent = `$${m.total_cost_usd.toFixed(4)}`;
        document.getElementById("metric-interrupt").textContent = `${(m.interrupt_rate * 100).toFixed(1)}%`;
      }

      if (rCosts.ok) {
        const costs = await rCosts.json();
        const tbody = document.getElementById("cost-table-body");
        tbody.innerHTML = "";
        if (costs.length === 0) {
          tbody.innerHTML = `<tr><td colspan="5" style="text-align:center;color:var(--text-muted);">暂无模型调用数据</td></tr>`;
          return;
        }
        costs.forEach(c => {
          const tr = document.createElement("tr");
          tr.innerHTML = `
            <td><strong>${c.intent}</strong></td>
            <td>${c.call_count}</td>
            <td>${c.input_tokens}</td>
            <td>${c.output_tokens}</td>
            <td style="color:var(--primary);font-weight:600;">$${c.total_cost_usd.toFixed(4)}</td>
          `;
          tbody.appendChild(tr);
        });
      }
    } catch (e) {
      console.error(e);
    }
  }

  btnRefreshMetrics.addEventListener("click", loadObservability);

  // Initialize
  loadConversations();
});
