/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        charcoal: {
          DEFAULT: "#202831",
          950: "#141A20",
          900: "#202831",
          800: "#28333E",
          700: "#364350",
          600: "#49596B",
        },
        warm: {
          DEFAULT: "#F7F5F1",
          offwhite: "#F7F5F1",
          card: "#FFFFFF",
          muted: "#EDE9E1",
        },
        burnt: {
          DEFAULT: "#E87545",
          orange: "#E87545",
          hover: "#D66536",
          active: "#BF5528",
          light: "#FDF1EB",
          subtle: "#F9DDD0",
        },
        slate: {
          muted: "#D9E0E5",
          dark: "#252A30",
          text: "#58626C",
        },
        // Mapped aliases for backwards-compatibility across existing components
        navy: {
          950: "#141A20",
          900: "#202831",
          800: "#28333E",
          700: "#364350",
        },
        teal: {
          700: "#D66536",
          600: "#E87545",
          500: "#E87545",
          100: "#FDF1EB",
          50: "#FFF8F5",
        },
        saffron: {
          600: "#E87545",
          500: "#E87545",
          100: "#FDF1EB",
        },
        surface: {
          DEFAULT: "#FFFFFF",
          sunken: "#F7F5F1",
        },
        bg: {
          DEFAULT: "#F7F5F1",
          raised: "#FFFFFF",
        },
        border: {
          DEFAULT: "#D9E0E5",
          strong: "#BCC7D0",
        },
        ink: {
          900: "#252A30",
          700: "#3D4650",
          500: "#5E6C79",
          400: "#8E9DAA",
        },
        success: {
          600: "#1F8A4D",
          100: "#EAF7EE",
        },
        warning: {
          600: "#C2820A",
          100: "#FEF7E6",
        },
        error: {
          600: "#C0392B",
          100: "#FDEEEC",
        },
      },
      fontFamily: {
        display: ["'Plus Jakarta Sans'", "system-ui", "sans-serif"],
        body: ["Inter", "system-ui", "sans-serif"],
        data: ["'IBM Plex Mono'", "monospace"],
      },
      borderRadius: {
        sm: "6px",
        md: "10px",
        lg: "16px",
        xl: "20px",
        "2xl": "24px",
      },
      boxShadow: {
        card: "0 1px 3px rgba(32,40,49,0.06), 0 1px 2px rgba(32,40,49,0.04)",
        elevated: "0 10px 25px -5px rgba(32,40,49,0.08), 0 8px 10px -6px rgba(32,40,49,0.04)",
        subtle: "0 1px 2px rgba(0,0,0,0.05)",
      },
    },
  },
  plugins: [],
};
