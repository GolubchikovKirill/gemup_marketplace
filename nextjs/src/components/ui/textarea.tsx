"use client";

import { useEffect, useRef } from "react";

interface Props extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  resize?: boolean;
}

export const Textarea: React.FC<Props> = (props) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (props.resize) {
      resize();
    }
  }, [props.value]);

  const resize = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${el.scrollHeight}px`;
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    if (props.resize) {
      resize();
    }

    if (props.onInput) {
      props.onInput(e);
    }
  };

  return (
    <textarea
      {...props}
      ref={textareaRef}
      onInput={handleInput}
      style={{ overflow: "hidden", resize: "none", ...props.style }}
    >
      {props.children}
    </textarea>
  );
};
