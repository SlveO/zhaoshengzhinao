/// <reference types="@dcloudio/types" />

declare module "*.vue" {
  import { DefineComponent } from "vue";
  const component: DefineComponent<{}, {}, any>;
  export default component;
}

declare module "@/tenant.config" {
  const config: {
    appId: string;
    tenantSlug: string;
    brand: {
      name: string;
      shortName: string;
      primaryColor: string;
      secondaryColor: string;
      welcomeText: string;
    };
    features: {
      guestMode: boolean;
      crossCollegeCompare: boolean;
    };
  };
  export default config;
}

interface Uni {
  request(options: UniRequestOptions): Promise<[any, any]>;
  showToast(options: { title: string; icon?: string; duration?: number }): void;
  showLoading(options: { title: string }): void;
  hideLoading(): void;
  showModal(options: { title: string; content: string }): Promise<{ confirm: boolean }>;
  setStorageSync(key: string, data: any): void;
  getStorageSync(key: string): any;
  removeStorageSync(key: string): void;
  connectSocket(options: { url: string; header?: Record<string, string> }): SocketTask;
}

interface UniRequestOptions {
  url: string;
  method?: "GET" | "POST" | "PUT" | "DELETE";
  data?: any;
  header?: Record<string, string>;
}

interface SocketTask {
  onOpen(cb: () => void): void;
  onMessage(cb: (res: { data: string }) => void): void;
  onError(cb: (err: any) => void): void;
  onClose(cb: (res: { code: number; reason: string }) => void): void;
  send(opts: { data: string }): void;
  close(opts?: { code?: number; reason?: string }): void;
}

declare const uni: Uni & { $brand: { name: string; shortName: string; primaryColor: string; secondaryColor: string; welcomeText: string } };
