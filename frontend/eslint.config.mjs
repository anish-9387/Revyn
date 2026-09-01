import coreWebVitals from "eslint-config-next/core-web-vitals";
import typescript from "eslint-config-next/typescript";

export default [
  ...coreWebVitals,
  ...typescript,
  // Pinned so eslint-plugin-react skips its filesystem version probe, which ESLint 10 breaks.
  { settings: { react: { version: "19.2" } } },
  { ignores: [".next/**", "node_modules/**", "next-env.d.ts"] },
];
