import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchIngestRuns, fetchLotQualityMetrics, fetchLots, fetchNotices } from "../api";
import { StatusBadge } from "../components/StatusBadge";
import { IngestRun, Lot, LotQualityMetrics, Notice } from "../types";

type Metrics = {
  lotsCount: number | null;
  noticesCount: number | null;
  lastRun: IngestRun | null;
  quality: LotQualityMetrics | null;
};

const initialMetrics: Metrics = { lotsCount: null, noticesCount: null, lastRun: null, quality: null };

function formatDate(value: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleString("ru-RU");
}

function formatPrice(value: number | null): string {
  if (value === null || value === undefined) return "—";
  return new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 0 }).format(value) + " ₽";
}

function formatPercent(value: number | null): string {
  if (value === null || value === undefined) return "—";
  return `${(value * 100).toFixed(1)}%`;
}

function formatShare(value: number, total: number): string {
  if (total <= 0) return "—";
  return `${Math.round((value / total) * 100)}%`;
}

function qualityItems(quality: LotQualityMetrics | null) {
  if (!quality) return [];
  return [
    ["ИЖС-кандидаты", quality.izhs_candidates],
    ["Есть муниципалитет", quality.with_municipality],
    ["Есть кадастр", quality.with_cadastral],
    ["Есть площадь", quality.with_area],
    ["Есть стартовая цена", quality.with_start_price],
    ["Можно считать ₽/сотка", quality.with_price_per_sotka],
    ["Есть baseline", quality.with_baseline],
    ["Положительный дисконт", quality.with_positive_discount],
    ["НСПД: данные найдены", quality.with_nspd_enriched],
    ["Есть центроид для карты", quality.with_map_centroid],
  ] as const;
}

export function DashboardPage() {
  const [metrics, setMetrics] = useState<Metrics>(initialMetrics);
  const [recentNotices, setRecentNotices] = useState<Notice[]>([]);
  const [recentLots, setRecentLots] = useState<Lot[]>([]);
  const [opportunityLots, setOpportunityLots] = useState<Lot[]>([]);
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
        const [lotsPage, noticesPage, runs, quality, opportunitiesPage] = await Promise.all([
          fetchLots({ limit: 5, offset: 0 }),
          fetchNotices({ limit: 5, offset: 0 }),
          fetchIngestRuns(1),
          fetchLotQualityMetrics("72"),
          fetchLots({
            limit: 10,
            offset: 0,
            region: "72",
            isIzhs: true,
            sort: "discount_to_baseline_desc",
          }),
        ]);
        if (cancelled) return;
        setMetrics({
          lotsCount: normalizePageTotal(lotsPage) ?? (lotsPage as { total: number }).total,
          noticesCount: normalizePageTotal(noticesPage) ?? (noticesPage as { total: number }).total,
          lastRun: runs[0] ?? null,
          quality,
        });
        setRecentNotices(normalizePageItems<Notice>(noticesPage));
        setRecentLots(normalizePageItems<Lot>(lotsPage));
        setOpportunityLots(
          normalizePageItems<Lot>(opportunitiesPage)
            .filter((lot) => lot.discount_to_baseline !== null)
            .slice(0, 5)
        );
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
          <h2>Качество данных по Тюменской области</h2>
          <Link to="/lots?region=72" className="section__more">Лоты региона →</Link>
        </div>
        {!metrics.quality && !isLoading ? (
          <p className="empty">Метрики качества пока недоступны. Проверьте, что backend запущен и БД создана.</p>
        ) : (
          <div className="quality-grid">
            {qualityItems(metrics.quality).map(([label, value]) => (
              <div className="quality-tile" key={label}>
                <div className="quality-tile__top">
                  <span>{label}</span>
                  <strong>{isLoading ? "…" : value}</strong>
                </div>
                <div className="quality-tile__bar" aria-hidden="true">
                  <span
                    style={{
                      width: metrics.quality ? `${Math.min(100, Math.round((value / Math.max(1, metrics.quality.total)) * 100))}%` : "0%",
                    }}
                  />
                </div>
                <small>{metrics.quality ? formatShare(value, metrics.quality.total) : "—"} от {metrics.quality?.total ?? "—"}</small>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="section">
        <div className="section__header">
          <h2>Потенциально интересные ИЖС-кандидаты по всей базе</h2>
          <Link to="/lots?is_izhs=true&sort=discount_to_baseline_desc" className="section__more">Все →</Link>
        </div>
        {opportunityLots.length === 0 && !isLoading ? (
          <p className="empty">Пока нет ИЖС-кандидатов с достаточными данными для baseline.</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Лот</th>
                <th>Регион</th>
                <th className="cell--num">₽/сотка</th>
                <th className="cell--num">Baseline</th>
                <th className="cell--num">Дисконт</th>
                <th>Основание</th>
              </tr>
            </thead>
            <tbody>
              {opportunityLots.map((lot) => (
                <tr key={lot.id}>
                  <td className="cell--name">
                    <Link to={`/lots/${lot.id}`}>{lot.title}</Link>
                  </td>
                  <td>{lot.region || "—"}</td>
                  <td className="cell--num">{formatPrice(lot.start_price_per_sotka)}</td>
                  <td className="cell--num">{formatPrice(lot.baseline_price_per_sotka)}</td>
                  <td className={lot.discount_to_baseline && lot.discount_to_baseline > 0 ? "cell--num cell--good" : "cell--num"}>
                    {formatPercent(lot.discount_to_baseline)}
                  </td>
                  <td>{lot.valuation_reason || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
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
