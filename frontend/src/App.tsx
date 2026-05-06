import { lazy, Suspense } from "react";
import { Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { DashboardPage } from "./pages/DashboardPage";
import { IngestRunsPage } from "./pages/IngestRunsPage";
import { LotDetailPage } from "./pages/LotDetailPage";
import { LotsPage } from "./pages/LotsPage";
import { TradesPage } from "./pages/TradesPage";

const MapPage = lazy(() => import("./pages/MapPage").then((module) => ({ default: module.MapPage })));

export function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<DashboardPage />} />
        <Route path="notices" element={<TradesPage />} />
        <Route path="lots" element={<LotsPage />} />
        <Route path="lots/:id" element={<LotDetailPage />} />
        <Route
          path="map"
          element={
            <Suspense fallback={<p className="loading">Загрузка страницы…</p>}>
              <MapPage />
            </Suspense>
          }
        />
        <Route path="ingest" element={<IngestRunsPage />} />
        <Route path="*" element={<DashboardPage />} />
      </Route>
    </Routes>
  );
}
