import { Link } from "react-router-dom";
import { Lot } from "../types";
import { LotExternalLinks } from "./LotExternalLinks";
import { StatusBadge } from "./StatusBadge";

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

function nspdStatusLabel(status: string | null | undefined): string {
  if (status === "enriched") return "НСПД: данные";
  if (status === "no_data") return "НСПД: пусто";
  if (status === "none") return "НСПД: не проверялось";
  return "НСПД: —";
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
          <th className="lots-table__date-col">Даты торгов</th>
          <th className="lots-table__links-col">Ссылки</th>
        </tr>
      </thead>
      <tbody>
        {lots.map((lot) => {
          return (
            <tr key={lot.id}>
              <td className="lots-table__lot-cell">
                <div className="lots-table__title-row">
                  <Link to={`/lots/${lot.id}`}>{lot.title}</Link>
                  {lot.is_izhs_candidate && <span className="badge badge--success">ИЖС</span>}
                </div>
                <div className="lots-table__meta">Кадастр: {lot.cadastral_number || "—"}</div>
                {lot.notice_reg_num && (
                  <div className="lots-table__meta">
                    Извещение: {lot.notice_reg_num}
                    {lot.notice_lot_number ? ` · лот ${lot.notice_lot_number}` : ""}
                  </div>
                )}
              </td>
              <td>
                <StatusBadge status={lot.status} />
                <div className="lots-table__meta">Регион: {lot.region || "—"}</div>
                <div className="lots-table__meta">{lot.municipality || lot.settlement || "—"}</div>
                <div className="lots-table__meta">{nspdStatusLabel(lot.nspd_data_status)}</div>
                <div className="lots-table__meta">
                  Центроид: {lot.map_centroid_available ? "да" : "нет"}
                </div>
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
              <td className="cell--nowrap lots-table__dates-cell">
                <div className="lots-table__meta" title="Дата и время начала приёма заявок (если указаны в данных)">
                  Начало: {formatDateTime(lot.start_date)}
                </div>
                <div className="lots-table__meta" title="Дата и время окончания">
                  Окончание: {formatDateTime(lot.end_date)}
                </div>
              </td>
              <td className="lots-table__links-cell">
                <LotExternalLinks lot={lot} showInternalCardLink />
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
