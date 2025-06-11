"use client";

import { useSettingsStore } from "@/store/settings";

export default function Burger() {
  const { isMenuOpen, setValue } = useSettingsStore((state) => state);

  return (
    <div
      style={{visibility: isMenuOpen ? "hidden" : "visible"}}
      className="burger__wrapper"
      onClick={() => setValue("isMenuOpen", true)}
    >
      <i className="ico-burger-mb"></i>
    </div>
  );
}
