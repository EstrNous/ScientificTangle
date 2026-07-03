export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        nn: {
          blue: '#0057B8',
          'blue-dark': '#004494',
          'blue-light': '#E8F1FA',
          gray: '#6B7280',
          'gray-light': '#F5F6F8',
          border: '#E5E7EB',
        },
      },
      boxShadow: {
        card: '0 1px 3px rgba(0, 0, 0, 0.08)',
      },
    },
  },
  plugins: [require('tailwind-scrollbar')],
};
