import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { fetchLot } from "../api";
import { StatusBadge } from "../components/StatusBadge";
import { TradesMap } from "../components/TradesMap";
import { LotDetail, MapPoint } from "../types";

function formatPrice(value: number | null): string {
  if (value === null || value === undefined) return "—";
  return new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 0 }).format(value) + " ₽";
}

function formatArea(value: number | null): string {
  if (value === null || value === undefined) return "—";
  if (value >= 10000) {
    return `${(value / 10000).toFixed(2)} га (${new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 0 }).format(value)} м²)`;
  }
  return `${new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 0 }).format(value)} м²`;
}

function formatDate(value: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleString("ru-RU");
}

function pkkLink(cadastral: string | null): string | null {
  if (!cadastral) return null;
  return `https://pkk.rosreestr.ru/#/search/${encodeURIComponent(cadastral)}/?text=${encodeURIComponent(cadastral)}`;
}

export function LotDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [lot, setLot] = useState<LotDetail | null>(null);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    async function load() {
      setIsLoading(true);
      try {
        const data = await fetchLot(id!);
        if (!cancelled) setLot(data);
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
  }, [id]);

  if (isLoading) {
    return (
      <div className="page">
        <p className="loading">Загрузка карточки лота…</p>
      </div>
    );
  }

  if (error || !lot) {
    return (
      <div className="page">
        <Link to="/lots" className="back-link">← К списку лотов</Link>
        <p className="error">{error || "Лот не найден"}</p>
      </div>
    );
  }

  const mapPoint: MapPoint | null =
    lot.latitude !== null && lot.longitude !== null
      ? { lot_id: lot.id, title: lot.title, status: lot.status, latitude: lot.latitude, longitude: lot.longitude }
      : null;

  const hasLandSection =
    lot.cadastral_number || lot.area_sqm !== null || lot.land_category || lot.permitted_use || lot.address;

  return (
    <div className="page">
      <Link to="/lots" className="back-link">← К списку лотов</Link>

      <div className="page__heading">
        <h1>{lot.title}</h1>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          {lot.is_izhs_candidate && <span className="badge badge--success">ИЖС</span>}
          <StatusBadge status={lot.status} />
        </div>
      </div>
      <p className="page__subtitle">ID источника: {lot.source_id}</p>

      <section className="card">
        <div className="card__row"><span className="card__label">Регион</span><span>{lot.region || "—"}</span></div>
        <div className="card__row"><span className="card__label">Категория</span><span>{lot.category || "—"}</span></div>
        <div className="card__row"><span className="card__label">Стартовая цена</span><span>{formatPrice(lot.start_price)}</span></div>
        <div className="card__row"><span className="card__label">Текущая цена</span><span>{formatPrice(lot.current_price)}</span></div>
        <div className="card__row">
          <span className="card__label">Старт. цена за сотку</span>
          <span title="100 м²; из извещения, не рыночная оценка">{formatPrice(lot.start_price_per_sotka)}</span>
        </div>
        <div className="card__row">
          <span className="card__label">Старт. цена за м²</span>
          <span title="Из извещения, не рыночная оценка">{formatPrice(lot.start_price_per_sqm)}</span>
        </div>
        <div className="card__row"><span className="card__label">Дата начала</span><span>{formatDate(lot.start_date)}</span></div>
        <div className="card__row"><span className="card__label">Дата окончания</span><span>{formatDate(lot.end_date)}</span></div>
        <div className="card__row"><span className="card__label">Организатор</span><span>{lot.organizer_name || "—"}</span></div>
        <div className="card__row"><span className="card__label">ИНН организатора</span><span>{lot.organizer_inn || "—"}</span></div>
        <div className="card__row">
          <span className="card__label">Источник</span>
          <span>
            {lot.source_url ? (
              <a href={lot.source_url} target="_blank" rel="noreferrer">Открыть JSON</a>
            ) : (
              "—"
            )}
          </span>
        </div>
      </section>

      {hasLandSection && (
        <section className="section">
          <h2>Кадастр и земля</h2>
          <div className="card">
            <div className="card__row">
              <span className="card__label">Кадастровый номер</span>
              <span className="cell--mono">
                {lot.cadastral_number ? (
                  <a href={pkkLink(lot.cadastral_number)!} target="_blank" rel="noreferrer">{lot.cadastral_number}</a>
                ) : (
                  "—"
                )}
              </span>
            </div>
            <div className="card__row"><span className="card__label">Площадь</span><span>{formatArea(lot.area_sqm)}</span></div>
            <div className="card__row"><span className="card__label">Категория земель</span><span>{lot.land_category || "—"}</span></div>
            <div className="card__row"><span className="card__label">ВРИ (вид разрешённого использования)</span><span>{lot.permitted_use || "—"}</span></div>
            <div className="card__row"><span className="card__label">Адрес</span><span>{lot.address || "—"}</span></div>
            {lot.cadastral_number && (
              <div className="card__row">
                <span className="card__label">Публичная кадастровая карта</span>
                <span><a href={pkkLink(lot.cadastral_number)!} target="_blank" rel="noreferrer">Открыть на ПКК Росреестра</a></span>
              </div>
            )}
          </div>
        </section>
      )}

      {mapPoint && (
        <section className="section">
          <h2>На карте</h2>
          <TradesMap points={[mapPoint]} height="320px" />
        </section>
      )}

      {lot.notice_payload && (
        <section className="section">
          <h2>Сырое извещение (opendata)</h2>
          <details className="raw-notice">
            <summary>
              Открыть полный JSON{lot.opendata_notice_id ? ` (notice id ${lot.opendata_notice_id})` : ""}
            </summary>
            <pre className="raw-notice__pre">
              {JSON.stringify(lot.notice_payload, null, 2)}
            </pre>
          </details>
        </section>
      )}
    </div>
  );
}
