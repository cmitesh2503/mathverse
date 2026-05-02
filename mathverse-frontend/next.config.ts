import path from "path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  pageExtensions: ["page.tsx", "page.ts", "route.ts", "route.tsx"],
  turbopack: {
    root: path.resolve(__dirname),
  },
  allowedDevOrigins: ["127.0.0.1"],
};

export default nextConfig;
