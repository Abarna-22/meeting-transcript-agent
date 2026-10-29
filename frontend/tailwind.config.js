/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        spruce: { 950: "#0C2420", 900: "#12332E", 800: "#1B4640", 700: "#27605A" },
        ink: "#17211F",
        muted: "#5E6B67",
        paper: "#F2F4F3",
        line: "#D8DEDB",
        amber: { chip: "#B7791F", soft: "#FBF1DC", deep: "#7A4E0E" },
      },
      fontFamily: {
        serif: ['"Iowan Old Style"', '"Palatino Linotype"', "Palatino", "Georgia", "serif"],
        sans: ["system-ui", "-apple-system", '"Segoe UI"', "Roboto", "sans-serif"],
      },
    },
  },
  plugins: [],
};
