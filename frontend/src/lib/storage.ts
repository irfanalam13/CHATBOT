// Token persistence. Access token is kept in memory + mirrored to localStorage
// for reloads; refresh token lives in localStorage and is rotated on each use.
import type { Tokens } from "./types";

const ACCESS = "cb_access";
const REFRESH = "cb_refresh";

let accessToken: string | null = null;

export const tokenStore = {
  get access(): string | null {
    if (accessToken) return accessToken;
    if (typeof window !== "undefined") accessToken = localStorage.getItem(ACCESS);
    return accessToken;
  },
  get refresh(): string | null {
    return typeof window !== "undefined" ? localStorage.getItem(REFRESH) : null;
  },
  set(tokens: Tokens) {
    accessToken = tokens.access_token;
    if (typeof window !== "undefined") {
      localStorage.setItem(ACCESS, tokens.access_token);
      localStorage.setItem(REFRESH, tokens.refresh_token);
    }
  },
  clear() {
    accessToken = null;
    if (typeof window !== "undefined") {
      localStorage.removeItem(ACCESS);
      localStorage.removeItem(REFRESH);
    }
  },
  has(): boolean {
    return Boolean(this.refresh);
  },
};
