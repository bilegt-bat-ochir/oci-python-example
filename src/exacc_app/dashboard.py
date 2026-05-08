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

    .resource-title {{
      display: inline-grid;
      grid-template-columns: 24px minmax(0, auto);
      gap: 7px;
      align-items: center;
      max-width: 100%;
    }}

    .console-link {{
      width: 24px;
      height: 24px;
      border: 1px solid var(--line);
      border-radius: 8px;
      color: var(--blue);
      display: inline-grid;
      place-items: center;
      background: #ffffff;
      flex: 0 0 24px;
    }}

    .console-link:hover {{
      border-color: #a9bbd9;
      background: #eef4ff;
      text-decoration: none;
    }}

    .console-link .icon {{
      width: 14px;
      height: 14px;
    }}

    .resource-name-button {{
      border: 0;
      background: transparent;
      color: var(--blue);
      cursor: pointer;
      font: inherit;
      font-weight: 800;
      min-width: 0;
      padding: 0;
      text-align: left;
      overflow-wrap: anywhere;
    }}

    .resource-name-button:hover {{
      text-decoration: underline;
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

    .detail-hero {{
      padding: 18px;
      display: grid;
      gap: 14px;
    }}

    .detail-title-row {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 16px;
      flex-wrap: wrap;
    }}

    .detail-title {{
      display: grid;
      gap: 7px;
      min-width: 0;
    }}

    .detail-title h3 {{
      font-size: 22px;
      line-height: 1.2;
      margin: 0;
      overflow-wrap: anywhere;
    }}

    .detail-actions {{
      display: flex;
      align-items: center;
      gap: 9px;
      flex-wrap: wrap;
    }}

    .back-button {{
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #ffffff;
      color: var(--ink);
      cursor: pointer;
      min-height: 34px;
      padding: 0 11px;
      font: inherit;
      font-weight: 800;
    }}

    .back-button:hover {{
      border-color: var(--line-strong);
      box-shadow: 0 2px 8px rgba(16, 24, 40, 0.08);
    }}

    .detail-grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 14px;
    }}

    .detail-field {{
      display: grid;
      gap: 5px;
      min-width: 0;
    }}

    .detail-field span {{
      color: var(--muted);
      font-size: 12px;
      font-weight: 800;
      text-transform: uppercase;
    }}

    .detail-field strong {{
      color: var(--ink);
      font-size: 13px;
      overflow-wrap: anywhere;
    }}

    .stack-list {{
      display: grid;
      gap: 7px;
      min-width: 180px;
    }}

    .stack-item {{
      display: grid;
      gap: 3px;
    }}

    .stack-item small {{
      color: var(--muted);
      font-size: 11px;
      line-height: 1.35;
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

    .metric-controls {{
      padding: 16px 18px;
      border-bottom: 1px solid var(--line);
      display: grid;
      grid-template-columns: repeat(3, minmax(160px, 1fr)) auto;
      gap: 12px;
      align-items: end;
    }}

    .metric-control {{
      display: grid;
      gap: 6px;
      min-width: 0;
    }}

    .metric-control span {{
      color: var(--muted);
      font-size: 12px;
      font-weight: 800;
      text-transform: uppercase;
    }}

    .metric-control input,
    .metric-control select {{
      width: 100%;
      min-width: 0;
      height: 38px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #ffffff;
      color: var(--ink);
      padding: 0 10px;
      font: inherit;
    }}

    .metric-actions {{
      display: flex;
      gap: 8px;
      align-items: center;
      justify-content: flex-end;
      flex-wrap: wrap;
    }}

    .metric-apply-button {{
      border: 0;
      border-radius: 8px;
      background: #2557a7;
      color: #ffffff;
      cursor: pointer;
      min-height: 38px;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 0 12px;
      font: inherit;
      font-weight: 800;
    }}

    .metric-apply-button:hover {{
      background: #1f4b92;
    }}

    .metric-apply-button:disabled,
    .metric-actions .icon-button:disabled {{
      cursor: wait;
      opacity: 0.68;
    }}

    .metric-status {{
      padding: 10px 18px 0;
      color: var(--muted);
      font-size: 12px;
      min-height: 24px;
      overflow-wrap: anywhere;
    }}

    .metric-status[data-tone="critical"] {{
      color: var(--red);
    }}

    .chart-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 16px;
      padding: 16px 18px 18px;
    }}

    .metric-chart {{
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #ffffff;
      min-width: 0;
      overflow: hidden;
    }}

    .metric-chart-head {{
      padding: 14px 14px 0;
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 12px;
    }}

    .metric-chart h4 {{
      margin: 0;
      font-size: 14px;
    }}

    .metric-chart small {{
      color: var(--muted);
      display: block;
      margin-top: 4px;
    }}

    .chart-summary {{
      text-align: right;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.45;
      white-space: nowrap;
    }}

    .chart-summary strong {{
      color: var(--ink);
      display: block;
      font-size: 18px;
    }}

    .chart-svg {{
      width: 100%;
      height: auto;
      display: block;
      padding: 8px 8px 0;
      overflow: visible;
    }}

    .chart-axis {{
      fill: #667085;
      font-size: 10px;
    }}

    .chart-gridline {{
      stroke: #e5e9f0;
      stroke-width: 1;
    }}

    .chart-legend {{
      padding: 0 14px 14px;
      display: flex;
      flex-wrap: wrap;
      gap: 8px 12px;
      color: var(--muted);
      font-size: 12px;
    }}

    .legend-item {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      min-width: 0;
    }}

    .legend-dot {{
      width: 8px;
      height: 8px;
      border-radius: 999px;
      flex: 0 0 8px;
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
      .detail-grid {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }}
      .metric-controls {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }}
      .metric-actions {{
        justify-content: flex-start;
      }}
      .chart-grid {{
        grid-template-columns: 1fr;
      }}
    }}

    @media (max-width: 560px) {{
      .content, .topbar {{ padding: 16px; }}
      .metrics {{ grid-template-columns: 1fr; }}
      .detail-grid {{ grid-template-columns: 1fr; }}
      .metric-controls {{ grid-template-columns: 1fr; }}
      .chart-summary {{ text-align: left; }}
      .metric-chart-head {{ flex-direction: column; }}
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
        <button class="tab" type="button" data-view="db_homes" aria-selected="false">
          <svg class="icon" aria-hidden="true" viewBox="0 0 24 24"><path d="M4 6c0 1.7 3.6 3 8 3s8-1.3 8-3-3.6-3-8-3-8 1.3-8 3z"></path><path d="M4 6v6c0 1.7 3.6 3 8 3s8-1.3 8-3V6"></path><path d="M4 12v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"></path></svg>
          <span>DB Homes</span><span class="count" id="dbHomeCount"></span>
        </button>
        <button class="tab" type="button" data-view="databases" aria-selected="false">
          <svg class="icon" aria-hidden="true" viewBox="0 0 24 24"><ellipse cx="12" cy="5" rx="8" ry="3"></ellipse><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5"></path><path d="M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"></path></svg>
          <span>Databases</span><span class="count" id="databaseCount"></span>
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
    const state = {{
      view: "overview",
      query: "",
      loading: false,
      compartmentPath: "root",
      detailType: "",
      detailId: "",
      detailFromView: "overview",
      inventorySource: {{ sample: false }},
      metricWindows: {{}},
      metricLoads: {{}}
    }};

    const icons = {{
      open: '<svg class="icon" aria-hidden="true" viewBox="0 0 24 24"><path d="M7 17L17 7"></path><path d="M8 7h9v9"></path></svg>',
      refresh: '<svg class="icon" aria-hidden="true" viewBox="0 0 24 24"><path d="M21 12a9 9 0 0 1-15.5 6.2"></path><path d="M3 12A9 9 0 0 1 18.5 5.8"></path><path d="M18 2v4h4"></path><path d="M6 22v-4H2"></path></svg>',
      left: '<svg class="icon" aria-hidden="true" viewBox="0 0 24 24"><path d="M15 18l-6-6 6-6"></path></svg>',
      right: '<svg class="icon" aria-hidden="true" viewBox="0 0 24 24"><path d="M9 18l6-6-6-6"></path></svg>',
      clock: '<svg class="icon" aria-hidden="true" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"></circle><path d="M12 7v5l3 2"></path></svg>'
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
        db_homes: data.db_homes || [],
        databases: data.databases || [],
        pluggable_databases: data.pluggable_databases || [],
        summary: data.summary || {{}}
      }};
    }}

    function setInventory(nextInventory) {{
      inventory = normalizeInventory(nextInventory);
      summary = inventory.summary || {{}};
      state.compartmentPath = "root";
      state.detailType = "";
      state.detailId = "";
      state.detailFromView = "overview";
      state.metricWindows = {{}};
      state.metricLoads = {{}};
      state.view = state.view === "detail" ? "overview" : state.view;
      document.title = `ExaCC Operations - ${{inventory.tenant_name || "Inventory"}}`;
      setCounts();
      render();
    }}

    function statusTone(status) {{
      const normalized = String(status || "").toUpperCase();
      if (["ACTIVE", "AVAILABLE"].includes(normalized)) return "healthy";
      if ([
        "PROVISIONING", "UPDATING", "TERMINATING", "MAINTENANCE_IN_PROGRESS",
        "SCALE_IN_PROGRESS", "BACKUP_IN_PROGRESS", "UPGRADING", "CONVERTING",
        "REFRESHING", "RELOCATING", "RELOCATED", "RESTORE_IN_PROGRESS", "DISABLED"
      ].includes(normalized)) return "attention";
      if (["FAILED", "INACTIVE", "REQUIRES_ACTIVATION", "TERMINATED", "UNAVAILABLE", "RESTORE_FAILED"].includes(normalized)) return "critical";
      return "neutral";
    }}

    function pill(status) {{
      const value = escapeHtml(status || "UNKNOWN");
      return `<span class="pill ${{statusTone(status)}}">${{value}}</span>`;
    }}

    function consoleLink(item) {{
      if (!item.console_url) return "";
      const label = escapeHtml(`Open ${{item.display_name || item.id}} in OCI Console`);
      return `<a class="console-link" href="${{escapeHtml(item.console_url)}}" target="_blank" rel="noreferrer" title="${{label}}" aria-label="${{label}}">${{icons.open}}</a>`;
    }}

    function resourceTitle(item, resourceType) {{
      return `<span class="resource-title">${{consoleLink(item)}}<button class="resource-name-button" type="button" data-detail-type="${{escapeHtml(resourceType)}}" data-detail-id="${{escapeHtml(item.id)}}">${{escapeHtml(item.display_name || item.pdb_name || item.id)}}</button></span>`;
    }}

    function nameCell(item, resourceType) {{
      return `<div class="name-cell"><strong>${{resourceTitle(item, resourceType)}}</strong><span class="ocid" title="${{escapeHtml(item.id)}}">${{escapeHtml(item.id)}}</span></div>`;
    }}

    function matchesQuery(item) {{
      if (!state.query) return true;
      const haystack = [
        item.display_name, item.id, item.region, item.compartment_path,
        item.lifecycle_state, item.shape, item.exadata_infrastructure_name,
        item.gi_version, item.system_version, item.vm_cluster_name,
        item.db_home_name, item.db_name, item.db_unique_name, item.db_version,
        item.db_workload, item.patch_version, item.pdb_name, item.open_mode,
        item.database_name
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
        ...inventory.infrastructures.map((item) => ({{ ...item, kind: "Infrastructure", resource_type: "infrastructure" }})),
        ...inventory.vm_clusters.map((item) => ({{ ...item, kind: "VM Cluster", resource_type: "vm_cluster" }})),
        ...inventory.autonomous_vm_clusters.map((item) => ({{ ...item, kind: "Autonomous VM Cluster", resource_type: "autonomous_vm_cluster" }})),
        ...inventory.db_homes.map((item) => ({{ ...item, kind: "DB Home", resource_type: "db_home" }})),
        ...inventory.databases.map((item) => ({{ ...item, kind: "Database", resource_type: "database" }})),
        ...inventory.pluggable_databases.map((item) => ({{ ...item, kind: "Pluggable Database", resource_type: "pluggable_database" }}))
      ];
    }}

    function scopedResources() {{
      return allResources().filter(matchesCompartment);
    }}

    function scopedSummary() {{
      const infra = inventory.infrastructures.filter(matchesCompartment);
      const vms = inventory.vm_clusters.filter(matchesCompartment);
      const autonomous = inventory.autonomous_vm_clusters.filter(matchesCompartment);
      const dbHomes = inventory.db_homes.filter(matchesCompartment);
      const databases = inventory.databases.filter(matchesCompartment);
      const pdbs = inventory.pluggable_databases.filter(matchesCompartment);
      const resources = [...infra, ...vms, ...autonomous, ...dbHomes, ...databases, ...pdbs];
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
        clusters: vms.length + autonomous.length,
        dbHomes: dbHomes.length,
        databases: databases.length,
        pdbs: pdbs.length
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
      document.getElementById("dbHomeCount").textContent = number(inventory.db_homes.length);
      document.getElementById("databaseCount").textContent = number(inventory.databases.length);
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
        state.inventorySource = {{ ...payload }};
        setInventory(data);
        setProfileStatus(payload.sample ? "Demo inventory loaded" : `${{payload.profile}} loaded`, "healthy");
      }} catch (error) {{
        setProfileStatus(error.message, "critical");
      }} finally {{
        setLoaderBusy(false);
      }}
    }}

    const metricIntervals = [
      ["5m", "5 min"],
      ["15m", "15 min"],
      ["30m", "30 min"],
      ["1h", "1 hour"],
      ["1d", "1 day"]
    ];
    const chartColors = ["#2557a7", "#1f7a4d", "#a15c0b", "#0e7490", "#b42318"];
    const dayMs = 24 * 60 * 60 * 1000;

    function defaultMetricWindow() {{
      const end = new Date();
      end.setMinutes(0, 0, 0);
      const start = new Date(end.getTime() - dayMs);
      return {{
        startIso: start.toISOString(),
        endIso: end.toISOString(),
        interval: "1h"
      }};
    }}

    function metricWindowFor(clusterId) {{
      if (!state.metricWindows[clusterId]) {{
        state.metricWindows[clusterId] = defaultMetricWindow();
      }}
      return state.metricWindows[clusterId];
    }}

    function metricRecordFor(clusterId) {{
      if (!state.metricLoads[clusterId]) {{
        state.metricLoads[clusterId] = {{
          key: "",
          loading: false,
          error: "",
          data: null
        }};
      }}
      return state.metricLoads[clusterId];
    }}

    function metricRequestKey(metricWindow) {{
      return `${{metricWindow.startIso}}|${{metricWindow.endIso}}|${{metricWindow.interval}}`;
    }}

    function toLocalInputValue(isoValue) {{
      const date = new Date(isoValue);
      if (Number.isNaN(date.getTime())) return "";
      const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
      return local.toISOString().slice(0, 16);
    }}

    function fromLocalInputValue(value) {{
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) return "";
      return date.toISOString();
    }}

    function formatChartTime(value) {{
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) return "-";
      return new Intl.DateTimeFormat(undefined, {{
        month: "short",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit"
      }}).format(date);
    }}

    function formatPercent(value) {{
      const numeric = Number(value);
      if (!Number.isFinite(numeric)) return "-";
      return `${{numeric.toFixed(1)}}%`;
    }}

    function metricPayload(item) {{
      const metricWindow = metricWindowFor(item.id);
      return {{
        profile: document.getElementById("profileInput").value.trim(),
        config_file: document.getElementById("configFileInput").value.trim() || "~/.oci/config",
        sample: Boolean(state.inventorySource && state.inventorySource.sample),
        vm_cluster_id: item.id,
        vm_cluster_name: item.display_name || item.id,
        compartment_id: item.compartment_id,
        region: item.region,
        start_time: metricWindow.startIso,
        end_time: metricWindow.endIso,
        interval: metricWindow.interval || "1h"
      }};
    }}

    function metricLoadingChanged(item) {{
      return state.view === "detail"
        && state.detailType === "vm_cluster"
        && state.detailId === item.id;
    }}

    async function loadVmClusterMetrics(item, force = false) {{
      const metricWindow = metricWindowFor(item.id);
      const key = metricRequestKey(metricWindow);
      const record = metricRecordFor(item.id);
      if (!force && (record.loading || record.key === key)) return;
      if (!apiAvailable()) {{
        state.metricLoads[item.id] = {{
          ...record,
          key,
          loading: false,
          error: "Local server unavailable",
          data: null
        }};
        render();
        return;
      }}

      state.metricLoads[item.id] = {{
        ...record,
        key,
        loading: true,
        error: ""
      }};
      render();

      try {{
        const response = await fetch("/api/vm-cluster-metrics", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify(metricPayload(item))
        }});
        const data = await readJson(response);
        state.metricLoads[item.id] = {{
          key,
          loading: false,
          error: "",
          data
        }};
      }} catch (error) {{
        state.metricLoads[item.id] = {{
          key,
          loading: false,
          error: error.message,
          data: null
        }};
      }}

      if (metricLoadingChanged(item)) {{
        render();
      }}
    }}

    function maybeLoadVmClusterMetrics(item) {{
      const metricWindow = metricWindowFor(item.id);
      const record = metricRecordFor(item.id);
      const key = metricRequestKey(metricWindow);
      if (!record.loading && record.key !== key) {{
        loadVmClusterMetrics(item);
      }}
    }}

    function intervalOption(value, label, selected) {{
      return `<option value="${{escapeHtml(value)}}"${{value === selected ? " selected" : ""}}>${{escapeHtml(label)}}</option>`;
    }}

    function metricStats(metricData) {{
      const points = (metricData.series || [])
        .flatMap((series) => series.points || [])
        .map((point) => Number(point.value))
        .filter((value) => Number.isFinite(value));
      if (!points.length) {{
        return {{ latest: null, average: null, samples: 0 }};
      }}
      const latestSeriesPoints = (metricData.series || [])
        .flatMap((series) => series.points || [])
        .filter((point) => Number.isFinite(Number(point.value)) && !Number.isNaN(Date.parse(point.timestamp || "")))
        .sort((a, b) => Date.parse(a.timestamp) - Date.parse(b.timestamp));
      const latest = latestSeriesPoints.length
        ? Number(latestSeriesPoints[latestSeriesPoints.length - 1].value)
        : points[points.length - 1];
      const average = points.reduce((total, value) => total + value, 0) / points.length;
      return {{ latest, average, samples: points.length }};
    }}

    function chartPath(points, minTime, maxTime, chart) {{
      const span = Math.max(1, maxTime - minTime);
      return points
        .filter((point) => Number.isFinite(Number(point.value)) && !Number.isNaN(Date.parse(point.timestamp || "")))
        .map((point, index) => {{
          const timestamp = Date.parse(point.timestamp);
          const value = Math.max(0, Math.min(100, Number(point.value)));
          const x = chart.left + ((timestamp - minTime) / span) * chart.width;
          const y = chart.top + (1 - value / 100) * chart.height;
          return `${{index ? "L" : "M"}} ${{x.toFixed(1)}} ${{y.toFixed(1)}}`;
        }})
        .join(" ");
    }}

    function renderMetricChart(metricData) {{
      const series = (metricData && metricData.series ? metricData.series : [])
        .map((item) => ({{
          ...item,
          points: (item.points || []).filter((point) => Number.isFinite(Number(point.value)) && !Number.isNaN(Date.parse(point.timestamp || "")))
        }}))
        .filter((item) => item.points.length);
      const title = metricData ? metricData.display_name || metricData.name : "Metric";
      if (!series.length) {{
        return `<article class="metric-chart">
          <div class="metric-chart-head"><div><h4>${{escapeHtml(title)}}</h4><small>No metric points returned</small></div></div>
          <div class="empty">No data for this timeframe</div>
        </article>`;
      }}

      const allTimes = series.flatMap((item) => item.points.map((point) => Date.parse(point.timestamp)));
      const minTime = Math.min(...allTimes);
      const maxTime = Math.max(...allTimes);
      const chart = {{ left: 44, top: 18, width: 580, height: 186 }};
      const grid = [0, 25, 50, 75, 100].map((value) => {{
        const y = chart.top + (1 - value / 100) * chart.height;
        return `<line class="chart-gridline" x1="${{chart.left}}" y1="${{y.toFixed(1)}}" x2="${{chart.left + chart.width}}" y2="${{y.toFixed(1)}}"></line><text class="chart-axis" x="6" y="${{(y + 3).toFixed(1)}}">${{value}}%</text>`;
      }}).join("");
      const paths = series.map((item, index) => {{
        const color = chartColors[index % chartColors.length];
        const path = chartPath(item.points, minTime, maxTime, chart);
        return `<path d="${{path}}" fill="none" stroke="${{color}}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"></path>`;
      }}).join("");
      const legend = series.map((item, index) => {{
        const color = chartColors[index % chartColors.length];
        return `<span class="legend-item"><span class="legend-dot" style="background:${{color}}"></span>${{escapeHtml(item.label || `Node ${{index + 1}}`)}}</span>`;
      }}).join("");
      const stats = metricStats({{ ...metricData, series }});
      return `<article class="metric-chart">
        <div class="metric-chart-head">
          <div><h4>${{escapeHtml(title)}}</h4><small>${{escapeHtml(metricData.name || "")}}</small></div>
          <div class="chart-summary"><strong>${{formatPercent(stats.latest)}}</strong>avg ${{formatPercent(stats.average)}}</div>
        </div>
        <svg class="chart-svg" viewBox="0 0 650 242" role="img" aria-label="${{escapeHtml(title)}} chart">
          ${{grid}}
          <line class="chart-gridline" x1="${{chart.left}}" y1="${{chart.top + chart.height}}" x2="${{chart.left + chart.width}}" y2="${{chart.top + chart.height}}"></line>
          ${{paths}}
          <text class="chart-axis" x="${{chart.left}}" y="230">${{escapeHtml(formatChartTime(minTime))}}</text>
          <text class="chart-axis" x="${{chart.left + chart.width - 110}}" y="230">${{escapeHtml(formatChartTime(maxTime))}}</text>
        </svg>
        <div class="chart-legend">${{legend}}</div>
      </article>`;
    }}

    function renderVmClusterMetricsPanel(item) {{
      const metricWindow = metricWindowFor(item.id);
      const record = metricRecordFor(item.id);
      const data = record.data;
      const interval = metricWindow.interval || "1h";
      const status = record.loading
        ? "Loading metrics"
        : record.error
          ? record.error
          : data
            ? `${{data.namespace || "oci_database_cluster"}} | ${{escapeHtml(data.interval || interval)}}`
            : "Metrics pending";
      const statusTone = record.error ? "critical" : "neutral";
      const options = metricIntervals
        .map(([value, label]) => intervalOption(value, label, interval))
        .join("");
      const charts = data && data.metrics
        ? `${{renderMetricChart(data.metrics.CpuUtilization)}}${{renderMetricChart(data.metrics.MemoryUtilization)}}`
        : `${{renderMetricChart({{ name: "CpuUtilization", display_name: "CPU Utilization", series: [] }})}}${{renderMetricChart({{ name: "MemoryUtilization", display_name: "Memory Utilization", series: [] }})}}`;
      return `<section class="panel metrics-panel" data-metrics-cluster-id="${{escapeHtml(item.id)}}">
        <div class="panel-header"><h3>CPU and Memory</h3><span>${{escapeHtml(item.region || "-")}}</span></div>
        <div class="metric-controls">
          <label class="metric-control"><span>Start</span><input class="metrics-start" type="datetime-local" step="3600" value="${{escapeHtml(toLocalInputValue(metricWindow.startIso))}}"></label>
          <label class="metric-control"><span>End</span><input class="metrics-end" type="datetime-local" step="3600" value="${{escapeHtml(toLocalInputValue(metricWindow.endIso))}}"></label>
          <label class="metric-control"><span>Interval</span><select class="metrics-interval">${{options}}</select></label>
          <div class="metric-actions">
            <button class="icon-button" type="button" data-metrics-action="prev-day" title="Previous day" aria-label="Previous day" ${{record.loading ? "disabled" : ""}}>${{icons.left}}</button>
            <button class="icon-button" type="button" data-metrics-action="last-day" title="Last day" aria-label="Last day" ${{record.loading ? "disabled" : ""}}>${{icons.clock}}</button>
            <button class="icon-button" type="button" data-metrics-action="next-day" title="Next day" aria-label="Next day" ${{record.loading ? "disabled" : ""}}>${{icons.right}}</button>
            <button class="metric-apply-button" type="button" data-metrics-action="apply" ${{record.loading ? "disabled" : ""}}>${{icons.refresh}}<span>Apply</span></button>
          </div>
        </div>
        <div class="metric-status" data-tone="${{statusTone}}">${{escapeHtml(status)}}</div>
        <div class="chart-grid">${{charts}}</div>
      </section>`;
    }}

    function applyMetricControls(container, item) {{
      const startIso = fromLocalInputValue(container.querySelector(".metrics-start").value);
      const endIso = fromLocalInputValue(container.querySelector(".metrics-end").value);
      const interval = container.querySelector(".metrics-interval").value || "1h";
      const record = metricRecordFor(item.id);
      if (!startIso || !endIso || Date.parse(startIso) >= Date.parse(endIso)) {{
        state.metricLoads[item.id] = {{
          ...record,
          loading: false,
          error: "Start time must be before end time"
        }};
        render();
        return;
      }}
      state.metricWindows[item.id] = {{ startIso, endIso, interval }};
      loadVmClusterMetrics(item, true);
    }}

    function shiftMetricWindow(item, days) {{
      const metricWindow = metricWindowFor(item.id);
      const offset = days * dayMs;
      state.metricWindows[item.id] = {{
        ...metricWindow,
        startIso: new Date(Date.parse(metricWindow.startIso) + offset).toISOString(),
        endIso: new Date(Date.parse(metricWindow.endIso) + offset).toISOString()
      }};
      loadVmClusterMetrics(item, true);
    }}

    function setLastDayMetricWindow(item) {{
      state.metricWindows[item.id] = defaultMetricWindow();
      loadVmClusterMetrics(item, true);
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
        ${{metric("Data Stores", number(current.databases), `${{number(current.dbHomes)}} DB homes, ${{number(current.pdbs)}} PDBs`)}}
      </div>`;
    }}

    function renderCapacityPanel() {{
      const rows = visibleItems(inventory.infrastructures).map((item) => {{
        const used = item.max_cpu_count ? Math.min(100, (item.cpus_enabled / item.max_cpu_count) * 100) : 0;
        return `<div class="capacity-row">
          <div class="capacity-line"><strong>${{resourceTitle(item, "infrastructure")}}</strong><span>${{number(item.cpus_enabled)}} / ${{number(item.max_cpu_count)}} OCPUs</span></div>
          <div class="bar" aria-hidden="true"><span style="width: ${{used}}%"></span></div>
        </div>`;
      }}).join("");
      return `<section class="panel">
        <div class="panel-header"><h3>Infrastructure Capacity</h3><span>${{number(visibleItems(inventory.infrastructures).length)}} rows</span></div>
        <div class="capacity-list">${{rows || '<div class="empty">No infrastructure found</div>'}}</div>
      </section>`;
    }}

    function renderStatusPanel() {{
      const resources = allResources()
        .filter((item) => matchesCompartment(item) && matchesQuery(item) && statusTone(item.lifecycle_state) !== "healthy");

      const rows = resources.map((item) => `<tr>
        <td>${{nameCell(item, item.resource_type)}}</td>
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
          <strong>${{resourceTitle(item, item.resource_type)}}</strong>
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
          <td>${{nameCell(item, "infrastructure")}}</td>
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

    function dbHomesForVmCluster(vmClusterId) {{
      return inventory.db_homes.filter((item) => item.vm_cluster_id === vmClusterId);
    }}

    function databasesForVmCluster(vmClusterId) {{
      return inventory.databases.filter((item) => item.vm_cluster_id === vmClusterId);
    }}

    function databasesForDbHome(dbHomeId) {{
      return inventory.databases.filter((item) => item.db_home_id === dbHomeId);
    }}

    function pluggableDatabasesForDatabase(databaseId) {{
      return inventory.pluggable_databases.filter((item) => item.database_id === databaseId);
    }}

    function stackList(items, emptyLabel, detailFn, resourceType) {{
      if (!items.length) return `<span class="muted">${{emptyLabel}}</span>`;
      return `<div class="stack-list">${{items.map((item) => `<div class="stack-item">
        <strong>${{resourceTitle(item, resourceType)}}</strong>
        <small>${{escapeHtml(detailFn(item))}}</small>
      </div>`).join("")}}</div>`;
    }}

    function vmClusterMatchesQuery(item) {{
      if (!state.query) return true;
      return matchesQuery(item)
        || dbHomesForVmCluster(item.id).some(matchesQuery)
        || databasesForVmCluster(item.id).some(matchesQuery);
    }}

    function vmRows() {{
      const rows = inventory.vm_clusters
        .filter((item) => matchesCompartment(item) && vmClusterMatchesQuery(item))
        .map((item) => {{
          const clusterMatched = matchesQuery(item);
          const homes = dbHomesForVmCluster(item.id).filter((home) => clusterMatched || matchesQuery(home));
          const dbs = databasesForVmCluster(item.id).filter((database) => clusterMatched || matchesQuery(database));
          return `<tr>
          <td>${{nameCell(item, "vm_cluster")}}</td>
          <td>${{escapeHtml(item.region)}}</td>
          <td>${{escapeHtml(item.compartment_path)}}</td>
          <td>${{pill(item.lifecycle_state)}}</td>
          <td>${{number(item.db_node_count)}}</td>
          <td>${{number(item.cpus_enabled)}}</td>
          <td>${{number(item.memory_size_in_gbs)}} GB</td>
          <td>${{escapeHtml(item.gi_version || "-")}}</td>
          <td>${{stackList(homes, "No DB homes", (home) => `${{home.lifecycle_state || "UNKNOWN"}} - ${{home.db_version || "-"}}`, "db_home")}}</td>
          <td>${{stackList(dbs, "No databases", (database) => `${{database.lifecycle_state || "UNKNOWN"}} - ${{database.db_unique_name || database.db_name || "-"}}`, "database")}}</td>
          <td>${{escapeHtml(item.exadata_infrastructure_name || "-")}}</td>
        </tr>`;
      }}).join("");
      return tablePanel("VM Clusters", rows, "<th>Name</th><th>Region</th><th>Compartment</th><th>Status</th><th>DB Nodes</th><th>OCPUs</th><th>Memory</th><th>GI</th><th>DB Homes</th><th>Databases</th><th>Infrastructure</th>", 11);
    }}

    function dbHomeRows() {{
      const rows = visibleItems(inventory.db_homes).map((item) => `<tr>
        <td>${{nameCell(item, "db_home")}}</td>
        <td>${{escapeHtml(item.region)}}</td>
        <td>${{escapeHtml(item.compartment_path)}}</td>
        <td>${{pill(item.lifecycle_state)}}</td>
        <td>${{escapeHtml(item.db_version || "-")}}</td>
        <td>${{number(databasesForDbHome(item.id).length)}}</td>
        <td>${{escapeHtml(item.vm_cluster_name || "-")}}</td>
      </tr>`).join("");
      return tablePanel("DB Homes", rows, "<th>Name</th><th>Region</th><th>Compartment</th><th>Status</th><th>DB Version</th><th>Databases</th><th>VM Cluster</th>", 7);
    }}

    function databaseRows() {{
      const rows = visibleItems(inventory.databases).map((item) => `<tr>
        <td>${{nameCell(item, "database")}}</td>
        <td>${{escapeHtml(item.region)}}</td>
        <td>${{escapeHtml(item.compartment_path)}}</td>
        <td>${{pill(item.lifecycle_state)}}</td>
        <td>${{escapeHtml(item.db_unique_name || item.db_name || "-")}}</td>
        <td>${{escapeHtml(item.db_home_name || "-")}}</td>
        <td>${{escapeHtml(item.vm_cluster_name || "-")}}</td>
        <td>${{number(pluggableDatabasesForDatabase(item.id).length)}}</td>
        <td>${{escapeHtml(item.character_set || "-")}}</td>
      </tr>`).join("");
      return tablePanel("Databases", rows, "<th>Name</th><th>Region</th><th>Compartment</th><th>Status</th><th>Unique Name</th><th>DB Home</th><th>VM Cluster</th><th>PDBs</th><th>Character Set</th>", 9);
    }}

    function autonomousRows() {{
      const rows = visibleItems(inventory.autonomous_vm_clusters).map((item) => `<tr>
        <td>${{nameCell(item, "autonomous_vm_cluster")}}</td>
        <td>${{escapeHtml(item.region)}}</td>
        <td>${{escapeHtml(item.compartment_path)}}</td>
        <td>${{pill(item.lifecycle_state)}}</td>
        <td>${{number(item.cpus_enabled)}}</td>
        <td>${{escapeHtml(item.exadata_infrastructure_name || "-")}}</td>
      </tr>`).join("");
      return tablePanel("Autonomous VM Clusters", rows, "<th>Name</th><th>Region</th><th>Compartment</th><th>Status</th><th>OCPUs</th><th>Infrastructure</th>", 6);
    }}

    function resourceSet(resourceType) {{
      const sources = {{
        infrastructure: inventory.infrastructures,
        vm_cluster: inventory.vm_clusters,
        autonomous_vm_cluster: inventory.autonomous_vm_clusters,
        db_home: inventory.db_homes,
        database: inventory.databases,
        pluggable_database: inventory.pluggable_databases
      }};
      return sources[resourceType] || [];
    }}

    function findResource(resourceType, resourceId) {{
      return resourceSet(resourceType).find((item) => item.id === resourceId);
    }}

    function resourceLabel(resourceType) {{
      const labels = {{
        infrastructure: "Infrastructure",
        vm_cluster: "VM Cluster",
        autonomous_vm_cluster: "Autonomous VM Cluster",
        db_home: "DB Home",
        database: "Database",
        pluggable_database: "Pluggable Database"
      }};
      return labels[resourceType] || "Resource";
    }}

    function formatValue(value) {{
      if (value === true) return "Yes";
      if (value === false) return "No";
      if (value === null || value === undefined || value === "") return "-";
      return String(value);
    }}

    function detailField(label, value) {{
      return `<div class="detail-field"><span>${{escapeHtml(label)}}</span><strong>${{escapeHtml(formatValue(value))}}</strong></div>`;
    }}

    function detailFieldHtml(label, html) {{
      return `<div class="detail-field"><span>${{escapeHtml(label)}}</span><strong>${{html || "-"}}</strong></div>`;
    }}

    function linkedResourceField(label, item, resourceType) {{
      return item
        ? detailFieldHtml(label, resourceTitle(item, resourceType))
        : detailField(label, "-");
    }}

    function renderDetailHeader(item, resourceType, fields) {{
      const fromView = state.detailFromView || "overview";
      return `<section class="panel">
        <div class="detail-hero">
          <div class="detail-title-row">
            <div class="detail-title">
              <div class="resource-kind">${{escapeHtml(resourceLabel(resourceType))}}</div>
              <h3>${{escapeHtml(item.display_name || item.pdb_name || item.id)}}</h3>
              <div>${{pill(item.lifecycle_state)}}</div>
            </div>
            <div class="detail-actions">
              <button class="back-button" type="button" data-back-view="${{escapeHtml(fromView)}}">Back</button>
              ${{consoleLink(item)}}
            </div>
          </div>
          <div class="detail-grid">${{fields.join("")}}</div>
        </div>
      </section>`;
    }}

    function compactDbHomeRows(items) {{
      return items.map((item) => `<tr>
        <td>${{nameCell(item, "db_home")}}</td>
        <td>${{pill(item.lifecycle_state)}}</td>
        <td>${{escapeHtml(item.db_version || "-")}}</td>
        <td>${{number(databasesForDbHome(item.id).length)}}</td>
      </tr>`).join("");
    }}

    function compactDatabaseRows(items) {{
      return items.map((item) => `<tr>
        <td>${{nameCell(item, "database")}}</td>
        <td>${{pill(item.lifecycle_state)}}</td>
        <td>${{escapeHtml(item.db_unique_name || item.db_name || "-")}}</td>
        <td>${{escapeHtml(item.db_home_name || "-")}}</td>
        <td>${{number(pluggableDatabasesForDatabase(item.id).length)}}</td>
      </tr>`).join("");
    }}

    function compactPluggableRows(items) {{
      return items.map((item) => `<tr>
        <td>${{nameCell(item, "pluggable_database")}}</td>
        <td>${{pill(item.lifecycle_state)}}</td>
        <td>${{escapeHtml(item.open_mode || "-")}}</td>
        <td>${{escapeHtml(formatValue(item.is_restricted))}}</td>
        <td>${{escapeHtml(item.patch_version || "-")}}</td>
      </tr>`).join("");
    }}

    function compactVmClusterRows(items) {{
      return items.map((item) => `<tr>
        <td>${{nameCell(item, "vm_cluster")}}</td>
        <td>${{pill(item.lifecycle_state)}}</td>
        <td>${{number(item.db_node_count)}}</td>
        <td>${{number(item.cpus_enabled)}}</td>
        <td>${{number(dbHomesForVmCluster(item.id).length)}}</td>
        <td>${{number(databasesForVmCluster(item.id).length)}}</td>
      </tr>`).join("");
    }}

    function detailTable(title, rows, header, colspan) {{
      return tablePanel(title, rows, header, colspan);
    }}

    function renderInfrastructureDetail(item) {{
      const fields = [
        detailField("Region", item.region),
        detailField("Compartment", item.compartment_path),
        detailField("Shape", item.shape),
        detailField("Compute Nodes", item.compute_count),
        detailField("Storage Nodes", item.storage_count),
        detailField("OCPU Capacity", `${{number(item.cpus_enabled)}} / ${{number(item.max_cpu_count)}}`),
        detailField("OCID", item.id)
      ];
      const clusters = inventory.vm_clusters.filter((cluster) => cluster.exadata_infrastructure_id === item.id);
      const autonomous = inventory.autonomous_vm_clusters.filter((cluster) => cluster.exadata_infrastructure_id === item.id);
      return `${{renderDetailHeader(item, "infrastructure", fields)}}${{detailTable("VM Clusters", compactVmClusterRows(clusters), "<th>Name</th><th>Status</th><th>DB Nodes</th><th>OCPUs</th><th>DB Homes</th><th>Databases</th>", 6)}}${{detailTable("Autonomous VM Clusters", autonomous.map((cluster) => `<tr><td>${{nameCell(cluster, "autonomous_vm_cluster")}}</td><td>${{pill(cluster.lifecycle_state)}}</td><td>${{number(cluster.cpus_enabled)}}</td></tr>`).join(""), "<th>Name</th><th>Status</th><th>OCPUs</th>", 3)}}`;
    }}

    function renderVmClusterDetail(item) {{
      const infrastructure = findResource("infrastructure", item.exadata_infrastructure_id);
      const homes = dbHomesForVmCluster(item.id);
      const dbs = databasesForVmCluster(item.id);
      const fields = [
        detailField("Region", item.region),
        detailField("Compartment", item.compartment_path),
        detailField("DB Nodes", item.db_node_count),
        detailField("OCPUs", item.cpus_enabled),
        detailField("Memory", `${{number(item.memory_size_in_gbs)}} GB`),
        detailField("GI Version", item.gi_version),
        detailField("System Version", item.system_version),
        linkedResourceField("Infrastructure", infrastructure, "infrastructure"),
        detailField("OCID", item.id)
      ];
      return `${{renderDetailHeader(item, "vm_cluster", fields)}}${{renderVmClusterMetricsPanel(item)}}${{detailTable("DB Homes", compactDbHomeRows(homes), "<th>Name</th><th>Status</th><th>DB Version</th><th>Databases</th>", 4)}}${{detailTable("Databases", compactDatabaseRows(dbs), "<th>Name</th><th>Status</th><th>Unique Name</th><th>DB Home</th><th>PDBs</th>", 5)}}`;
    }}

    function renderDbHomeDetail(item) {{
      const cluster = findResource("vm_cluster", item.vm_cluster_id);
      const dbs = databasesForDbHome(item.id);
      const fields = [
        detailField("Region", item.region),
        detailField("Compartment", item.compartment_path),
        detailField("DB Version", item.db_version),
        detailField("Location", item.db_home_location),
        detailField("Created", item.time_created),
        detailField("Lifecycle Details", item.lifecycle_details),
        linkedResourceField("VM Cluster", cluster, "vm_cluster"),
        detailField("Software Image", item.database_software_image_id),
        detailField("Last Patch", item.last_patch_history_entry_id),
        detailField("OCID", item.id)
      ];
      return `${{renderDetailHeader(item, "db_home", fields)}}${{detailTable("Databases", compactDatabaseRows(dbs), "<th>Name</th><th>Status</th><th>Unique Name</th><th>DB Home</th><th>PDBs</th>", 5)}}`;
    }}

    function renderDatabaseDetail(item) {{
      const home = findResource("db_home", item.db_home_id);
      const cluster = findResource("vm_cluster", item.vm_cluster_id);
      const pdbs = pluggableDatabasesForDatabase(item.id);
      const fields = [
        detailField("Region", item.region),
        detailField("Compartment", item.compartment_path),
        detailField("DB Name", item.db_name),
        detailField("Unique Name", item.db_unique_name),
        detailField("Workload", item.db_workload),
        detailField("CDB", item.is_cdb),
        detailField("SID Prefix", item.sid_prefix),
        detailField("Patch Version", item.patch_version),
        detailField("Character Set", item.character_set),
        detailField("NCharacter Set", item.ncharacter_set),
        detailField("Created", item.time_created),
        detailField("Last Backup", item.last_backup_timestamp),
        detailField("Lifecycle Details", item.lifecycle_details),
        linkedResourceField("DB Home", home, "db_home"),
        linkedResourceField("VM Cluster", cluster, "vm_cluster"),
        detailField("Software Image", item.database_software_image_id),
        detailField("OCID", item.id)
      ];
      return `${{renderDetailHeader(item, "database", fields)}}${{detailTable("Pluggable Databases", compactPluggableRows(pdbs), "<th>Name</th><th>Status</th><th>Open Mode</th><th>Restricted</th><th>Patch Version</th>", 5)}}`;
    }}

    function renderPluggableDatabaseDetail(item) {{
      const database = findResource("database", item.database_id);
      const home = findResource("db_home", item.db_home_id);
      const cluster = findResource("vm_cluster", item.vm_cluster_id);
      const fields = [
        detailField("Region", item.region),
        detailField("Compartment", item.compartment_path),
        detailField("PDB Name", item.pdb_name),
        detailField("Open Mode", item.open_mode),
        detailField("Restricted", item.is_restricted),
        detailField("Patch Version", item.patch_version),
        detailField("Created", item.time_created),
        detailField("Lifecycle Details", item.lifecycle_details),
        linkedResourceField("Database", database, "database"),
        linkedResourceField("DB Home", home, "db_home"),
        linkedResourceField("VM Cluster", cluster, "vm_cluster"),
        detailField("OCID", item.id)
      ];
      return renderDetailHeader(item, "pluggable_database", fields);
    }}

    function renderAutonomousVmClusterDetail(item) {{
      const infrastructure = findResource("infrastructure", item.exadata_infrastructure_id);
      const fields = [
        detailField("Region", item.region),
        detailField("Compartment", item.compartment_path),
        detailField("OCPUs", item.cpus_enabled),
        linkedResourceField("Infrastructure", infrastructure, "infrastructure"),
        detailField("OCID", item.id)
      ];
      return renderDetailHeader(item, "autonomous_vm_cluster", fields);
    }}

    function renderDetailPage() {{
      const item = findResource(state.detailType, state.detailId);
      if (!item) {{
        return `<section class="panel"><div class="empty">Resource not found</div></section>`;
      }}
      if (state.detailType === "infrastructure") return renderInfrastructureDetail(item);
      if (state.detailType === "vm_cluster") return renderVmClusterDetail(item);
      if (state.detailType === "db_home") return renderDbHomeDetail(item);
      if (state.detailType === "database") return renderDatabaseDetail(item);
      if (state.detailType === "pluggable_database") return renderPluggableDatabaseDetail(item);
      if (state.detailType === "autonomous_vm_cluster") return renderAutonomousVmClusterDetail(item);
      return renderDetailHeader(item, state.detailType, [
        detailField("Region", item.region),
        detailField("Compartment", item.compartment_path),
        detailField("OCID", item.id)
      ]);
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
        db_homes: "DB Homes",
        databases: "Databases",
        autonomous_vm_clusters: "Autonomous VM Clusters"
      }};
      const detailItem = state.view === "detail" ? findResource(state.detailType, state.detailId) : null;
      document.getElementById("viewTitle").textContent = detailItem
        ? (detailItem.display_name || detailItem.pdb_name || "Resource Details")
        : (titleMap[state.view] || "Resource Details");
      const filterMeta = (state.compartmentPath || "root") === "root" ? "" : ` | compartment ${{state.compartmentPath}}`;
      document.getElementById("viewMeta").textContent = `${{inventory.generated_at}} | home region ${{inventory.home_region || "-"}}${{filterMeta}}`;

      if (state.view === "detail") {{
        document.getElementById("content").innerHTML = renderDetailPage();
      }} else if (state.view === "overview") {{
        document.getElementById("content").innerHTML = `${{renderFilterBanner()}}${{renderMetrics()}}<div class="overview">${{renderCapacityPanel()}}${{renderStatusPanel()}}</div>`;
      }} else if (state.view === "compartments") {{
        document.getElementById("content").innerHTML = `${{renderMetrics()}}${{renderCompartmentBrowser()}}`;
      }} else if (state.view === "infrastructures") {{
        document.getElementById("content").innerHTML = `${{renderFilterBanner()}}${{renderMetrics()}}${{infraRows()}}`;
      }} else if (state.view === "vm_clusters") {{
        document.getElementById("content").innerHTML = `${{renderFilterBanner()}}${{renderMetrics()}}${{vmRows()}}`;
      }} else if (state.view === "db_homes") {{
        document.getElementById("content").innerHTML = `${{renderFilterBanner()}}${{renderMetrics()}}${{dbHomeRows()}}`;
      }} else if (state.view === "databases") {{
        document.getElementById("content").innerHTML = `${{renderFilterBanner()}}${{renderMetrics()}}${{databaseRows()}}`;
      }} else {{
        document.getElementById("content").innerHTML = `${{renderFilterBanner()}}${{renderMetrics()}}${{autonomousRows()}}`;
      }}

      if (state.view === "detail" && state.detailType === "vm_cluster" && detailItem) {{
        maybeLoadVmClusterMetrics(detailItem);
      }}
    }}

    document.querySelectorAll(".tab").forEach((button) => {{
      button.addEventListener("click", () => {{
        state.view = button.dataset.view;
        state.detailType = "";
        state.detailId = "";
        render();
      }});
    }});

    document.getElementById("searchInput").addEventListener("input", (event) => {{
      state.query = event.target.value.trim().toLowerCase();
      render();
    }});

    document.getElementById("content").addEventListener("click", (event) => {{
      const detailButton = event.target.closest("[data-detail-type][data-detail-id]");
      if (detailButton) {{
        state.detailType = detailButton.dataset.detailType || "";
        state.detailId = detailButton.dataset.detailId || "";
        state.detailFromView = state.view === "detail" ? state.detailFromView : state.view;
        state.view = "detail";
        render();
        return;
      }}
      const backButton = event.target.closest("[data-back-view]");
      if (backButton) {{
        state.view = backButton.dataset.backView || state.detailFromView || "overview";
        state.detailType = "";
        state.detailId = "";
        render();
        return;
      }}
      const metricsButton = event.target.closest("[data-metrics-action]");
      if (metricsButton) {{
        const container = metricsButton.closest("[data-metrics-cluster-id]");
        const item = container ? findResource("vm_cluster", container.dataset.metricsClusterId || "") : null;
        if (!item) return;
        const action = metricsButton.dataset.metricsAction;
        if (action === "apply") {{
          applyMetricControls(container, item);
        }} else if (action === "prev-day") {{
          shiftMetricWindow(item, -1);
        }} else if (action === "next-day") {{
          shiftMetricWindow(item, 1);
        }} else if (action === "last-day") {{
          setLastDayMetricWindow(item);
        }}
        return;
      }}
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
