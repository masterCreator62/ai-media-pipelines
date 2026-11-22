# AI Media Automation — Portfolio

https://github.com/user-attachments/assets/ec4170b8-56f6-4fb9-9e32-394639679019

**Demo video, 2:21** ([full-HD file](media/portfolio_demo.mp4)) — the pipelines at work: a one-line request becomes a rendered Short, QA blocks a broken render until it is fixed, then music Shorts, highlight cutting, local image generation and Blender → Roblox weapons. AI voice (edge-tts).

**Sergey** · AI-native media engineer ("vibe coder") · Python · ffmpeg · LLM agents · Blender · Roblox/Luau

I build automated content factories with AI coding agents (Claude Code): a script or a JSON brief goes in, a finished, fact-checked, branded video, image set or game asset comes out, together with upload metadata. Everything below runs on one consumer PC (RTX 3060 Ti, 8 GB VRAM) at near-zero running cost.

| | Pipeline | What it produces | Output so far |
|---|---|---|---|
| 1 | [Game news video factory](01-game-news-video-factory/) | News Shorts and 8–9 min long videos from official press kits: script → AI narration → animated infographics → captions → procedural music → automated QA → scheduled upload | 49 videos rendered in 4 days; 20 published or scheduled on the channel |
| 2 | [Music lyric Shorts](02-music-lyric-shorts/) | Vertical Shorts for an AI-music channel, with sung lyrics synced on screen by speech recognition and alignment | 30 Shorts produced and scheduled (3 a day) |
| 3 | [Gameplay highlight Shorts](03-gameplay-highlight-shorts/) | Finds the best moments in hours of game recordings by audio analysis and renders hook-first Shorts and CapCut compilations | 19 videos (Shorts and a TOP-10) |
| 4 | [Local image generation](04-local-image-generation/) | Free, offline image generation (covers, icons, game art) with batch jobs and a licence log | 155 images; commercial-safe Apache-2.0 models only |
| 5 | [Blender → Roblox 3D pipeline](05-blender-to-roblox-3d-pipeline/) | Procedural game weapons modelled in code, rendered for review, imported into a Roblox game with automated checks | 17 weapons, 85 skin kits, 86/86 in-engine self-tests |
| 6 | [Live system map](06-live-system-map/) | A 2D/3D "city" visualising an AI agent workstation, rebuilt every 10 minutes from live logs | Runs unattended via Windows Task Scheduler |

## How I work

- **Agents write, I direct and verify.** I set the spec, constraints and acceptance checks; the coding agent implements them; an independent critic agent reviews facts, policy and quality before anything ships.
- **Every pipeline checks itself.** Loudness (−14 LUFS), safe areas for the Shorts UI, length against the title's promise, banned claims, source URLs that open, contact sheets of frames, transcription of the rendered audio. A video that fails QA does not get uploaded.
- **Cost-aware by default.** Free TTS, local diffusion models, procedural music (no Content ID claims), a local LLM router for bulk text work. Paid services only where they clearly win.
- **Rights first.** Only official press-kit material, my own recordings and my own generated assets; sources listed in every description; AI disclosure on AI music.

## Stack

Python (Pillow, NumPy, edge-tts) · ffmpeg (filter graphs, libass, two-pass loudnorm, Media Foundation H.264) · ComfyUI (Z-Image-Turbo, FLUX.1 schnell) · Blender Python API + Blender MCP · Roblox Studio, Rojo, Luau · three.js · browser automation of YouTube Studio · Claude Code with custom skills and sub-agents · local LLMs (LM Studio, OpenAI-compatible router)

## Certifications

In progress: Anthropic Academy (Claude Code in Action, Building with the Claude API), GitHub Foundations.

## Notes on the code

The scripts are shown as they run in production on my workstation, so paths point to local folders and some names are in Russian. Third-party footage, channel credentials and personal data are not included.

## Contact

GitHub: [masterCreator62](https://github.com/masterCreator62) · YouTube: [Game Pulse News](https://www.youtube.com/channel/UCVTV79tn8Ap07EiKKa3qBng) · [World Metal Empire](https://www.youtube.com/channel/UCDw5DJxMjjiqrDTudBJrITg)

© 2026 Sergey. Code shown for portfolio review; all rights reserved.
