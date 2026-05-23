const SESSION_STORAGE_KEY = "scnu_consult_session_id"

export function getStoredSessionId(): string | null {
  try {
    const value = uni.getStorageSync(SESSION_STORAGE_KEY)

    if (typeof value !== "string") {
      return null
    }

    const sessionId = value.trim()
    return sessionId ? sessionId : null
  } catch (error) {
    return null
  }
}

export function saveSessionId(sessionId: string): void {
  const value = sessionId.trim()

  if (!value) {
    return
  }

  try {
    uni.setStorageSync(SESSION_STORAGE_KEY, value)
  } catch (error) {
    // 第一阶段先静默处理，避免影响页面演示
  }
}

export function clearStoredSessionId(): void {
  try {
    uni.removeStorageSync(SESSION_STORAGE_KEY)
  } catch (error) {
    // 第一阶段先静默处理，避免影响页面演示
  }
}