"use client";

import { useContext, useEffect, useState } from "react";
import { SettingsContext } from "@/context/settings";
import { useSettingsStore } from "@/store/settings";

interface Props {
  children: React.ReactNode;
}

export const SettingsProvider: React.FC<Props> = ({ children }) => {
  const settings = useSettingsStore((state) => state);

  return (
    <SettingsContext.Provider value={settings}>
      {children}
    </SettingsContext.Provider>
  )
}