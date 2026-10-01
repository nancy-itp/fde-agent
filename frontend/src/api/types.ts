// Mirrors backend/app/employee_profile/schemas.py and backend/app/auth/schemas.py.

export type EmployeeRole = "Employee" | "Manager" | "Admin";

export type AvailabilityStatus = "Available" | "Unavailable" | "PartiallyAvailable";

export type ReviewCycleStatus = "Draft" | "Open" | "Closed";

export interface EmployeeProfile {
  employee_id: number;
  name: string;
  email: string;
  role: EmployeeRole;
  skills: string | null;
  availability_status: AvailabilityStatus | null;
}

export interface Availability {
  employee_id: number;
  available: boolean;
  skill_set: string | null;
  client_name: string | null;
  project_name: string | null;
  allocation_percent: number | null;
}

export interface AvailabilityUpdate {
  available?: boolean;
  skill_set?: string;
  availability_status?: AvailabilityStatus;
  skills?: string;
}

export interface ReviewCycle {
  cycle_id: number;
  cycle_start: string;
  cycle_end: string;
  status: ReviewCycleStatus;
}

export interface PerformanceScore {
  score_id: number;
  cycle_id: number;
  dimension_name: string;
  score: number;
  confidence: number | null;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}
