import { Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./auth/AuthContext";
import { DevLogin } from "./pages/DevLogin";
import { EmployeeDashboard } from "./pages/EmployeeDashboard";

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/" element={<DevLogin />} />
        <Route path="/dashboard" element={<EmployeeDashboard />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  );
}
