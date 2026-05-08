import { Notice, NoticeSort } from "../types";
import { StatusBadge } from "./StatusBadge";

type NoticeSortField = "reg_num" | "document_type" | "bidd_type_code" | "publish_date";

type Props = {
  notices: Notice[];
  sort: NoticeSort;
  onSort: (field: NoticeSortField) => void;
};

const sortLabels: Record<NoticeSortField, string> = {
  reg_num: "Реестровый номер",
  document_type: "Тип документа",
  bidd_type_code: "Вид торгов",
  publish_date: "Дата публикации",
};

function formatDate(value: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleString("ru-RU");
}

function sortField(sort: NoticeSort): NoticeSortField {
  if (sort.startsWith("reg_num_")) return "reg_num";
  if (sort.startsWith("document_type_")) return "document_type";
  if (sort.startsWith("bidd_type_code_")) return "bidd_type_code";
  return "publish_date";
}

function sortDirection(sort: NoticeSort): "asc" | "desc" {
  return sort.endsWith("_asc") ? "asc" : "desc";
}

function SortableHeader({
  field,
  sort,
  onSort,
}: {
  field: NoticeSortField;
  sort: NoticeSort;
  onSort: (field: NoticeSortField) => void;
}) {
  const active = sortField(sort) === field;
  const direction = sortDirection(sort);
  const label = sortLabels[field];
  return (
    <th className="table__sortable-heading" aria-sort={active ? (direction === "asc" ? "ascending" : "descending") : "none"}>
      <button
        type="button"
        className={active ? "table__sort-button table__sort-button--active" : "table__sort-button"}
        onClick={() => onSort(field)}
      >
        <span>{label}</span>
        <span className="table__sort-indicator" aria-hidden>
          {active ? (direction === "asc" ? "↑" : "↓") : "↕"}
        </span>
      </button>
    </th>
  );
}

export function TradesTable({ notices, sort, onSort }: Props) {
  if (notices.length === 0) {
    return <p className="empty">Извещений по фильтрам не найдено.</p>;
  }
  return (
    <table className="table notices-table">
      <thead>
        <tr>
          <SortableHeader field="reg_num" sort={sort} onSort={onSort} />
          <SortableHeader field="document_type" sort={sort} onSort={onSort} />
          <SortableHeader field="bidd_type_code" sort={sort} onSort={onSort} />
          <SortableHeader field="publish_date" sort={sort} onSort={onSort} />
          <th>Ссылка</th>
        </tr>
      </thead>
      <tbody>
        {notices.map((notice) => (
          <tr key={notice.id}>
            <td className="cell--mono cell--nowrap">{notice.reg_num}</td>
            <td>
              <StatusBadge status={notice.document_type} />
            </td>
            <td>{notice.bidd_type_code || "—"}</td>
            <td className="cell--nowrap">{formatDate(notice.publish_date)}</td>
            <td>
              <a href={notice.href} target="_blank" rel="noreferrer">
                Открыть
              </a>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
