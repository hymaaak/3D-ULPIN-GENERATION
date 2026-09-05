import { Navigate, Outlet, Route, Routes, useLocation } from 'react-router-dom';
import { useAuthStore } from './stores/authStore.js';
import Layout from './components/Layout.jsx';
import LoginPage from './pages/LoginPage.jsx';
import RegisterPage from './pages/RegisterPage.jsx';
import Dashboard from './pages/Dashboard.jsx';
import UploadPage from './pages/UploadPage.jsx';
import MapViewer from './pages/MapViewer.jsx';
import ParcelDetail from './pages/ParcelDetail.jsx';
import ULPINManager from './pages/ULPINManager.jsx';
import OwnershipPage from './pages/OwnershipPage.jsx';
import ConflictPage from './pages/ConflictPage.jsx';
import AdminPanel from './pages/AdminPanel.jsx';

function ProtectedRoute() {
  const token = useAuthStore((s) => s.token);
  const location = useLocation();
  if (!token) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return <Outlet />;
}

function AdminRoute() {
  const user = useAuthStore((s) => s.user);
  const roleFn = useAuthStore((s) => s.role);
  const role = user?.role || roleFn?.() || null;
  if (role !== 'admin') {
    return <Navigate to="/" replace />;
  }
  return <Outlet />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/map" element={<MapViewer />} />
          <Route path="/parcels/:id" element={<ParcelDetail />} />
          <Route path="/ulpin" element={<ULPINManager />} />
          <Route path="/ownership" element={<OwnershipPage />} />
          <Route path="/conflicts" element={<ConflictPage />} />
          <Route element={<AdminRoute />}>
            <Route path="/admin" element={<AdminPanel />} />
          </Route>
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
