/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'brand-primary': '#00ff95',
        'brand-primary-dark': '#00cc78',
        'bg-dark': '#0a0a0c',
        'bg-card': '#121216',
        'border-card': 'rgba(255, 255, 255, 0.05)',
      },
    },
  },
  plugins: [],
}
