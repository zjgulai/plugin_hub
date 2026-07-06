"use client";

import { useFormStatus } from "react-dom";

export function RedditCaptureSubmitButton() {
  const { pending } = useFormStatus();

  return (
    <button type="submit" disabled={pending} aria-disabled={pending}>
      {pending ? "解析中…" : "解析并入库"}
    </button>
  );
}
