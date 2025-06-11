"use client";

import { useContext, useEffect, useState } from "react";
import { AuthContext } from "@/context/auth";
import { useAuthStore } from "@/store/auth";

interface Props {
  children: React.ReactNode;
}

export const AuthProvider: React.FC<Props> = ({ children }) => {
  const isAuth = useAuthStore((state) => state.isAuth);

  return (
    <AuthContext.Provider value={{ isAuth }}>
      {children}
    </AuthContext.Provider>
  );
};
