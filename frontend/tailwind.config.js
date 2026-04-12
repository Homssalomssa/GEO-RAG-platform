/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx}",
  ],
  theme: {
    extend: {
      colors: {
        "primary": "#004e9f",
        "primary-container": "#0066cc",
        "primary-fixed": "#d7e3ff",
        "primary-fixed-dim": "#aac7ff",
        "on-primary": "#ffffff",
        "on-primary-container": "#dfe8ff",
        "on-primary-fixed": "#001b3e",
        "on-primary-fixed-variant": "#00458e",
        "inverse-primary": "#aac7ff",

        "secondary": "#006a6a",
        "secondary-container": "#90efef",
        "secondary-fixed": "#93f2f2",
        "secondary-fixed-dim": "#76d6d5",
        "on-secondary": "#ffffff",
        "on-secondary-container": "#006e6e",
        "on-secondary-fixed": "#002020",
        "on-secondary-fixed-variant": "#004f4f",

        "tertiary": "#5f00e4",
        "tertiary-container": "#7836ff",
        "tertiary-fixed": "#e9ddff",
        "tertiary-fixed-dim": "#cfbcff",
        "on-tertiary": "#ffffff",
        "on-tertiary-container": "#eee4ff",
        "on-tertiary-fixed": "#22005d",
        "on-tertiary-fixed-variant": "#5400cc",

        "surface": "#f8f9fa",
        "surface-bright": "#f8f9fa",
        "surface-container": "#edeeef",
        "surface-container-high": "#e7e8e9",
        "surface-container-highest": "#e1e3e4",
        "surface-container-low": "#f3f4f5",
        "surface-container-lowest": "#ffffff",
        "surface-dim": "#d9dadb",
        "surface-tint": "#005cba",
        "on-surface": "#191c1d",
        "on-surface-variant": "#414753",
        "inverse-surface": "#2e3132",
        "inverse-on-surface": "#f0f1f2",

        "error": "#ba1a1a",
        "error-container": "#ffdad6",
        "on-error": "#ffffff",
        "on-error-container": "#93000a",

        "outline": "#727784",
        "outline-variant": "#c1c6d5",

        "background": "#f8f9fa",
        "on-background": "#191c1d",
      },
      fontFamily: {
        headline: ["Inter", "sans-serif"],
        body: ["Inter", "sans-serif"],
        label: ["Space Grotesk", "monospace"],
      },
      borderRadius: {
        DEFAULT: "0.125rem",
        lg: "0.25rem",
        xl: "0.5rem",
        full: "0.75rem",
      },
      boxShadow: {
        sm: "0px 1px 2px rgba(25, 28, 29, 0.05)",
        md: "0px 4px 12px rgba(25, 28, 29, 0.08)",
        lg: "0px 8px 32px rgba(25, 28, 29, 0.12)",
        glow: "0px 0px 20px rgba(0, 78, 159, 0.15)",
      },
    },
  },
  plugins: [],
}
