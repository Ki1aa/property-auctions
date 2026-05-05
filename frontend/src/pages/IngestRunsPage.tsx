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

function friendlyError(status: string, message: string | null): { text: string; title?: string } {
  if (!message) return { text: "—" };
  const m = message.trim();
  if (status === "partial_failed" && m.toLowerCase().startsWith("files processed=")) {
    return {
      text: "Источник временно не отдал часть файлов (срез еще не опубликован/недоступен). Попробуйте позже.",
      title: m,
    };
  }
  if (status === "failed" && m.toLowerCase().includes("torgi opendata:")) {
    return {
      text: "Источник Torgi вернул ошибку по данным (файл недоступен или еще не опубликован). Попробуйте позже.",
      title: m,
    };
  }
  return { text: m };
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
              <th className="cell--num">#</th>
              <th>Статус</th>
              <th className="cell--nowrap">Старт</th>
              <th className="cell--nowrap">Финиш</th>
              <th className="cell--num">Длительность</th>
              <th className="cell--num">Получено</th>
              <th className="cell--num">Сохранено</th>
              <th className="cell--num">Изменено</th>
              <th className="ingest-runs__error-col">Ошибка</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run) => {
              const err = friendlyError(run.status, run.error_message);
              return (
                <tr key={run.id}>
                  <td className="cell--num">{run.id}</td>
                  <td>
                    <StatusBadge status={run.status} variant="ingest" />
                  </td>
                  <td className="cell--nowrap">{formatDate(run.started_at)}</td>
                  <td className="cell--nowrap">{formatDate(run.finished_at)}</td>
                  <td className="cell--num">{durationMs(run.started_at, run.finished_at)}</td>
                  <td className="cell--num">{run.fetched_count}</td>
                  <td className="cell--num">{run.upserted_count}</td>
                  <td className="cell--num">{run.changed_count}</td>
                  <td className="cell--error ingest-runs__error-col" title={err.title ?? undefined}>
                    {err.text}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}
