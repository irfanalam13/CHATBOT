/** @type {import('next').NextConfig} */
const API_BASE = process.env.BACKEND_URL || "http://localhost:8000";

const nextConfig = {
  reactStrictMode: true,
  // Proxy API + WS to the backend in dev so the browser talks same-origin.
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${API_BASE}/api/:path*` },
      { source: "/metrics", destination: `${API_BASE}/metrics` },
    ];
  },
  experimental: {
    optimizePackageImports: ["lucide-react", "recharts", "date-fns"],
  },
};

export default nextConfig;
