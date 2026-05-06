import { Link } from "react-router-dom";
import { Lot } from "../types";
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

function formatDate(value: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleDateString("ru-RU");
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

export function LotsTable({ lots }: Props) {
  if (lots.length === 0) {
    return <p className="empty">Лотов по фильтрам не найдено.</p>;
  }
  return (
    <table className="table">
      <thead>
        <tr>
          <th>Название</th>
          <th>Статус</th>
          <th>Регион</th>
          <th>Площадь</th>
          <th>Кадастр</th>
          <th>Текущая цена</th>
          <th className="cell--hint" title="Стартовая цена за сотку (100 м²) по данным извещения, не оценка рынка">
            ₽/сотка
          </th>
          <th className="cell--hint" title="Медиана ₽/сотка по уже загруженным торгам, не внешняя рыночная оценка">
            Baseline
          </th>
          <th className="cell--hint" title="Положительное значение означает цену ниже внутреннего baseline">
            Дисконт
          </th>
          <th>Уверенность</th>
          <th>Дата окончания</th>
        </tr>
      </thead>
      <tbody>
        {lots.map((lot) => (
          <tr key={lot.id}>
            <td className="cell--name">
              <Link to={`/lots/${lot.id}`}>{lot.title}</Link>
              {lot.is_izhs_candidate && <span className="badge badge--success">ИЖС</span>}
            </td>
            <td><StatusBadge status={lot.status} /></td>
            <td>{lot.region || "—"}</td>
            <td>{formatArea(lot.area_sqm)}</td>
            <td className="cell--mono">{lot.cadastral_number || "—"}</td>
            <td className="cell--num">{formatPrice(lot.current_price ?? lot.start_price)}</td>
            <td className="cell--num">{formatPrice(lot.start_price_per_sotka)}</td>
            <td className="cell--num">{formatPrice(lot.baseline_price_per_sotka)}</td>
            <td className={lot.discount_to_baseline && lot.discount_to_baseline > 0 ? "cell--num cell--good" : "cell--num"}>
              {formatPercent(lot.discount_to_baseline)}
            </td>
            <td title={lot.valuation_reason ?? undefined}>{confidenceLabel(lot.valuation_confidence)}</td>
            <td className="cell--nowrap">{formatDate(lot.end_date)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
