import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        mono: ["JetBrains Mono", "Fira Code", "Menlo", "monospace"],
      },
      colors: {
        surface: {
          DEFAULT: "#0f1117",
          1: "#161b22",
          2: "#1c2333",
          3: "#21262d",
        },
        border: "#30363d",
        accent: {
          blue: "#58a6ff",
          green: "#3fb950",
          yellow: "#d29922",
          gray: "#8b949e",
        },
      },
      animation: {
        "fade-in": "fadeIn 0.3s ease-in-out",
        "count-up": "countUp 0.6s ease-out",
        "pulse-soft": "pulseSoft 2s ease-in-out infinite",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0", transform: "translateY(4px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        pulseSoft: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.6" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
