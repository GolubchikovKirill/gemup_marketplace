import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { IAppSettings } from "@/types/data";
import type { IStoreMethod } from "@/types/store";


type SettingsStoreType = IAppSettings & IStoreMethod<IAppSettings>;

export const useSettingsStore = create<SettingsStoreType>()(
  persist(
    (set) => ({
      language: "EN",
      isSidebarOpen: true,
      isMenuOpen: false,
      setValue: <K extends keyof Omit<IAppSettings, "setValue">>(
        key: K,
        value: IAppSettings[K]
      ) => {
        set((state) => ({
          ...state,
          [key]: value,
        }));
      }
    }),
    {
      name: "gemups-settings-storage",
    }
  )
);
