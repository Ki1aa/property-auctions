import { useEffect, useMemo, useState } from "react";
import { fetchNotices, fetchOpenDataNoticeFacets } from "../api";
import { FacetMultiPicker } from "../components/FacetMultiPicker";
import { TradesTable } from "../components/TradesTable";
import { Notice, OpenDataNoticeFacets } from "../types";

const PAGE_SIZE = 50;

type NoticeFilters = {
  documentTypes: string[];
  biddTypeCodes: string[];
  regNum: string;
};

export function TradesPage() {
  const [notices, setNotices] = useState<Notice[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
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

  async function load(filters: NoticeFilters = { documentTypes, biddTypeCodes, regNum }, nextOffset = offset) {
    try {
      setError("");
      setIsLoading(true);
      const page = await fetchNotices({
        documentType: filters.documentTypes.length ? filters.documentTypes : undefined,
        biddTypeCode: filters.biddTypeCodes.length ? filters.biddTypeCodes : undefined,
        regNum: filters.regNum.trim() || undefined,
        limit: PAGE_SIZE,
        offset: nextOffset,
      });
      setNotices(page.items);
      setTotal(page.total);
      setOffset(page.offset);
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
    void load({ documentTypes, biddTypeCodes, regNum }, 0);
  }

  function handleReset() {
    const empty: NoticeFilters = { documentTypes: [], biddTypeCodes: [], regNum: "" };
    setDocumentTypes([]);
    setBiddTypeCodes([]);
    setRegNum("");
    void load(empty, 0);
  }

  function handlePage(nextOffset: number) {
    void load(undefined, nextOffset);
  }

  const pageFrom = total === 0 ? 0 : offset + 1;
  const pageTo = offset + notices.length;

  return (
    <div className="page">
      <h1>Извещения</h1>
      <p className="page__subtitle">
        Найдено: {isLoading ? "…" : total}
        {!isLoading && total > 0 ? ` · записи ${pageFrom}—${pageTo}` : ""}
      </p>

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
      {!isLoading && total > PAGE_SIZE ? (
        <div className="pagination">
          <button
            type="button"
            className="button button--ghost"
            disabled={offset === 0}
            onClick={() => handlePage(Math.max(0, offset - PAGE_SIZE))}
          >
            Назад
          </button>
          <button
            type="button"
            className="button button--ghost"
            disabled={offset + PAGE_SIZE >= total}
            onClick={() => handlePage(offset + PAGE_SIZE)}
          >
            Вперёд
          </button>
        </div>
      ) : null}
      {isLoading ? <p className="loading">Загрузка…</p> : <TradesTable notices={notices} />}
    </div>
  );
}
