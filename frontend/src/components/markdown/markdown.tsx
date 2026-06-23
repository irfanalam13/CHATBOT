"use client";

import * as React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import { Check, Copy } from "lucide-react";

import { cn } from "@/lib/utils";
import { Mermaid } from "./mermaid";

function CodeBlock({ className, children }: { className?: string; children: React.ReactNode }) {
  const [copied, setCopied] = React.useState(false);
  const code = String(children).replace(/\n$/, "");
  const lang = /language-(\w+)/.exec(className ?? "")?.[1];

  if (lang === "mermaid") return <Mermaid chart={code} />;

  const copy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="group relative my-3">
      <div className="flex items-center justify-between rounded-t-md bg-zinc-800 px-3 py-1.5 text-xs text-zinc-300">
        <span>{lang ?? "code"}</span>
        <button onClick={copy} className="flex items-center gap-1 hover:text-white" aria-label="Copy code">
          {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <pre className="overflow-x-auto rounded-b-md bg-zinc-900 p-3 text-sm">
        <code className={className}>{children}</code>
      </pre>
    </div>
  );
}

export function Markdown({ content, className }: { content: string; className?: string }) {
  return (
    <div
      className={cn(
        "prose-sm max-w-none break-words leading-relaxed [&_a]:text-[var(--primary)] [&_a]:underline",
        className,
      )}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={{
          pre: ({ children }) => <>{children}</>,
          code({ className, children, ...props }) {
            const isBlock = /language-/.test(className ?? "");
            if (isBlock) return <CodeBlock className={className}>{children}</CodeBlock>;
            return (
              <code className="rounded bg-[var(--muted)] px-1.5 py-0.5 text-[0.85em]" {...props}>
                {children}
              </code>
            );
          },
          table: ({ children }) => (
            <div className="my-3 overflow-x-auto">
              <table className="w-full border-collapse text-sm">{children}</table>
            </div>
          ),
          th: ({ children }) => (
            <th className="border border-[var(--border)] bg-[var(--muted)] px-3 py-1.5 text-left font-semibold">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="border border-[var(--border)] px-3 py-1.5">{children}</td>
          ),
          ul: ({ children }) => <ul className="my-2 list-disc pl-5">{children}</ul>,
          ol: ({ children }) => <ol className="my-2 list-decimal pl-5">{children}</ol>,
          h1: ({ children }) => <h1 className="mb-2 mt-4 text-xl font-bold">{children}</h1>,
          h2: ({ children }) => <h2 className="mb-2 mt-3 text-lg font-bold">{children}</h2>,
          h3: ({ children }) => <h3 className="mb-1 mt-3 text-base font-semibold">{children}</h3>,
          p: ({ children }) => <p className="my-2">{children}</p>,
          blockquote: ({ children }) => (
            <blockquote className="my-2 border-l-2 border-[var(--primary)] pl-3 text-[var(--muted-foreground)]">
              {children}
            </blockquote>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
