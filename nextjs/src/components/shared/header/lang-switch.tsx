"use client"

import { useState } from "react";
import { v4 as uuidv4 } from "uuid";
import { LanguageType } from "@/types/data";
import { useSettingsStore } from "@/store/settings";

interface ILangItem {
  isActive: boolean;
  label: string;
  language: LanguageType;
}

export default function LangSwitch() {
  const { language, setValue } = useSettingsStore();

  const [isOpen, setIsOpen] = useState<boolean>(false);
  const [langItemList, setLangItemList] = useState<ILangItem[]>([
    { isActive: true, label: "EN", language: "EN" },
    { isActive: false, label: "RU", language: "RU" },
    { isActive: false, label: "KZ", language: "KZ" },
    { isActive: false, label: "FR", language: "FR" },
  ])

  const handleItemClick = (language: LanguageType) => {
    setValue("language", language);
    setLangItemList(
      langItemList.map((item) => ({
        ...item,
        isActive: item.language === language
      }))
    )
  }

  return (
    <div className="lang__switch">
      <div className="currect__lang" onClick={() => setIsOpen(!isOpen)}>
        <span>{language}</span>
        <i className="ico-arrow"></i>
      </div>
      <div className="lang__list">
        <ul className={isOpen ? "active" : ""}>
          {langItemList.map(({ isActive, label, language }) => (
            <li
              key={uuidv4()}
              className={`lang__item ${isActive ? "active" : ""}`}
              onClick={() => handleItemClick(language)}
            >
              {label}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
