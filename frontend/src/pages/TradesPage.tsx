import { FormEvent, useEffect, useMemo, useState } from "react";
import { fetchNotices, fetchOpenDataNoticeFacets } from "../api";
import { FacetMultiPicker } from "../components/FacetMultiPicker";
import { TradesTable } from "../components/TradesTable";
import { Notice, NoticeSort, OpenDataNoticeFacets } from "../types";

const PAGE_SIZE = 50;
const DEFAULT_SORT: NoticeSort = "publish_date_desc";

type NoticeSortField = "reg_num" | "document_type" | "bidd_type_code" | "publish_date";

type NoticeFilters = {
  documentTypes: string[];
  biddTypeCodes: string[];
  regNum: string;
};

function sortField(sort: NoticeSort): NoticeSortField {
  if (sort.startsWith("reg_num_")) return "reg_num";
  if (sort.startsWith("document_type_")) return "document_type";
  if (sort.startsWith("bidd_type_code_")) return "bidd_type_code";
  return "publish_date";
}

function sortDirection(sort: NoticeSort): "asc" | "desc" {
  return sort.endsWith("_asc") ? "asc" : "desc";
}

function nextSortForField(current: NoticeSort, field: NoticeSortField): NoticeSort {
  if (sortField(current) === field) {
    const nextDirection = sortDirection(current) === "asc" ? "desc" : "asc";
    return `${field}_${nextDirection}` as NoticeSort;
  }
  return field === "publish_date" ? "publish_date_desc" : (`${field}_asc` as NoticeSort);
}

export function TradesPage() {
  const [notices, setNotices] = useState<Notice[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [sort, setSort] = useState<NoticeSort>(DEFAULT_SORT);
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

  async function load(
    filters: NoticeFilters = { documentTypes, biddTypeCodes, regNum },
    nextOffset = offset,
    nextSort = sort,
  ) {
    try {
      setError("");
      setIsLoading(true);
      const page = await fetchNotices({
        documentType: filters.documentTypes.length ? filters.documentTypes : undefined,
        biddTypeCode: filters.biddTypeCodes.length ? filters.biddTypeCodes : undefined,
        regNum: filters.regNum.trim() || undefined,
        sort: nextSort,
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

  function currentFilters(): NoticeFilters {
    return { documentTypes, biddTypeCodes, regNum };
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    void load(currentFilters(), 0, sort);
  }

  function handleReset() {
    const empty: NoticeFilters = { documentTypes: [], biddTypeCodes: [], regNum: "" };
    setDocumentTypes([]);
    setBiddTypeCodes([]);
    setRegNum("");
    setSort(DEFAULT_SORT);
    void load(empty, 0, DEFAULT_SORT);
  }

  function handlePage(nextOffset: number) {
    void load(currentFilters(), nextOffset, sort);
  }

  function handleSort(field: NoticeSortField) {
    const nextSort = nextSortForField(sort, field);
    setSort(nextSort);
    void load(currentFilters(), 0, nextSort);
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

      <form className="filters notices-filters" onSubmit={handleSubmit}>
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
        <label className="filters__field">
          <span className="filters__facet-label">Реестровый номер</span>
          <input
            value={regNum}
            onChange={(e) => setRegNum(e.target.value)}
            placeholder="Точное совпадение"
          />
        </label>
        <div className="filters__actions notices-filters__actions">
          <button type="submit">Применить</button>
          <button type="button" className="button button--ghost" onClick={handleReset}>
            Сбросить
          </button>
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
      {isLoading ? <p className="loading">Загрузка…</p> : <TradesTable notices={notices} sort={sort} onSort={handleSort} />}
    </div>
  );
}
