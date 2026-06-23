"use client";

import * as React from "react";

let mermaidInit = false;

export function Mermaid({ chart }: { chart: string }) {
  const ref = React.useRef<HTMLDivElement>(null);
  const [error, setError] = React.useState<string | null>(null);
  const id = React.useId().replace(/:/g, "");

  React.useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const mermaid = (await import("mermaid")).default;
        if (!mermaidInit) {
          mermaid.initialize({ startOnLoad: false, theme: "neutral", securityLevel: "strict" });
          mermaidInit = true;
        }
        const { svg } = await mermaid.render(`m-${id}`, chart);
        if (!cancelled && ref.current) ref.current.innerHTML = svg;
      } catch (e) {
        if (!cancelled) setError((e as Error).message);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [chart, id]);

  if (error) {
    return <pre className="overflow-x-auto rounded-md bg-[var(--muted)] p-3 text-xs">{chart}</pre>;
  }
  return <div ref={ref} className="my-3 flex justify-center" />;
}
