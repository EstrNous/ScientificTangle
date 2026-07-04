import appLogo from '../../assets/app-logo.png';

export default function AppLogo({ className = 'h-9 w-9' }) {
  return (
    <span
      className={`inline-flex shrink-0 items-center justify-center bg-inherit ${className}`}
    >
      <img
        src={appLogo}
        alt=""
        className="h-full w-full object-contain"
      />
    </span>
  );
}
