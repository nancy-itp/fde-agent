import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/useAuth";

// Dev-only stand-in for the real IdP redirect flow (see backend/app/auth/router.py).
// Swapping in real OIDC/SAML later only touches this file plus AuthContext.
export function DevLogin() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [employeeId, setEmployeeId] = useState("2");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(Number(employeeId));
      navigate("/dashboard");
    } catch {
      setError("No active employee with that id.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card" style={{ maxWidth: 360, margin: "80px auto" }}>
      <h1>Dev login</h1>
      <p className="muted">
        Placeholder for the real IdP login. Never available outside a development environment.
      </p>
      <form onSubmit={handleSubmit}>
        <label htmlFor="employee-id">Employee id</label>
        <input
          id="employee-id"
          type="number"
          value={employeeId}
          onChange={(e) => setEmployeeId(e.target.value)}
          required
        />
        {error && <p className="error-text">{error}</p>}
        <button type="submit" disabled={loading} style={{ marginTop: 16, width: "100%" }}>
          {loading ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </div>
  );
}
