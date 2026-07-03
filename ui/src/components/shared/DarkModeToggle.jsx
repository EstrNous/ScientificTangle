import { useThemeStore } from '../../stores/themeStore.js';

export default function DarkModeToggle() {
  const theme = useThemeStore((s) => s.theme);
  const toggleTheme = useThemeStore((s) => s.toggleTheme);
  const isDark = theme === 'dark';

  return (
    <button
      type="button"
      onClick={toggleTheme}
      className="rounded-lg bg-nn-blue px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-nn-blue-dark"
      aria-pressed={isDark}
      aria-label={isDark ? 'Включить светлую тему' : 'Включить тёмную тему'}
    >
      {isDark ? 'LightMode' : 'DarkMode'}
    </button>
  );
}
