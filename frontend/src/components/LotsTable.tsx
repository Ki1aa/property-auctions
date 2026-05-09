import { Link } from "react-router-dom";
import { Lot } from "../types";
import { StatusBadge } from "./StatusBadge";
import { pkkMapUrl } from "../utils/links";

type Props = {
  lots: Lot[];
};

function formatPrice(value: number | null): string {
  if (value === null || value === undefined) return "—";
  return new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 0 }).format(value) + " ₽";
}

function formatArea(value: number | null): string {
  if (value === null || value === undefined) return "—";
  if (value >= 10000) {
    return `${(value / 10000).toFixed(2)} га`;
  }
  return `${new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 0 }).format(value)} м²`;
}

function formatDateTime(value: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleString("ru-RU", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
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

function LotLinksCell({ lot }: { lot: Lot }) {
  const pkk = lot.pkk_map_url ?? pkkMapUrl(lot.cadastral_number);
  const external: { href: string; label: string }[] = [];
  if (lot.app_lot_url) external.push({ href: lot.app_lot_url, label: "Публичный URL" });
  if (lot.torgi_url) external.push({ href: lot.torgi_url, label: "ГИС Торги" });
  if (pkk) external.push({ href: pkk, label: "ПКК" });
  if (lot.domclick_search_url) external.push({ href: lot.domclick_search_url, label: "Домклик" });
  if (lot.avito_search_url) external.push({ href: lot.avito_search_url, label: "Авито" });
  return (
    <div className="lots-table__links">
      <Link to={`/lots/${lot.id}`} className="lots-table__ext-link">
        В приложении
      </Link>
      {external.map(({ href, label }) => (
        <a key={label} className="lots-table__ext-link" href={href} target="_blank" rel="noreferrer">
          {label}
        </a>
      ))}
    </div>
  );
}

export function LotsTable({ lots }: Props) {
  if (lots.length === 0) {
    return <p className="empty">Лотов по фильтрам не найдено.</p>;
  }
  return (
    <table className="table lots-table">
      <thead>
        <tr>
          <th className="lots-table__lot-col">Лот</th>
          <th className="lots-table__status-col">Статус / регион</th>
          <th className="lots-table__area-col">Площадь</th>
          <th className="lots-table__price-col">Цена</th>
          <th className="lots-table__baseline-col">Baseline</th>
          <th className="lots-table__confidence-col">Уверенность</th>
          <th className="lots-table__date-col">Даты торгов</th>
          <th className="lots-table__links-col">Ссылки</th>
        </tr>
      </thead>
      <tbody>
        {lots.map((lot) => {
          const discountClass =
            lot.discount_to_baseline && lot.discount_to_baseline > 0
              ? "lots-table__subvalue lots-table__discount lots-table__discount--good"
              : "lots-table__subvalue lots-table__discount";
          return (
            <tr key={lot.id}>
              <td className="lots-table__lot-cell">
                <div className="lots-table__title-row">
                  <Link to={`/lots/${lot.id}`}>{lot.title}</Link>
                  {lot.is_izhs_candidate && <span className="badge badge--success">ИЖС</span>}
                </div>
                <div className="lots-table__meta">Кадастр: {lot.cadastral_number || "—"}</div>
              </td>
              <td>
                <StatusBadge status={lot.status} />
                <div className="lots-table__meta">Регион: {lot.region || "—"}</div>
                <div className="lots-table__meta">{lot.municipality || lot.settlement || "—"}</div>
              </td>
              <td className="cell--nowrap">{formatArea(lot.area_sqm)}</td>
              <td className="cell--num">
                <div className="lots-table__value">{formatPrice(lot.current_price ?? lot.start_price)}</div>
                <div
                  className="lots-table__subvalue"
                  title="Стартовая цена за сотку (100 м²) по данным извещения"
                >
                  {formatPrice(lot.start_price_per_sotka)} / сотка
                </div>
              </td>
              <td className="cell--num">
                <div className="lots-table__value">{formatPrice(lot.baseline_price_per_sotka)}</div>
                <div
                  className={discountClass}
                  title="Положительное значение означает цену ниже внутреннего baseline"
                >
                  {formatPercent(lot.discount_to_baseline)}
                </div>
              </td>
              <td title={lot.valuation_reason ?? undefined}>{confidenceLabel(lot.valuation_confidence)}</td>
              <td className="cell--nowrap lots-table__dates-cell">
                <div className="lots-table__meta" title="Дата и время начала приёма заявок (если указаны в данных)">
                  Начало: {formatDateTime(lot.start_date)}
                </div>
                <div className="lots-table__meta" title="Дата и время окончания">
                  Окончание: {formatDateTime(lot.end_date)}
                </div>
              </td>
              <td className="lots-table__links-cell">
                <LotLinksCell lot={lot} />
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
