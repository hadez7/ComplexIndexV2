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
        canvas: 'var(--canvas)',
        surface: {
          DEFAULT: 'var(--surface)',
          hover: 'var(--surface-hover)',
        },
        ink: 'var(--ink)',
        muted: 'var(--muted)',
        faint: 'var(--faint)',
        line: {
          DEFAULT: 'var(--line)',
          strong: 'var(--line-strong)',
        },
        brand: {
          DEFAULT: 'var(--blue)',
          deep: 'var(--blue-deep)',
          soft: 'var(--blue-soft)',
        },
        cyan: {
          DEFAULT: 'var(--cyan)',
          100: '#cffafe',
          200: '#a5f3fc',
          300: '#67e8f9',
          400: '#22d3ee',
          500: '#06b6d4',
        },
        slate: {
          850: '#151F32',
          950: '#070A10',
        },
      },
    },
  },
  plugins: [],
}

