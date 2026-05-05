import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { fetchLotFacets, fetchLots } from "../api";
import { FacetMultiPicker } from "../components/FacetMultiPicker";
import { LotsTable } from "../components/LotsTable";
import { FACET_SINGLE_SELECT_MAX } from "../facetFilterUi";
import { Lot, LotFacets } from "../types";

export function LotsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [lots, setLots] = useState<Lot[]>([]);
  const [region, setRegion] = useState(searchParams.get("region") ?? "");
  const [status, setStatus] = useState(searchParams.get("status") ?? "");
  const [categories, setCategories] = useState<string[]>(() => searchParams.getAll("category"));
  const [isIzhs, setIsIzhs] = useState(searchParams.get("is_izhs") === "true");
  const [minArea, setMinArea] = useState(searchParams.get("min_area") ?? "");
  const [maxArea, setMaxArea] = useState(searchParams.get("max_area") ?? "");
  const [maxStartPrice, setMaxStartPrice] = useState(searchParams.get("max_start_price") ?? "");
  const [cadastral, setCadastral] = useState(searchParams.get("cadastral_number") ?? "");
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

  const regionAsSelect =
    Boolean(facets) && regionOptions.length > 0 && regionOptions.length <= FACET_SINGLE_SELECT_MAX;
  const statusAsSelect =
    Boolean(facets) && statusOptions.length > 0 && statusOptions.length <= FACET_SINGLE_SELECT_MAX;
  async function load() {
    try {
      setError("");
      setIsLoading(true);
      const data = await fetchLots({
        region: region || undefined,
        status: status || undefined,
        category: categories.length ? categories : undefined,
        isIzhs: isIzhs ? true : undefined,
        minArea: minArea ? Number(minArea) : undefined,
        maxArea: maxArea ? Number(maxArea) : undefined,
        maxStartPrice: maxStartPrice ? Number(maxStartPrice) : undefined,
        cadastralNumber: cadastral || undefined,
        limit: 500,
      });
      setLots(data);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void fetchLotFacets()
      .then(setFacets)
      .catch((e) => setError((e as Error).message));
  }, []);

  useEffect(() => {
    void load();
  }, []);

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
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
    setSearchParams(next, { replace: true });
    void load();
  }

  function handleReset() {
    setRegion("");
    setStatus("");
    setCategories([]);
    setIsIzhs(false);
    setMinArea("");
    setMaxArea("");
    setMaxStartPrice("");
    setCadastral("");
    setSearchParams(new URLSearchParams(), { replace: true });
    void load();
  }

  return (
    <div className="page">
      <h1>Лоты</h1>
      <p className="page__subtitle">Найдено: {isLoading ? "…" : lots.length}</p>

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
        <div className="filters__actions">
          <button type="submit">Применить</button>
          <button type="button" className="button button--ghost" onClick={handleReset}>Сбросить</button>
        </div>
      </form>

      {error && <p className="error">{error}</p>}
      {isLoading ? <p className="loading">Загрузка…</p> : <LotsTable lots={lots} />}
    </div>
  );
}
