export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: { primary: "#0a0e1a", secondary: "#0f1629", card: "#141c2e" },
        border: { subtle: "#1e2d4a", active: "#2d4a7a" },
      },
    },
  },
  plugins: [],
};
