"use client";

import { useFormStatus } from "react-dom";

export function PlatformSettingSubmitButton({ label }: { label: string }) {
  const { pending } = useFormStatus();

  return (
    <button type="submit" disabled={pending} aria-disabled={pending}>
      {pending ? "保存中…" : label}
    </button>
  );
}
