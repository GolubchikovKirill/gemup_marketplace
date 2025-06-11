import { createContext } from "react";
import type { IAppSettings } from "@/types/data";


export const SettingsContext = createContext<IAppSettings>({
    language: "EN",
    isSidebarOpen: true
});