import { useEffect, useState } from "react";
import { fetchNotices } from "../api";
import { TradesTable } from "../components/TradesTable";
import { Notice } from "../types";

export function TradesPage() {
  const [notices, setNotices] = useState<Notice[]>([]);
  const [documentType, setDocumentType] = useState("");
  const [biddTypeCode, setBiddTypeCode] = useState("");
  const [regNum, setRegNum] = useState("");
  const [error, setError] = useState("");

  async function load() {
    try {
      setError("");
      const data = await fetchNotices({ documentType, biddTypeCode, regNum });
      setNotices(data);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  return (
    <main className="container">
      <h1>Мониторинг ГИС Торги</h1>

      <section className="filters">
        <input value={documentType} onChange={(e) => setDocumentType(e.target.value)} placeholder="Тип документа" />
        <input value={biddTypeCode} onChange={(e) => setBiddTypeCode(e.target.value)} placeholder="Вид торгов" />
        <input value={regNum} onChange={(e) => setRegNum(e.target.value)} placeholder="Реестровый номер" />
        <button onClick={() => void load()}>Применить фильтры</button>
      </section>

      {error && <p className="error">{error}</p>}

      <section>
        <h2>Список извещений</h2>
        <TradesTable notices={notices} />
      </section>
    </main>
  );
}
