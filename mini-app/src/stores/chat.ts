import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { wsManager, WsStatus } from "@/utils/websocket";
import { chatApi } from "@/utils/api";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "thinking" | "system";
  content: string;
  stage?: string;
  timestamp: number;
}

export interface ProfileSnapshot {
  riasec: Record<string, number>;
  values: string[];
  confidence: number;
  completeness: string;
}

export type ChatStage = "explore" | "focus" | "confirm" | "done";

export const useChatStore = defineStore("chat", () => {
  const sessionId = ref<string | null>(null);
  const isGuest = ref(true);
  const messages = ref<ChatMessage[]>([]);
  const currentStage = ref<ChatStage>("explore");
  const profile = ref<ProfileSnapshot | null>(null);
  const wsStatus = ref<WsStatus>("disconnected");
  const isThinking = ref(false);
  const summary = ref<string | null>(null);

  const conversationStarted = computed(() => messages.value.length > 0);

  let unsubStatus: (() => void) | null = null;
  let unsubMessage: (() => void) | null = null;
  let unsubThinking: (() => void) | null = null;
  let unsubProfileUpdate: (() => void) | null = null;
  let unsubStageChange: (() => void) | null = null;
  let unsubSummary: (() => void) | null = null;
  let unsubError: (() => void) | null = null;

  function initWs(sid: string): void {
    sessionId.value = sid;

    wsManager.onStatusChange((status: WsStatus) => {
      wsStatus.value = status;
    });

    unsubThinking = wsManager.on("thinking", () => {
      isThinking.value = true;
    });

    unsubMessage = wsManager.on("message", (data: any) => {
      isThinking.value = false;
      messages.value.push({
        id: `ai-${Date.now()}`,
        role: "assistant",
        content: data.content,
        stage: data.stage || currentStage.value,
        timestamp: Date.now(),
      });
    });

    unsubProfileUpdate = wsManager.on("profile_update", (data: any) => {
      if (data.riasec) {
        profile.value = {
          riasec: data.riasec,
          values: data.values || [],
          confidence: data.confidence || 0,
          completeness: data.completeness || "L1",
        };
      }
    });

    unsubStageChange = wsManager.on("stage_change", (data: any) => {
      if (data.to) {
        currentStage.value = data.to as ChatStage;
      }
    });

    unsubSummary = wsManager.on("summary", (data: any) => {
      summary.value = data.content;
      if (data.profile_snapshot) {
        profile.value = data.profile_snapshot;
      }
    });

    unsubError = wsManager.on("error", (data: any) => {
      uni.showToast({
        title: data.message || "出错了",
        icon: "none",
        duration: 3000,
      });
    });

    wsManager.connect(sid);
  }

  async function createSession(guest = true): Promise<string | null> {
    try {
      const res = await chatApi.createSession();
      if (res.data) {
        sessionId.value = res.data.session_id;
        isGuest.value = res.data.guest;
        initWs(res.data.session_id);
        return res.data.session_id;
      }
    } catch (e: any) {
      uni.showToast({ title: e?.message || "创建会话失败", icon: "none" });
    }
    return null;
  }

  function sendMessage(content: string): void {
    if (!content.trim()) return;

    messages.value.push({
      id: `user-${Date.now()}`,
      role: "user",
      content,
      timestamp: Date.now(),
    });

    wsManager.send(content);
  }

  function disconnect(): void {
    wsManager.disconnect();
    if (unsubStatus) { unsubStatus(); unsubStatus = null; }
    if (unsubMessage) { unsubMessage(); unsubMessage = null; }
    if (unsubThinking) { unsubThinking(); unsubThinking = null; }
    if (unsubProfileUpdate) { unsubProfileUpdate(); unsubProfileUpdate = null; }
    if (unsubStageChange) { unsubStageChange(); unsubStageChange = null; }
    if (unsubSummary) { unsubSummary(); unsubSummary = null; }
    if (unsubError) { unsubError(); unsubError = null; }
  }

  function reset(): void {
    disconnect();
    sessionId.value = null;
    isGuest.value = true;
    messages.value = [];
    currentStage.value = "explore";
    profile.value = null;
    isThinking.value = false;
    summary.value = null;
  }

  return {
    sessionId,
    isGuest,
    messages,
    currentStage,
    profile,
    wsStatus,
    isThinking,
    summary,
    conversationStarted,
    createSession,
    sendMessage,
    disconnect,
    reset,
    initWs,
  };
});
