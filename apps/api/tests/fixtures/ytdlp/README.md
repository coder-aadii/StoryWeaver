# yt-dlp fixtures

Recorded 2026-10-01 from the real service for the public video `jNQXAC9IVRw` ("Me at the zoo"),
metadata-only (`skip_download`). They back the offline tests in `test_youtube_captions.py` and
`test_source_metadata_mapping.py`.

- `info_jNQXAC9IVRw.json` — trimmed yt-dlp info dict (formats removed; signed-URL query values replaced by
  `REDACTED`, keeping only `fmt`/`lang`/`hl`/`caps`).
- `caption_en.json3`, `caption_en.vtt` — the real manual English caption bodies.
- `auto_playlist_en.m3u8`, `auto_segment_en.vtt` — the real automatic-caption HLS playlist (segment URL
  redacted) and its single WebVTT segment.

Observed hosts: manual captions `www.youtube.com/api/timedtext` (json3, vtt, srt, ttml, srv1–3);
automatic captions are `vtt` with protocol `m3u8_native` on `manifest.googlevideo.com`, whose playlist points
at WebVTT segments on `www.youtube.com/api/timedtext`. Multi-segment (long-video) playlists were NOT captured.
