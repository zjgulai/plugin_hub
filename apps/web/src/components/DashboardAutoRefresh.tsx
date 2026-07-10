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

    let timer: number | undefined;

    const stopTimer = () => {
      if (timer !== undefined) {
        window.clearInterval(timer);
        timer = undefined;
      }
    };
    const startTimer = () => {
      stopTimer();
      if (document.visibilityState === "visible") {
        timer = window.setInterval(() => router.refresh(), intervalSeconds * 1000);
      }
    };
    const handleVisibilityChange = () => {
      if (document.visibilityState === "visible") {
        router.refresh();
        startTimer();
      } else {
        stopTimer();
      }
    };

    startTimer();
    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => {
      stopTimer();
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [intervalSeconds, router]);

  return null;
}
