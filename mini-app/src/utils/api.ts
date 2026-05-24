import { TENANT_SLUG } from "./config";

const BASE_URL =
  process.env.NODE_ENV === "development"
    ? "http://localhost:8000/api/v1"
    : (import.meta.env.VITE_API_BASE_URL as string) || "/api/v1";

interface ApiResponse<T = any> {
  data: T | null;
  error: { code: string; message: string } | null;
}

function getToken(): string | null {
  try {
    return uni.getStorageSync("token") || null;
  } catch {
    return null;
  }
}

function getRefreshToken(): string | null {
  try {
    return uni.getStorageSync("refresh_token") || null;
  } catch {
    return null;
  }
}

function saveTokens(access: string, refresh: string): void {
  try {
    uni.setStorageSync("token", access);
    uni.setStorageSync("refresh_token", refresh);
  } catch {
    // storage full or unavailable
  }
}

function clearTokens(): void {
  try {
    uni.removeStorageSync("token");
    uni.removeStorageSync("refresh_token");
  } catch {
    // ignore
  }
}

function buildHeaders(): Record<string, string> {
  const headers: Record<string, string> = {
    "X-Tenant": TENANT_SLUG,
    "Content-Type": "application/json",
  };
  const token = getToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

let _refreshPromise: Promise<string | null> | null = null;

async function tryRefreshToken(): Promise<string | null> {
  if (_refreshPromise) return _refreshPromise;

  _refreshPromise = (async () => {
    const refreshToken = getRefreshToken();
    if (!refreshToken) return null;
    try {
      const body = await new Promise<ApiResponse<{ access_token: string }>>((resolve, reject) => {
        uni.request({
          url: `${BASE_URL}/auth/refresh`,
          method: "POST",
          data: { refresh_token: refreshToken },
          header: { "Content-Type": "application/json", "X-Tenant": TENANT_SLUG },
          success: (res: any) => resolve(res.data),
          fail: (err: any) => reject(err),
        });
      });
      if (body.data?.access_token) {
        uni.setStorageSync("token", body.data.access_token);
        return body.data.access_token;
      }
      return null;
    } catch {
      return null;
    } finally {
      _refreshPromise = null;
    }
  })();

  return _refreshPromise;
}

async function request<T = any>(
  method: "GET" | "POST" | "PUT" | "DELETE",
  path: string,
  data?: any,
  retry = true,
): Promise<ApiResponse<T>> {
  return new Promise((resolve, reject) => {
    uni.request({
      url: `${BASE_URL}${path}`,
      method,
      data,
      header: buildHeaders(),
      success: async (res: any) => {
        const body = res.data as ApiResponse<T>;
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(body);
        } else if (res.statusCode === 401 && retry) {
          const newToken = await tryRefreshToken();
          if (newToken) {
            resolve(request<T>(method, path, data, false));
          } else {
            clearTokens();
            reject(body.error || { code: "AUTH_EXPIRED", message: "登录已过期，请重新登录" });
          }
        } else {
          reject(body.error || { code: "HTTP_ERROR", message: `Status ${res.statusCode}` });
        }
      },
      fail: (err: any) => {
        reject({ code: "NETWORK_ERROR", message: err.errMsg || "网络请求失败" });
      },
    });
  });
}

export const api = {
  get: <T = any>(path: string) => request<T>("GET", path),
  post: <T = any>(path: string, data?: any) => request<T>("POST", path, data),
  put: <T = any>(path: string, data?: any) => request<T>("PUT", path, data),
  del: <T = any>(path: string) => request<T>("DELETE", path),
};

export const chatApi = {
  createSession: () => api.post<{ session_id: string; guest: boolean }>("/chat/session"),
  getSession: (id: string) => api.get(`/chat/session/${id}`),
  deleteSession: (id: string) => api.del(`/chat/session/${id}`),
};

export const authApi = {
  register: async (data: { username: string; password: string; region?: string; score?: number; subjects?: string }) => {
    const result = await api.post<{ access_token: string; refresh_token: string; user_id: string; username: string }>("/auth/register", data);
    if (result.data?.access_token && result.data?.refresh_token) {
      saveTokens(result.data.access_token, result.data.refresh_token);
    }
    return result;
  },
  login: async (data: { username: string; password: string }) => {
    const result = await api.post<{ access_token: string; refresh_token: string; user_id: string; username: string }>("/auth/login", data);
    if (result.data?.access_token && result.data?.refresh_token) {
      saveTokens(result.data.access_token, result.data.refresh_token);
    }
    return result;
  },
  refresh: () => api.post<{ access_token: string }>("/auth/refresh"),
  logout: () => { clearTokens(); },
};

export const recommendationsApi = {
  getAll: (params?: { page?: number; page_size?: number }) => {
    const qs = params ? `?${new URLSearchParams(params as any).toString()}` : "";
    return api.get(`/recommendations${qs}`);
  },
  submitFeedback: (data: { college_name: string; major_name: string; feedback_type: string }) =>
    api.post("/recommendations/feedback", data),
};

export const profileApi = {
  get: () => api.get("/profile"),
  submitFeedback: (data: { dimension: string; score: number }) =>
    api.post("/profile/feedback", data),
};

export const compareApi = {
  getRecommendations: (profileSnapshot?: string | null) => {
    const qs = profileSnapshot
      ? `?profile_snapshot=${encodeURIComponent(profileSnapshot)}`
      : "";
    return api.get<{
      recommendations: Array<{
        tenant_slug: string;
        tenant_name: string;
        majors: Array<{
          college_name: string;
          major_name: string;
          level: string;
          province: string;
          city: string;
          min_rank: number;
          min_score: number;
          subjects: string;
          source_url: string;
        }>;
        match_score: number;
      }>;
      profile_snapshot: Record<string, any>;
      tenants_compared: number;
    }>(`/compare/recommendations${qs}`);
  },
};

export const collegeApi = {
  list: () => api.get("/colleges"),
  get: (id: string) => api.get(`/colleges/${id}`),
};
