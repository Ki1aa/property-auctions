import { NavLink, Outlet } from "react-router-dom";

const navItems = [
  { to: "/", label: "Сводка", end: true },
  { to: "/lots", label: "Лоты" },
  { to: "/ingest", label: "Загрузки" },
];

export function Layout() {
  return (
    <div className="app">
      <header className="header">
        <div className="header__inner">
          <div className="header__brand">
            <span className="header__logo">ГТ</span>
            <span className="header__title">ГИС Торги Monitor</span>
          </div>
          <nav className="nav">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) => (isActive ? "nav__link nav__link--active" : "nav__link")}
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>
      <main className="container">
        <Outlet />
      </main>
    </div>
  );
}
