import type { NextConfig } from "next";

const config: NextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  typedRoutes: true,
  // Emits a self-contained server bundle so the runtime image needs no node_modules.
  output: "standalone",
};

export default config;
