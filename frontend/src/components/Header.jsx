import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth.js';

const TITLES = [
  { match: /^\/$/, title: 'Dashboard' },
  { match: /^\/upload/, title: 'Upload Data' },
  { match: /^\/map/, title: '3D Map Viewer' },
  { match: /^\/parcels\//, title: 'Parcel Detail' },
  { match: /^\/ulpin/, title: 'ULPIN Registry' },
  { match: /^\/ownership/, title: 'Ownership Records' },
  { match: /^\/conflicts/, title: 'Conflict Alerts' },
  { match: /^\/admin/, title: 'Admin Panel' },
];

function titleFor(pathname) {
  return TITLES.find((t) => t.match.test(pathname))?.title || '3D ULPIN';
}

export default function Header() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, role, logout } = useAuth();

  const handleLogout = () => {
    logout();
    navigate('/login', { replace: true });
  };

  return (
    <header className="flex h-14 items-center justify-between border-b border-slate-200 bg-white px-4">
      <h1 className="text-base font-semibold text-slate-800">
        {titleFor(location.pathname)}
      </h1>
      <div className="flex items-center gap-3">
        <div className="text-right">
          <div className="text-sm font-medium text-slate-700">
            {user?.full_name || user?.email || 'User'}
          </div>
          {role && (
            <div className="text-xs capitalize text-slate-500">{role.replace(/_/g, ' ')}</div>
          )}
        </div>
        <button type="button" onClick={handleLogout} className="btn-secondary">
          Logout
        </button>
      </div>
    </header>
  );
}
