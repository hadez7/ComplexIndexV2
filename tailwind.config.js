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

