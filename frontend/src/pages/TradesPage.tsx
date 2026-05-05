import { useEffect, useMemo, useState } from "react";
import { fetchNotices, fetchOpenDataNoticeFacets } from "../api";
import { FacetMultiPicker } from "../components/FacetMultiPicker";
import { TradesTable } from "../components/TradesTable";
import { Notice, OpenDataNoticeFacets } from "../types";

export function TradesPage() {
  const [notices, setNotices] = useState<Notice[]>([]);
  const [documentTypes, setDocumentTypes] = useState<string[]>([]);
  const [biddTypeCodes, setBiddTypeCodes] = useState<string[]>([]);
  const [regNum, setRegNum] = useState("");
  const [facets, setFacets] = useState<OpenDataNoticeFacets | null>(null);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  const docOptions = useMemo(() => {
    const s = new Set([...(facets?.document_type ?? []), ...documentTypes]);
    return Array.from(s).sort();
  }, [facets, documentTypes]);

  const biddOptions = useMemo(() => {
    const s = new Set([...(facets?.bidd_type_code ?? []), ...biddTypeCodes]);
    return Array.from(s).sort();
  }, [facets, biddTypeCodes]);

  async function load() {
    try {
      setError("");
      setIsLoading(true);
      const data = await fetchNotices({
        documentType: documentTypes.length ? documentTypes : undefined,
        biddTypeCode: biddTypeCodes.length ? biddTypeCodes : undefined,
        regNum: regNum.trim() || undefined,
        limit: 500,
      });
      setNotices(data);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void fetchOpenDataNoticeFacets()
      .then(setFacets)
      .catch((e) => setError((e as Error).message));
  }, []);

  useEffect(() => {
    void load();
  }, []);

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    void load();
  }

  function handleReset() {
    setDocumentTypes([]);
    setBiddTypeCodes([]);
    setRegNum("");
    void load();
  }

  return (
    <div className="page">
      <h1>Извещения</h1>
      <p className="page__subtitle">Найдено: {isLoading ? "…" : notices.length}</p>

      <form className="filters filters--grid" onSubmit={handleSubmit}>
        {docOptions.length > 0 && (
          <FacetMultiPicker
            label="Тип документа"
            options={docOptions}
            value={documentTypes}
            onChange={setDocumentTypes}
          />
        )}
        {biddOptions.length > 0 && (
          <FacetMultiPicker
            label="Вид торгов"
            options={biddOptions}
            value={biddTypeCodes}
            onChange={setBiddTypeCodes}
          />
        )}
        <input
          value={regNum}
          onChange={(e) => setRegNum(e.target.value)}
          placeholder="Реестровый номер (точное совпадение)"
        />
        <div className="filters__actions">
          <button type="submit">Применить</button>
          <button type="button" className="button button--ghost" onClick={handleReset}>Сбросить</button>
        </div>
      </form>

      {error && <p className="error">{error}</p>}
      {isLoading ? <p className="loading">Загрузка…</p> : <TradesTable notices={notices} />}
    </div>
  );
}
