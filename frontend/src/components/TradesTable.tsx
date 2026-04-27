import { Notice } from "../types";

type Props = {
  notices: Notice[];
};

export function TradesTable({ notices }: Props) {
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
            <td>{notice.reg_num}</td>
            <td>{notice.document_type || "—"}</td>
            <td>{notice.bidd_type_code || "—"}</td>
            <td>{notice.publish_date ? new Date(notice.publish_date).toLocaleString() : "—"}</td>
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
