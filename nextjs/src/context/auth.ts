import { createContext } from "react";

interface IAuthContext {
    isAuth: boolean
}

export const AuthContext = createContext<IAuthContext | undefined>(undefined);