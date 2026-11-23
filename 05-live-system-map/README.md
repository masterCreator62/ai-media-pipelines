# 5. Live system map ("D.A.V.E. City")

**Problem.** An AI workstation with dozens of chats, sub-agents, skills, scheduled jobs and local services is hard to keep track of.

**Result.** A city map you can explore in 2D (SVG) or 3D (three.js): the model is the centre, every subsystem is a district, and every building opens into an office where "employees" (chats and agents) show on their monitors what they are working on right now. The data rebuilds every 10 minutes through Windows Task Scheduler in 0.1–0.7 seconds, without calling a paid model.

## How it works

- `src/build_data.py` reads agent and skill definitions, memory notes, project folders, MCP configuration and the agents' session logs (incrementally, only what was appended), checks local service ports, and writes `data.js` atomically. A failing section falls back to the previous data instead of breaking the build; a lock file prevents parallel runs.
- Privacy filter: e-mails, phone numbers, key-like strings and "password: …" values are removed during the build, and links are reduced to the site name.
- `src/index.html` (2D) and `src/3d/index.html` + `src/3d/interior.js` (3D) render the city and the interiors; monitors are canvas textures redrawn in place when data changes, without resetting the camera.
- `src/live.js` reloads the data every 60 seconds even from `file://`, where `fetch` does not work.
- `src/make_share.py` packs everything into one offline HTML file (~1.5 MB).

The generated data is personal and is not included in this repository.
