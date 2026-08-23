/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        navy: {
          950: "#0A1D31",
          900: "#0B2A47",
          800: "#123A5E",
          700: "#1B4A73",
        },
        teal: {
          700: "#0B5B57",
          600: "#0E756E",
          500: "#158F86",
          100: "#E1F1EF",
        },
        saffron: {
          600: "#C26A0E",
          500: "#DE8A1F",
          100: "#FBEBD6",
        },
        surface: {
          DEFAULT: "#FFFFFF",
          sunken: "#EDF2F6",
        },
        bg: {
          DEFAULT: "#F2F6F9",
          raised: "#F8FAFC",
        },
        border: {
          DEFAULT: "#D7E1E9",
          strong: "#B9C8D3",
        },
        ink: {
          900: "#152534",
          700: "#33465A",
          500: "#5B6E80",
          400: "#8497A6",
        },
        success: {
          600: "#1B7A45",
          100: "#E4F5EA",
        },
        warning: {
          600: "#A85E00",
          100: "#FCEFD9",
        },
        error: {
          600: "#B23327",
          100: "#FBEAE8",
        },
      },
      fontFamily: {
        display: ["'IBM Plex Sans'", "system-ui", "sans-serif"],
        body: ["Inter", "system-ui", "sans-serif"],
        data: ["'IBM Plex Mono'", "monospace"],
      },
      borderRadius: {
        sm: "6px",
        md: "10px",
        lg: "16px",
      },
      boxShadow: {
        card: "0 1px 3px rgba(11,42,71,0.08)",
        elevated: "0 6px 20px rgba(11,42,71,0.08), 0 2px 6px rgba(11,42,71,0.05)",
      },
    },
  },
  plugins: [],
};
