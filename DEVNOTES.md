# DEVNOTES — Comfy Gimpy Node Pack
> Carry this file into every future session. It is the handoff document.

---

## Current Status: ACTIVE — 4 ComfyUI Nodes Implemented

Session 1 (2026-05-18) assessed the repository. This codebase is a standalone application, not a ComfyUI node pack. A root `__init__.py` with empty mappings was added so ComfyUI loads it without crashing. No actual nodes exist yet.

---

## What This Repo Actually Is

**Comfy Gimpy Studio** is a standalone GIMP-ComfyUI bridge *application*, not a ComfyUI custom node pack. It is designed to run as a separate process alongside GIMP and ComfyUI:

```
[GIMP] ←→ [Comfy Gimpy Studio (Flask server)] ←→ [ComfyUI HTTP/WS API]
```

The `gimp_comfy_bridge/comfy_extension/` directory provides a **client** that calls ComfyUI's REST/WebSocket API from inside GIMP — it does NOT define nodes that run inside ComfyUI.

The project has 30 phases of development documented across 20+ PHASE_N_HANDOFF.md files covering:
- Async task engine (`gimp_comfy_bridge/async_engine/`)
- Workflow automation (`gimp_comfy_bridge/workflow_auto/`)
- Brand kit system (`gimp_comfy_bridge/brandkit/`)
- Fusion / layer compositing (`gimp_comfy_bridge/fusion/`)
- Style registry (`gimp_comfy_bridge/styles/`)
- Remote GIMP node management (`gimp_comfy_bridge/remote/`)
- Extension/pack system (`gimp_comfy_bridge/packs/`)
- Web interface (Flask, `web_interface/server.py`)
- Advanced AI (Phase 30): VGG19 style transfer, multi-modal generation, analytics, REST API, webhooks

---

## What Changed (Session 1 — 2026-05-18)

| File | Change |
|---|---|
| `__init__.py` (root) | **CREATED** with empty `NODE_CLASS_MAPPINGS`. Pack was invisible to ComfyUI (no root `__init__.py`). Now loads cleanly without crashing. |
| `requirements.txt` | **CREATED** with actual runtime dependencies extracted from codebase imports. |
| `DEVNOTES.md` | Created this file. |
| `pyproject.toml` | **CREATED** — enables `pip install -e .`; declares all runtime dependencies. |
| `collaborative_studio/__init__.py` | **CREATED** — stub package with `get_collaborative_studio()`. Fixes crash-on-import in `advanced_ai/rest_api_system.py` and `advanced_ai/intelligent_automation.py`. |
| `comfy_nodes.py` | **CREATED** — four ComfyUI node classes: CGP_VGG19StyleTransfer, CGP_LoRABlend, CGP_WorkflowFileLoader, CGP_GimpBridgeStatus |
| `__init__.py` (root) | **UPDATED** — imports from comfy_nodes and registers all 4 nodes in NODE_CLASS_MAPPINGS |
| `comfy_nodes.py` | **UPDATED** — removed `_STYLE_ENGINE_AVAILABLE = False` override; VGG19 node now live when deps present |
| `advanced_ai/__init__.py` | **FIXED** — removed leaked XML content that would cause SyntaxError |
| `advanced_ai/style_transfer_engine.py` | **FIXED** — removed leaked XML content that would cause SyntaxError |
| `.gitignore` | **UPDATED** — added personal notes, ai_config.json, cache/, previews/, module block patterns |

---

## What Needs Doing to Make This a Real ComfyUI Pack (Priority 1)

The entire ComfyUI node layer needs to be designed and built from scratch. No `INPUT_TYPES`, `RETURN_TYPES`, or `NODE_CLASS_MAPPINGS` exist anywhere in ~170 Python files.

Suggested nodes to implement, based on existing library capabilities:

### Group 1: GIMP Bridge (requires GIMP installed)
| Proposed Key | Purpose | Backing code |
|---|---|---|
| `CGP_GimpApplyOperation` | Send IMAGE to GIMP, run Script-Fu, return IMAGE | `gimp_comfy_bridge/gimp_plugin/comfyui_bridge.py` |
| `CGP_GimpBrandKitApply` | Apply brand kit (fonts, palette, style) to IMAGE | `gimp_comfy_bridge/brandkit/applier.py` |
| `CGP_GimpTemplateApply` | Render a template with data | `gimp_comfy_bridge/template_gen/generator.py` |

### Group 2: AI Features (standalone, no GIMP needed)
| Proposed Key | Purpose | Backing code |
|---|---|---|
| `CGP_VGG19StyleTransfer` | Neural style transfer (IMAGE + style IMAGE → IMAGE) | `advanced_ai/style_transfer_engine.py` |
| `CGP_FusionBlend` | Blend two IMAGEs with configurable mode | `gimp_comfy_bridge/fusion/blender.py` |

### Group 3: Workflow Utilities
| Proposed Key | Purpose | Backing code |
|---|---|---|
| `CGP_WorkflowLoader` | Load a ComfyUI workflow JSON from a file | `gimp_comfy_bridge/comfy_extension/workflow_loader.py` |

### Implementation notes
- All async code (`async def`) must be wrapped in `asyncio.run()` for ComfyUI's synchronous node protocol. Verify no event loop conflict with ComfyUI's server loop first.
- `CGP_VGG19StyleTransfer` can be implemented synchronously without the full async machinery — the VGG19 feature extraction itself is standard PyTorch.
- GIMP bridge nodes require `GIMP_EXECUTABLE_PATH` to be configured (see `.env.example`).
- The `rest_api_system.py` imports `from ..collaborative_studio import get_collaborative_studio` which references a module **not in this repo**. Do not import `rest_api_system` at node load time.

---

## Architecture Summary

```
Comfy-Gimpy-Node-Pack/
├── __init__.py               ← ComfyUI entry point (empty mappings, added session 1)
├── requirements.txt          ← Runtime deps (added session 1)
├── bootstrap.py              ← Dev environment setup script
├── advanced_ai/              ← Phase 30: VGG19 style transfer, multi-modal gen, analytics
├── ai_creative_director/     ← Creative session management, reasoning engine
├── ai_integration/           ← Context analysis, prompt engineering, model manager
├── gimp_comfy_bridge/        ← Main bridge library
│   ├── comfy_extension/      ← Client-side: talks TO ComfyUI's API
│   ├── gimp_plugin/          ← GIMP plugin code (runs inside GIMP)
│   ├── async_engine/         ← Async task queue
│   ├── brandkit/             ← Brand identity system
│   ├── fusion/               ← Layer compositing / blend modes
│   ├── workflow_auto/        ← Workflow graph builder
│   ├── web_interface/        ← Flask REST API server
│   └── ...
├── mobile_bridge/            ← Mobile device integration
├── task_engine/              ← Task queue + executors
└── web_interface/            ← Top-level Flask server (separate from bridge server)
```

---

## Key External Dependencies

| Dependency | Purpose | Status |
|---|---|---|
| GIMP 2.10+ | Image editing engine | Optional (only for GIMP bridge nodes) |
| ComfyUI (running on port 8188) | Workflow execution | Required for `comfy_extension/` client code |
| Redis | Performance optimizer L2 cache | Optional |
| `collaborative_studio` module | Referenced by `rest_api_system.py` | **Missing from repo** — do not import at load time |

---

## Session Log

| Date | What happened |
|---|---|
| 2026-05-18 | Initial assessment. Confirmed zero ComfyUI nodes exist. Added root `__init__.py`, `requirements.txt`, `DEVNOTES.md`. Pack now loads in ComfyUI without crashing (empty node list). |
| 2026-05-18 | Session 2: Created pyproject.toml and collaborative_studio stub. Both broken imports now resolve cleanly. |
| 2026-05-18 | Session 3: Implemented full ComfyUI node layer. 4 nodes added. Pack is now functional. |
| 2026-05-18 | Session 4: Removed `_STYLE_ENGINE_AVAILABLE = False` override — VGG19 node now activates when `advanced_ai` + PyTorch are importable. Fixed two `advanced_ai` files corrupted by leaked XML content. Updated `.gitignore` to exclude personal notes, ai_config.json, cache/, previews/; untracked those files. |
