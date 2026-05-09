import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: "#0B1020",
        surface: "#121A2B",
        card: "#182238",
        border: "#263247",
        primary: "#7C5CFF",
        success: "#22C55E",
        warning: "#F59E0B",
        error: "#EF4444",
        foreground: "#F8FAFC",
        muted: "#94A3B8",
      },
      fontFamily: {
        sans: ["Inter", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
