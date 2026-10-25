# WeChat Chat Generator

A local, reproducible renderer for **WeChat-style** chat mockups: full 9:16 captures, content-only captures, and optional natural downward scroll videos. It is a layout generator, not a WeChat client. It neither logs into WeChat nor verifies or recreates real chat records.

## What is included

- JSON or plain-text conversation input
- Light/dark theme, title, both participant names, and both avatars
- Text, system notice, image/GIF placeholder, video card, transfer card, and call notice blocks
- `AUTO` and gated `REVIEW` execution modes with persisted `state.json`
- Reference-path provenance only: no unreviewed OCR or automatic inference from a reference image
- 9:16 PNG capture plus a 3-second scroll MP4 when requested
- Public-release audit, manifest, and tests

Private presets, private avatars, source screenshots, source videos, and generated runs are deliberately excluded.

## Quick start

```bash
git clone https://github.com/574210187-ship-it/wechat-chat-generator.git
cd wechat-chat-generator
python3 -m pip install -r requirements.txt
python3 chatflow.py --project examples/project.json --run-dir runs/demo --mode AUTO --scroll
```

Outputs are in `runs/demo/`:

- `chat-capture.png` — full phone-style capture
- `chat-content-full-9x16.png` — content-only 9:16 version
- `chat-scroll-3s.mp4` — only with `--scroll`
- `analysis.json`, `normalized-project.json`, `render-manifest.json`, `state.json` — reproducibility and acceptance record

`ffmpeg` must be available on `PATH` to make the MP4. PNG-only generation does not need it.

The bundled examples use English so they render deterministically on minimal Linux CI images. For Chinese or other CJK text, pass a local CJK font with `--font` (or set `WECHAT_CHAT_FONT`); macOS and Windows normally already provide an appropriate system font.

## Use your own names, avatars, and text

```bash
python3 chatflow.py \
  --project examples/project.json \
  --title "项目沟通" \
  --left-name "陈女士" --right-name "张顾问" \
  --left-avatar /absolute/path/customer.png \
  --right-avatar /absolute/path/adviser.png \
  --theme dark --chrome content \
  --replace "某某顾问=张顾问" \
  --run-dir runs/custom --mode AUTO --scroll
```

`--avatar` is retained as an alias for `--right-avatar`; `--client-avatar` is an alias for `--left-avatar`.

For best CJK typography, provide a local CJK font:

```bash
python3 chatflow.py --project examples/project.json --font /absolute/path/your-cjk-font.ttc --run-dir runs/font-test
```

## Project JSON

```json
{
  "title": "项目沟通",
  "theme": "light",
  "chrome": "full",
  "participants": {
    "left": {"name": "陈女士", "avatar": "/absolute/path/customer.png"},
    "right": {"name": "张顾问", "avatar": "/absolute/path/adviser.png"}
  },
  "messages": [
    {"side": "left", "type": "text", "text": "你好，想确认一下时间。"},
    {"side": "right", "type": "text", "text": "可以，下午三点发你。"},
    {"type": "system", "text": "今天 14:30"},
    {"side": "right", "type": "transfer", "amount": "¥0.10", "note": "测试"},
    {"side": "left", "type": "video", "path": "/absolute/path/video-cover.jpg", "duration": "0:30"}
  ]
}
```

Supported message types: `text`, `system`, `image`, `gif`, `video`, `transfer`, and `call`. Media `path` is optional; without it, the renderer creates a neutral placeholder.

## REVIEW mode and local rework

`REVIEW` never advances an unapproved stage. Start it once, edit `normalized-project.json` or your source project after checking the analysis, then resume the same run directory.

```bash
python3 chatflow.py --project examples/project.json --run-dir runs/review --mode REVIEW
# inspect runs/review/analysis.json and normalized-project.json
python3 chatflow.py --resume --run-dir runs/review --mode REVIEW --approve analysis
# inspect rendered PNG, then finish acceptance
python3 chatflow.py --resume --run-dir runs/review --mode REVIEW --approve render
```

On a renderer error, `state.json` becomes `FAILED` at the current stage and the workflow does not advance.

## Reference-image contract

You may pass `--reference /path/to/reference.png`. The path is recorded as provenance only. The tool does not OCR, scrape, clone a user interface automatically, or silently copy names, avatars, or content from the reference. Review measurements and explicitly encode the desired title, participants, theme, spacing, and messages in the project before production use.

## Verify the release

```bash
python3 -m unittest discover -s tests -v
python3 release_audit.py
python3 make_bundle_manifest.py
python3 release_verify.py
```

## Use from another ChatGPT / Codex account

Open [`CHATGPT_CODEX_PROMPT.md`](CHATGPT_CODEX_PROMPT.md), copy it into a coding-enabled ChatGPT or Codex session, attach your JSON/text/reference/avatars, and ask it to run the requested mode. The prompt requires it to use the supplied source, keep assets local, inspect the output, and stop on a failed stage.

## Responsible use

Use this for mockups, storyboards, demonstrations, and clearly disclosed reconstructions. Do not present generated images or videos as authentic platform records, payment proof, legal evidence, or messages sent by another person.

## License

[MIT](LICENSE)
