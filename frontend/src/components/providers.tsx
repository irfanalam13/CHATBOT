"use client";

import * as React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { Toaster } from "sonner";

import { usePreferences } from "@/stores/preferences-store";
import { PwaRegister } from "./pwa-register";

function makeClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { staleTime: 30_000, retry: 1, refetchOnWindowFocus: false },
    },
  });
}

/** Applies theme + accessibility classes to <html> from preferences. */
function ThemeApplier() {
  const { theme, highContrast, reducedMotion } = usePreferences();

  React.useEffect(() => {
    const root = document.documentElement;
    const apply = () => {
      const dark =
        theme === "dark" ||
        (theme === "system" &&
          window.matchMedia("(prefers-color-scheme: dark)").matches);
      root.classList.toggle("dark", dark);
      root.classList.toggle("high-contrast", highContrast);
      root.classList.toggle("reduce-motion", reducedMotion);
    };
    apply();
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, [theme, highContrast, reducedMotion]);

  return null;
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [client] = React.useState(makeClient);
  return (
    <QueryClientProvider client={client}>
      <ThemeApplier />
      <PwaRegister />
      {children}
      <Toaster richColors position="top-right" closeButton />
      {process.env.NODE_ENV === "development" && <ReactQueryDevtools initialIsOpen={false} />}
    </QueryClientProvider>
  );
}
