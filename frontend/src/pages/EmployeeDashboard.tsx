import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import type { Availability, AvailabilityUpdate, EmployeeProfile, PerformanceScore, ReviewCycle } from "../api/types";
import { useAuth } from "../auth/useAuth";
import { AvailabilityCard } from "../components/AvailabilityCard";
import { ProfileCard } from "../components/ProfileCard";
import { ScoresTable } from "../components/ScoresTable";

// Every field here is scoped server-side to the calling employee — this
// page never sends or receives another employee's id (see
// backend/app/employee_profile/router.py).
export function EmployeeDashboard() {
  const { token, logout } = useAuth();
  const navigate = useNavigate();

  const [profile, setProfile] = useState<EmployeeProfile | null>(null);
  const [availability, setAvailability] = useState<Availability | null>(null);
  const [cycle, setCycle] = useState<ReviewCycle | null>(null);
  const [scores, setScores] = useState<PerformanceScore[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) {
      navigate("/", { replace: true });
    }
  }, [token, navigate]);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;

    async function load(currentToken: string) {
      setLoading(true);
      setError(null);
      try {
        const [profileResult, availabilityResult] = await Promise.all([
          api.getMyProfile(currentToken),
          api.getMyAvailability(currentToken),
        ]);
        if (cancelled) return;
        setProfile(profileResult);
        setAvailability(availabilityResult);

        // No open cycle yet is a normal state (scoring pipeline isn't built
        // yet), not an error — scores just come back empty.
        try {
          const cycleResult = await api.getCurrentCycle(currentToken);
          if (cancelled) return;
          setCycle(cycleResult);
          const scoresResult = await api.getMyScores(currentToken, cycleResult.cycle_id);
          if (!cancelled) setScores(scoresResult);
        } catch {
          if (!cancelled) {
            setCycle(null);
            setScores([]);
          }
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Could not load dashboard data.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void load(token);
    return () => {
      cancelled = true;
    };
  }, [token]);

  if (!token) {
    return null;
  }

  async function handleSaveAvailability(payload: AvailabilityUpdate) {
    if (!token) return;
    const updated = await api.updateMyAvailability(token, payload);
    setAvailability(updated);
    if (profile) {
      setProfile({ ...profile, skills: payload.skills ?? profile.skills, availability_status: payload.availability_status ?? profile.availability_status });
    }
  }

  return (
    <div>
      <div className="row">
        <h1>My Dashboard</h1>
        <button
          type="button"
          className="secondary"
          onClick={() => {
            logout();
            navigate("/");
          }}
        >
          Sign out
        </button>
      </div>

      {loading && <p className="muted">Loading…</p>}
      {error && <p className="error-text">{error}</p>}

      {profile && <ProfileCard profile={profile} cycle={cycle} />}
      {availability && profile && (
        <AvailabilityCard
          availability={availability}
          availabilityStatus={profile.availability_status}
          onSave={handleSaveAvailability}
        />
      )}
      {!loading && <ScoresTable scores={scores} />}
    </div>
  );
}
