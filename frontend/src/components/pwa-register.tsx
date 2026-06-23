"use client";

import * as React from "react";

/** Registers the service worker for PWA / offline shell (production only). */
export function PwaRegister() {
  React.useEffect(() => {
    if (
      process.env.NODE_ENV === "production" &&
      typeof navigator !== "undefined" &&
      "serviceWorker" in navigator
    ) {
      navigator.serviceWorker.register("/sw.js").catch(() => undefined);
    }
  }, []);
  return null;
}
