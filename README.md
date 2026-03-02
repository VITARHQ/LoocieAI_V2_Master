
# Loocie AI — V2 Master (VITAR Division)

**Product of iVenomLegacy Studios, LLC** **IP Held by Seven Holy Creations, LLC (SHC)**

## 🚀 Overview
Loocie is a high-performance, FastAPI-based AI Executive Engine. This V2 Master build implements the **Business Vault Standard (BVS)**, decoupling the core engine from encrypted business data.

## 🏗 Project Structure
Based on the current V2 repository:
- `app/`: Core FastAPI application logic.
- `api/`: Route definitions (`health`, `root`, `router`).
- `core/`: System configuration, logging, and security baselines.
- `env/`: Virtual environment and dependency management.

## 🔒 Business Vault Standard (BVS)
This engine requires an external encrypted Vault to be mounted.
- **Root Path:** Defined by `LOOCIE_VAULT_PATH` environment variable.
- **Isolation:** Each business unit (LU, MW, IVL) has its own isolated Vault.

## 🛠 Setup (Mac/Linux)

### 1) Create + Activate Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
