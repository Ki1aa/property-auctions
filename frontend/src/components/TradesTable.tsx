import { Notice } from "../types";
import { StatusBadge } from "./StatusBadge";

type Props = {
  notices: Notice[];
};

function formatDate(value: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleString("ru-RU");
}

export function TradesTable({ notices }: Props) {
  if (notices.length === 0) {
    return <p className="empty">Извещений по фильтрам не найдено.</p>;
  }
  return (
    <table className="table">
      <thead>
        <tr>
          <th>Реестровый номер</th>
          <th>Тип документа</th>
          <th>Вид торгов</th>
          <th>Дата публикации</th>
          <th>Ссылка</th>
        </tr>
      </thead>
      <tbody>
        {notices.map((notice) => (
          <tr key={notice.id}>
            <td className="cell--mono cell--nowrap">{notice.reg_num}</td>
            <td><StatusBadge status={notice.document_type} /></td>
            <td>{notice.bidd_type_code || "—"}</td>
            <td className="cell--nowrap">{formatDate(notice.publish_date)}</td>
            <td>
              <a href={notice.href} target="_blank" rel="noreferrer">Открыть</a>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
