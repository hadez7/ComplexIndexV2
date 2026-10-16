/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    './Counter/templates/**/*.html',
    './User/templates/**/*.html',
    './WordCounter/templates/**/*.html',
    './Counter/static/js/**/*.js',
    './Counter/**/*.py',
    './User/**/*.py',
    './WordCounter/**/*.py',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Manrope', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'Helvetica', 'Arial', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
      },
      colors: {
        slate: {
          850: '#151F32',
          950: '#070A10',
        },
      },
    },
  },
  plugins: [],
}

