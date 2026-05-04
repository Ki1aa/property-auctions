import { useEffect, useState } from "react";
import { fetchMapPoints } from "../api";
import { TradesMap } from "../components/TradesMap";
import { MapPoint } from "../types";

export function MapPage() {
  const [points, setPoints] = useState<MapPoint[]>([]);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const data = await fetchMapPoints();
        if (!cancelled) setPoints(data);
      } catch (e) {
        if (!cancelled) setError((e as Error).message);
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="page">
      <div className="page__heading">
        <h1>Карта лотов</h1>
        <span className="page__subtitle">{isLoading ? "Загрузка…" : `${points.length} точек`}</span>
      </div>

      {error && <p className="error">{error}</p>}
      {!isLoading && points.length === 0 ? (
        <p className="empty">У лотов пока нет координат.</p>
      ) : (
        <TradesMap points={points} height="calc(100vh - 220px)" />
      )}
    </div>
  );
}
