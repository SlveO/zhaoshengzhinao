import { TENANT_SLUG } from "./config";

const BASE_URL =
  process.env.NODE_ENV === "development"
    ? "http://localhost:8000/api/v1"
    : "/api/v1";

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

async function request<T = any>(
  method: "GET" | "POST" | "PUT" | "DELETE",
  path: string,
  data?: any
): Promise<ApiResponse<T>> {
  return new Promise((resolve, reject) => {
    uni.request({
      url: `${BASE_URL}${path}`,
      method,
      data,
      header: buildHeaders(),
      success: (res: any) => {
        const body = res.data as ApiResponse<T>;
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(body);
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
  register: (data: { username: string; password: string; region?: string; score?: number; subjects?: string }) =>
    api.post<{ access_token: string; refresh_token: string; user_id: string; username: string }>("/auth/register", data),
  login: (data: { username: string; password: string }) =>
    api.post<{ access_token: string; refresh_token: string; user_id: string; username: string }>("/auth/login", data),
  refresh: () => api.post<{ access_token: string }>("/auth/refresh"),
};

export const recommendationsApi = {
  getAll: (params?: { page?: number; page_size?: number }) => {
    const qs = params ? `?${new URLSearchParams(params as any).toString()}` : "";
    return api.get(`/recommendations${qs}`);
  },
  submitFeedback: (data: { recommendation_id: string; rating: number; comment?: string }) =>
    api.post("/recommendations/feedback", data),
};

export const profileApi = {
  get: () => api.get("/profiles"),
  submitFeedback: (data: { dimension: string; score: number }) =>
    api.post("/profiles/feedback", data),
};

export const compareApi = {
  getRecommendations: () =>
    api.get<{
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
    }>("/compare/recommendations"),
};

export const collegeApi = {
  list: () => api.get("/colleges"),
  get: (id: string) => api.get(`/colleges/${id}`),
};
