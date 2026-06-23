import Link from "next/link";

import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-3 text-center">
      <h1 className="text-4xl font-bold">404</h1>
      <p className="text-[var(--muted-foreground)]">This page could not be found.</p>
      <Link href="/chat">
        <Button>Back to chat</Button>
      </Link>
    </div>
  );
}
