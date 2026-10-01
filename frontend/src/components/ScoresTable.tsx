import type { PerformanceScore } from "../api/types";

export function ScoresTable({ scores }: { scores: PerformanceScore[] }) {
  return (
    <section className="card">
      <h2>Scores this cycle</h2>
      {scores.length === 0 ? (
        <p className="muted">No scores recorded yet for this cycle.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Dimension</th>
              <th>Score</th>
              <th>Confidence</th>
            </tr>
          </thead>
          <tbody>
            {scores.map((score) => (
              <tr key={score.score_id}>
                <td>{score.dimension_name}</td>
                <td>{score.score}</td>
                <td>{score.confidence != null ? `${Math.round(score.confidence * 100)}%` : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
