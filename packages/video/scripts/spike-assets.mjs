#!/usr/bin/env node
// P0-T7 render asset-path spike (see docs/decisions/ADR-009-render-asset-resolution.md).
//
// Proves that a generated image + WAV reach the Remotion renderer when referenced by a
// project-relative key and resolved with staticFile() against `--public-dir`:
//   1. regenerate the deterministic fixture (sample/fixture)  -- the .wav is git-ignored
//   2. render the `Assets` composition with `--public-dir sample/fixture`
//   3. verify the MP4 using ONLY the ffmpeg/ffprobe binaries bundled with Remotion:
//        video+audio streams, duration, a decoded frame contains the fixture image,
//        the placeholder scene does not, audio is non-silent for ~the WAV length only
//   4. (--perf) render a 60 s timeline built from the fixture and print wall-clock time
//
// Usage:  node scripts/spike-assets.mjs [--out <dir>] [--perf]
// Not part of `make test` (needs the Remotion headless Chrome and takes a while).
// Output goes to --out (default: <os tmpdir>/storyweaver-spike), never into the repo.
import { execFileSync } from "node:child_process";
import { mkdirSync, readdirSync, readFileSync, statSync, writeFileSync, existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { inflateSync } from "node:zlib";

const videoDir = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const repoRoot = resolve(videoDir, "..", "..");
const fixtureDir = join(videoDir, "sample", "fixture");
const args = process.argv.slice(2);
const argValue = (name) => (args.includes(name) ? args[args.indexOf(name) + 1] : undefined);
const outDir = resolve(argValue("--out") ?? join(tmpdir(), "storyweaver-spike"));
mkdirSync(outDir, { recursive: true });

let failures = 0;
const check = (ok, label, detail = "") => {
  console.log(`${ok ? "PASS" : "FAIL"}  ${label}${detail ? "  " + detail : ""}`);
  if (!ok) failures++;
};

// ---- locate Remotion's bundled binaries (pnpm layout; no system ffmpeg is used) ------------
function findBundled(name) {
  const store = join(repoRoot, "node_modules", ".pnpm");
  for (const dir of readdirSync(store).filter((d) => d.startsWith("@remotion+compositor-"))) {
    const pkg = join(store, dir, "node_modules", "@remotion", dir.replace(/^@remotion\+/, "").replace(/@[\d.]+$/, ""));
    for (const candidate of [join(pkg, name), join(pkg, name + ".exe")]) {
      if (existsSync(candidate)) return candidate;
    }
  }
  throw new Error(`bundled ${name} not found under ${store}`);
}
const ffmpeg = findBundled("ffmpeg");
const ffprobe = findBundled("ffprobe");
const remotion = join(videoDir, "node_modules", ".bin", "remotion");
console.log("ffmpeg :", ffmpeg, "\nffprobe:", ffprobe);

// ---- 1. fixture ------------------------------------------------------------------------------
execFileSync(process.execPath, [join(videoDir, "scripts", "make-fixture.mjs")], { stdio: "inherit" });

// ---- helpers -----------------------------------------------------------------------------------
function render(timelinePath, outFile) {
  const t0 = process.hrtime.bigint();
  execFileSync(
    remotion,
    ["render", "src/entry.ts", "Assets", outFile, `--props=${timelinePath}`, `--public-dir=${fixtureDir}`, "--overwrite", "--log=error"],
    { cwd: videoDir, stdio: ["ignore", "inherit", "inherit"] },
  );
  return Number(process.hrtime.bigint() - t0) / 1e9;
}
const probe = (file) =>
  JSON.parse(execFileSync(ffprobe, ["-v", "error", "-print_format", "json", "-show_streams", "-show_format", file]).toString());

/** Minimal 8-bit non-interlaced PNG decoder (colour types 2 and 6). Returns {w,h,bpp,data}. */
function decodePng(buf) {
  let pos = 8, w = 0, h = 0, ct = 0;
  const idat = [];
  while (pos < buf.length) {
    const len = buf.readUInt32BE(pos), tag = buf.toString("ascii", pos + 4, pos + 8);
    const body = buf.subarray(pos + 8, pos + 8 + len);
    if (tag === "IHDR") { w = body.readUInt32BE(0); h = body.readUInt32BE(4); ct = body[9]; if (body[8] !== 8 || body[12] !== 0) throw new Error("unsupported PNG"); }
    if (tag === "IDAT") idat.push(body);
    pos += 12 + len;
  }
  const bpp = ct === 6 ? 4 : ct === 2 ? 3 : (() => { throw new Error("unsupported colour type " + ct); })();
  const raw = inflateSync(Buffer.concat(idat)), stride = w * bpp, out = Buffer.alloc(h * stride);
  for (let y = 0; y < h; y++) {
    const f = raw[y * (stride + 1)], src = y * (stride + 1) + 1;
    for (let x = 0; x < stride; x++) {
      const a = x >= bpp ? out[y * stride + x - bpp] : 0, b = y ? out[(y - 1) * stride + x] : 0, c = x >= bpp && y ? out[(y - 1) * stride + x - bpp] : 0;
      let v = raw[src + x];
      if (f === 1) v += a; else if (f === 2) v += b; else if (f === 3) v += (a + b) >> 1;
      else if (f === 4) { const p = a + b - c, pa = Math.abs(p - a), pb = Math.abs(p - b), pc = Math.abs(p - c); v += pa <= pb && pa <= pc ? a : pb <= pc ? b : c; }
      out[y * stride + x] = v & 255;
    }
  }
  return { w, h, bpp, data: out };
}
const meanColour = ({ w, bpp, data }, cx, cy, r = 20) => {
  const s = [0, 0, 0]; let n = 0;
  for (let y = cy - r; y < cy + r; y++) for (let x = cx - r; x < cx + r; x++) { for (let k = 0; k < 3; k++) s[k] += data[(y * w + x) * bpp + k]; n++; }
  return s.map((v) => v / n);
};
const frameAt = (file, seconds) =>
  decodePng(execFileSync(ffmpeg, ["-v", "error", "-ss", String(seconds), "-i", file, "-frames:v", "1", "-f", "image2pipe", "-c:v", "png", "pipe:1"], { maxBuffer: 64 << 20 }));
const near = (a, b, tol) => a.every((v, i) => Math.abs(v - b[i]) <= tol);

/** Decode audio to mono 16 kHz WAV via the bundled ffmpeg; return per-100 ms RMS (0..1). */
function audioRms(file) {
  const wav = join(outDir, "decoded-audio.wav");
  execFileSync(ffmpeg, ["-v", "error", "-y", "-i", file, "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", "-f", "wav", wav]);
  const b = readFileSync(wav);
  let p = 12, dataStart = 0, dataLen = 0;
  while (p < b.length) { const tag = b.toString("ascii", p, p + 4), len = b.readUInt32LE(p + 4); if (tag === "data") { dataStart = p + 8; dataLen = Math.min(len, b.length - dataStart); break; } p += 8 + len; }
  const samples = new Int16Array(b.buffer.slice(b.byteOffset + dataStart, b.byteOffset + dataStart + (dataLen & ~1)));
  const win = 1600, rms = [];
  for (let i = 0; i + win <= samples.length; i += win) { let s = 0; for (let j = 0; j < win; j++) s += (samples[i + j] / 32768) ** 2; rms.push(Math.sqrt(s / win)); }
  return rms;
}

// ---- 2+3. fixture render and assertions ----------------------------------------------------------
const timelinePath = join(fixtureDir, "timeline.json");
const timeline = JSON.parse(readFileSync(timelinePath, "utf8"));
const expectedSeconds = Math.max(...timeline.scenes.map((s) => s.start + s.duration));
const out = join(outDir, "fixture.mp4");
const renderSeconds = render(timelinePath, out);
console.log(`rendered ${expectedSeconds}s fixture in ${renderSeconds.toFixed(1)}s -> ${out} (${(statSync(out).size / 1024).toFixed(0)} KiB)`);

const info = probe(out);
const video = info.streams.find((s) => s.codec_type === "video");
const audio = info.streams.find((s) => s.codec_type === "audio");
check(!!video && video.codec_name === "h264", "video stream is h264", video && `${video.width}x${video.height} @ ${video.r_frame_rate}`);
check(video && video.width === timeline.width && video.height === timeline.height && video.r_frame_rate === `${timeline.fps}/1`, "video size and fps match the timeline");
check(Math.abs(Number(info.format.duration) - expectedSeconds) <= 0.1, "container duration matches the timeline", `${info.format.duration}s vs ${expectedSeconds}s`);
check(!!audio, "audio stream present", audio && `${audio.codec_name} ${audio.sample_rate} Hz, ${audio.duration ?? "?"}s`);

const Q = { tl: [220, 40, 40], tr: [40, 180, 60], bl: [50, 80, 220], br: [240, 210, 40] };
const f1 = frameAt(out, 1.0);
const spots = { tl: [320, 180], tr: [960, 180], bl: [320, 540], br: [960, 540] };
for (const [name, [x, y]] of Object.entries(spots)) {
  const m = meanColour(f1, x, y);
  check(near(m, Q[name], 30), `frame @1.0s quadrant ${name} shows the fixture colour`, `got ${m.map(Math.round)} want ${Q[name]}`);
}
const f2 = frameAt(out, 2.5);
const placeholder = meanColour(f2, 320, 180);
check(!near(placeholder, Q.tl, 60), "frame @2.5s (scene without image) does NOT show the fixture", `got ${placeholder.map(Math.round)}`);

const rms = audioRms(out), THRESH = 0.05;
const loud = rms.map((v, i) => (v > THRESH ? i : -1)).filter((i) => i >= 0);
const firstLoud = loud[0] / 10, lastLoud = (loud[loud.length - 1] + 1) / 10;
check(loud.length > 0, "audio is not silent");
check(Math.abs(loud.length / 10 - 2.0) <= 0.2, "non-silent audio lasts ~ the WAV length (2.0 s)", `${(loud.length / 10).toFixed(1)}s`);
check(firstLoud <= 0.2 && Math.abs(lastLoud - 2.0) <= 0.2, "audio starts at scene start and stops at scene end", `${firstLoud}s..${lastLoud}s`);

// ---- 4. 60 s measurement -----------------------------------------------------------------------------
if (args.includes("--perf")) {
  const movements = ["slow_zoom_in", "pan_left", "slow_zoom_out", "pan_right", "tilt_up", "tilt_down"];
  const scenes = Array.from({ length: 30 }, (_, i) => ({
    scene_id: `scene_${String(i + 1).padStart(3, "0")}`, start: i * 2, duration: 2, narration: "", subtitle: i % 3 === 0 ? "Fixture caption" : null,
    image_src: "images/fixture.png", audio_src: "audio/fixture.wav", camera: { shot: "wide", movement: movements[i % movements.length] },
  }));
  const perfTimeline = join(outDir, "timeline-60s.json");
  writeFileSync(perfTimeline, JSON.stringify({ version: 1, fps: 30, width: 1280, height: 720, scenes }));
  const perfOut = join(outDir, "perf-60s.mp4");
  const secs = render(perfTimeline, perfOut);
  const pi = probe(perfOut);
  check(Math.abs(Number(pi.format.duration) - 60) <= 0.2, "60 s render has the expected duration", `${pi.format.duration}s`);
  console.log(`MEASUREMENT  60 s / 1800 frames @1280x720 rendered in ${secs.toFixed(1)} s wall-clock (${(60 / secs).toFixed(2)}x realtime); ${(statSync(perfOut).size / 1024 / 1024).toFixed(1)} MiB. One run, one machine: a measurement, not a promise.`);
}

console.log(failures ? `\n${failures} check(s) FAILED` : "\nall checks passed");
process.exit(failures ? 1 : 0);
