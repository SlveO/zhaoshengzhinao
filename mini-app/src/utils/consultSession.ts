/** 咨询模块 session_id 存取 — 独立 storage key 与推荐模块隔离 */

const CONSULT_SESSION_KEY = "scnu_consult_module_session_id";

export function getConsultSessionId(): string | null {
  try {
    const value = uni.getStorageSync(CONSULT_SESSION_KEY);
    if (typeof value !== "string") return null;
    const id = value.trim();
    return id.startsWith("sess_consult_") ? id : null;
  } catch {
    return null;
  }
}

export function saveConsultSessionId(sessionId: string): void {
  const value = sessionId.trim();
  if (!value || !value.startsWith("sess_consult_")) return;
  try {
    uni.setStorageSync(CONSULT_SESSION_KEY, value);
  } catch {
    // 静默忽略
  }
}

export function clearConsultSessionId(): void {
  try {
    uni.removeStorageSync(CONSULT_SESSION_KEY);
  } catch {
    // 静默忽略
  }
}
