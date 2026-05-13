/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: '#4f8cf7',
        primaryDark: '#3b6fd4',
        warm: '#ff8c42',
        success: '#4caf50',
        warning: '#f5a623',
        danger: '#e74c3c',
        bg: '#f5f6f8',
        card: '#ffffff',
        text: '#1a1a2e',
        muted: '#8b919e',
        border: '#e2e4e9',
      },
    },
  },
  plugins: [],
}
