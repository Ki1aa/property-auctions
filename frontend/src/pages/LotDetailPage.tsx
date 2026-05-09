import { lazy, Suspense, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { fetchLot } from "../api";
import { StatusBadge } from "../components/StatusBadge";
import { LotDetail, MapPoint } from "../types";
import { pkkMapUrl } from "../utils/links";

const TradesMap = lazy(() =>
  import("../components/TradesMap").then((module) => ({ default: module.TradesMap }))
);

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

function formatPercent(value: number | null): string {
  if (value === null || value === undefined) return "—";
  return `${(value * 100).toFixed(1)}%`;
}

function confidenceLabel(value: string | null): string {
  if (value === "high") return "Высокая";
  if (value === "medium") return "Средняя";
  if (value === "low") return "Низкая";
  return "—";
}

function izhsReason(lot: LotDetail): string {
  if (lot.is_izhs_candidate && lot.permitted_use_codes) {
    return `Да, по коду ВРИ: ${lot.permitted_use_codes}.`;
  }
  if (lot.is_izhs_candidate) {
    return "Да, по текстовому fallback из извещения.";
  }
  if (lot.permitted_use_codes) {
    return `Нет, коды ВРИ не входят в ИЖС-whitelist: ${lot.permitted_use_codes}.`;
  }
  return "Нет, код ВРИ не найден в извещении.";
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

  const pkkHref = lot.pkk_map_url ?? pkkMapUrl(lot.cadastral_number);
  const jsonNoticeHref = lot.torgi_json_url || lot.notice_detail_url || lot.source_url;

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

      <section className="section">
        <h2>Ссылки</h2>
        <div className="card">
          <div className="card__row">
            <span className="card__label">В приложении</span>
            <span>
              <Link to={`/lots/${lot.id}`}>Карточка в мониторе</Link>
            </span>
          </div>
          {lot.app_lot_url ? (
            <div className="card__row">
              <span className="card__label">Публичный URL</span>
              <span>
                <a href={lot.app_lot_url} target="_blank" rel="noreferrer">
                  {lot.app_lot_url}
                </a>
              </span>
            </div>
          ) : null}
          {lot.torgi_url ? (
            <div className="card__row">
              <span className="card__label">ГИС Торги</span>
              <span>
                <a href={lot.torgi_url} target="_blank" rel="noreferrer">
                  Открыть извещение
                </a>
              </span>
            </div>
          ) : null}
          {lot.torgi_json_url ? (
            <div className="card__row">
              <span className="card__label">JSON извещения</span>
              <span>
                <a href={lot.torgi_json_url} target="_blank" rel="noreferrer">
                  Скачать / открыть JSON
                </a>
              </span>
            </div>
          ) : jsonNoticeHref && jsonNoticeHref !== lot.torgi_url ? (
            <div className="card__row">
              <span className="card__label">JSON извещения</span>
              <span>
                <a href={jsonNoticeHref} target="_blank" rel="noreferrer">
                  Скачать / открыть JSON
                </a>
              </span>
            </div>
          ) : null}
          {pkkHref ? (
            <div className="card__row">
              <span className="card__label">ПКК Росреестра</span>
              <span>
                <a href={pkkHref} target="_blank" rel="noreferrer">
                  Публичная кадастровая карта
                </a>
              </span>
            </div>
          ) : null}
          {lot.domclick_search_url_cadastral ? (
            <div className="card__row">
              <span className="card__label">Домклик (кадастр)</span>
              <span>
                <a href={lot.domclick_search_url_cadastral} target="_blank" rel="noreferrer">
                  Поиск по кадастровому номеру
                </a>
              </span>
            </div>
          ) : null}
          {lot.domclick_search_url ? (
            <div className="card__row">
              <span className="card__label">Домклик (расширенный)</span>
              <span>
                <a href={lot.domclick_search_url} target="_blank" rel="noreferrer">
                  Поиск участков (оценочно)
                </a>
              </span>
            </div>
          ) : null}
          {lot.avito_search_url_cadastral ? (
            <div className="card__row">
              <span className="card__label">Авито (кадастр)</span>
              <span>
                <a href={lot.avito_search_url_cadastral} target="_blank" rel="noreferrer">
                  Поиск по кадастровому номеру
                </a>
              </span>
            </div>
          ) : null}
          {lot.avito_search_url ? (
            <div className="card__row">
              <span className="card__label">Авито (расширенный)</span>
              <span>
                <a href={lot.avito_search_url} target="_blank" rel="noreferrer">
                  Поиск участков (оценочно)
                </a>
              </span>
            </div>
          ) : null}
          {lot.cian_search_url_cadastral ? (
            <div className="card__row">
              <span className="card__label">Циан (кадастр)</span>
              <span>
                <a href={lot.cian_search_url_cadastral} target="_blank" rel="noreferrer">
                  Поиск по кадастровому номеру
                </a>
              </span>
            </div>
          ) : null}
          {lot.cian_search_url ? (
            <div className="card__row">
              <span className="card__label">Циан (расширенный)</span>
              <span>
                <a href={lot.cian_search_url} target="_blank" rel="noreferrer">
                  Поиск участков (оценочно)
                </a>
              </span>
            </div>
          ) : null}
          {(lot.domclick_search_url ||
            lot.domclick_search_url_cadastral ||
            lot.avito_search_url ||
            lot.avito_search_url_cadastral ||
            lot.cian_search_url ||
            lot.cian_search_url_cadastral) && (
            <p className="card__footnote">
              Ссылки на Домклик, Авито и Циан ведут в общий текстовый поиск (кадастр и/или адрес); это не официальная
              карточка участка и не оценка рынка.
            </p>
          )}
        </div>
      </section>

      <section className="card">
        <div className="card__row"><span className="card__label">Регион</span><span>{lot.region || "—"}</span></div>
        <div className="card__row"><span className="card__label">Муниципалитет</span><span>{lot.municipality || "—"}</span></div>
        <div className="card__row"><span className="card__label">Населённый пункт</span><span>{lot.settlement || "—"}</span></div>
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
        <div className="card__row">
          <span className="card__label">Baseline за сотку</span>
          <span title="Медиана по уже загруженным торгам, не внешняя рыночная оценка">
            {formatPrice(lot.baseline_price_per_sotka)}
          </span>
        </div>
        <div className="card__row">
          <span className="card__label">Дисконт к baseline</span>
          <span className={lot.discount_to_baseline && lot.discount_to_baseline > 0 ? "cell--good" : ""}>
            {formatPercent(lot.discount_to_baseline)}
          </span>
        </div>
        <div className="card__row">
          <span className="card__label">Уверенность оценки</span>
          <span>{confidenceLabel(lot.valuation_confidence)}</span>
        </div>
        <div className="card__row">
          <span className="card__label">Основание baseline</span>
          <span>{lot.valuation_reason || "—"}</span>
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
                {lot.cadastral_number && pkkHref ? (
                  <a href={pkkHref} target="_blank" rel="noreferrer">{lot.cadastral_number}</a>
                ) : (
                  lot.cadastral_number || "—"
                )}
              </span>
            </div>
            <div className="card__row"><span className="card__label">Площадь</span><span>{formatArea(lot.area_sqm)}</span></div>
            <div className="card__row"><span className="card__label">Категория земель</span><span>{lot.land_category || "—"}</span></div>
            <div className="card__row"><span className="card__label">ВРИ (вид разрешённого использования)</span><span>{lot.permitted_use || "—"}</span></div>
            <div className="card__row"><span className="card__label">Коды ВРИ</span><span>{lot.permitted_use_codes || "—"}</span></div>
            <div className="card__row"><span className="card__label">ИЖС-кандидат</span><span>{izhsReason(lot)}</span></div>
            <div className="card__row"><span className="card__label">Адрес</span><span>{lot.address || "—"}</span></div>
            {pkkHref ? (
              <div className="card__row">
                <span className="card__label">Публичная кадастровая карта</span>
                <span><a href={pkkHref} target="_blank" rel="noreferrer">Открыть на ПКК Росреестра</a></span>
              </div>
            ) : null}
          </div>
        </section>
      )}

      {(lot.nspd_enriched_at ||
        lot.nspd_specified_area_sqm != null ||
        lot.nspd_readable_address ||
        lot.nspd_cost_value != null ||
        lot.nspd_centroid_latitude != null) && (
        <section className="section">
          <h2>НСПД (геопортал)</h2>
          <p className="card__footnote" style={{ marginBottom: 12 }}>
            Данные из nspd.gov.ru при включённом загрузчиком флаге NSPD_ENABLED. Не заменяют поля из извещения без
            отдельной политики слияния.
          </p>
          <div className="card">
            <div className="card__row">
              <span className="card__label">Площадь по НСПД</span>
              <span>{lot.nspd_specified_area_sqm != null ? formatArea(lot.nspd_specified_area_sqm) : "—"}</span>
            </div>
            <div className="card__row">
              <span className="card__label">Адрес (читаемый)</span>
              <span>{lot.nspd_readable_address || "—"}</span>
            </div>
            <div className="card__row">
              <span className="card__label">Кадастровая стоимость</span>
              <span>{formatPrice(lot.nspd_cost_value)}</span>
            </div>
            <div className="card__row">
              <span className="card__label">Центроид полигона (WGS84)</span>
              <span>
                {lot.nspd_centroid_latitude != null && lot.nspd_centroid_longitude != null
                  ? `${lot.nspd_centroid_latitude.toFixed(6)}, ${lot.nspd_centroid_longitude.toFixed(6)}`
                  : "—"}
              </span>
            </div>
            <div className="card__row">
              <span className="card__label">Обновлено из НСПД</span>
              <span>{lot.nspd_enriched_at ? formatDate(lot.nspd_enriched_at) : "—"}</span>
            </div>
          </div>
        </section>
      )}

      {mapPoint && (
        <section className="section">
          <h2>На карте</h2>
          <Suspense fallback={<p className="loading">Загрузка карты…</p>}>
            <TradesMap points={[mapPoint]} height="320px" />
          </Suspense>
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
