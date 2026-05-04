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
  const [isLoading, setIsLoading] = useState(true);

  async function load() {
    try {
      setError("");
      setIsLoading(true);
      const data = await fetchNotices({ documentType, biddTypeCode, regNum, limit: 500 });
      setNotices(data);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    void load();
  }

  function handleReset() {
    setDocumentType("");
    setBiddTypeCode("");
    setRegNum("");
    void load();
  }

  return (
    <div className="page">
      <h1>Извещения</h1>
      <p className="page__subtitle">Найдено: {isLoading ? "…" : notices.length}</p>

      <form className="filters" onSubmit={handleSubmit}>
        <input value={documentType} onChange={(e) => setDocumentType(e.target.value)} placeholder="Тип документа" />
        <input value={biddTypeCode} onChange={(e) => setBiddTypeCode(e.target.value)} placeholder="Вид торгов" />
        <input value={regNum} onChange={(e) => setRegNum(e.target.value)} placeholder="Реестровый номер" />
        <button type="submit">Применить</button>
        <button type="button" className="button button--ghost" onClick={handleReset}>Сбросить</button>
      </form>

      {error && <p className="error">{error}</p>}
      {isLoading ? <p className="loading">Загрузка…</p> : <TradesTable notices={notices} />}
    </div>
  );
}
