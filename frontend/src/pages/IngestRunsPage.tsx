import { useEffect, useState } from "react";
import { fetchIngestRuns } from "../api";
import { StatusBadge } from "../components/StatusBadge";
import { IngestRun } from "../types";

function formatDate(value: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleString("ru-RU");
}

function durationMs(started: string | null, finished: string | null): string {
  if (!started || !finished) return "—";
  const ms = new Date(finished).getTime() - new Date(started).getTime();
  if (Number.isNaN(ms) || ms < 0) return "—";
  if (ms < 1000) return `${ms} мс`;
  const sec = ms / 1000;
  if (sec < 60) return `${sec.toFixed(1)} с`;
  const min = sec / 60;
  return `${min.toFixed(1)} мин`;
}

export function IngestRunsPage() {
  const [runs, setRuns] = useState<IngestRun[]>([]);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  async function load() {
    try {
      setIsLoading(true);
      setError("");
      const data = await fetchIngestRuns(50);
      setRuns(data);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  return (
    <div className="page">
      <div className="page__heading">
        <h1>Загрузки данных</h1>
        <button className="button button--ghost" onClick={() => void load()} disabled={isLoading}>
          Обновить
        </button>
      </div>
      <p className="page__subtitle">История последних 50 запусков ingest-пайплайна</p>

      {error && <p className="error">{error}</p>}
      {isLoading ? (
        <p className="loading">Загрузка…</p>
      ) : runs.length === 0 ? (
        <p className="empty">Запусков пока не было.</p>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>#</th>
              <th>Статус</th>
              <th>Старт</th>
              <th>Финиш</th>
              <th>Длительность</th>
              <th>Получено</th>
              <th>Сохранено</th>
              <th>Изменено</th>
              <th>Ошибка</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run) => (
              <tr key={run.id}>
                <td>{run.id}</td>
                <td><StatusBadge status={run.status} variant="ingest" /></td>
                <td>{formatDate(run.started_at)}</td>
                <td>{formatDate(run.finished_at)}</td>
                <td>{durationMs(run.started_at, run.finished_at)}</td>
                <td>{run.fetched_count}</td>
                <td>{run.upserted_count}</td>
                <td>{run.changed_count}</td>
                <td className="cell--error">{run.error_message || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
