import coreWebVitals from "eslint-config-next/core-web-vitals";
import typescript from "eslint-config-next/typescript";

const config = [
  ...coreWebVitals,
  ...typescript,
  // Pinned so eslint-plugin-react skips its filesystem version probe, which ESLint 10 breaks.
  { settings: { react: { version: "19.2" } } },
  { ignores: [".next/**", "node_modules/**", "next-env.d.ts"] },
];

export default config;
