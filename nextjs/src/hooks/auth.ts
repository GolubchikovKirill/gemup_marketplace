import { useContext } from "react";
import { AuthContext } from "@/context/auth";

export const useAuth = () => {
    const ctx = useContext(AuthContext);
    if (!ctx) {
        throw new Error("Auth Context error");
    }
    return ctx;
};