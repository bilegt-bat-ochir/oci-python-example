from __future__ import annotations

import json
from html import escape
from pathlib import Path

from .models import Inventory


def write_dashboard(inventory: Inventory, output_path: str | Path) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_dashboard(inventory), encoding="utf-8")
    return output


def render_dashboard(inventory: Inventory) -> str:
    payload = json.dumps(inventory.to_dict(), ensure_ascii=True).replace("</", "<\\/")
    title = f"ExaCC Operations - {inventory.tenant_name or 'Inventory'}"
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f6f7f9;
      --panel: #ffffff;
      --ink: #172033;
      --muted: #667085;
      --line: #d9dee8;
      --line-strong: #c6cedb;
      --blue: #2557a7;
      --green: #1f7a4d;
      --amber: #a15c0b;
      --red: #b42318;
      --cyan: #0e7490;
      --shadow: 0 12px 30px rgba(16, 24, 40, 0.08);
      --radius: 8px;
    }}

    * {{ box-sizing: border-box; }}

    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      letter-spacing: 0;
    }}

    a {{ color: var(--blue); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}

    .shell {{
      min-height: 100vh;
      display: grid;
      grid-template-columns: minmax(224px, 260px) minmax(0, 1fr);
    }}

    .rail {{
      background: #101828;
      color: #f8fafc;
      padding: 24px 18px;
      display: flex;
      flex-direction: column;
      gap: 22px;
    }}

    .brand {{
      display: flex;
      align-items: center;
      gap: 12px;
      min-width: 0;
    }}

    .mark {{
      width: 38px;
      height: 38px;
      border-radius: 8px;
      background: #e84d2a;
      color: #fff;
      display: grid;
      place-items: center;
      font-weight: 800;
    }}

    .brand h1 {{
      font-size: 16px;
      line-height: 1.2;
      margin: 0;
      overflow-wrap: anywhere;
    }}

    .brand small {{
      color: #aeb8c7;
      display: block;
      font-size: 12px;
      margin-top: 3px;
    }}

    .nav {{
      display: grid;
      gap: 6px;
    }}

    .profile-loader {{
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-radius: 8px;
      background: #182230;
      padding: 14px;
      display: grid;
      gap: 12px;
    }}

    .loader-title {{
      color: #ffffff;
      font-size: 13px;
      font-weight: 800;
      text-transform: uppercase;
    }}

    .field {{
      display: grid;
      gap: 6px;
      min-width: 0;
    }}

    .field span, .check-row span {{
      color: #c7d0df;
      font-size: 12px;
      font-weight: 700;
    }}

    .field input {{
      width: 100%;
      min-width: 0;
      height: 36px;
      border: 1px solid rgba(255, 255, 255, 0.18);
      border-radius: 8px;
      background: #101828;
      color: #ffffff;
      padding: 0 10px;
      font: inherit;
      outline: 0;
    }}

    .field input:focus {{
      border-color: #7aa7ff;
      box-shadow: 0 0 0 3px rgba(122, 167, 255, 0.18);
    }}

    .check-row {{
      display: flex;
      align-items: center;
      gap: 9px;
      min-height: 28px;
    }}

    .check-row input {{
      width: 16px;
      height: 16px;
      accent-color: #7aa7ff;
    }}

    .loader-actions {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) 40px;
      gap: 8px;
    }}

    .load-button, .secondary-icon-button {{
      border-radius: 8px;
      cursor: pointer;
      font: inherit;
      min-height: 38px;
    }}

    .load-button {{
      border: 0;
      background: #e84d2a;
      color: #ffffff;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      padding: 0 12px;
      font-weight: 800;
    }}

    .load-button:hover {{
      background: #d83f1e;
    }}

    .load-button:disabled, .secondary-icon-button:disabled {{
      cursor: wait;
      opacity: 0.72;
    }}

    .secondary-icon-button {{
      border: 1px solid rgba(255, 255, 255, 0.18);
      background: #101828;
      color: #ffffff;
      display: grid;
      place-items: center;
      width: 40px;
    }}

    .secondary-icon-button:hover {{
      border-color: rgba(255, 255, 255, 0.34);
    }}

    .status-message {{
      min-height: 17px;
      color: #aeb8c7;
      font-size: 12px;
      line-height: 1.4;
      overflow-wrap: anywhere;
    }}

    .status-message[data-tone="healthy"] {{ color: #9ee0b8; }}
    .status-message[data-tone="attention"] {{ color: #ffd090; }}
    .status-message[data-tone="critical"] {{ color: #ffb4ac; }}

    .tab {{
      border: 0;
      border-radius: 8px;
      background: transparent;
      color: #d0d5dd;
      cursor: pointer;
      display: grid;
      grid-template-columns: 22px 1fr auto;
      gap: 10px;
      align-items: center;
      min-height: 42px;
      padding: 0 12px;
      text-align: left;
      font: inherit;
    }}

    .tab:hover, .tab[aria-selected="true"] {{
      background: #1d2939;
      color: #ffffff;
    }}

    .tab .count {{
      color: #aeb8c7;
      font-size: 12px;
    }}

    .icon {{
      width: 18px;
      height: 18px;
      flex: 0 0 18px;
      stroke: currentColor;
      fill: none;
      stroke-width: 2;
      stroke-linecap: round;
      stroke-linejoin: round;
    }}

    main {{
      min-width: 0;
      display: flex;
      flex-direction: column;
    }}

    .topbar {{
      background: var(--panel);
      border-bottom: 1px solid var(--line);
      padding: 18px 24px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 18px;
      position: sticky;
      top: 0;
      z-index: 3;
    }}

    .headline {{
      min-width: 0;
    }}

    .headline h2 {{
      margin: 0;
      font-size: clamp(20px, 2.4vw, 30px);
      line-height: 1.15;
    }}

    .headline p {{
      color: var(--muted);
      margin: 6px 0 0;
      font-size: 13px;
    }}

    .actions {{
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }}

    .search {{
      width: min(360px, 44vw);
      min-width: 220px;
      display: flex;
      align-items: center;
      gap: 8px;
      border: 1px solid var(--line);
      background: #fff;
      border-radius: 8px;
      padding: 0 11px;
      height: 38px;
    }}

    .search input {{
      border: 0;
      outline: 0;
      width: 100%;
      min-width: 0;
      font: inherit;
      color: var(--ink);
    }}

    .icon-button {{
      width: 38px;
      height: 38px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      color: var(--ink);
      display: grid;
      place-items: center;
      cursor: pointer;
    }}

    .icon-button:hover {{
      border-color: var(--line-strong);
      box-shadow: 0 2px 8px rgba(16, 24, 40, 0.08);
    }}

    .content {{
      padding: 24px;
      display: grid;
      gap: 20px;
    }}

    .metrics {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 14px;
    }}

    .metric {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
      min-width: 0;
      box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
    }}

    .metric span {{
      color: var(--muted);
      display: block;
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
    }}

    .metric strong {{
      display: block;
      font-size: 28px;
      line-height: 1;
      margin-top: 10px;
      overflow-wrap: anywhere;
    }}

    .metric small {{
      display: block;
      color: var(--muted);
      margin-top: 9px;
      line-height: 1.4;
    }}

    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
      min-width: 0;
      overflow: hidden;
    }}

    .panel-header {{
      padding: 16px 18px;
      border-bottom: 1px solid var(--line);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 14px;
    }}

    .panel-header h3 {{
      margin: 0;
      font-size: 16px;
    }}

    .panel-header span {{
      color: var(--muted);
      font-size: 13px;
    }}

    .table-wrap {{
      overflow-x: auto;
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
      min-width: 920px;
    }}

    th, td {{
      padding: 13px 14px;
      border-bottom: 1px solid #edf0f5;
      text-align: left;
      vertical-align: top;
      font-size: 13px;
    }}

    th {{
      background: #f9fafb;
      color: #475467;
      font-size: 12px;
      text-transform: uppercase;
      white-space: nowrap;
    }}

    tr:hover td {{
      background: #fbfdff;
    }}

    .name-cell {{
      display: grid;
      gap: 5px;
      min-width: 220px;
    }}

    .muted {{
      color: var(--muted);
    }}

    .ocid {{
      color: #667085;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 11px;
      max-width: 360px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}

    .pill {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      border-radius: 999px;
      padding: 4px 9px;
      font-size: 12px;
      font-weight: 700;
      white-space: nowrap;
    }}

    .pill::before {{
      content: "";
      width: 7px;
      height: 7px;
      border-radius: 999px;
      background: currentColor;
    }}

    .healthy {{ color: var(--green); background: #eaf7ef; }}
    .attention {{ color: var(--amber); background: #fff4e5; }}
    .critical {{ color: var(--red); background: #feeceb; }}
    .neutral {{ color: var(--cyan); background: #e7f7fb; }}

    .bar {{
      height: 9px;
      background: #e8edf4;
      border-radius: 999px;
      overflow: hidden;
      min-width: 130px;
      margin-top: 7px;
    }}

    .bar span {{
      display: block;
      height: 100%;
      background: linear-gradient(90deg, #2557a7, #1f7a4d);
    }}

    .empty {{
      padding: 42px 20px;
      text-align: center;
      color: var(--muted);
    }}

    .overview {{
      display: grid;
      grid-template-columns: minmax(0, 1.1fr) minmax(320px, 0.9fr);
      gap: 20px;
    }}

    .filter-banner {{
      background: #eaf1ff;
      border: 1px solid #c8d8f7;
      color: #1f3f72;
      border-radius: 8px;
      padding: 12px 14px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      font-size: 13px;
    }}

    .filter-banner button {{
      border: 1px solid #aac0ea;
      background: #ffffff;
      color: #1f3f72;
      border-radius: 8px;
      cursor: pointer;
      min-height: 32px;
      padding: 0 10px;
      font: inherit;
      font-weight: 700;
    }}

    .compartment-layout {{
      display: grid;
      grid-template-columns: minmax(280px, 0.85fr) minmax(0, 1.15fr);
      gap: 20px;
      align-items: start;
    }}

    .compartment-list {{
      display: grid;
      gap: 4px;
      padding: 10px;
      max-height: 680px;
      overflow: auto;
    }}

    .compartment-button {{
      width: 100%;
      border: 1px solid transparent;
      border-radius: 8px;
      background: transparent;
      color: var(--ink);
      cursor: pointer;
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 12px;
      align-items: center;
      min-height: 40px;
      padding: 7px 10px;
      text-align: left;
      font: inherit;
    }}

    .compartment-button:hover {{
      background: #f6f8fb;
      border-color: var(--line);
    }}

    .compartment-button[aria-selected="true"] {{
      background: #eef4ff;
      border-color: #bfd0f1;
      color: #1f3f72;
    }}

    .compartment-name {{
      display: flex;
      align-items: center;
      gap: 8px;
      min-width: 0;
    }}

    .compartment-name strong {{
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}

    .compartment-counts {{
      color: var(--muted);
      font-size: 12px;
      white-space: nowrap;
    }}

    .resource-list {{
      display: grid;
      gap: 10px;
      padding: 14px;
    }}

    .resource-row {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 12px;
      align-items: start;
    }}

    .resource-row strong {{
      display: block;
      margin-bottom: 4px;
      overflow-wrap: anywhere;
    }}

    .resource-kind {{
      color: var(--muted);
      font-size: 12px;
      font-weight: 800;
      text-transform: uppercase;
      white-space: nowrap;
    }}

    .capacity-list {{
      display: grid;
      gap: 14px;
      padding: 18px;
    }}

    .capacity-row {{
      display: grid;
      gap: 7px;
    }}

    .capacity-line {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      font-size: 13px;
    }}

    @media (max-width: 920px) {{
      .shell {{ grid-template-columns: 1fr; }}
      .rail {{
        position: static;
        padding: 16px;
      }}
      .nav {{
        display: flex;
        overflow-x: auto;
        padding-bottom: 2px;
      }}
      .profile-loader {{
        max-width: 520px;
      }}
      .tab {{
        min-width: max-content;
      }}
      .topbar {{
        position: static;
        align-items: stretch;
        flex-direction: column;
      }}
      .actions {{
        justify-content: flex-start;
      }}
      .search {{
        width: 100%;
      }}
      .metrics {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }}
      .overview {{
        grid-template-columns: 1fr;
      }}
      .compartment-layout {{
        grid-template-columns: 1fr;
      }}
    }}

    @media (max-width: 560px) {{
      .content, .topbar {{ padding: 16px; }}
      .metrics {{ grid-template-columns: 1fr; }}
      .brand h1 {{ font-size: 15px; }}
      .headline h2 {{ font-size: 22px; }}
    }}
  </style>
</head>
<body>
  <script id="inventory-data" type="application/json">{payload}</script>
  <div class="shell">
    <aside class="rail">
      <div class="brand">
        <div class="mark" aria-hidden="true">EX</div>
        <div>
          <h1>ExaCC Operations</h1>
          <small id="tenantLabel"></small>
        </div>
      </div>
      <nav class="nav" aria-label="Inventory views">
        <button class="tab" type="button" data-view="overview" aria-selected="true">
          <svg class="icon" aria-hidden="true" viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="9"></rect><rect x="14" y="3" width="7" height="5"></rect><rect x="14" y="12" width="7" height="9"></rect><rect x="3" y="16" width="7" height="5"></rect></svg>
          <span>Overview</span><span class="count" id="overviewCount"></span>
        </button>
        <button class="tab" type="button" data-view="compartments" aria-selected="false">
          <svg class="icon" aria-hidden="true" viewBox="0 0 24 24"><path d="M3 6h6l2 2h10v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6z"></path><path d="M3 10h18"></path></svg>
          <span>Compartments</span><span class="count" id="compartmentCount"></span>
        </button>
        <button class="tab" type="button" data-view="infrastructures" aria-selected="false">
          <svg class="icon" aria-hidden="true" viewBox="0 0 24 24"><path d="M4 6h16"></path><path d="M4 12h16"></path><path d="M4 18h16"></path><path d="M7 6v12"></path><path d="M17 6v12"></path></svg>
          <span>Infrastructure</span><span class="count" id="infraCount"></span>
        </button>
        <button class="tab" type="button" data-view="vm_clusters" aria-selected="false">
          <svg class="icon" aria-hidden="true" viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="6"></rect><rect x="3" y="14" width="18" height="6"></rect><path d="M7 7h.01"></path><path d="M7 17h.01"></path></svg>
          <span>VM Clusters</span><span class="count" id="vmCount"></span>
        </button>
        <button class="tab" type="button" data-view="autonomous_vm_clusters" aria-selected="false">
          <svg class="icon" aria-hidden="true" viewBox="0 0 24 24"><path d="M12 3l8 4v6c0 4.5-3.2 7.4-8 8-4.8-.6-8-3.5-8-8V7l8-4z"></path><path d="M9 12l2 2 4-5"></path></svg>
          <span>Autonomous</span><span class="count" id="autoCount"></span>
        </button>
      </nav>
      <form class="profile-loader" id="profileForm">
        <div class="loader-title">Load OCI Profile</div>
        <label class="field">
          <span>Profile</span>
          <input id="profileInput" list="profileOptions" autocomplete="off" value="DEFAULT">
          <datalist id="profileOptions"></datalist>
        </label>
        <label class="field">
          <span>Config file</span>
          <input id="configFileInput" autocomplete="off" value="~/.oci/config">
        </label>
        <label class="check-row">
          <input id="allRegionsInput" type="checkbox">
          <span>All regions</span>
        </label>
        <div class="loader-actions">
          <button class="load-button" id="loadProfileButton" type="submit">
            <svg class="icon" aria-hidden="true" viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><path d="M7 10l5 5 5-5"></path><path d="M12 15V3"></path></svg>
            <span class="button-label">Load</span>
          </button>
          <button class="secondary-icon-button" id="demoButton" type="button" title="Load demo inventory" aria-label="Load demo inventory">
            <svg class="icon" aria-hidden="true" viewBox="0 0 24 24"><path d="M12 2v4"></path><path d="M12 18v4"></path><path d="M4.93 4.93l2.83 2.83"></path><path d="M16.24 16.24l2.83 2.83"></path><path d="M2 12h4"></path><path d="M18 12h4"></path><path d="M4.93 19.07l2.83-2.83"></path><path d="M16.24 7.76l2.83-2.83"></path></svg>
          </button>
        </div>
        <div class="status-message" id="profileStatus" role="status"></div>
      </form>
    </aside>
    <main>
      <header class="topbar">
        <div class="headline">
          <h2 id="viewTitle">Overview</h2>
          <p id="viewMeta"></p>
        </div>
        <div class="actions">
          <label class="search">
            <svg class="icon" aria-hidden="true" viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"></circle><path d="M20 20l-3.5-3.5"></path></svg>
            <input id="searchInput" type="search" autocomplete="off" aria-label="Search inventory">
          </label>
          <button class="icon-button" id="downloadButton" type="button" title="Export JSON" aria-label="Export JSON">
            <svg class="icon" aria-hidden="true" viewBox="0 0 24 24"><path d="M12 3v12"></path><path d="M7 10l5 5 5-5"></path><path d="M5 21h14"></path></svg>
          </button>
        </div>
      </header>
      <section class="content" id="content"></section>
    </main>
  </div>
  <script>
    let inventory = normalizeInventory(JSON.parse(document.getElementById("inventory-data").textContent));
    let summary = inventory.summary || {{}};
    const state = {{ view: "overview", query: "", loading: false, compartmentPath: "root" }};

    const icons = {{
      open: '<svg class="icon" aria-hidden="true" viewBox="0 0 24 24"><path d="M7 17L17 7"></path><path d="M8 7h9v9"></path></svg>'
    }};

    function escapeHtml(value) {{
      return String(value ?? "").replace(/[&<>"']/g, (char) => ({{
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
      }}[char]));
    }}

    function number(value) {{
      return new Intl.NumberFormat().format(value || 0);
    }}

    function normalizeInventory(data) {{
      return {{
        tenant_name: data.tenant_name || "OCI tenant",
        home_region: data.home_region || "",
        generated_at: data.generated_at || "",
        regions: data.regions || [],
        compartments: data.compartments || [],
        infrastructures: data.infrastructures || [],
        vm_clusters: data.vm_clusters || [],
        autonomous_vm_clusters: data.autonomous_vm_clusters || [],
        summary: data.summary || {{}}
      }};
    }}

    function setInventory(nextInventory) {{
      inventory = normalizeInventory(nextInventory);
      summary = inventory.summary || {{}};
      state.compartmentPath = "root";
      document.title = `ExaCC Operations - ${{inventory.tenant_name || "Inventory"}}`;
      setCounts();
      render();
    }}

    function statusTone(status) {{
      const normalized = String(status || "").toUpperCase();
      if (["ACTIVE", "AVAILABLE"].includes(normalized)) return "healthy";
      if (["PROVISIONING", "UPDATING", "TERMINATING", "MAINTENANCE_IN_PROGRESS", "SCALE_IN_PROGRESS", "BACKUP_IN_PROGRESS"].includes(normalized)) return "attention";
      if (["FAILED", "INACTIVE", "REQUIRES_ACTIVATION", "TERMINATED", "UNAVAILABLE"].includes(normalized)) return "critical";
      return "neutral";
    }}

    function pill(status) {{
      const value = escapeHtml(status || "UNKNOWN");
      return `<span class="pill ${{statusTone(status)}}">${{value}}</span>`;
    }}

    function resourceLink(item) {{
      if (!item.console_url) return escapeHtml(item.display_name || item.id);
      return `<a href="${{escapeHtml(item.console_url)}}" target="_blank" rel="noreferrer">${{escapeHtml(item.display_name || item.id)}}</a>`;
    }}

    function nameCell(item) {{
      return `<div class="name-cell"><strong>${{resourceLink(item)}}</strong><span class="ocid" title="${{escapeHtml(item.id)}}">${{escapeHtml(item.id)}}</span></div>`;
    }}

    function matchesQuery(item) {{
      if (!state.query) return true;
      const haystack = [
        item.display_name, item.id, item.region, item.compartment_path,
        item.lifecycle_state, item.shape, item.exadata_infrastructure_name,
        item.gi_version, item.system_version
      ].join(" ").toLowerCase();
      return haystack.includes(state.query);
    }}

    function matchesCompartment(item) {{
      const selected = state.compartmentPath || "root";
      if (selected === "root") return true;
      const path = item.compartment_path || "";
      return path === selected || path.startsWith(`${{selected}}:`);
    }}

    function visibleItems(items) {{
      return items.filter((item) => matchesCompartment(item) && matchesQuery(item));
    }}

    function allResources() {{
      return [
        ...inventory.infrastructures.map((item) => ({{ ...item, kind: "Infrastructure" }})),
        ...inventory.vm_clusters.map((item) => ({{ ...item, kind: "VM Cluster" }})),
        ...inventory.autonomous_vm_clusters.map((item) => ({{ ...item, kind: "Autonomous VM Cluster" }}))
      ];
    }}

    function scopedResources() {{
      return allResources().filter(matchesCompartment);
    }}

    function scopedSummary() {{
      const infra = inventory.infrastructures.filter(matchesCompartment);
      const vms = inventory.vm_clusters.filter(matchesCompartment);
      const autonomous = inventory.autonomous_vm_clusters.filter(matchesCompartment);
      const resources = [...infra, ...vms, ...autonomous];
      const healthy = resources.filter((item) => statusTone(item.lifecycle_state) === "healthy").length;
      const ocpus = infra.reduce((total, item) => total + (item.cpus_enabled || 0), 0);
      const capacity = infra.reduce((total, item) => total + (item.max_cpu_count || 0), 0);
      return {{
        resources: resources.length,
        healthy,
        attention: resources.length - healthy,
        regions: new Set(resources.map((item) => item.region).filter(Boolean)).size,
        ocpus,
        capacity,
        capacityPct: capacity ? Math.round((ocpus / capacity) * 1000) / 10 : 0,
        memory: vms.reduce((total, item) => total + (item.memory_size_in_gbs || 0), 0),
        clusters: vms.length + autonomous.length
      }};
    }}

    function synthesizeCompartments() {{
      const byPath = new Map();
      byPath.set("root", {{
        id: "root",
        name: "root",
        parent_id: "",
        path: "root",
        lifecycle_state: "ACTIVE"
      }});
      allResources().forEach((item) => {{
        const parts = String(item.compartment_path || "").split(":").filter(Boolean);
        let current = "";
        parts.forEach((part, index) => {{
          current = current ? `${{current}}:${{part}}` : part;
          if (!byPath.has(current)) {{
            const parent = index === 0 ? "root" : parts.slice(0, index).join(":");
            byPath.set(current, {{
              id: current,
              name: part,
              parent_id: parent,
              path: current,
              lifecycle_state: "ACTIVE"
            }});
          }}
        }});
      }});
      return Array.from(byPath.values());
    }}

    function compartmentsForUI() {{
      const source = inventory.compartments && inventory.compartments.length
        ? inventory.compartments
        : synthesizeCompartments();
      const unique = new Map();
      source.forEach((item) => unique.set(item.path || item.id, item));
      if (!unique.has("root")) {{
        unique.set("root", {{
          id: "root",
          name: "root",
          parent_id: "",
          path: "root",
          lifecycle_state: "ACTIVE"
        }});
      }}
      return Array.from(unique.values()).sort((a, b) => {{
        if (a.path === "root") return -1;
        if (b.path === "root") return 1;
        return String(a.path).localeCompare(String(b.path));
      }});
    }}

    function compartmentMatch(path, selected) {{
      if (selected === "root") return true;
      return path === selected || String(path || "").startsWith(`${{selected}}:`);
    }}

    function compartmentCounts(path) {{
      const resources = allResources();
      return {{
        direct: resources.filter((item) => (item.compartment_path || "") === path).length,
        total: resources.filter((item) => compartmentMatch(item.compartment_path || "", path)).length
      }};
    }}

    function setCounts() {{
      document.getElementById("tenantLabel").textContent = inventory.tenant_name || "OCI tenant";
      document.getElementById("overviewCount").textContent = number(summary.resource_count);
      document.getElementById("compartmentCount").textContent = number(compartmentsForUI().length);
      document.getElementById("infraCount").textContent = number(inventory.infrastructures.length);
      document.getElementById("vmCount").textContent = number(inventory.vm_clusters.length);
      document.getElementById("autoCount").textContent = number(inventory.autonomous_vm_clusters.length);
    }}

    function apiAvailable() {{
      return window.location.protocol === "http:" || window.location.protocol === "https:";
    }}

    function setProfileStatus(message, tone = "neutral") {{
      const status = document.getElementById("profileStatus");
      status.textContent = message || "";
      status.dataset.tone = tone;
    }}

    function setLoaderBusy(isBusy) {{
      state.loading = isBusy;
      const loadButton = document.getElementById("loadProfileButton");
      const demoButton = document.getElementById("demoButton");
      loadButton.disabled = isBusy;
      demoButton.disabled = isBusy;
      loadButton.querySelector(".button-label").textContent = isBusy ? "Loading" : "Load";
    }}

    async function readJson(response) {{
      const text = await response.text();
      const data = text ? JSON.parse(text) : {{}};
      if (!response.ok) {{
        throw new Error(data.error || `Request failed with status ${{response.status}}`);
      }}
      return data;
    }}

    function profilePayload(extra = {{}}) {{
      return {{
        profile: document.getElementById("profileInput").value.trim(),
        config_file: document.getElementById("configFileInput").value.trim() || "~/.oci/config",
        all_regions: document.getElementById("allRegionsInput").checked,
        ...extra
      }};
    }}

    async function refreshProfiles() {{
      if (!apiAvailable()) {{
        setProfileStatus("Local server unavailable", "attention");
        return;
      }}
      const configFile = document.getElementById("configFileInput").value.trim() || "~/.oci/config";
      try {{
        const response = await fetch(`/api/profiles?config_file=${{encodeURIComponent(configFile)}}`);
        const data = await readJson(response);
        const options = document.getElementById("profileOptions");
        options.innerHTML = (data.profiles || [])
          .map((profile) => `<option value="${{escapeHtml(profile)}}"></option>`)
          .join("");
        const input = document.getElementById("profileInput");
        if (!input.value && data.profiles && data.profiles.length) {{
          input.value = data.profiles.includes("DEFAULT") ? "DEFAULT" : data.profiles[0];
        }}
        if (data.profiles && data.profiles.length) {{
          setProfileStatus(`${{data.profiles.length}} profile${{data.profiles.length === 1 ? "" : "s"}} found`, "healthy");
        }} else {{
          setProfileStatus("No profiles found", "attention");
        }}
      }} catch (error) {{
        setProfileStatus(error.message, "critical");
      }}
    }}

    async function loadInventory(payload) {{
      if (!apiAvailable()) {{
        setProfileStatus("Run the local server to load OCI profiles", "attention");
        return;
      }}
      setLoaderBusy(true);
      setProfileStatus(payload.sample ? "Loading demo inventory" : `Loading ${{payload.profile}}`, "neutral");
      try {{
        const response = await fetch("/api/inventory", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify(payload)
        }});
        const data = await readJson(response);
        setInventory(data);
        setProfileStatus(payload.sample ? "Demo inventory loaded" : `${{payload.profile}} loaded`, "healthy");
      }} catch (error) {{
        setProfileStatus(error.message, "critical");
      }} finally {{
        setLoaderBusy(false);
      }}
    }}

    function metric(label, value, note) {{
      return `<article class="metric"><span>${{label}}</span><strong>${{value}}</strong><small>${{note}}</small></article>`;
    }}

    function renderMetrics() {{
      const current = scopedSummary();
      return `<div class="metrics">
        ${{metric("Resources", number(current.resources), `${{number(current.healthy)}} healthy, ${{number(current.attention)}} need attention`)}}
        ${{metric("Regions", number(current.regions), escapeHtml((inventory.regions || []).join(", ")) || "No regions")}}
        ${{metric("OCPU Capacity", `${{number(current.ocpus)}} / ${{number(current.capacity)}}`, `${{current.capacityPct || 0}}% enabled`)}}
        ${{metric("VM Memory", `${{number(current.memory)}} GB`, `${{number(current.clusters)}} total clusters`)}}
      </div>`;
    }}

    function renderCapacityPanel() {{
      const rows = visibleItems(inventory.infrastructures).map((item) => {{
        const used = item.max_cpu_count ? Math.min(100, (item.cpus_enabled / item.max_cpu_count) * 100) : 0;
        return `<div class="capacity-row">
          <div class="capacity-line"><strong>${{resourceLink(item)}}</strong><span>${{number(item.cpus_enabled)}} / ${{number(item.max_cpu_count)}} OCPUs</span></div>
          <div class="bar" aria-hidden="true"><span style="width: ${{used}}%"></span></div>
        </div>`;
      }}).join("");
      return `<section class="panel">
        <div class="panel-header"><h3>Infrastructure Capacity</h3><span>${{number(visibleItems(inventory.infrastructures).length)}} rows</span></div>
        <div class="capacity-list">${{rows || '<div class="empty">No infrastructure found</div>'}}</div>
      </section>`;
    }}

    function renderStatusPanel() {{
      const resources = [
        ...inventory.infrastructures.map((item) => ({{ ...item, kind: "Infrastructure" }})),
        ...inventory.vm_clusters.map((item) => ({{ ...item, kind: "VM Cluster" }})),
        ...inventory.autonomous_vm_clusters.map((item) => ({{ ...item, kind: "Autonomous VM Cluster" }}))
      ].filter((item) => matchesCompartment(item) && matchesQuery(item) && statusTone(item.lifecycle_state) !== "healthy");

      const rows = resources.map((item) => `<tr>
        <td>${{nameCell(item)}}</td>
        <td>${{escapeHtml(item.kind)}}</td>
        <td>${{escapeHtml(item.region)}}</td>
        <td>${{pill(item.lifecycle_state)}}</td>
      </tr>`).join("");

      return `<section class="panel">
        <div class="panel-header"><h3>Status Watch</h3><span>${{number(resources.length)}} rows</span></div>
        <div class="table-wrap">
          <table><thead><tr><th>Name</th><th>Type</th><th>Region</th><th>Status</th></tr></thead>
          <tbody>${{rows || '<tr><td class="empty" colspan="4">All resources are healthy</td></tr>'}}</tbody></table>
        </div>
      </section>`;
    }}

    function renderFilterBanner() {{
      if ((state.compartmentPath || "root") === "root") return "";
      return `<div class="filter-banner">
        <span>Compartment filter: <strong>${{escapeHtml(state.compartmentPath)}}</strong></span>
        <button type="button" id="clearCompartmentButton">Clear</button>
      </div>`;
    }}

    function renderCompartmentBrowser() {{
      const compartments = compartmentsForUI();
      const selected = state.compartmentPath || "root";
      const rows = compartments.map((item) => {{
        const path = item.path || item.id;
        const level = path === "root" ? 0 : String(path).split(":").length;
        const counts = compartmentCounts(path);
        return `<button class="compartment-button" type="button" data-compartment-path="${{escapeHtml(path)}}" aria-selected="${{String(path === selected)}}">
          <span class="compartment-name" style="padding-left: ${{Math.max(0, level - 1) * 16}}px">
            <svg class="icon" aria-hidden="true" viewBox="0 0 24 24"><path d="M3 6h6l2 2h10v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6z"></path></svg>
            <strong>${{escapeHtml(item.name || path)}}</strong>
          </span>
          <span class="compartment-counts">${{number(counts.total)}} total</span>
        </button>`;
      }}).join("");

      const resources = scopedResources().filter(matchesQuery);
      const resourceRows = resources.map((item) => `<div class="resource-row">
        <div>
          <strong>${{resourceLink(item)}}</strong>
          <div class="muted">${{escapeHtml(item.compartment_path || "root")}} - ${{escapeHtml(item.region || "-")}}</div>
        </div>
        <div>
          <div class="resource-kind">${{escapeHtml(item.kind)}}</div>
          <div>${{pill(item.lifecycle_state)}}</div>
        </div>
      </div>`).join("");

      return `<div class="compartment-layout">
        <section class="panel">
          <div class="panel-header"><h3>Compartment Browser</h3><span>${{number(compartments.length)}} compartments</span></div>
          <div class="compartment-list">${{rows || '<div class="empty">No compartments found</div>'}}</div>
        </section>
        <section class="panel">
          <div class="panel-header"><h3>${{escapeHtml(selected)}}</h3><span>${{number(resources.length)}} matching resources</span></div>
          <div class="resource-list">${{resourceRows || '<div class="empty">No resources in this compartment scope</div>'}}</div>
        </section>
      </div>`;
    }}

    function infraRows() {{
      const rows = visibleItems(inventory.infrastructures).map((item) => {{
        const used = item.max_cpu_count ? Math.min(100, (item.cpus_enabled / item.max_cpu_count) * 100) : 0;
        return `<tr>
          <td>${{nameCell(item)}}</td>
          <td>${{escapeHtml(item.region)}}</td>
          <td>${{escapeHtml(item.compartment_path)}}</td>
          <td>${{escapeHtml(item.shape)}}</td>
          <td>${{number(item.compute_count)}} / ${{number(item.storage_count)}}</td>
          <td>${{number(item.cpus_enabled)}} / ${{number(item.max_cpu_count)}}<div class="bar" aria-hidden="true"><span style="width:${{used}}%"></span></div></td>
          <td>${{pill(item.lifecycle_state)}}</td>
        </tr>`;
      }}).join("");
      return tablePanel("Infrastructure", rows, "<th>Name</th><th>Region</th><th>Compartment</th><th>Shape</th><th>Compute / Storage</th><th>OCPUs</th><th>Status</th>", 7);
    }}

    function vmRows() {{
      const rows = visibleItems(inventory.vm_clusters).map((item) => `<tr>
        <td>${{nameCell(item)}}</td>
        <td>${{escapeHtml(item.region)}}</td>
        <td>${{escapeHtml(item.compartment_path)}}</td>
        <td>${{pill(item.lifecycle_state)}}</td>
        <td>${{number(item.db_node_count)}}</td>
        <td>${{number(item.cpus_enabled)}}</td>
        <td>${{number(item.memory_size_in_gbs)}} GB</td>
        <td>${{escapeHtml(item.gi_version || "-")}}</td>
        <td>${{escapeHtml(item.system_version || "-")}}</td>
        <td>${{escapeHtml(item.exadata_infrastructure_name || "-")}}</td>
      </tr>`).join("");
      return tablePanel("VM Clusters", rows, "<th>Name</th><th>Region</th><th>Compartment</th><th>Status</th><th>DB Nodes</th><th>OCPUs</th><th>Memory</th><th>GI</th><th>Image</th><th>Infrastructure</th>", 10);
    }}

    function autonomousRows() {{
      const rows = visibleItems(inventory.autonomous_vm_clusters).map((item) => `<tr>
        <td>${{nameCell(item)}}</td>
        <td>${{escapeHtml(item.region)}}</td>
        <td>${{escapeHtml(item.compartment_path)}}</td>
        <td>${{pill(item.lifecycle_state)}}</td>
        <td>${{number(item.cpus_enabled)}}</td>
        <td>${{escapeHtml(item.exadata_infrastructure_name || "-")}}</td>
      </tr>`).join("");
      return tablePanel("Autonomous VM Clusters", rows, "<th>Name</th><th>Region</th><th>Compartment</th><th>Status</th><th>OCPUs</th><th>Infrastructure</th>", 6);
    }}

    function tablePanel(title, rows, header, colspan) {{
      const count = (rows.match(/<tr>/g) || []).length;
      return `<section class="panel">
        <div class="panel-header"><h3>${{title}}</h3><span>${{number(count)}} rows</span></div>
        <div class="table-wrap">
          <table><thead><tr>${{header}}</tr></thead>
          <tbody>${{rows || `<tr><td class="empty" colspan="${{colspan}}">No matching resources</td></tr>`}}</tbody></table>
        </div>
      </section>`;
    }}

    function render() {{
      document.querySelectorAll(".tab").forEach((button) => {{
        button.setAttribute("aria-selected", String(button.dataset.view === state.view));
      }});
      const titleMap = {{
        overview: "Overview",
        compartments: "Compartments",
        infrastructures: "Infrastructure",
        vm_clusters: "VM Clusters",
        autonomous_vm_clusters: "Autonomous VM Clusters"
      }};
      document.getElementById("viewTitle").textContent = titleMap[state.view];
      const filterMeta = (state.compartmentPath || "root") === "root" ? "" : ` | compartment ${{state.compartmentPath}}`;
      document.getElementById("viewMeta").textContent = `${{inventory.generated_at}} | home region ${{inventory.home_region || "-"}}${{filterMeta}}`;

      if (state.view === "overview") {{
        document.getElementById("content").innerHTML = `${{renderFilterBanner()}}${{renderMetrics()}}<div class="overview">${{renderCapacityPanel()}}${{renderStatusPanel()}}</div>`;
      }} else if (state.view === "compartments") {{
        document.getElementById("content").innerHTML = `${{renderMetrics()}}${{renderCompartmentBrowser()}}`;
      }} else if (state.view === "infrastructures") {{
        document.getElementById("content").innerHTML = `${{renderFilterBanner()}}${{renderMetrics()}}${{infraRows()}}`;
      }} else if (state.view === "vm_clusters") {{
        document.getElementById("content").innerHTML = `${{renderFilterBanner()}}${{renderMetrics()}}${{vmRows()}}`;
      }} else {{
        document.getElementById("content").innerHTML = `${{renderFilterBanner()}}${{renderMetrics()}}${{autonomousRows()}}`;
      }}
    }}

    document.querySelectorAll(".tab").forEach((button) => {{
      button.addEventListener("click", () => {{
        state.view = button.dataset.view;
        render();
      }});
    }});

    document.getElementById("searchInput").addEventListener("input", (event) => {{
      state.query = event.target.value.trim().toLowerCase();
      render();
    }});

    document.getElementById("content").addEventListener("click", (event) => {{
      const compartmentButton = event.target.closest("[data-compartment-path]");
      if (compartmentButton) {{
        state.compartmentPath = compartmentButton.dataset.compartmentPath || "root";
        render();
        return;
      }}
      if (event.target.closest("#clearCompartmentButton")) {{
        state.compartmentPath = "root";
        render();
      }}
    }});

    document.getElementById("downloadButton").addEventListener("click", () => {{
      const blob = new Blob([JSON.stringify(inventory, null, 2)], {{ type: "application/json" }});
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `exacc-inventory-${{inventory.tenant_name || "tenant"}}.json`;
      link.click();
      URL.revokeObjectURL(url);
    }});

    document.getElementById("profileForm").addEventListener("submit", (event) => {{
      event.preventDefault();
      loadInventory(profilePayload());
    }});

    document.getElementById("demoButton").addEventListener("click", () => {{
      loadInventory(profilePayload({{ sample: true }}));
    }});

    document.getElementById("configFileInput").addEventListener("change", () => {{
      refreshProfiles();
    }});

    setCounts();
    render();
    refreshProfiles();
  </script>
</body>
</html>
"""
