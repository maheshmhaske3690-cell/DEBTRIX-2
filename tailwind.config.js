/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#0B0F14",
          900: "#131922",
          800: "#1B2330",
          700: "#2A3547",
        },
        paper: "#E8EAED",
        muted: "#8A93A3",
        gold: {
          DEFAULT: "#D4A017",
          soft: "#E8C766",
        },
        loss: "#C4453A",
        health: "#4A9B6E",
      },
      fontFamily: {
        display: ["var(--font-space-grotesk)", "sans-serif"],
        body: ["var(--font-inter)", "sans-serif"],
        mono: ["var(--font-jetbrains-mono)", "monospace"],
      },
    },
  },
  plugins: [],
};
