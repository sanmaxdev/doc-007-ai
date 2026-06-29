import { create } from "zustand";
import { persist } from "zustand/middleware";

type WorkspaceState = {
  activeId: string | null;
  setActive: (id: string | null) => void;
};

export const useWorkspaceStore = create<WorkspaceState>()(
  persist(
    (set) => ({
      activeId: null,
      setActive: (activeId) => set({ activeId }),
    }),
    { name: "doc007-workspace" },
  ),
);
