import { NavLink } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth.js';

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', end: true },
  { to: '/upload', label: 'Upload Data' },
  { to: '/map', label: '3D Map Viewer' },
  { to: '/ulpin', label: 'ULPIN Registry' },
  { to: '/ownership', label: 'Ownership' },
  { to: '/conflicts', label: 'Conflicts' },
];

const ADMIN_ITEM = { to: '/admin', label: 'Admin Panel' };

function NavItem({ to, label, end }) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        `block rounded-md px-3 py-2 text-sm font-medium transition-colors ${
          isActive
            ? 'bg-brand-600 text-white'
            : 'text-slate-300 hover:bg-slate-800 hover:text-white'
        }`
      }
    >
      {label}
    </NavLink>
  );
}

export default function Sidebar() {
  const { isAdmin } = useAuth();
  return (
    <aside className="flex w-56 shrink-0 flex-col bg-slate-900">
      <div className="px-4 py-5">
        <div className="text-lg font-bold text-white">3D ULPIN</div>
        <div className="text-xs text-slate-400">Vertical Property Mapping</div>
      </div>
      <nav className="flex-1 space-y-1 px-2">
        {NAV_ITEMS.map((item) => (
          <NavItem key={item.to} {...item} />
        ))}
        {isAdmin && <NavItem {...ADMIN_ITEM} />}
      </nav>
      <div className="px-4 py-4 text-xs text-slate-500">
        SIH26011 · Smart India Hackathon
      </div>
    </aside>
  );
}
