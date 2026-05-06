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

const errorKindLabels: Record<string, string> = {
  source_unavailable: "Источник недоступен",
  schema_migration_required: "Новая схема",
  file_processing_error: "Ошибка файла",
  interrupted: "Прервано",
};

function shortUrl(value: string | null): string {
  if (!value) return "—";
  try {
    const url = new URL(value);
    const path = `${url.pathname}${url.search}`;
    const shortenedPath = path.length > 46 ? `${path.slice(0, 43)}…` : path;
    return `${url.host}${shortenedPath}`;
  } catch {
    return value.length > 56 ? `${value.slice(0, 53)}…` : value;
  }
}

function friendlyError(run: IngestRun): { text: string; title?: string } {
  const message = run.error_message;
  if (!message) return { text: "—" };
  const m = message.trim();
  if (run.error_kind === "source_unavailable") {
    return {
      text: "Источник временно не отдал часть файлов (срез еще не опубликован/недоступен). Попробуйте позже.",
      title: m,
    };
  }
  if (run.error_kind === "schema_migration_required") {
    return {
      text: "Источник прислал неподдерживаемую структуру данных. Нужна миграция схемы.",
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
              <th className="cell--num">Файлы</th>
              <th>Тип сбоя</th>
              <th className="ingest-runs__url-col">Последний URL ошибки</th>
              <th className="ingest-runs__error-col">Ошибка</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run) => {
              const err = friendlyError(run);
              const errorKindLabel = run.error_kind ? errorKindLabels[run.error_kind] ?? run.error_kind : "—";
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
                  <td className="cell--num" title="Обработано / с ошибкой">
                    {run.processed_files} / {run.failed_files}
                  </td>
                  <td>{errorKindLabel}</td>
                  <td className="cell--mono ingest-runs__url-col" title={run.last_error_source_url ?? undefined}>
                    {run.last_error_source_url ? (
                      <a href={run.last_error_source_url} target="_blank" rel="noreferrer">
                        {shortUrl(run.last_error_source_url)}
                      </a>
                    ) : (
                      "—"
                    )}
                  </td>
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
