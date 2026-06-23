import { z } from "zod";

// Lenient, professional-grade email check that mirrors the backend's LooseEmail
// (app/schemas/common.py): require an "@" and a "." in the domain part — no
// strict RFC / deliverability checks, so addresses like admin@demo.test work.
export const emailSchema = z
  .string()
  .trim()
  .refine((v) => {
    const [local, ...rest] = v.split("@");
    const domain = rest.join("@");
    return (
      rest.length === 1 &&
      local.length > 0 &&
      domain.includes(".") &&
      !domain.startsWith(".") &&
      !domain.endsWith(".")
    );
  }, "Enter a valid email (must contain '@' and '.')");
