const v = (name) => `rgb(var(--${name}) / <alpha-value>)`

export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        bg: v('bg'), surface: v('surface'), ink: v('ink'), muted: v('muted'), line: v('line'), linkc: v('linkc'),
        accent: { DEFAULT: v('accent'), dark: v('accent-dark'), soft: v('accent-soft') },
      },
      fontFamily: {
        sans: ['ui-sans-serif', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'Noto Sans', 'Noto Sans Devanagari', 'sans-serif'],
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'Consolas', 'monospace'],
      },
    },
  },
  plugins: [],
}
