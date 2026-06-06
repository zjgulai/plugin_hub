"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

type DashboardAutoRefreshProps = {
  intervalSeconds: number;
};

export function DashboardAutoRefresh({ intervalSeconds }: DashboardAutoRefreshProps) {
  const router = useRouter();

  useEffect(() => {
    if (!Number.isFinite(intervalSeconds) || intervalSeconds <= 0) {
      return undefined;
    }

    const timer = window.setInterval(() => router.refresh(), intervalSeconds * 1000);
    return () => window.clearInterval(timer);
  }, [intervalSeconds, router]);

  return null;
}
