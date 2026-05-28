/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: "class",
  content: ["./src/**/*.{html,js,jsx,ts,tsx}", "./*.html"],
  theme: {
    extend: {
      // ── Colores ─────────────────────────────────────────────
      colors: {
        // Primario (Gold)
        primary: "#b8860b",
        "on-primary": "#ffffff",
        "primary-container": "#986d00",
        "on-primary-container": "#fffbff",
        "primary-fixed": "#ffdea6",
        "primary-fixed-dim": "#f7bd48",
        "inverse-primary": "#f7bd48",
        "on-primary-fixed": "#271900",
        "on-primary-fixed-variant": "#5d4200",
        "surface-tint": "#7b5800",

        // Secundario (Dark Brown)
        secondary: "#3e2c1c",
        "on-secondary": "#ffffff",
        "secondary-container": "#fcddc5",
        "on-secondary-container": "#77604d",
        "secondary-fixed": "#fcddc5",
        "secondary-fixed-dim": "#dec1aa",
        "on-secondary-fixed": "#28180a",
        "on-secondary-fixed-variant": "#574331",

        // Terciario (Warm Grey)
        tertiary: "#8a7e6d",
        "on-tertiary": "#ffffff",
        "tertiary-container": "#7e7362",
        "on-tertiary-container": "#fffbff",
        "tertiary-fixed": "#f0e0cc",
        "tertiary-fixed-dim": "#d3c4b1",
        "on-tertiary-fixed": "#221a0e",
        "on-tertiary-fixed-variant": "#4f4537",

        // Error / Alerta
        error: "#ba1a1a",
        "on-error": "#ffffff",
        "error-container": "#ffdad6",
        "on-error-container": "#93000a",

        // Éxito (usado en tablas de competencia)
        success: "#2e7d32",
        "success-container": "#e8f5e9",

        // Superficies
        background: "#fff9ef",
        "on-background": "#1d1b16",
        surface: "#fff9ef",
        "surface-bright": "#fff9ef",
        "surface-dim": "#dfd9d1",
        "surface-container-lowest": "#ffffff",
        "surface-container-low": "#f9f3ea",
        "surface-container": "#f3ede4",
        "surface-container-high": "#ede7de",
        "surface-container-highest": "#e7e2d9",
        "surface-variant": "#e7e2d9",
        "on-surface": "#1d1b16",
        "on-surface-variant": "#4f4535",
        "inverse-surface": "#32302a",
        "inverse-on-surface": "#f6f0e7",

        // Bordes
        outline: "#817563",
        "outline-variant": "#d3c4af",
      },

      // ── Bordes redondeados ─────────────────────────────────
      borderRadius: {
        sm: "0.125rem",   // 2px
        DEFAULT: "0.25rem", // 4px — radio principal
        md: "0.375rem",   // 6px
        lg: "0.5rem",     // 8px
        xl: "0.75rem",    // 12px
        full: "9999px",
      },

      // ── Espaciado ───────────────────────────────────────────
      spacing: {
        xs: "4px",
        base: "8px",
        sm: "12px",
        md: "24px",
        lg: "48px",
        xl: "80px",
        gutter: "24px",
        "margin-mobile": "16px",
        "margin-desktop": "40px",
      },

      // ── Tipografía ──────────────────────────────────────────
      fontFamily: {
        "display-lg": ["Playfair Display", "serif"],
        "headline-lg": ["Playfair Display", "serif"],
        "headline-lg-mobile": ["Playfair Display", "serif"],
        "headline-md": ["Playfair Display", "serif"],
        "body-lg": ["Inter", "sans-serif"],
        "body-md": ["Inter", "sans-serif"],
        "label-md": ["Inter", "sans-serif"],
        "data-tabular": ["Inter", "sans-serif"],
      },

      fontSize: {
        "display-lg": [
          "48px",
          { lineHeight: "1.2", letterSpacing: "-0.02em", fontWeight: "700" },
        ],
        "headline-lg": [
          "32px",
          { lineHeight: "1.3", fontWeight: "600" },
        ],
        "headline-lg-mobile": [
          "28px",
          { lineHeight: "1.3", fontWeight: "600" },
        ],
        "headline-md": [
          "24px",
          { lineHeight: "1.4", fontWeight: "600" },
        ],
        "body-lg": [
          "18px",
          { lineHeight: "1.6", fontWeight: "400" },
        ],
        "body-md": [
          "16px",
          { lineHeight: "1.5", fontWeight: "400" },
        ],
        "label-md": [
          "14px",
          { lineHeight: "1", letterSpacing: "0.05em", fontWeight: "500" },
        ],
        "data-tabular": [
          "13px",
          { lineHeight: "1", fontWeight: "400" },
        ],
      },
    },
  },
  plugins: [require("@tailwindcss/forms"), require("@tailwindcss/container-queries")],
};
