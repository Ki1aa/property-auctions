import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { buildLotsExportUrl, fetchLotFacets, fetchLots } from "../api";
import { FacetMultiPicker } from "../components/FacetMultiPicker";
import { LotsTable } from "../components/LotsTable";
import { FACET_SINGLE_SELECT_MAX } from "../facetFilterUi";
import { Lot, LotFacets, LotsSort } from "../types";

const PAGE_SIZE = 50;
const DEFAULT_SORT: LotsSort = "updated_at_desc";

type LotsQueryState = {
  region: string;
  status: string;
  categories: string[];
  isIzhs: boolean;
  minArea: string;
  maxArea: string;
  maxStartPrice: string;
  cadastral: string;
  sort: LotsSort;
  offset: number;
};

function parseLotsSort(value: string | null): LotsSort {
  if (
    value === "price_per_sotka_asc" ||
    value === "price_per_sotka_desc" ||
    value === "discount_to_baseline_desc" ||
    value === "updated_at_desc"
  ) {
    return value;
  }
  return DEFAULT_SORT;
}

function parseOffset(value: string | null): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : 0;
}

function queryStateFromSearchParams(params: URLSearchParams): LotsQueryState {
  return {
    region: params.get("region") ?? "",
    status: params.get("status") ?? "",
    categories: params.getAll("category"),
    isIzhs: params.get("is_izhs") === "true",
    minArea: params.get("min_area") ?? "",
    maxArea: params.get("max_area") ?? "",
    maxStartPrice: params.get("max_start_price") ?? "",
    cadastral: params.get("cadastral_number") ?? "",
    sort: parseLotsSort(params.get("sort")),
    offset: parseOffset(params.get("offset")),
  };
}

function optionalNumber(value: string): number | undefined {
  return value ? Number(value) : undefined;
}

export function LotsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialQuery = queryStateFromSearchParams(searchParams);
  const [lots, setLots] = useState<Lot[]>([]);
  const [total, setTotal] = useState(0);
  const [sort, setSort] = useState<LotsSort>(initialQuery.sort);
  const [offset, setOffset] = useState(initialQuery.offset);
  const [region, setRegion] = useState(initialQuery.region);
  const [status, setStatus] = useState(initialQuery.status);
  const [categories, setCategories] = useState<string[]>(initialQuery.categories);
  const [isIzhs, setIsIzhs] = useState(initialQuery.isIzhs);
  const [minArea, setMinArea] = useState(initialQuery.minArea);
  const [maxArea, setMaxArea] = useState(initialQuery.maxArea);
  const [maxStartPrice, setMaxStartPrice] = useState(initialQuery.maxStartPrice);
  const [cadastral, setCadastral] = useState(initialQuery.cadastral);
  const [facets, setFacets] = useState<LotFacets | null>(null);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  const regionOptions = useMemo(() => {
    const s = new Set([...(facets?.region ?? []), ...(region ? [region] : [])]);
    return Array.from(s).sort();
  }, [facets, region]);

  const statusOptions = useMemo(() => {
    const s = new Set([...(facets?.status ?? []), ...(status ? [status] : [])]);
    return Array.from(s).sort();
  }, [facets, status]);

  const categoryOptions = useMemo(() => {
    const s = new Set([...(facets?.category ?? []), ...categories]);
    return Array.from(s).sort();
  }, [facets, categories]);

  const exportUrl = useMemo(() => {
    const applied = queryStateFromSearchParams(searchParams);
    return buildLotsExportUrl({
      region: applied.region || undefined,
      status: applied.status || undefined,
      category: applied.categories.length ? applied.categories : undefined,
      isIzhs: applied.isIzhs ? true : undefined,
      minArea: optionalNumber(applied.minArea),
      maxArea: optionalNumber(applied.maxArea),
      maxStartPrice: optionalNumber(applied.maxStartPrice),
      cadastralNumber: applied.cadastral || undefined,
      sort: applied.sort,
      maxRows: 50_000,
    });
  }, [searchParams]);

  const regionAsSelect =
    Boolean(facets) && regionOptions.length > 0 && regionOptions.length <= FACET_SINGLE_SELECT_MAX;
  const statusAsSelect =
    Boolean(facets) && statusOptions.length > 0 && statusOptions.length <= FACET_SINGLE_SELECT_MAX;

  async function load(query: LotsQueryState) {
    try {
      setError("");
      setIsLoading(true);
      const page = await fetchLots({
        region: query.region || undefined,
        status: query.status || undefined,
        category: query.categories.length ? query.categories : undefined,
        isIzhs: query.isIzhs ? true : undefined,
        minArea: optionalNumber(query.minArea),
        maxArea: optionalNumber(query.maxArea),
        maxStartPrice: optionalNumber(query.maxStartPrice),
        cadastralNumber: query.cadastral || undefined,
        limit: PAGE_SIZE,
        offset: query.offset,
        sort: query.sort,
      });
      setLots(page.items);
      setTotal(page.total);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setIsLoading(false);
    }
  }

  function syncFormState(query: LotsQueryState) {
    setRegion(query.region);
    setStatus(query.status);
    setCategories(query.categories);
    setIsIzhs(query.isIzhs);
    setMinArea(query.minArea);
    setMaxArea(query.maxArea);
    setMaxStartPrice(query.maxStartPrice);
    setCadastral(query.cadastral);
    setSort(query.sort);
    setOffset(query.offset);
  }

  function draftToSearchParams(nextOffset: number, nextSort: LotsSort): URLSearchParams {
    const next = new URLSearchParams();
    if (region) next.set("region", region);
    if (status) next.set("status", status);
    for (const c of categories) {
      next.append("category", c);
    }
    if (isIzhs) next.set("is_izhs", "true");
    if (minArea) next.set("min_area", minArea);
    if (maxArea) next.set("max_area", maxArea);
    if (maxStartPrice) next.set("max_start_price", maxStartPrice);
    if (cadastral) next.set("cadastral_number", cadastral);
    if (nextSort !== DEFAULT_SORT) next.set("sort", nextSort);
    if (nextOffset > 0) next.set("offset", String(nextOffset));
    return next;
  }

  function updateAppliedSearchParams(nextOffset: number, nextSort = sort) {
    const next = new URLSearchParams(searchParams);
    if (nextSort === DEFAULT_SORT) {
      next.delete("sort");
    } else {
      next.set("sort", nextSort);
    }
    if (nextOffset > 0) {
      next.set("offset", String(nextOffset));
    } else {
      next.delete("offset");
    }
    setSearchParams(next, { replace: true });
  }

  useEffect(() => {
    void fetchLotFacets()
      .then(setFacets)
      .catch((e) => setError((e as Error).message));
  }, []);

  useEffect(() => {
    const query = queryStateFromSearchParams(searchParams);
    syncFormState(query);
    void load(query);
  }, [searchParams]);

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setSearchParams(draftToSearchParams(0, sort), { replace: true });
  }

  function handleReset() {
    const next = new URLSearchParams();
    const emptyQuery = queryStateFromSearchParams(next);
    syncFormState(emptyQuery);
    if (searchParams.toString() === next.toString()) {
      void load(emptyQuery);
      return;
    }
    setSearchParams(next, { replace: true });
  }

  const pageFrom = total === 0 ? 0 : offset + 1;
  const pageTo = offset + lots.length;

  return (
    <div className="page">
      <h1>Лоты</h1>
      <p className="page__subtitle">
        Найдено: {isLoading ? "…" : total}
        {!isLoading && total > 0 ? ` · записи ${pageFrom}—${pageTo}` : ""}
      </p>

      <form className="filters filters--grid" onSubmit={handleSubmit}>
        {regionAsSelect ? (
          <label className="filters__field">
            <span className="filters__facet-label">Регион</span>
            <select className="filters__select" value={region} onChange={(e) => setRegion(e.target.value)}>
              <option value="">Все</option>
              {regionOptions.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </label>
        ) : (
          <input
            value={region}
            onChange={(e) => setRegion(e.target.value)}
            placeholder="Регион (код, например 72)"
          />
        )}
        {statusAsSelect ? (
          <label className="filters__field">
            <span className="filters__facet-label">Тип документа</span>
            <select className="filters__select" value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="">Все</option>
              {statusOptions.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </label>
        ) : (
          <input
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            placeholder="Тип документа (код documentType)"
          />
        )}
        {categoryOptions.length > 0 && (
          <FacetMultiPicker
            label="Вид торгов"
            options={categoryOptions}
            value={categories}
            onChange={setCategories}
          />
        )}
        <input value={cadastral} onChange={(e) => setCadastral(e.target.value)} placeholder="Кадастровый номер (часть)" />
        <input
          value={minArea}
          onChange={(e) => setMinArea(e.target.value)}
          placeholder="Площадь от, м²"
          type="number"
          min={0}
        />
        <input
          value={maxArea}
          onChange={(e) => setMaxArea(e.target.value)}
          placeholder="Площадь до, м²"
          type="number"
          min={0}
        />
        <input
          value={maxStartPrice}
          onChange={(e) => setMaxStartPrice(e.target.value)}
          placeholder="Макс. стартовая цена, ₽"
          type="number"
          min={0}
        />
        <label className="checkbox">
          <input type="checkbox" checked={isIzhs} onChange={(e) => setIsIzhs(e.target.checked)} />
          <span>Только ИЖС</span>
        </label>
        <label className="filters__field">
          <span className="filters__facet-label">Сортировка</span>
          <select
            className="filters__select"
            value={sort}
            onChange={(e) => {
              const nextSort = e.target.value as LotsSort;
              setSort(nextSort);
              updateAppliedSearchParams(0, nextSort);
            }}
          >
            <option value="updated_at_desc">По дате обновления</option>
            <option value="discount_to_baseline_desc">По дисконту к baseline</option>
            <option value="price_per_sotka_asc">Старт. цена за сотку (дешевле первые)</option>
            <option value="price_per_sotka_desc">Старт. цена за сотку (дороже первые)</option>
          </select>
        </label>
        <div className="filters__actions">
          <button type="submit">Применить</button>
          <button type="button" className="button button--ghost" onClick={handleReset}>Сбросить</button>
          <a className="button button--ghost" href={exportUrl} download="lots_export.csv">
            Скачать CSV
          </a>
        </div>
      </form>

      {error && <p className="error">{error}</p>}
      {!isLoading && total > PAGE_SIZE ? (
        <div className="pagination">
          <button
            type="button"
            className="button button--ghost"
            disabled={offset === 0}
            onClick={() => updateAppliedSearchParams(Math.max(0, offset - PAGE_SIZE))}
          >
            Назад
          </button>
          <button
            type="button"
            className="button button--ghost"
            disabled={offset + PAGE_SIZE >= total}
            onClick={() => updateAppliedSearchParams(offset + PAGE_SIZE)}
          >
            Вперёд
          </button>
        </div>
      ) : null}
      {isLoading ? <p className="loading">Загрузка…</p> : <LotsTable lots={lots} />}
    </div>
  );
}
