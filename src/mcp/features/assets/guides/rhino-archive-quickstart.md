# Almond workspace for Rhino 8

설치·업데이트는 [AGENTS.md](../../../../../AGENTS.md)를 따른다. 등록된 `src/rhp/RhinoAlmondBridge/plugin-runtime`의 RHP와 인접 의존 파일을 사용한다. Rhino에서 **Almond** 또는 **RhinoTerminal**을 실행한다.

The panel reads the installed asset libraries through the daily Almond Python environment; it does not need an MCP connection. Included source files remain available if that lookup fails. The structural engine and optional AI workflow use the matching Python package (see below).

The archive opens in a dockable **Almond** panel inside Rhino. Its background, text, controls and font follow Rhino appearance settings, including theme changes.
Drag the panel tab beside Layers or Properties, or float it on another monitor.
Rhino remembers its docking position. Use the **Open in browser** arrow in the compact header or the **`AlmondLibraryBrowser`** command for the full-size browser view.
The panel has compact search, coloured model cards and full-width object details.
Thumbnails use the models' assigned material colours, not photographic textures.
Source links and download links open in your browser. The archive runs locally while Rhino stays open. Browsing included files needs no Meshy login, AI subscription or Internet connection after installation. Rhino's licence is separate. **Reload** reads the currently registered assets, including new or refreshed 3DMs. A lookup failure appears above the cards while the included sources remain available.

Search registered models and included source files, inspect available drawing packages, and download 3DM, source GLB, SVG, DXF and A3 SVG sheets. Choose 1:50 or 1:100 drawing views; DXF geometry uses full-size millimetres. Viewports fit drawings to the screen, so screen size is not print scale. Import downloaded DXFs into Rhino using millimetres. GLB downloads retain the original Almond numeric-mm convention and Y-up coordinates; prepare and register them as 3DMs before placement.

## Place a model

1. Register a source **3DM** with Almond's `asset_09-register` tool. For GLB or another model format, use `asset_07-prepare` tool first, then register the prepared 3DM. Click **Reload** in the Rhino panel to see it.
2. Finish other Rhino commands. Click **Verify & place** (or **Place** for a verified record), then pick a point; object snaps and keyboard entry work.
   You can also drag the card into a viewport and release there. Esc cancels; releasing outside a viewport cancels after a short timeout. Measured bounds, when available, provide an orange size preview.
3. The source origin lands at that point, aligned to world axes. Source units are converted to document units without recentering the source geometry.
   Use Rhino Rotate afterwards if needed. Undo removes the placement.

Placement creates a **Linked** block with **Active** layers, so source layers join the document's layers rather than reference layers. Repeated placements share that canonical 3DM definition. Instances carry the asset ID and metadata identified as a snapshot from placement time. Ordinary Rhino blocks remain ordinary blocks.

The catalogue's **unverified** state means it has not checked the current model bytes. **Verify & place** checks the registered source hash before changing the document. A changed source needs `asset_08-refresh tool(asset_id)` first. To edit an asset, edit and save its canonical 3DM, run `asset_08-refresh` tool to renew measurements and drawings, then update its linked definition in Rhino. **Reload** refreshes the panel list. A drawing package may be present without being verified current.

Native placement is available inside the Rhino panel for registered 3DMs.
Legacy GLBs remain downloadable source files and show **3DM conversion required**.

Karamba results come from your own Karamba installation; Almond's automated and browser checks do not establish solver correctness.

Each record includes dimensions, an asset ID, source evidence, generation task IDs, declared licence and known evidence gaps. Dimensions describe generated geometry; drawings are silhouettes, not certified construction details.

Community drawing entries can be catalogue-only; the source link identifies the original file.

Saved selections are browser-local. The Rhino archive uses a fresh loopback port when it starts, so saved selections are not guaranteed across Rhino restarts.
The separately installed Python archive uses a stable configurable port.

## Structural Validation

Choose **Structure** from the Almond menu, or run **AlmondStructure** (the older **AlmondKaramba** still works). The step-by-step guide is the [Structure workspace tutorial](../../structure/guides/tutorial.md).

**Almond native** uses the registered checkout's Python environment and solver source. Prepare `src/engine/.venv` with `src/mcp/rebuild_environment.ps1` using the root installation procedure. The panel checks that the editable package belongs to this checkout before running; it does not download an engine. It analyses frames drawn as centre lines:

- loads: total load, floor area loads (imposed and build-up), placed Almond models, self-weight;
- EN 1990 load combinations from the selected design code (Eurocode recommended values by default; National Annex profiles can be added);
- rigid or simple (pinned beam end) connections, and per-curve `almond:release`;
- per-curve sections with `almond:section` user text (`rect 300x640`, `box 200x300x8`, `chs 114.3x4`, mm unless a unit follows); otherwise inferred, or CHS 114.3 × 4;
- stability: alpha-cr, sway imperfections and P-Delta second-order analysis below 10;
- EN 1993-1-1 steel member checks: section class, buckling curves by fabrication, flexural buckling with Annex B interaction;
- the deflected shape or first buckling mode in the viewport, and every member, support and combination in the **Almond Results** panel (`AlmondResults`), with CSV export.

Concrete, timber and aluminium results are indicative: forces, deflection and stability are computed, but EN 1992/1995/1999 are not applied, so there is no capacity pass/fail. Prismatic solids are read as their centre lines; other solids are skipped with a warning. One study takes at most 200 selected objects.
**Karamba3D** needs its own installation and licence and also handles shells.
The solver location follows the registered RHP's fixed checkout layout. The previous `ALMOND_SOLVER_COMMAND` override is no longer used. AppData libraries and explicit `RHINO_MCP_*` library locations remain unchanged.

Changing settings marks results stale; recapture after changing Rhino geometry.
Results are snapshots, not live monitoring. This is design-stage screening of the stated idealisation, not a substitute for an engineer's design and sign-off.

## Optional AI/MCP workflow

Use the daily installation's isolated MCP runtime as described in [Codex/CoS connection setup](../../../../cos/EXTERNAL_CLIENTS.md). In Rhino, run `almondconnect`, then select the saved document from the client's connection tools. `almonddisconnect` releases that connection without saving or closing Rhino.
The old port-5000 listener and standalone server start/stop commands are removed from this fork. Browsing the archive itself does not require an MCP connection.

## Troubleshooting

- Native engine unavailable or source mismatch: read the reported path and rebuild the Python environment from the registered checkout using the root installation procedure. The panel requires its local editable package and fixed solver launcher.
- Archive folder missing: reinstall the full Yak package; copying only the RHP is insufficient. Keep its dependencies and `archive` directory together.
- Installed library lookup failed: read the message above the cards, check the daily Almond Python environment or manifest, then click **Reload**.
- An installed file changed while browsing: click **Reload**. If placement reports a source mismatch, run `asset_08-refresh tool(asset_id)` before placing it.
  A changed bundled file instead requires restoring that release's archive.
- Optional drawing element says unavailable: its community model is not bundled.
- Browser cannot connect_02-session tool after quitting Rhino: reopen Rhino and run `AlmondLibrary`.
- Models remain available on disk inside the installed package's `archive/files/generated/models` directory; source records are in `archive/evidence`.

Support: <https://github.com/liangjunglj-cpu/almond-mcp/issues>.

In Karamba, press the small **?** beside a heading for guidance. Press it again or use Escape to close it. The diagrams explain supports and display symbols; opening help does not change analysis inputs.

Search **organic** for the detailed natural/textile source models. Object details show recorded triangle counts, topology checks and the generated reference image. Preview colours are Almond materials; source-image textures are not baked into these geometry editions.

### Preview display mode

The Preview selector defaults to Follow Rhino viewport inside Rhino. Ghosted, Arctic, Shaded and Rendered are approximated in the thumbnails and enlarged 3D preview. Choose Material colours to keep colour previews. Custom/unsupported modes fall back to material colours. Scene lighting and edge settings are not reproduced; placed objects use Rhino’s actual display mode.
