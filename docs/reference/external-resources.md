# External Resources

> Third-party GitHub repositories reviewed as possible inputs to StoryWeaver — grouped by need, with licence, relevance, the plan phase it feeds, and cautions. None is a dependency.

## Status

Implemented (documentation). Everything here is **reference material only — not adopted, not a dependency, nothing in the codebase uses it**. Entries were reviewed on 2026-10-01 from each repository's front page (a page fetch, not a read of its files). "Verified-on-page" means exactly that; **CPU/offline/speed statements are the repositories' own claims and are unmeasured on our hardware**; a field marked "not shown" was not visible on the page and must be checked before relying on it. Third-party facts (licences, limits, supported engines, maintenance state) change; re-check at the time of use.

## How to use this page

Consult it at the start of the phase named in each table. If something is adopted, record the decision in an [ADR](../decisions/README.md), keep any required licence notice, and change its status here to *Adopted*. Borrowing rules: copy small snippets at most, rewrite against our schemas and provider interfaces, never import example apps wholesale ([agent guide](../development/ai-agent-guide.md), rules 6, 7, 13, 14).

**Licence cautions that apply across this page**
- **Copyleft:** GPL-3.0 (ComfyUI, ComfyUI_IPAdapter_plus, pysrt) and AGPL-3.0 (react-video-timeline-editor) can impose obligations if code is copied or linked into StoryWeaver. Calling ComfyUI as a separate HTTP service is a different matter from copying its code; we have not taken legal advice and this page is not legal advice.
- **Model weights are licensed separately from code**, often non-commercial (for example F5-TTS and AudioCraft weights). None of the weight licences for image models was verified here — check before choosing any.
- **Source-available / usage-restricted:** Remotion (company licence in some cases; terms in its `LICENSE.md`, not seen), OpenVideo Editor (company licence above 3 employees), Twick (resale limits).
- **System FFmpeg:** several tools below need it. StoryWeaver's render path does not (Remotion bundles its own, reportedly a reduced build — see [FFmpeg](../media/ffmpeg.md) and the [P8 plan](../../implementation-plan/06-timeline-render-qa.md)); prefer tools that avoid adding it.

## Index by need

| Need | Section | Phase fed |
| --- | --- | --- |
| Model/provider choices, free tiers, voice shortlist, example apps | [Overviews and lists](#overviews-and-lists) | P2, P3–P4, P7, P11 |
| Source ingestion, structured output, routing, evaluation, similarity, embeddings | [Source, intelligence and story](#source-intelligence-and-story) | P1, P2, P3–P5, P11, P12 |
| Image generation | [Image generation](#image-generation) | P6 (P12 for consistency training) |
| TTS, alignment, loudness, subtitles, music | [Voice and audio](#voice-and-audio) | P7, P12 |
| Rendering, timeline editors, captions, transitions, video QA | [Video, editor and rendering](#video-editor-and-rendering) | P8, P9, P12 |

## Overviews and lists

| Resource | What it is | Licence (as stated) | Relevance | Phase | Status |
| --- | --- | --- | --- | --- | --- |
| [awesome-free-llm-apis](https://github.com/mnfst/awesome-free-llm-apis) | Curated documentation list of free-tier LLM API providers: models, limits, base URLs (21 providers at review: Google Gemini, OpenRouter, Groq, Mistral, Cohere, Cloudflare Workers AI, NVIDIA NIM, Hugging Face, Ollama Cloud, …). States endpoints are OpenAI-compatible unless noted | CC0-1.0 | **Most relevant overview:** provider candidates and limits for the ₹0 path and model routing. Most OpenAI-compatible endpoints could reuse `OpenAICompatibleProvider`; making them configuration-driven is a small P2 task (today only OpenRouter and Grok are registered) | P2 | Reference only |
| [awesome-llm-apps](https://github.com/Shubhamsaboo/awesome-llm-apps) | Collection of standalone example LLM apps/tutorials (agents, multi-agent teams, voice, RAG, MCP); mostly Python (Streamlit, LangGraph, CrewAI, AG2). Not a library | Apache-2.0 | Reading material for prompt/role decomposition and RAG ideas | P3–P4, P7, P11 | Reference only |
| [Open-LLM-VTuber](https://github.com/Open-LLM-VTuber/Open-LLM-VTuber) | Real-time voice-chat companion with Live2D avatars and pluggable LLM/ASR/TTS backends; says it can run fully offline incl. CPU; v1.0.0 has breaking changes | MIT (Live2D sample models excluded) | Its engine lists are a voice-engine shortlist; avatar/chat parts are out of scope | P7 | Reference only |

Cautions: the free-LLM list itself notes free prompts may be used for training (it names some providers), limits change, some providers require identity verification — see [provider security](../security/provider-security.md); re-measure limits in the P2 benchmark. Two providers from it (Google, OpenRouter) have keys in the git-ignored local `.env` and have had one minimal connectivity check each. The three repos above each lean on frameworks or vendor APIs that conflict with our provider abstraction ([ADR-003](../decisions/ADR-003-provider-abstraction.md), [ADR-004](../decisions/ADR-004-ai-vs-deterministic-responsibilities.md)).

## Source, intelligence and story

| Resource | What it is | Licence | Relevance & phase | Recommendation / cautions |
| --- | --- | --- | --- | --- |
| [yt-dlp](https://github.com/yt-dlp/yt-dlp) | Downloader CLI + Python API; supports `--skip-download`, `--write-subs`, `--write-auto-subs`, `--list-subs`, `--flat-playlist`, `--dump-json` | Unlicense (bundled executables GPLv3+) | P1 metadata + captions, P11 channel enumeration — all without media download | **Already our optional extra.** Page shows a `.NO_AI` file (meaning not stated); no ToS caveat on the page |
| [youtube-transcript-api](https://github.com/jdepoix/youtube-transcript-api) | Fetches transcripts incl. auto-generated, no API key, no download | MIT | P1 lighter captions-only alternative | Reference only. Uses an undocumented YouTube API ("no guarantee it won't stop working"); cloud-provider IPs mostly blocked; age-restricted videos unavailable. Keep transcript upload first-class |
| [scrapetube](https://github.com/dermasmid/scrapetube) | Lists channel/playlist/search videos without an API key | MIT | P11 channel enumeration | Reference only; scrapes YouTube (page says this may violate ToS — no assessment made). yt-dlp `--flat-playlist` covers the need |
| [Instructor](https://github.com/567-labs/instructor) | Pydantic structured outputs with retry on validation failure; many providers | MIT | P2 structured-output hardening | Reference only — we already have `generate_structured` with retry; adding it would layer a second provider abstraction |
| [Outlines](https://github.com/dottxt-ai/outlines) | Structured generation guaranteed during decoding for local backends (transformers, llama.cpp, vLLM, Ollama) | Apache-2.0 | P2 if a local model cannot produce valid JSON in the benchmark | Reference only; heavy local runtimes; one API is early-access |
| [LiteLLM](https://github.com/BerriAI/litellm) | SDK + proxy for 100+ providers with retry/fallback, load balancing, spend tracking | **Not shown on page** (LICENSE file exists; enterprise features licensed separately) | P2 routing/fallback/cost tracking | Reference only — overlaps routing we plan, large surface, its own proxy service. Check licence before any adoption |
| [RouteLLM](https://github.com/lm-sys/RouteLLM) | Routes each query between a strong and a cheap model by predicted win rate | Apache-2.0 | P2/P12 cost-aware routing research | Reference only; pretrained routers trained on one model pair; embeddings need an OpenAI key; our routing is per task |
| [llama.cpp](https://github.com/ggml-org/llama.cpp) | C/C++ LLM inference; CPU-only supported, GGUF quantization, OpenAI-compatible `llama-server` | MIT | P2 local-model option for the benchmark | Candidate runtime, not a Python dependency. Speed on a Ryzen 5 5500U **unmeasured**; `llama-server` could reuse `OpenAICompatibleProvider` |
| [pgvector](https://github.com/pgvector/pgvector) | Postgres vector extension (HNSW, IVFFlat; many metrics; ≤16,000 dims) | Not shown on page (LICENSE file mentioned) | P11/P12; **already in use** | Its docs suggest combining with full-text search via Reciprocal Rank Fusion — matches decision D7/P11 |
| [pgvector-python](https://github.com/pgvector/pgvector-python) | Python bindings (SQLAlchemy, psycopg 3, …) with hybrid-search examples | MIT | P11 hybrid search | **Already a dependency**; the hybrid examples are a template |
| [promptfoo](https://github.com/promptfoo/promptfoo) | Declarative LLM eval/regression harness; runs locally; CI integration; Node tool | MIT | P2 prompt regression ([AI evaluation](../testing/ai-evaluation.md)) | Candidate; evaluate against golden-fixture tests first. Page says it is now part of OpenAI while staying MIT |
| [datasketch](https://github.com/ekzhu/datasketch) | MinHash/LSH near-duplicate detection | MIT | P12 near-duplicate sources/scripts | Reference only for now; v2.0 changed MinHash defaults (persisted sketches need rebuilding); exact fingerprints and n-gram checks come first |
| [RapidFuzz](https://github.com/rapidfuzz/RapidFuzz) | Fast Levenshtein-based string similarity | MIT | P12 cheap similarity signals; P1 fuzzy title matching | Candidate small dependency; needs Python ≥3.11 (we use 3.12); normalize text first |
| [sentence-transformers](https://github.com/UKPLab/sentence-transformers) | Embeddings, cross-encoders, reranking | Apache-2.0 | P11 embeddings alternative; P12 similarity | Reference only — requires PyTorch 2.2+ and transformers v5+ (heavy); model licences separate; a 384-dim model would not match our fixed 768 column ([KI-6](status.md#known-issues-and-limitations)) |
| [Re3 story generation](https://github.com/yangkevin2/emnlp22-re3-story-generation) | EMNLP 2022 research code: long-story generation by recursive reprompting/revision | MIT | P4–P5 ideas: outline-then-write and revise loops | Reference only — needs Python 3.8, PyTorch 1.12 and the GPT-3 API; page warns outputs may include unfiltered NSFW content. Read the ideas, not the code |

Not checked (named in the brief, left out for lack of verification): DOC, "storywriter", Inspect, DeepEval.

## Image generation

CPU speed claims below are the repositories' own and **unmeasured on the Ryzen 5 5500U**; settling them is the P6 spike ([visuals plan](../../implementation-plan/05-visuals-and-audio.md)).

| Resource | What it is | Licence | CPU/offline claim | Relevance & phase | Cautions |
| --- | --- | --- | --- | --- | --- |
| [stable-diffusion.cpp](https://github.com/leejet/stable-diffusion.cpp) | Diffusion inference in C/C++ on ggml: SD1.x/2.x/SDXL, SD-/SDXL-Turbo, LCM, LoRA, ControlNet (SD1.5), PhotoMaker, img2img | MIT | "Working in the same way as llama.cpp", "without external dependencies" (a search snippet, not the page, mentioned ~2.3 GB RAM for 512×512 fp16) | **Best CPU-first candidate** for an `ImageGenerator` adapter (CLI subprocess with argument list, or its web UI) | Speed unmeasured; web UI is new (2026-04); Python bindings are third-party |
| [ComfyUI](https://github.com/comfyanonymous/ComfyUI) | Node-graph engine for local image/video/audio generation; workflows saved as JSON | GPL-3.0 | "Runs fully offline"; as low as 4 GB VRAM + 8 GB RAM; CPU-only mentioned for portable builds | P6: the planned `ComfyUIProvider` target (HTTP workflow client) | GPL-3.0 (see cautions above); page did not show the API endpoints or a CPU flag; weight licences not shown |
| [ComfyUI_IPAdapter_plus](https://github.com/cubiq/ComfyUI_IPAdapter_plus) | ComfyUI nodes for IP-Adapter: style/subject transfer from reference images | GPL-3.0 | Not stated | P6/P12 reference-image consistency | Author put it in "maintenance only" mode; FaceID needs `insightface` (licence unverified) |
| [IP-Adapter](https://github.com/tencent-ailab/IP-Adapter) | Image-prompt adapter for diffusion models (22M parameters) | Apache-2.0 | Not stated | Background for consistency work | FaceID variant licences unverified |
| [StoryDiffusion](https://github.com/HVision-NKU/StoryDiffusion) | Consistent self-attention for character-consistent image sequences | Apache-2.0 (page; search snippets said MIT) | None stated; tested on a 24 GB GPU, 30 GB RAM | Reference for P12 consistency — not usable on the baseline machine | Needs ≥3 prompts per run |
| [diffusers](https://github.com/huggingface/diffusers) | PyTorch library of diffusion pipelines | Apache-2.0 | Not stated; README links to speed/memory guides | P6 Python-native adapter option | PyTorch is a heavy new dependency; LCM/LoRA/IP-Adapter support not shown on the page |
| [optimum-intel](https://github.com/huggingface/optimum-intel) | Transformers/Diffusers ↔ OpenVINO bridge | Apache-2.0 | Generic "Intel CPUs/GPUs" | P6 CPU-speed spike candidate | Intel-oriented; AMD CPUs not mentioned; no SD numbers shown |
| [openvino.genai](https://github.com/openvinotoolkit/openvino.genai) | OpenVINO GenAI pipelines incl. Stable Diffusion/Flux image generation; C++/Python/Node APIs | Apache-2.0 | "Friendly to PC and laptop execution"; CPU/GPU/NPU | Same spike as above | AMD support and speeds not stated |
| [kohya-ss/sd-scripts](https://github.com/kohya-ss/sd-scripts) | LoRA / DreamBooth / textual-inversion training scripts | Mostly Apache-2.0 (some MIT/BSD-3) | CPU not mentioned (CUDA, xformers) | P12 per-project character/style LoRA | Needs a GPU in practice |
| [ComfyAPI](https://github.com/SamratBarai/ComfyAPI) | Python package to queue ComfyUI workflows, poll progress, download outputs | MIT | n/a (client) | P6 reference for our own ComfyUI client | Tiny project (14 commits); read for ideas, don't depend |
| [comfyui-api (9elements)](https://github.com/9elements/comfyui-api) | Python wrapper for programmatic ComfyUI execution (uses `/ws`) | **Not shown** | n/a (client) | Same | Don't copy code until the licence is checked |
| [rough.js](https://github.com/rough-stuff/rough) | <9 kB library for sketchy, hand-drawn-style Canvas/SVG graphics | MIT | n/a (deterministic code, no model) | P6 fallback: code-drawn sketch/stick-figure illustrations with no model or GPU | Draws shapes, not scenes; a product decision (D10) |

## Voice and audio

| Resource | What it is | Licence | CPU/offline claim | Relevance & phase | Cautions |
| --- | --- | --- | --- | --- | --- |
| [Piper](https://github.com/rhasspy/piper) | "Fast, local neural text to speech system" | MIT | Claimed, no figures | P7 TTS spike candidate | **Archived 2025-10-06 (read-only)**; page says development moved to `OHF-Voice/piper1-gpl` — verify that successor's licence (name suggests GPL, unverified). Voice licences, WAV output not stated |
| [Kokoro](https://github.com/hexgrad/kokoro) | Inference library for the 82M-parameter Kokoro-82M TTS model | Apache-2.0 (weights described as Apache-licensed — confirm) | "Significantly faster and more cost-efficient"; no CPU figure | P7 TTS candidate; WAV via `soundfile` in its example | Needs espeak-ng; 9 languages incl. English, Hindi, Spanish, French, Japanese, Mandarin |
| [Coqui TTS](https://github.com/coqui-ai/TTS) | TTS toolkit with pretrained models | MPL-2.0 | CPU Docker image exists; speed not stated | P7 TTS candidate; WAV in examples | Python ≥3.9 and <3.12 only; XTTS model licence not stated; heavy PyTorch |
| [MeloTTS](https://github.com/myshell-ai/MeloTTS) | Multilingual TTS (MIT & MyShell.ai) | MIT | "Fast enough for CPU real-time inference" | P7 TTS candidate | Output format and weight licence not stated |
| [Sherpa-ONNX](https://github.com/k2-fsa/sherpa-onnx) | Offline speech toolkit: TTS, ASR, VAD, diarization on onnxruntime | Apache-2.0 | Runs without Internet; CPU speed not stated | One dependency could cover TTS + VAD + ASR (P7, P12) | Each model needs its own licence check; TTS output format not stated |
| [F5-TTS](https://github.com/SWivid/F5-TTS) | Flow-matching TTS with voice cloning; WAV output | Code MIT; **pretrained model CC-BY-NC** | CPU not stated; GPU-oriented | Low fit for P7 | **Non-commercial model licence** |
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | CTranslate2 Whisper reimplementation (**already our transcription adapter**) | MIT | CPU supported; "up to 4× faster than openai/whisper" (own benchmark, unmeasured here) | P1/P12 transcription; `word_timestamps` supported | **No system FFmpeg needed** (decodes with PyAV, which bundles FFmpeg libraries) |
| [whisper.cpp](https://github.com/ggml-org/whisper.cpp) | C/C++ Whisper without dependencies | MIT | "CPU-only inference", fully offline | P12 alternative ASR | `whisper-cli` takes 16-bit WAV only (page shows an ffmpeg conversion) |
| [WhisperX](https://github.com/m-bain/whisperX) | Whisper ASR with word-level timestamps + diarization | BSD-2-Clause | CPU via `--compute_type int8 --device cpu` (speed not stated) | P12 word-level subtitle alignment | **Requires FFmpeg**; diarization needs a Hugging Face token; default alignment models for en/fr/de/es/it |
| [stable-ts](https://github.com/jianfch/stable-ts) | Whisper wrapper: stable timestamps, forced alignment, SRT/VTT/ASS | MIT | Not stated | P12 alignment idea | **Archived 2026-05-30**, development paused; needs FFmpeg |
| [pyloudnorm](https://github.com/csteinmetz1/pyloudnorm) | ITU-R BS.1770-4 loudness meter/normalisation in Python | MIT | NumPy + SciPy only | P7 audio checks; P12 LUFS | FFmpeg not mentioned as required; last-activity date not shown |
| [AudioCraft](https://github.com/facebookresearch/audiocraft) | MusicGen/AudioGen music and sound-effect models | Code MIT; **weights CC-BY-NC 4.0** | Not stated | P12 music/SFX | **Non-commercial weights**; Python 3.9, PyTorch 2.1.0 |
| [webvtt-py](https://github.com/glut23/webvtt-py) | Read/write/convert WebVTT (and SRT/SBV) | MIT | n/a | P7 subtitle export (or write our own small formatters) | Python versions not stated |
| [pysrt](https://github.com/byroot/pysrt) | Parse/edit/create SRT files | **GPL-3.0** | n/a | P7 subtitle files | **Copyleft — avoid adding; write a small SRT formatter instead** |

Also checked, not listed: `ffmpeg-normalize` (needs system ffmpeg; licence not shown) and Montreal Forced Aligner (MIT, but needs Kaldi via conda) — both heavy for our setup.

## Video, editor and rendering

| Resource | What it is | Licence | Relevance & phase | Cautions |
| --- | --- | --- | --- | --- |
| [Remotion](https://github.com/remotion-dev/remotion) | React framework for programmatic video (**in use**); includes `@remotion/captions` and `@remotion/transitions` | Custom, source-available — "requires obtaining a company license in some cases" (terms in `LICENSE.md`, not seen) | P8 (in use); transitions P12 | Read `LICENSE.md` before relying on it commercially |
| [Revideo](https://github.com/redotvideo/revideo) | TypeScript video engine, headless `renderVideo()`, React player | MIT | Alternative renderer to compare with Remotion (P8) | PostHog telemetry on by default (`DISABLE_TELEMETRY=true`); different programming model |
| [Motion Canvas](https://github.com/motion-canvas/motion-canvas) | TypeScript vector-animation library + editor | MIT | Animation reference; little use for illustration + camera motion | Maintenance not verified (page errored on last commit) |
| [Editly](https://github.com/mifi/editly) | Declarative JSON/JS video editing on ffmpeg: transitions, subtitles, audio ducking, Ken Burns pan-zoom | MIT | Closest design match to a JSON timeline renderer; reference for P12 transitions/audio mixing | **Needs system ffmpeg/ffprobe**; ESM-only |
| [MoviePy](https://github.com/Zulko/moviepy) | Python video editing library (v2.0, breaking changes) | MIT | Python-side post-processing; duplicates Remotion | Needs ffmpeg; README says "Maintainers wanted" |
| [OpenVideo Editor](https://github.com/designcombo/react-video-editor) (formerly designcombo/react-video-editor) | Next.js 15 web editor on PixiJS v8, multi-track timeline | Dual: free for individuals/non-profits/orgs ≤3 employees, company licence above | P9 timeline-UX reference only | Needs R2/S3, Deepgram and Pexels keys; company-licence rule |
| [OpenCut](https://github.com/OpenCut-app/OpenCut) | CapCut-style open-source editor (web/desktop/mobile), Rust core | MIT | P9 UX inspiration | Being rewritten; not accepting outside contributions; stable version is `opencut-classic` |
| [Twick](https://github.com/ncounterspecialist/twick) | React SDK for timeline editing with canvas, AI captions, export options | Sustainable Use License v1.0 (free to use/self-host; not resellable as a standalone SDK) | P9 timeline reference | Non-standard licence |
| [react-video-timeline-editor](https://github.com/Ektie/react-video-timeline-editor) | React multi-track timeline component, JSON serialization, no backend | **AGPL-3.0** | P9 timeline UI reference | Copyleft risk if code copied; 4 commits |
| [remotion-templates](https://github.com/reactvideoeditor/remotion-templates) | 81 copy-paste Remotion components incl. 9 transitions | MIT | P12 transitions (copy and adapt) | Not an npm package; low maintenance (5 commits); Remotion's licence still applies |
| [remotion-captions-kit](https://github.com/Fats403/remotion-captions-kit) | Six animated caption presets on `@remotion/captions`, SRT support | MIT | P12 word-level captions; P7 styling reference | Early stage (5 commits); word-level presets need per-word timing we don't have in the MVP |
| [ffmpeg-quality-metrics](https://github.com/slhck/ffmpeg-quality-metrics) | CLI computing PSNR, SSIM, VMAF, VIF between reference and distorted video | MIT | P12 render-regression QA (comparing two renders) | **Needs a full ffmpeg ≥7.1** (+ libvmaf for VMAF) and a reference video — conflicts with Remotion's reduced bundled build |
| [PySceneDetect](https://github.com/Breakthrough/PySceneDetect) | OpenCV-based cut/fade detection; Threshold Detector finds fades to/from black | BSD-3-Clause | P8/P10 black-frame QA without ffmpeg `blackdetect` | Adds OpenCV (large); v0.7.1 (2026-07) |
| [MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo) | Topic-to-short-video pipeline: LLM script → TTS → subtitles → stock footage (FastAPI + Streamlit) | MIT | Study of end-to-end orchestration and subtitle modes (TTS timestamps vs local faster-whisper) | Uses stock footage, not illustrations; needs system FFmpeg |

Note on the reduced-FFmpeg claim: the P8 plan investigation found Remotion's bundled ffmpeg lacks filters such as `blackdetect` and `volumedetect`; that was not re-verified here, and the two QA tools above rest on it.

## Candidate shortlist per spike (where to start)

| Spike | Start with |
| --- | --- |
| P2 provider/model benchmark | awesome-free-llm-apis (pick 2–3 providers); llama.cpp for local; promptfoo for regression |
| P6 image engine | stable-diffusion.cpp (CPU-first), ComfyUI client; rough.js as the no-model fallback |
| P7 TTS engine | Kokoro, Sherpa-ONNX, MeloTTS (verify weight licences); Piper only after checking its successor repo |
| P8 render QA | Our own stdlib/PNG-based checks (plan) before adding PySceneDetect/OpenCV |
| P11 semantic search | pgvector + pgvector-python hybrid examples |
| P12 | WhisperX/Whisper.cpp alignment, remotion-templates transitions, datasketch/RapidFuzz similarity |
