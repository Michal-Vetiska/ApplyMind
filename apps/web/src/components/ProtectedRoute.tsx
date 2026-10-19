import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { PageLoader } from "@/components/ui/spinner";

export function ProtectedRoute() {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) return <PageLoader />;
  if (!user) {
    return <Navigate to="/prihlaseni" replace state={{ from: location.pathname }} />;
  }
  return <Outlet />;
}
