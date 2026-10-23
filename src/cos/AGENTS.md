# User-made COS adapter

Follow `../../AGENTS.md`, `../../LOCAL_SETUP.md` and `../engine/AGENTS.md`.
One stdio host owns separate workers for each bound Rhino. Engine handles
storage, native completion and helper compatibility. Do not duplicate these
policies in COS. Preserve source/schema checks; regenerate the catalog without
importing the DB-owning server. Register `../rhp/AlmondCOS/plugin-runtime/AlmondCOS.rhp`
with all dependencies beside it. Build/registration are not proof of live Rhino loading.
