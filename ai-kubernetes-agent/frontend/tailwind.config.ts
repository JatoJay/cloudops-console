import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        canvas: "#fbfcfa",
        ink: "#082754",
        muted: "#50627b",
        action: "#1268ee",
        ready: "#0d9f60",
        line: "#dce4ec",
      },
      fontFamily: {
        sans: ["Manrope Variable", "ui-sans-serif", "system-ui"],
        mono: ["IBM Plex Mono", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
