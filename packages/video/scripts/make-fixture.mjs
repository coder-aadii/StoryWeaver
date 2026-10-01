#!/usr/bin/env node
// Deterministically generates the tiny fixture used by the render asset-path spike (P0-T7):
//   sample/fixture/images/fixture.png  320x180, four solid colour quadrants (survives scaling)
//   sample/fixture/audio/fixture.wav   2.0 s, 16 kHz mono 16-bit, 440 Hz sine
//   sample/fixture/timeline.json       Timeline v1 referencing them by project-relative key
// Node stdlib only. Re-running produces byte-identical files.
import { deflateSync } from "node:zlib";
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..", "sample", "fixture");
mkdirSync(join(root, "images"), { recursive: true });
mkdirSync(join(root, "audio"), { recursive: true });

// ---- PNG -------------------------------------------------------------------------------
export const QUADRANTS = { tl: [220, 40, 40], tr: [40, 180, 60], bl: [50, 80, 220], br: [240, 210, 40] };
const W = 320, H = 180;
const crcTable = Array.from({ length: 256 }, (_, n) => {
  let c = n;
  for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
  return c >>> 0;
});
const crc32 = (buf) => {
  let c = 0xffffffff;
  for (const b of buf) c = crcTable[(c ^ b) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
};
const chunk = (tag, data) => {
  const len = Buffer.alloc(4); len.writeUInt32BE(data.length);
  const body = Buffer.concat([Buffer.from(tag, "ascii"), data]);
  const crc = Buffer.alloc(4); crc.writeUInt32BE(crc32(body));
  return Buffer.concat([len, body, crc]);
};
const raw = Buffer.alloc((W * 3 + 1) * H);
for (let y = 0; y < H; y++) {
  raw[y * (W * 3 + 1)] = 0; // filter: none
  for (let x = 0; x < W; x++) {
    const q = QUADRANTS[(y < H / 2 ? "t" : "b") + (x < W / 2 ? "l" : "r")];
    raw.set(q, y * (W * 3 + 1) + 1 + x * 3);
  }
}
const ihdr = Buffer.alloc(13);
ihdr.writeUInt32BE(W, 0); ihdr.writeUInt32BE(H, 4); ihdr[8] = 8; ihdr[9] = 2;
writeFileSync(
  join(root, "images", "fixture.png"),
  Buffer.concat([
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    chunk("IHDR", ihdr),
    chunk("IDAT", deflateSync(raw, { level: 9 })),
    chunk("IEND", Buffer.alloc(0)),
  ]),
);

// ---- WAV -------------------------------------------------------------------------------
const RATE = 16000, SECONDS = 2.0, FREQ = 440;
const n = Math.round(RATE * SECONDS);
const pcm = Buffer.alloc(n * 2);
for (let i = 0; i < n; i++) pcm.writeInt16LE(Math.round(Math.sin((2 * Math.PI * FREQ * i) / RATE) * 0.5 * 32767), i * 2);
const hdr = Buffer.alloc(44);
hdr.write("RIFF", 0); hdr.writeUInt32LE(36 + pcm.length, 4); hdr.write("WAVEfmt ", 8);
hdr.writeUInt32LE(16, 16); hdr.writeUInt16LE(1, 20); hdr.writeUInt16LE(1, 22);
hdr.writeUInt32LE(RATE, 24); hdr.writeUInt32LE(RATE * 2, 28); hdr.writeUInt16LE(2, 32); hdr.writeUInt16LE(16, 34);
hdr.write("data", 36); hdr.writeUInt32LE(pcm.length, 40);
writeFileSync(join(root, "audio", "fixture.wav"), Buffer.concat([hdr, pcm]));

// ---- Timeline v1 (3 s: scene_001 image+audio, static camera; scene_002 placeholder) -----
const timeline = {
  version: 1, fps: 30, width: 1280, height: 720,
  scenes: [
    { scene_id: "scene_001", start: 0, duration: 2, narration: "", subtitle: null,
      image_src: "images/fixture.png", audio_src: "audio/fixture.wav",
      camera: { shot: "wide", movement: "static" } },
    { scene_id: "scene_002", start: 2, duration: 1, narration: "", subtitle: null,
      image_src: null, audio_src: null, camera: { shot: "medium", movement: "static" } },
  ],
};
writeFileSync(join(root, "timeline.json"), JSON.stringify(timeline, null, 2) + "\n");
console.log("fixture written to", root);
