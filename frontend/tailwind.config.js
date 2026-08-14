/** @type {import('tailwindcss').Config} */
import plugin from 'tailwindcss/plugin'
import colors from 'tailwindcss/colors'

export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx,ts,tsx}",
    // include shadcn generated components if present
    './src/components/**/*.{js,jsx,ts,tsx}',
    './node_modules/@shadcn/**/*.{js,jsx,ts,tsx}'
  ],
  theme: {
    extend: {
      colors: {
        // Sidebar tokens mapped to CSS variables
        sidebar: {
          DEFAULT: 'var(--sidebar-bg)',
          fg: 'var(--sidebar-fg)',
          border: 'var(--sidebar-border)',
          active: 'var(--sidebar-active-bg)',
          hover: 'var(--sidebar-hover)'
        },
        // Priority color groups (semantic only)
        priority: {
          critical: colors.red,
          veryHigh: colors.orange,
          high: colors.amber,
          moderate: colors.green,
          low: colors.blue,
        }
      },
      spacing: {
        'sidebar-width': 'var(--sidebar-width)'
      },
      borderRadius: {
        'base': 'var(--radius)'
      }
    }
  },
  plugins: [
    // keep plugin placeholder for project-specific plugins
    plugin(function () {})
  ]
}