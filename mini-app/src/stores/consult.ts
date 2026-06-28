import { defineStore } from "pinia";
import { ref } from "vue";
import { api, getToken } from "@/utils/api";
import { TENANT_SLUG } from "@/utils/config";
import {
  getConsultSessionId,
  saveConsultSessionId,
  clearConsultSessionId,
} from "@/utils/consultSession";

const API_BASE =
  process.env.NODE_ENV === "development"
    ? "/api/v1"
    : (import.meta.env.VITE_API_BASE_URL as string) || "/api/v1";

export interface ConsultSource {
  title: string;
  url: string;
  text?: string;
}

export interface ConsultMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  kind?: "answer" | "validation_warning";
  regenerated?: boolean;
  validationPassed?: boolean;
  sources?: ConsultSource[];
}

// 默认开场白（结合知识库项目信息：KB001/003/005-007/008-012/017-019/021-023/030）
const DEFAULT_GREETING =
  "你好，我是华南师范大学国际商学院出国留学项目咨询助手。\n\n本系统仅提供国际留学项目相关咨询，涵盖以下内容：\n• 2+2 出国留学培训项目（商科/新媒体方向）\n• 3+1 SQA-AD 项目（市场营销/人力资源管理/商务会计）\n• 招生报名、入学考试、学费奖学金、学历认证\n• 合作院校、专业设置、升学就业\n\n你可以直接提问，我会基于学校官方信息为你解答。";

export const useConsultStore = defineStore("consult", () => {
  const sessionId = ref<string | null>(getConsultSessionId());
  const messages = ref<ConsultMessage[]>([]);
  const isLoading = ref(false);
  const validationWarning = ref<string | null>(null);
  const greeting = ref<string | null>(null);
  const assistantName = ref<string | null>(null);

  /** 初始化或恢复咨询会话 */
  async function enterSession(): Promise<boolean> {
    const token = getToken();
    if (!token) return false;

    // 每次进入重新读取存储，避免 logout 清存储后内存 ref 仍持有旧 session_id
    const storedId = getConsultSessionId();
    sessionId.value = storedId;

    try {
      const result = await api.post<{
        session_id: string;
        chat_history?: Array<{ message_id: string; role: string; content: string }>;
        greeting?: string | null;
        assistant_name?: string | null;
      }>("/miniapp/enter", {
        session_id: storedId || null,
        tenant_slug: TENANT_SLUG,
        module_type: "consult",
      });

      if (result.data?.session_id) {
        sessionId.value = result.data.session_id;
        saveConsultSessionId(result.data.session_id);
        if (result.data.greeting) greeting.value = result.data.greeting;
        if (result.data.assistant_name) assistantName.value = result.data.assistant_name;
        if (result.data.chat_history?.length) {
          messages.value = result.data.chat_history.map((m) => ({
            id: m.message_id,
            role: m.role as "user" | "assistant",
            content: m.content,
          }));
        } else {
          // 新会话：插入开场白（后端 greeting 优先，否则使用默认开场白）
          messages.value = [{
            id: `greeting_${Date.now()}`,
            role: "assistant",
            content: greeting.value || DEFAULT_GREETING,
            kind: "answer",
          }];
        }
        return true;
      }
      return false;
    } catch (e) {
      console.error("Consult enter failed:", e);
      return false;
    }
  }

  /** SSE 流式发送消息 */
  async function sendMessage(content: string): Promise<void> {
    if (!sessionId.value || !content.trim()) return;

    const userMsg: ConsultMessage = {
      id: `u_${Date.now()}`,
      role: "user",
      content,
    };
    messages.value.push(userMsg);

    const aiMsg: ConsultMessage = {
      id: `a_${Date.now()}`,
      role: "assistant",
      content: "",
      kind: "answer",
      sources: [],
    };
    messages.value.push(aiMsg);

    isLoading.value = true;
    validationWarning.value = null;

    try {
      const resp = await fetch(`${API_BASE}/consult/messages`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${getToken()}`,
          "X-Tenant": TENANT_SLUG,
        },
        body: JSON.stringify({
          session_id: sessionId.value,
          tenant_slug: TENANT_SLUG,
          message: content,
        }),
      });

      if (!resp.ok || !resp.body) {
        throw new Error(`HTTP ${resp.status}`);
      }

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        // 后端 SSE 格式：data: {...}\n\n（无 event: 行，type 嵌在 JSON）
        const events = buffer.split("\n\n");
        buffer = events.pop() || "";

        for (const evt of events) {
          const line = evt.trim();
          if (!line.startsWith("data: ")) continue;
          const dataStr = line.slice(6);
          try {
            const data = JSON.parse(dataStr);
            handleSSEEvent(data.type, data, aiMsg);
          } catch (e) {
            console.warn("SSE parse failed:", e, dataStr);
          }
        }
      }
    } catch (e: any) {
      aiMsg.content = "抱歉，AI 服务暂时不可用，请稍后重试。";
      console.error("Consult SSE failed:", e);
    } finally {
      isLoading.value = false;
    }
  }

  function handleSSEEvent(type: string, data: any, aiMsg: ConsultMessage) {
    switch (type) {
      case "thinking":
        // UI 可显示"正在理解你的问题..."
        break;
      case "intent":
        // 意图抽取结果（可选展示）
        break;
      case "admission_data":
        // SQL 检索结果计数
        break;
      case "search_start":
        // RAG 检索中
        break;
      case "source":
        if (aiMsg.sources && data.item) {
          aiMsg.sources.push({
            title: data.item.source_title || "",
            url: data.item.source_url || "",
            text: data.item.text || "",
          });
        }
        break;
      case "search_end":
        break;
      case "token":
        // 增量累积 token（后端字段是 text）
        aiMsg.content += data.text || "";
        break;
      case "validation":
        if (!data.passed) {
          aiMsg.kind = "validation_warning";
          aiMsg.validationPassed = false;
          const issueCount = data.issues_count || 0;
          validationWarning.value =
            issueCount > 0
              ? `本次回答中有 ${issueCount} 项数据未通过校验，正在重新生成...`
              : "本次回答中的部分数据未经系统校验通过，请核对官方来源";
        } else {
          aiMsg.validationPassed = true;
          if (data.regenerated) {
            aiMsg.regenerated = true;
            validationWarning.value = null;
          }
        }
        break;
      case "regeneration":
        // 清空当前 content 准备接收重生成
        aiMsg.content = "";
        break;
      case "done":
        if (data.assistant_message?.message_id) {
          aiMsg.id = data.assistant_message.message_id;
        }
        if (data.validation_passed === false) {
          aiMsg.kind = "validation_warning";
          aiMsg.validationPassed = false;
          validationWarning.value =
            "本次回答仍存在数据校验未通过项，请参考官方招生章程核对";
        }
        break;
      case "error":
        aiMsg.content = data.message || "AI 服务暂时不可用";
        break;
    }
  }

  function clearSession() {
    clearConsultSessionId();
    sessionId.value = null;
    messages.value = [];
    validationWarning.value = null;
    greeting.value = null;
    assistantName.value = null;
  }

  return {
    sessionId,
    messages,
    isLoading,
    validationWarning,
    greeting,
    assistantName,
    enterSession,
    sendMessage,
    clearSession,
  };
});
