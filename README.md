# OCI ExaCC Operations App

This repo includes a reusable Python app for OCI Exadata Cloud@Customer inventory and safe VM cluster operations. The entry point is `exacc.py`.

## What It Does

- Fetches ExaCC Exadata infrastructures, VM clusters, and autonomous VM clusters.
- Browses OCI compartments and filters inventory by selected compartment scope.
- Renders a self-contained modern HTML dashboard that opens directly in a browser.
- Exports summary, JSON, and CSV inventory views.
- Preserves the tag-driven OCPU scale workflow with dry-run by default.
- Keeps OCI access in a reusable package under `src/exacc_app`.

Inventory discovery uses the Database API directly for each compartment, matching scripts that call `oci db exadata-infrastructure list` and `oci db vm-cluster list`.

## Setup

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

The app uses your existing OCI config, usually `~/.oci/config`.
When `.venv` exists, `./exacc.py` automatically runs through that virtual environment.

## Quick Start

Start the local interface and load an OCI profile from the sidebar:

```bash
./exacc.py serve
```

Render a demo dashboard without OCI access:

```bash
./exacc.py dashboard --sample
```

Render a live dashboard for one profile region:

```bash
./exacc.py dashboard --profile DEFAULT --output exacc-dashboard.html
```

Render across all subscribed regions:

```bash
./exacc.py dashboard --profile DEFAULT --all-regions
```

Serve the dashboard locally:

```bash
./exacc.py serve --port 8000
```

The served interface can discover profile names from `~/.oci/config`, load a selected profile, toggle all subscribed regions, and refresh the dashboard without restarting the server.
The Compartments view shows the loaded compartment tree, resource counts, and click-to-filter behavior for the rest of the dashboard.

## Inventory Exports

```bash
./exacc.py inventory --profile DEFAULT
./exacc.py inventory --profile DEFAULT --format json --output inventory.json
./exacc.py inventory --profile DEFAULT --format csv --resource infrastructures
./exacc.py inventory --profile DEFAULT --format csv --resource vm-clusters
./exacc.py inventory --profile DEFAULT --format csv --resource autonomous-vm-clusters
./exacc.py inventory --profile DEFAULT --format csv --resource versions
```

## Tag-Based Scaling

Dry-run is the default:

```bash
./exacc.py scale-tagged --profile DEFAULT --all-regions --verbose
```

Submit matching scale operations:

```bash
./exacc.py scale-tagged --profile DEFAULT --all-regions --confirm
```

Default defined tags:

| Tag | Default |
| --- | --- |
| Namespace | `osc_exacc` |
| Down time | `scale_down_time` |
| Up time | `scale_up_time` |
| Down OCPUs | `scale_down_ocpus` |
| Up OCPUs | `scale_up_ocpus` |

Time tags should match the current UTC hour marker, for example `21:00_UTC`.

## Project Layout

```text
src/exacc_app/
  cli.py          command-line interface
  oci_gateway.py  OCI SDK integration
  models.py       reusable inventory dataclasses
  dashboard.py    self-contained HTML dashboard renderer
  scaling.py      pure scaling decision logic
  server.py       optional local dashboard server
```
