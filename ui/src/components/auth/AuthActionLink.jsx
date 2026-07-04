import { Link } from 'react-router-dom';

export default function AuthActionLink({ to, className, children }) {
  return (
    <Link to={to} className={className}>
      {children}
    </Link>
  );
}
