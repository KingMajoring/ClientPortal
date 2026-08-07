import { Navigate, Route, Routes } from "react-router-dom";
import { CLIENT_ROLES, WGTK_ROLES } from "./auth/AuthContext";
import { LoginPage } from "./auth/LoginPage";
import { ProtectedRoute } from "./auth/ProtectedRoute";
import { LandingPage } from "./LandingPage";
import { ClientsPage } from "./portals/staff/ClientsPage";
import { StaffDashboardPage } from "./portals/staff/DashboardPage";
import { EnquiryDetailPage } from "./portals/staff/EnquiryDetailPage";
import { EnquiryListPage } from "./portals/staff/EnquiryListPage";
import { StaffLayout } from "./portals/staff/StaffLayout";
import { UsersPage } from "./portals/staff/UsersPage";
import { ClientLayout } from "./portals/client/ClientLayout";
import { CompanyPage } from "./portals/client/CompanyPage";
import { ClientDashboardPage } from "./portals/client/DashboardPage";
import { ClientEnquiryDetailPage } from "./portals/client/EnquiryDetailPage";
import { ClientEnquiryListPage } from "./portals/client/EnquiryListPage";
import { RaiseEnquiryPage } from "./portals/client/RaiseEnquiryPage";

export function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />

      <Route
        path="/staff/login"
        element={
          <LoginPage
            title="WGTK Staff Portal"
            allowedRoles={WGTK_ROLES}
            homePath="/staff/enquiries"
            otherPortalHint="That account is a client account — please use the Client Portal login."
          />
        }
      />
      <Route
        path="/staff"
        element={
          <ProtectedRoute allowedRoles={WGTK_ROLES} redirectTo="/staff/login">
            <StaffLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="enquiries" replace />} />
        <Route path="enquiries" element={<EnquiryListPage />} />
        <Route path="enquiries/:id" element={<EnquiryDetailPage />} />
        <Route path="clients" element={<ClientsPage />} />
        <Route path="users" element={<UsersPage />} />
        <Route path="dashboard" element={<StaffDashboardPage />} />
      </Route>

      <Route
        path="/portal/login"
        element={
          <LoginPage
            title="Client Portal"
            allowedRoles={CLIENT_ROLES}
            homePath="/portal/enquiries"
            otherPortalHint="That account is a WGTK staff account — please use the Staff Portal login."
          />
        }
      />
      <Route
        path="/portal"
        element={
          <ProtectedRoute allowedRoles={CLIENT_ROLES} redirectTo="/portal/login">
            <ClientLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="enquiries" replace />} />
        <Route path="enquiries" element={<ClientEnquiryListPage />} />
        <Route path="enquiries/new" element={<RaiseEnquiryPage />} />
        <Route path="enquiries/:id" element={<ClientEnquiryDetailPage />} />
        <Route path="dashboard" element={<ClientDashboardPage />} />
        <Route path="company" element={<CompanyPage />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
