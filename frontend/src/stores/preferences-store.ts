import { create } from "zustand";
import { persist } from "zustand/middleware";

type ThemeMode = "light" | "dark" | "system";

interface PreferencesState {
  theme: ThemeMode;
  highContrast: boolean;
  reducedMotion: boolean;
  sidebarCollapsed: boolean;
  defaultModel: string | null;
  setTheme: (t: ThemeMode) => void;
  toggleHighContrast: () => void;
  toggleReducedMotion: () => void;
  toggleSidebar: () => void;
  setDefaultModel: (m: string | null) => void;
}

export const usePreferences = create<PreferencesState>()(
  persist(
    (set) => ({
      theme: "system",
      highContrast: false,
      reducedMotion: false,
      sidebarCollapsed: false,
      defaultModel: null,
      setTheme: (theme) => set({ theme }),
      toggleHighContrast: () => set((s) => ({ highContrast: !s.highContrast })),
      toggleReducedMotion: () => set((s) => ({ reducedMotion: !s.reducedMotion })),
      toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
      setDefaultModel: (defaultModel) => set({ defaultModel }),
    }),
    { name: "cb_prefs" },
  ),
);
