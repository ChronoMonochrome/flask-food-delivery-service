/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        'mandarin': {
          'bg': '#1D1D1B',
          'card': '#2C2C2A',
          'orange': '#EAB545',
        }
      }
    },
  },
  plugins: [],
};