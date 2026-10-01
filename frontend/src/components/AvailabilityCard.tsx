import { useState } from "react";
import type { Availability, AvailabilityStatus, AvailabilityUpdate } from "../api/types";

const STATUS_OPTIONS: AvailabilityStatus[] = ["Available", "Unavailable", "PartiallyAvailable"];

export function AvailabilityCard({
  availability,
  availabilityStatus,
  onSave,
}: {
  availability: Availability;
  availabilityStatus: AvailabilityStatus | null;
  onSave: (payload: AvailabilityUpdate) => Promise<void>;
}) {
  const [editing, setEditing] = useState(false);
  const [available, setAvailable] = useState(availability.available);
  const [skillSet, setSkillSet] = useState(availability.skill_set ?? "");
  const [status, setStatus] = useState<AvailabilityStatus>(availabilityStatus ?? "Available");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      await onSave({ available, skill_set: skillSet, availability_status: status, skills: skillSet });
      setEditing(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save availability.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="card">
      <div className="row">
        <h2>Availability</h2>
        {!editing && (
          <button type="button" className="secondary" onClick={() => setEditing(true)}>
            Edit
          </button>
        )}
      </div>

      {!editing ? (
        <>
          <div className="row">
            <span className="muted">Available</span>
            <span>{availability.available ? "Yes" : "No"}</span>
          </div>
          <div className="row">
            <span className="muted">Status</span>
            <span>{availabilityStatus ?? "—"}</span>
          </div>
          <div className="row">
            <span className="muted">Skill set</span>
            <span>{availability.skill_set ?? "—"}</span>
          </div>
          <div className="row">
            <span className="muted">Client / project</span>
            <span>
              {availability.client_name ?? "—"} / {availability.project_name ?? "—"}
            </span>
          </div>
          <div className="row">
            <span className="muted">Allocation</span>
            <span>{availability.allocation_percent != null ? `${availability.allocation_percent}%` : "—"}</span>
          </div>
          <p className="muted" style={{ fontSize: 12, marginTop: 12 }}>
            Client, project and allocation are set by your manager and can't be edited here.
          </p>
        </>
      ) : (
        <>
          <label>
            <input type="checkbox" checked={available} onChange={(e) => setAvailable(e.target.checked)} />
            Currently available
          </label>

          <label htmlFor="availability-status">Status</label>
          <select
            id="availability-status"
            value={status}
            onChange={(e) => setStatus(e.target.value as AvailabilityStatus)}
          >
            {STATUS_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>

          <label htmlFor="skill-set">Skill set</label>
          <input
            id="skill-set"
            type="text"
            value={skillSet}
            onChange={(e) => setSkillSet(e.target.value)}
            maxLength={1000}
          />

          {error && <p className="error-text">{error}</p>}

          <div className="row" style={{ marginTop: 16, justifyContent: "flex-end", gap: 8 }}>
            <button type="button" className="secondary" onClick={() => setEditing(false)} disabled={saving}>
              Cancel
            </button>
            <button type="button" onClick={handleSave} disabled={saving}>
              {saving ? "Saving…" : "Save"}
            </button>
          </div>
        </>
      )}
    </section>
  );
}
