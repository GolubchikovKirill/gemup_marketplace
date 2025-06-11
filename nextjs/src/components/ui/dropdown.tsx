"use client";

import { useEffect, useState } from "react";
import { v4 as uuidv4 } from "uuid";
import type { IDropdown } from "@/types/component";

type Props = IDropdown & React.HTMLAttributes<HTMLDivElement>

export const Dropdown: React.FC<Props> = ({
  className = "",
  caption = undefined,
  icon = "/img/icons/dropdown-arrow.svg",
  enableIcon = false,
  disabled = false,
  closeOnSelect = true,
  list = [],
  setList,
  onSelect = undefined,
  ...props
}) => {
  const [isOpen, setIsOpen] = useState<boolean>(false);
  const [current, setCurrent] = useState<string>("");

  useEffect(() => {
    const item = list.find((item) => item.isActive);
    item && setCurrent(item.label);
    if (!item && caption) {
      setCurrent(caption);
    }
  }, [list]);

  const handleSelect = (e: React.MouseEvent<HTMLLIElement>, id: string | number) => {
    setList(
      list.map((item) => ({
        ...item,
        isActive: item.id === id
      }))
    );

    if (closeOnSelect) {
      setIsOpen(false);
    }

    if (onSelect) {
      onSelect(e, id);
    }
  };
  
  return (
    <div
      id="generate-proxy-state-dropdown"
      className={`${className} dropdown ${!disabled && isOpen ? "active" : ""} ${disabled ? "disabled" : ""}`}
      {...props}
    >
      <button className="dropdown__toggle" onClick={() => setIsOpen(!isOpen)}>
        <span id="dropdown-value">{current}</span>
        {enableIcon && <img src={icon} alt="icon" />}
      </button>
      <ul className="dropdown__menu">
        {list.map(({ id, isActive, label }) => (
          <li
            key={id}
            className={`dropdown__menu-item ${isActive ? "active" : ""}`}
            onClick={(e) => handleSelect(e, id)}
          >
            {label}
          </li>
        ))}
      </ul>
    </div>
  );
};
