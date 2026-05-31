import { create } from 'zustand'

interface MobileState {
  isMobile: boolean
  isTablet: boolean
  sidebarOpen: boolean
  setSize: (w: number) => void
  openSidebar: () => void
  closeSidebar: () => void
  toggleSidebar: () => void
}

export const useMobileStore = create<MobileState>((set) => ({
  isMobile: typeof window !== 'undefined' ? window.innerWidth <= 768 : false,
  isTablet: typeof window !== 'undefined' ? window.innerWidth <= 1024 : false,
  sidebarOpen: false,

  setSize: (w: number) =>
    set({ isMobile: w <= 768, isTablet: w <= 1024 }),

  openSidebar: () => set({ sidebarOpen: true }),
  closeSidebar: () => set({ sidebarOpen: false }),
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
}))
