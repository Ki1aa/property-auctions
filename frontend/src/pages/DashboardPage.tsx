import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchIngestRuns, fetchLots, fetchNotices } from "../api";
import { StatusBadge } from "../components/StatusBadge";
import { IngestRun, Lot, Notice } from "../types";

type Metrics = {
  lotsCount: number | null;
  noticesCount: number | null;
  lastRun: IngestRun | null;
};

const initialMetrics: Metrics = { lotsCount: null, noticesCount: null, lastRun: null };

function formatDate(value: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleString("ru-RU");
}

export function DashboardPage() {
  const [metrics, setMetrics] = useState<Metrics>(initialMetrics);
  const [recentNotices, setRecentNotices] = useState<Notice[]>([]);
  const [recentLots, setRecentLots] = useState<Lot[]>([]);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    function normalizePageItems<T>(value: unknown): T[] {
      if (Array.isArray(value)) return value as T[];
      if (value && typeof value === "object" && Array.isArray((value as { items?: unknown }).items)) {
        return (value as { items: T[] }).items;
      }
      return [];
    }

    function normalizePageTotal(value: unknown): number | null {
      if (value && typeof value === "object" && typeof (value as { total?: unknown }).total === "number") {
        return (value as { total: number }).total;
      }
      return null;
    }

    async function load() {
      setIsLoading(true);
      try {
        const [lotsPage, noticesPage, runs] = await Promise.all([
          fetchLots({ limit: 5, offset: 0 }),
          fetchNotices({ limit: 5, offset: 0 }),
          fetchIngestRuns(1),
        ]);
        if (cancelled) return;
        setMetrics({
          lotsCount: normalizePageTotal(lotsPage) ?? (lotsPage as { total: number }).total,
          noticesCount: normalizePageTotal(noticesPage) ?? (noticesPage as { total: number }).total,
          lastRun: runs[0] ?? null,
        });
        setRecentNotices(normalizePageItems<Notice>(noticesPage));
        setRecentLots(normalizePageItems<Lot>(lotsPage));
        setError("");
      } catch (e) {
        if (!cancelled) setError((e as Error).message);
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="page">
      <h1>Сводка</h1>

      {error && <p className="error">{error}</p>}

      <section className="dashboard">
        <div className="metric">
          <span className="metric__label">Лотов в базе</span>
          <span className="metric__value">{isLoading ? "…" : metrics.lotsCount ?? "—"}</span>
          <Link className="metric__link" to="/lots">Перейти к списку →</Link>
        </div>
        <div className="metric">
          <span className="metric__label">Извещений в базе</span>
          <span className="metric__value">{isLoading ? "…" : metrics.noticesCount ?? "—"}</span>
          <Link className="metric__link" to="/notices">Все извещения →</Link>
        </div>
        <div className="metric">
          <span className="metric__label">Последняя загрузка</span>
          <span className="metric__value metric__value--small">
            {metrics.lastRun ? <StatusBadge status={metrics.lastRun.status} variant="ingest" /> : isLoading ? "…" : "—"}
          </span>
          <span className="metric__sub">{metrics.lastRun ? formatDate(metrics.lastRun.finished_at ?? metrics.lastRun.started_at) : ""}</span>
          <Link className="metric__link" to="/ingest">История загрузок →</Link>
        </div>
      </section>

      <section className="section">
        <div className="section__header">
          <h2>Последние извещения</h2>
          <Link to="/notices" className="section__more">Все →</Link>
        </div>
        {recentNotices.length === 0 && !isLoading ? (
          <p className="empty">Извещений пока нет.</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Реестровый номер</th>
                <th>Тип</th>
                <th>Вид торгов</th>
                <th>Дата публикации</th>
              </tr>
            </thead>
            <tbody>
              {recentNotices.map((notice) => (
                <tr key={notice.id}>
                  <td className="cell--mono cell--nowrap">{notice.reg_num}</td>
                  <td><StatusBadge status={notice.document_type} /></td>
                  <td>{notice.bidd_type_code || "—"}</td>
                  <td className="cell--nowrap">{formatDate(notice.publish_date)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section className="section">
        <div className="section__header">
          <h2>Последние лоты</h2>
          <Link to="/lots" className="section__more">Все →</Link>
        </div>
        {recentLots.length === 0 && !isLoading ? (
          <p className="empty">Лотов пока нет.</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Название</th>
                <th>Статус</th>
                <th>Регион</th>
                <th>Категория</th>
              </tr>
            </thead>
            <tbody>
              {recentLots.map((lot) => (
                <tr key={lot.id}>
                  <td className="cell--name">
                    <Link to={`/lots/${lot.id}`}>{lot.title}</Link>
                  </td>
                  <td><StatusBadge status={lot.status} /></td>
                  <td>{lot.region || "—"}</td>
                  <td>{lot.category || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
