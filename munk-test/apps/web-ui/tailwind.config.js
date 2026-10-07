/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        surface: {
          default: 'var(--surface-default)',
          muted: 'var(--surface-muted)',
          elevated: 'var(--surface-elevated)',
          accent: 'var(--surface-accent)',
          overlay: 'var(--surface-overlay)',
        },
        border: {
          DEFAULT: 'var(--border-default)',
          muted: 'var(--border-muted)',
          strong: 'var(--border-strong)',
        },
        text: {
          primary: 'var(--text-primary)',
          secondary: 'var(--text-secondary)',
          muted: 'var(--text-muted)',
        },
        accent: {
          DEFAULT: 'var(--accent-primary)',
          soft: 'var(--accent-primary-soft)',
          strong: 'var(--accent-primary-strong)',
        },
        success: {
          bg: 'var(--status-success-bg)',
          text: 'var(--status-success-text)',
        },
        error: {
          bg: 'var(--status-error-bg)',
          text: 'var(--status-error-text)',
        },
        warning: {
          bg: 'var(--status-warning-bg)',
          text: 'var(--status-warning-text)',
        },
      },
      borderRadius: {
        sm: 'var(--radius-sm)',
        md: 'var(--radius-md)',
        lg: 'var(--radius-lg)',
        xl: 'var(--radius-xl)',
      },
      boxShadow: {
        panel: 'var(--shadow-panel)',
        card: 'var(--shadow-card)',
        glow: 'var(--shadow-glow)',
      },
      fontFamily: {
        sans: ['var(--font-sans)'],
        mono: ['var(--font-mono)'],
      },
    },
  },
  plugins: [],
}
