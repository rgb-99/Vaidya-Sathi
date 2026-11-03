const v = (name) => `rgb(var(--${name}) / <alpha-value>)`

export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        bg: v('bg'), surface: v('surface'), ink: v('ink'), muted: v('muted'), line: v('line'), linkc: v('linkc'), onaccent: v('on-accent'),
        accent: { DEFAULT: v('accent'), dark: v('accent-dark'), soft: v('accent-soft') },
      },
      fontFamily: {
        // Neue Montreal is a commercial font and is not bundled: it is used where installed, otherwise the next one applies.
        // 'Noto Sans Devanagari' is kept near the end so Marathi and Hindi text still renders well.
        sans: ['"Neue Montreal"', 'system-ui', '-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell',
          '"Open Sans"', '"Helvetica Neue"', '"Noto Sans Devanagari"', 'sans-serif'],
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'Consolas', 'monospace'],
      },
    },
  },
  plugins: [],
}
