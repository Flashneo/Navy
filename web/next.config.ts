import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "https://navy.up.railway.app",
    NEXT_PUBLIC_API_KEY: process.env.NEXT_PUBLIC_API_KEY || "",
  },
};

export default nextConfig;
