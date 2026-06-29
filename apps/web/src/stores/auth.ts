import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { User } from "@/lib/types";

type AuthState = {
  accessToken: string | null;
  refreshToken: string | null;
  user: User | null;
  setSession: (access: string, refresh: string, user: User | null) => void;
  setTokens: (access: string, refresh: string) => void;
  setUser: (user: User | null) => void;
  clear: () => void;
};

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      user: null,
      setSession: (accessToken, refreshToken, user) =>
        set({ accessToken, refreshToken, user }),
      setTokens: (accessToken, refreshToken) => set({ accessToken, refreshToken }),
      setUser: (user) => set({ user }),
      clear: () => set({ accessToken: null, refreshToken: null, user: null }),
    }),
    { name: "doc007-auth" },
  ),
);
