import type { EmployeeProfile, ReviewCycle } from "../api/types";

export function ProfileCard({ profile, cycle }: { profile: EmployeeProfile; cycle: ReviewCycle | null }) {
  return (
    <section className="card">
      <h2>Profile</h2>
      <div className="row">
        <span className="muted">Name</span>
        <span>{profile.name}</span>
      </div>
      <div className="row">
        <span className="muted">Email</span>
        <span>{profile.email}</span>
      </div>
      <div className="row">
        <span className="muted">Skills</span>
        <span>{profile.skills ?? "—"}</span>
      </div>
      <div className="row">
        <span className="muted">Current cycle</span>
        <span>{cycle ? `${cycle.cycle_start} – ${cycle.cycle_end} (${cycle.status})` : "No open cycle"}</span>
      </div>
    </section>
  );
}
