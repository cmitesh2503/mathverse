import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  turbopack: {
    root: __dirname, // 🔥 THIS FIXES YOUR ISSUE
  },
  allowedDevOrigins: ['127.0.0.1', 'localhost'],
};

export default nextConfig;