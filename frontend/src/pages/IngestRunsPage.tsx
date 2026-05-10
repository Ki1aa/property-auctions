import { Fragment, useEffect, useState } from "react";
import { fetchIngestRuns, fetchIngestStatus, startIngestNow } from "../api";
import { StatusBadge } from "../components/StatusBadge";
import { IngestRun, IngestStatus } from "../types";

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

function intervalLabel(minutes: number): string {
  if (minutes >= 1440 && minutes % 1440 === 0) {
    const days = minutes / 1440;
    return days === 1 ? "раз в сутки" : `раз в ${days} дн.`;
  }
  if (minutes >= 60 && minutes % 60 === 0) {
    const hours = minutes / 60;
    return hours === 1 ? "раз в час" : `раз в ${hours} ч.`;
  }
  return `раз в ${minutes} мин.`;
}

function ingestRegionLabel(value: string | undefined): string {
  const cleaned = (value ?? "").trim();
  return cleaned ? `только ${cleaned}` : "все регионы";
}

function telegramRegionLabel(value: string | undefined): string {
  const cleaned = (value ?? "").trim();
  if (!cleaned) return "все регионы";
  if (cleaned === "72") return "только 72 (Тюменская область)";
  return `только ${cleaned}`;
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
    const shortenedPath = path.length > 76 ? `${path.slice(0, 73)}…` : path;
    return `${url.host}${shortenedPath}`;
  } catch {
    return value.length > 86 ? `${value.slice(0, 83)}…` : value;
  }
}

function friendlyError(run: IngestRun): { text: string; title?: string } {
  const message = run.error_message;
  if (!message) return { text: "—" };
  const m = message.trim();
  if (run.error_kind === "source_unavailable") {
    return {
      text: "Источник временно не отдал часть файлов: срез ещё не опубликован или недоступен. Попробуйте позже.",
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

function errorKindLabel(run: IngestRun): string {
  if (!run.error_kind) return run.error_message ? "Есть ошибка" : "—";
  return errorKindLabels[run.error_kind] ?? run.error_kind;
}

export function IngestRunsPage() {
  const [runs, setRuns] = useState<IngestRun[]>([]);
  const [status, setStatus] = useState<IngestStatus | null>(null);
  const [expandedRunId, setExpandedRunId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [startMessage, setStartMessage] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isStarting, setIsStarting] = useState(false);

  async function load() {
    try {
      setIsLoading(true);
      setError("");
      const [data, ingestStatus] = await Promise.all([fetchIngestRuns(50), fetchIngestStatus()]);
      setRuns(data);
      setStatus(ingestStatus);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setIsLoading(false);
    }
  }

  async function handleStart() {
    try {
      setIsStarting(true);
      setStartMessage("");
      setError("");
      const response = await startIngestNow();
      setStartMessage(response.message);
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setIsStarting(false);
    }
  }

  function toggleRunDetails(runId: number) {
    setExpandedRunId((current) => (current === runId ? null : runId));
  }

  useEffect(() => {
    void load();
  }, []);

  useEffect(() => {
    if (!status?.is_running) return undefined;
    const id = window.setInterval(() => {
      void load();
    }, 5000);
    return () => window.clearInterval(id);
  }, [status?.is_running]);

  return (
    <div className="page">
      <div className="page__heading">
        <h1>Загрузки данных</h1>
        <div className="page__actions">
          <button
            type="button"
            onClick={() => void handleStart()}
            disabled={isStarting || status?.is_running}
          >
            {status?.is_running ? "Загрузка идёт" : isStarting ? "Запускаю…" : "Запустить загрузку"}
          </button>
          <button className="button button--ghost" onClick={() => void load()} disabled={isLoading}>
            Обновить
          </button>
        </div>
      </div>
      <p className="page__subtitle">История последних 50 запусков ingest-пайплайна</p>

      {error && <p className="error">{error}</p>}
      {startMessage && <p className="notice">{startMessage}</p>}

      <section className="ingest-status">
        <div>
          <span className="ingest-status__label">Сейчас</span>
          <strong>{status?.is_running ? "идёт загрузка" : "не загружает"}</strong>
        </div>
        <div>
          <span className="ingest-status__label">Автоматически</span>
          <strong>
            {status
              ? status.scheduler_running
                ? intervalLabel(status.interval_minutes)
                : "планировщик выключен"
              : "—"}
          </strong>
        </div>
        <div>
          <span className="ingest-status__label">Следующий запуск</span>
          <strong>{status?.next_run_at ? formatDate(status.next_run_at) : "—"}</strong>
        </div>
        <div>
          <span className="ingest-status__label">Detail JSON</span>
          <strong>{status?.fetch_notice_details ? `включён, до ${status.detail_max_per_run}` : "выключен"}</strong>
        </div>
        <div>
          <span className="ingest-status__label">Регионы в интерфейсе</span>
          <strong>{status ? ingestRegionLabel(status.target_region_codes) : "—"}</strong>
        </div>
        <div>
          <span className="ingest-status__label">Типы лотов</span>
          <strong>{status?.ingest_only_land_lots ? "земельные участки" : "все типы"}</strong>
        </div>
        <div>
          <span className="ingest-status__label">Telegram-регионы</span>
          <strong>{status ? telegramRegionLabel(status.telegram_alert_region_codes) : "—"}</strong>
        </div>
        <div>
          <span className="ingest-status__label">Telegram digest</span>
          <strong>
            {status?.telegram_digest_enabled
              ? `вкл, каждые ${status.telegram_digest_interval_minutes} мин; следующий: ${
                  status.telegram_digest_next_at ? formatDate(status.telegram_digest_next_at) : "—"
                }`
              : "выкл"}
          </strong>
        </div>
      </section>

      <p className="help-text">
        Ручной запуск выполняет обычный operational-проход; подробности ошибок открываются в строках истории.
      </p>

      {isLoading ? (
        <p className="loading">Загрузка…</p>
      ) : runs.length === 0 ? (
        <p className="empty">Запусков пока не было.</p>
      ) : (
        <table className="table table--compact ingest-runs-table">
          <thead>
            <tr>
              <th className="cell--num ingest-runs-table__id">#</th>
              <th className="ingest-runs-table__status">Статус</th>
              <th className="cell--nowrap ingest-runs-table__started">Старт</th>
              <th className="cell--num ingest-runs-table__duration">Длительность</th>
              <th className="cell--num ingest-runs-table__count">Получено</th>
              <th className="cell--num ingest-runs-table__count">Сохранено</th>
              <th className="cell--num ingest-runs-table__count">Изменено</th>
              <th className="cell--num ingest-runs-table__files">Файлы</th>
              <th className="ingest-runs-table__failure">Сбой</th>
              <th className="ingest-runs-table__details">Детали</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run) => {
              const isExpanded = expandedRunId === run.id;
              const err = friendlyError(run);
              const detailRowId = `ingest-run-${run.id}-details`;
              const failureLabel = errorKindLabel(run);
              return (
                <Fragment key={run.id}>
                  <tr className={isExpanded ? "ingest-runs-table__row ingest-runs-table__row--expanded" : "ingest-runs-table__row"}>
                    <td className="cell--num">{run.id}</td>
                    <td>
                      <StatusBadge status={run.status} variant="ingest" />
                    </td>
                    <td className="cell--nowrap">{formatDate(run.started_at)}</td>
                    <td className="cell--num">{durationMs(run.started_at, run.finished_at)}</td>
                    <td className="cell--num">{run.fetched_count}</td>
                    <td className="cell--num">{run.upserted_count}</td>
                    <td className="cell--num">{run.changed_count}</td>
                    <td className="cell--num" title="Обработано / с ошибкой">
                      {run.processed_files} / {run.failed_files}
                    </td>
                    <td className="ingest-runs-table__failure-cell" title={failureLabel}>
                      {failureLabel}
                    </td>
                    <td>
                      <button
                        type="button"
                        className="button button--ghost button--compact ingest-runs-table__details-button"
                        aria-expanded={isExpanded}
                        aria-controls={detailRowId}
                        onClick={() => toggleRunDetails(run.id)}
                      >
                        {isExpanded ? "Скрыть" : "Детали"}
                      </button>
                    </td>
                  </tr>
                  {isExpanded && (
                    <tr id={detailRowId} className="ingest-runs-table__details-row">
                      <td colSpan={10}>
                        <div className="ingest-run-details">
                          <div className="ingest-run-details__grid">
                            <div>
                              <span>Финиш</span>
                              <strong>{formatDate(run.finished_at)}</strong>
                            </div>
                            <div>
                              <span>Тип сбоя</span>
                              <strong>{failureLabel}</strong>
                            </div>
                            <div>
                              <span>Файлы</span>
                              <strong>
                                {run.processed_files} обработано / {run.failed_files} с ошибкой
                              </strong>
                            </div>
                          </div>

                          {run.last_error_source_url && (
                            <div className="ingest-run-details__block">
                              <span>Последний URL ошибки</span>
                              <a
                                className="cell--mono ingest-run-details__url"
                                href={run.last_error_source_url}
                                target="_blank"
                                rel="noreferrer"
                                title={run.last_error_source_url}
                              >
                                {shortUrl(run.last_error_source_url)}
                              </a>
                            </div>
                          )}

                          {err.text !== "—" && (
                            <div className="ingest-run-details__block">
                              <span>Ошибка</span>
                              <p className="ingest-run-details__error" title={err.title ?? undefined}>
                                {err.text}
                              </p>
                            </div>
                          )}
                        </div>
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}
