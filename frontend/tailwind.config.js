/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        dark: {
          900: '#1a1b1e',
          800: '#25262b',
          700: '#2c2e33',
          600: '#373a40',
        },
        accent: '#228be6'
      }
    },
  },
  plugins: [],
}
