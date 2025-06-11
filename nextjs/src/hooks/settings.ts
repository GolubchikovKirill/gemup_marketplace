import { useContext } from "react";
import { SettingsContext } from "@/context/settings";

export const useSettings = () => {
    const ctx = useContext(SettingsContext);
    if (!ctx) {
        throw new Error("Settings Context error");
    }
    return ctx;
};