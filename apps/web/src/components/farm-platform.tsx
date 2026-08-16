"use client";

import {
  Bell,
  FileDown,
  Leaf,
  Loader2,
  LogOut,
  MapPin,
  Plus,
  RefreshCw,
  UploadCloud,
  UserRound
} from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { apiForm, apiJson, ApiError } from "@/lib/api";

type User = {
  id: string;
  email: string | null;
  phone: string | null;
  full_name: string;
  role: string;
};

type Farm = {
  id: string;
  name: string;
  country: string;
  region: string | null;
  latitude: string | null;
  longitude: string | null;
  area_hectares: string | null;
  created_at: string;
};

type Detection = {
  id: string;
  image_url: string;
  disease_label: string;
  confidence: string;
  affected_area_pct: string | null;
  severity: "low" | "medium" | "high";
  recommendation: {
    summary: string;
    actions: string[];
    yield_impact?: unknown;
  };
  created_at: string;
};

type Report = {
  id: string;
  report_type: string;
  title: string;
  file_url: string;
  created_at: string;
};

type NotificationItem = {
  id: string;
  title: string;
  body: string;
  channel: string;
  status: string;
  created_at: string;
};

type AuthMode = "login" | "register";

export function FarmPlatform() {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [farms, setFarms] = useState<Farm[]>([]);
  const [reports, setReports] = useState<Report[]>([]);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [latestDetection, setLatestDetection] = useState<Detection | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    const stored = window.localStorage.getItem("farm_ai_token");
    if (stored) {
      setToken(stored);
    }
  }, []);

  useEffect(() => {
    if (token) {
      void refreshData(token);
    }
  }, [token]);

  async function refreshData(activeToken = token) {
    if (!activeToken) {
      return;
    }
    setLoading(true);
    setMessage(null);
    try {
      const [me, farmList, reportList, notificationList] = await Promise.all([
        apiJson<User>("/api/v1/auth/me", { token: activeToken }),
        apiJson<Farm[]>("/api/v1/farms", { token: activeToken }),
        apiJson<Report[]>("/api/v1/reports", { token: activeToken }),
        apiJson<NotificationItem[]>("/api/v1/notifications", { token: activeToken })
      ]);
      setUser(me);
      setFarms(farmList);
      setReports(reportList);
      setNotifications(notificationList);
    } catch (error) {
      setMessage(errorMessage(error));
    } finally {
      setLoading(false);
    }
  }

  function handleAuthenticated(accessToken: string) {
    window.localStorage.setItem("farm_ai_token", accessToken);
    setToken(accessToken);
  }

  function logout() {
    window.localStorage.removeItem("farm_ai_token");
    setToken(null);
    setUser(null);
    setFarms([]);
    setReports([]);
    setNotifications([]);
    setLatestDetection(null);
  }

  const highRiskCount = useMemo(
    () => notifications.filter((item) => item.title.toLowerCase().includes("risk")).length,
    [notifications]
  );

  if (!token) {
    return <AuthShell onAuthenticated={handleAuthenticated} message={message} setMessage={setMessage} />;
  }

  return (
    <main className="app-shell">
      <aside className="sidebar" aria-label="Workspace navigation">
        <div className="brand">
          <span className="brand-mark">
            <Leaf aria-hidden="true" size={21} />
          </span>
          <span>Farm AI</span>
        </div>
        <nav className="nav-list">
          <a href="#dashboard">Dashboard</a>
          <a href="#farms">Farms</a>
          <a href="#scan">AI Scan</a>
          <a href="#reports">Reports</a>
        </nav>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">Production Console</p>
            <h1>{user ? user.full_name : "Farm Intelligence"}</h1>
          </div>
          <div className="topbar-actions">
            <button className="icon-button" type="button" onClick={() => refreshData()} title="Refresh">
              {loading ? <Loader2 className="spin" size={18} /> : <RefreshCw size={18} />}
            </button>
            <button className="icon-button" type="button" onClick={logout} title="Sign out">
              <LogOut size={18} />
            </button>
          </div>
        </header>

        {message ? <div className="notice">{message}</div> : null}

        <section id="dashboard" className="metric-grid">
          <Metric label="Farms" value={farms.length.toString()} icon={<MapPin size={18} />} />
          <Metric label="Reports" value={reports.length.toString()} icon={<FileDown size={18} />} />
          <Metric label="Alerts" value={highRiskCount.toString()} icon={<Bell size={18} />} />
        </section>

        <section className="content-grid">
          <FarmPanel token={token} farms={farms} onChanged={() => refreshData()} setMessage={setMessage} />
          <ScanPanel
            token={token}
            farms={farms}
            onDetection={setLatestDetection}
            onChanged={() => refreshData()}
            setMessage={setMessage}
          />
        </section>

        {latestDetection ? <DetectionPanel detection={latestDetection} /> : null}

        <section className="content-grid">
          <ListPanel
            id="reports"
            title="Reports"
            empty="No generated reports yet."
            items={reports.map((report) => ({
              id: report.id,
              title: report.title,
              detail: `${report.report_type} report`,
              href: report.file_url
            }))}
          />
          <ListPanel
            title="Notifications"
            empty="No notifications yet."
            items={notifications.map((notification) => ({
              id: notification.id,
              title: notification.title,
              detail: notification.body
            }))}
          />
        </section>
      </section>
    </main>
  );
}

function AuthShell({
  onAuthenticated,
  message,
  setMessage
}: {
  onAuthenticated: (token: string) => void;
  message: string | null;
  setMessage: (value: string | null) => void;
}) {
  const [mode, setMode] = useState<AuthMode>("login");
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setMessage(null);
    const form = new FormData(event.currentTarget);
    const payload =
      mode === "register"
        ? {
            email: String(form.get("email")),
            password: String(form.get("password")),
            full_name: String(form.get("full_name"))
          }
        : {
            email: String(form.get("email")),
            password: String(form.get("password"))
          };

    try {
      const result = await apiJson<{ access_token: string }>(
        mode === "register" ? "/api/v1/auth/register" : "/api/v1/auth/login",
        {
          method: "POST",
          body: JSON.stringify(payload)
        }
      );
      onAuthenticated(result.access_token);
    } catch (error) {
      setMessage(errorMessage(error));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-panel">
        <div className="brand auth-brand">
          <span className="brand-mark">
            <Leaf aria-hidden="true" size={21} />
          </span>
          <span>Farm AI</span>
        </div>
        <div className="segmented" role="tablist" aria-label="Auth mode">
          <button
            className={mode === "login" ? "active" : ""}
            type="button"
            onClick={() => setMode("login")}
          >
            Sign in
          </button>
          <button
            className={mode === "register" ? "active" : ""}
            type="button"
            onClick={() => setMode("register")}
          >
            Create account
          </button>
        </div>
        <form className="form" onSubmit={submit}>
          {mode === "register" ? (
            <label>
              Name
              <input name="full_name" required placeholder="Asha Patel" />
            </label>
          ) : null}
          <label>
            Email
            <input name="email" type="email" required placeholder="farmer@example.com" />
          </label>
          <label>
            Password
            <input name="password" type="password" required minLength={8} />
          </label>
          {message ? <div className="notice compact">{message}</div> : null}
          <button className="primary-button" type="submit" disabled={loading}>
            {loading ? <Loader2 className="spin" size={18} /> : <UserRound size={18} />}
            {mode === "register" ? "Create Account" : "Sign In"}
          </button>
        </form>
      </section>
    </main>
  );
}

function Metric({ label, value, icon }: { label: string; value: string; icon: React.ReactNode }) {
  return (
    <article className="metric-card">
      <span className="metric-icon">{icon}</span>
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}

function FarmPanel({
  token,
  farms,
  onChanged,
  setMessage
}: {
  token: string;
  farms: Farm[];
  onChanged: () => void;
  setMessage: (value: string | null) => void;
}) {
  const [saving, setSaving] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setMessage(null);
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const payload = {
      name: String(form.get("name")),
      country: String(form.get("country")),
      region: nullableString(form.get("region")),
      latitude: nullableString(form.get("latitude")),
      longitude: nullableString(form.get("longitude")),
      area_hectares: nullableString(form.get("area_hectares"))
    };

    try {
      await apiJson<Farm>("/api/v1/farms", {
        method: "POST",
        token,
        body: JSON.stringify(payload)
      });
      formElement?.reset();
      onChanged();
    } catch (error) {
      setMessage(errorMessage(error));
    } finally {
      setSaving(false);
    }
  }

  return (
    <section id="farms" className="panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Farm Registry</p>
          <h2>Add a farm</h2>
        </div>
      </div>
      <form className="form two-column" onSubmit={submit}>
        <label>
          Farm name
          <input name="name" required placeholder="North Field" />
        </label>
        <label>
          Country
          <input name="country" required placeholder="India" />
        </label>
        <label>
          Region
          <input name="region" placeholder="Punjab" />
        </label>
        <label>
          Area ha
          <input name="area_hectares" inputMode="decimal" placeholder="4.5" />
        </label>
        <label>
          Latitude
          <input name="latitude" inputMode="decimal" placeholder="30.7333" />
        </label>
        <label>
          Longitude
          <input name="longitude" inputMode="decimal" placeholder="76.7794" />
        </label>
        <button className="primary-button" type="submit" disabled={saving}>
          {saving ? <Loader2 className="spin" size={18} /> : <Plus size={18} />}
          Add Farm
        </button>
      </form>
      <div className="list">
        {farms.length === 0 ? <p className="empty">No farms registered yet.</p> : null}
        {farms.map((farm) => (
          <article className="list-row" key={farm.id}>
            <div>
              <strong>{farm.name}</strong>
              <span>
                {[farm.region, farm.country].filter(Boolean).join(", ")}
                {farm.area_hectares ? `, ${farm.area_hectares} ha` : ""}
              </span>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function ScanPanel({
  token,
  farms,
  onDetection,
  onChanged,
  setMessage
}: {
  token: string;
  farms: Farm[];
  onDetection: (detection: Detection) => void;
  onChanged: () => void;
  setMessage: (value: string | null) => void;
}) {
  const [scanning, setScanning] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setScanning(true);
    setMessage(null);
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const farmId = String(form.get("farm_id") ?? "");
    const farm = farms.find((item) => item.id === farmId);
    if (!farmId) {
      form.delete("farm_id");
    }
    if (farm?.latitude && farm.longitude) {
      form.set("latitude", farm.latitude);
      form.set("longitude", farm.longitude);
    }

    try {
      const detection = await apiForm<Detection>("/api/v1/ai/disease-detections", form, token);
      onDetection(detection);
      onChanged();
      formElement?.reset();
    } catch (error) {
      setMessage(errorMessage(error));
    } finally {
      setScanning(false);
    }
  }

  return (
    <section id="scan" className="panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">AI Diagnosis</p>
          <h2>Upload leaf image</h2>
        </div>
      </div>
      <form className="form" onSubmit={submit}>
        <label>
          Farm
          <select name="farm_id" defaultValue="">
            <option value="">Unassigned</option>
            {farms.map((farm) => (
              <option key={farm.id} value={farm.id}>
                {farm.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Image
          <input name="image" type="file" accept="image/*" required />
        </label>
        <button className="primary-button" type="submit" disabled={scanning}>
          {scanning ? <Loader2 className="spin" size={18} /> : <UploadCloud size={18} />}
          Run Detection
        </button>
      </form>
    </section>
  );
}

function DetectionPanel({ detection }: { detection: Detection }) {
  return (
    <section className={`detection-panel ${detection.severity}`}>
      <div>
        <p className="eyebrow">Latest Detection</p>
        <h2>{detection.disease_label}</h2>
        <p>{detection.recommendation.summary}</p>
      </div>
      <div className="detection-meta">
        <span>Confidence {(Number(detection.confidence) * 100).toFixed(1)}%</span>
        {detection.affected_area_pct ? <span>Affected {detection.affected_area_pct}%</span> : null}
        <span>{detection.severity} severity</span>
      </div>
      <ul>
        {detection.recommendation.actions.map((action) => (
          <li key={action}>{action}</li>
        ))}
      </ul>
    </section>
  );
}

function ListPanel({
  id,
  title,
  empty,
  items
}: {
  id?: string;
  title: string;
  empty: string;
  items: Array<{ id: string; title: string; detail: string; href?: string }>;
}) {
  return (
    <section id={id} className="panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Activity</p>
          <h2>{title}</h2>
        </div>
      </div>
      <div className="list">
        {items.length === 0 ? <p className="empty">{empty}</p> : null}
        {items.map((item) => (
          <article className="list-row" key={item.id}>
            <div>
              <strong>{item.title}</strong>
              <span>{item.detail}</span>
            </div>
            {item.href ? (
              <a className="icon-link" href={item.href} target="_blank" rel="noreferrer" title="Download">
                <FileDown size={18} />
              </a>
            ) : null}
          </article>
        ))}
      </div>
    </section>
  );
}

function nullableString(value: FormDataEntryValue | null): string | null {
  const next = String(value ?? "").trim();
  return next.length > 0 ? next : null;
}

function errorMessage(error: unknown) {
  if (error instanceof ApiError) {
    return `${error.status}: ${error.message}`;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Request failed";
}
