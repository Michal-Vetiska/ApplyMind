import { Navigate, Route, Routes } from "react-router-dom";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { AppLayout } from "@/components/layout/AppLayout";
import { LoginPage } from "@/features/auth/LoginPage";
import { DashboardPage } from "@/features/dashboard/DashboardPage";
import { JobsPage } from "@/features/jobs/JobsPage";
import { JobDetailPage } from "@/features/jobs/JobDetailPage";
import { ApplicationsPage } from "@/features/applications/ApplicationsPage";
import { InboxPage } from "@/features/inbox/InboxPage";
import { KnowledgePage } from "@/features/knowledge/KnowledgePage";
import { AnalyticsPage } from "@/features/analytics/AnalyticsPage";
import { AutomationPage } from "@/features/automation/AutomationPage";
import { SourcesPage } from "@/features/sources/SourcesPage";
import { SettingsPage } from "@/features/settings/SettingsPage";

export default function App() {
  return (
    <Routes>
      <Route path="/prihlaseni" element={<LoginPage />} />
      <Route path="/login" element={<Navigate to="/prihlaseni" replace />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="nabidky" element={<JobsPage />} />
          <Route path="nabidky/:id" element={<JobDetailPage />} />
          <Route path="prihlasky" element={<ApplicationsPage />} />
          <Route path="email" element={<InboxPage />} />
          <Route path="znalosti" element={<KnowledgePage />} />
          <Route path="analytika" element={<AnalyticsPage />} />
          <Route path="automatizace" element={<AutomationPage />} />
          <Route path="zdroje" element={<SourcesPage />} />
          <Route path="nastaveni" element={<SettingsPage />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
