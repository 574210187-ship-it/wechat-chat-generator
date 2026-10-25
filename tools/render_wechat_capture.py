#!/usr/bin/env python3
"""Draw deterministic, editable WeChat-style chat captures from project JSON."""
from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont, ImageOps

W, H = 1296, 2304
HEADER_H, INPUT_H = 232, 252
CHAT_H = H - HEADER_H - INPUT_H
AVATAR = 108
GAP = 26

PALETTES = {
    "light": {
        "background": "#ededed", "bar": "#f7f7f7", "line": "#dedede",
        "text": "#181818", "muted": "#9c9c9c", "left": "#ffffff",
        "right": "#95ec69", "input": "#ffffff", "card": "#f19a35",
        "card_soft": "#ffd097", "system": "#a7a7a7", "icon": "#191919",
    },
    "dark": {
        "background": "#111111", "bar": "#161616", "line": "#282828",
        "text": "#f2f2f2", "muted": "#727272", "left": "#2d2d2d",
        "right": "#28c461", "input": "#303030", "card": "#bc7625",
        "card_soft": "#bc7625", "system": "#696969", "icon": "#e8e8e8",
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--scroll", action="store_true")
    parser.add_argument("--duration", type=float, default=3.0)
    parser.add_argument("--font")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def font_paths(explicit: str | None) -> list[str]:
    values = [explicit, os.getenv("WECHAT_CHAT_FONT"),
              "/System/Library/Fonts/PingFang.ttc",
              "/System/Library/Fonts/STHeiti Light.ttc",
              "C:/Windows/Fonts/msyh.ttc",
              "C:/Windows/Fonts/simhei.ttf",
              "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    return [item for item in values if item]


def get_font(size: int, explicit: str | None, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = font_paths(explicit)
    if bold:
        candidates = ([explicit] if explicit else []) + [
            "/System/Library/Fonts/PingFang.ttc", "C:/Windows/Fonts/msyhbd.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"] + candidates
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size=size, index=0)
        except OSError:
            continue
    return ImageFont.load_default()


def text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> int:
    return int(draw.textlength(text, font=font))


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    output: list[str] = []
    for source_line in str(text).split("\n") or [""]:
        if not source_line:
            output.append("")
            continue
        line = ""
        for char in source_line:
            trial = line + char
            if line and text_width(draw, trial, font) > max_width:
                output.append(line)
                line = char
            else:
                line = trial
        output.append(line)
    return output or [""]


def rounded_tail(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], fill: str, side: str, radius: int = 18) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill)
    x0, y0, x1, y1 = box
    cy = y0 + min(45, max(28, (y1 - y0) // 2))
    if side == "left":
        draw.polygon([(x0 + 3, cy - 14), (x0 - 22, cy), (x0 + 3, cy + 15)], fill=fill)
    else:
        draw.polygon([(x1 - 3, cy - 14), (x1 + 22, cy), (x1 - 3, cy + 15)], fill=fill)


def neutral_avatar(seed: str, size: int = AVATAR) -> Image.Image:
    colors = [(124, 151, 188), (166, 138, 108), (111, 162, 145), (152, 126, 174)]
    index = sum(ord(item) for item in seed) % len(colors)
    base = Image.new("RGB", (size, size), colors[index])
    draw = ImageDraw.Draw(base)
    draw.ellipse((size * .20, size * .16, size * .80, size * .76), fill=(238, 222, 203))
    draw.arc((size * .27, size * .28, size * .73, size * .60), 198, 342, fill=(77, 58, 45), width=max(3, size // 18))
    draw.ellipse((size * .36, size * .39, size * .43, size * .46), fill=(49, 42, 39))
    draw.ellipse((size * .57, size * .39, size * .64, size * .46), fill=(49, 42, 39))
    draw.arc((size * .40, size * .46, size * .60, size * .62), 5, 175, fill=(120, 75, 70), width=max(2, size // 28))
    return base


def avatar(path_value: Any, label: str) -> Image.Image:
    if path_value:
        candidate = Path(str(path_value)).expanduser()
        if candidate.exists() and candidate.is_file():
            try:
                return ImageOps.fit(Image.open(candidate).convert("RGB"), (AVATAR, AVATAR), method=Image.Resampling.LANCZOS)
            except Exception:
                pass
    return neutral_avatar(label)


def media_image(path_value: Any, width: int, height: int, kind: str, colors: dict[str, str]) -> Image.Image:
    if path_value:
        candidate = Path(str(path_value)).expanduser()
        if candidate.exists() and candidate.is_file():
            try:
                return ImageOps.fit(Image.open(candidate).convert("RGB"), (width, height), method=Image.Resampling.LANCZOS)
            except Exception:
                pass
    image = Image.new("RGB", (width, height), "#bababa" if colors["background"] == "#ededed" else "#464646")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, height * .66, width, height), fill="#8ca48c")
    draw.ellipse((width * .12, height * .12, width * .35, height * .35), fill="#e6c96e")
    label_font = get_font(max(24, width // 12), None, bold=True)
    label = kind.upper()
    bbox = draw.textbbox((0, 0), label, font=label_font)
    draw.text(((width - (bbox[2] - bbox[0])) / 2, height * .48), label, font=label_font, fill="white", stroke_width=1, stroke_fill="#555555")
    return image


def draw_message(draw: ImageDraw.ImageDraw, canvas: Image.Image, message: dict[str, Any], y: int, project: dict[str, Any], colors: dict[str, str], font_path: str | None, avatars: dict[str, Image.Image]) -> int:
    kind = str(message.get("type", "text"))
    side = str(message.get("side", "left"))
    text_font = get_font(45, font_path)
    name_font = get_font(31, font_path)
    body_left = 38 + AVATAR + GAP
    body_right = W - 38 - AVATAR - GAP
    max_bubble = 770
    if kind == "system":
        content = str(message.get("text", ""))
        width = min(720, max(180, text_width(draw, content, name_font) + 46))
        draw.rounded_rectangle(((W - width) // 2, y, (W + width) // 2, y + 54), 18, fill=colors["bar"])
        draw.text((W // 2, y + 27), content, anchor="mm", font=name_font, fill=colors["system"])
        return y + 98
    if side == "left":
        avatar_x = 38
        bubble_x = body_left
    else:
        avatar_x = W - 38 - AVATAR
        bubble_x = None
    canvas.paste(avatars[side], (avatar_x, y), avatars[side] if avatars[side].mode == "RGBA" else None)
    if message.get("show_name"):
        label = str(project["participants"][side].get("name", ""))
        tx = body_left if side == "left" else body_right
        anchor = "la" if side == "left" else "ra"
        draw.text((tx, y - 35), label, anchor=anchor, font=name_font, fill=colors["muted"])
    if kind in {"image", "gif", "video"}:
        width = int(message.get("width", 500))
        height = int(message.get("height", 500 if kind != "video" else 380))
        width = max(250, min(730, width))
        height = max(180, min(830, height))
        x0 = body_left if side == "left" else body_right - width
        picture = media_image(message.get("path") or message.get("media"), width, height, kind, colors)
        canvas.paste(picture, (x0, y))
        if kind == "video":
            cx, cy = x0 + width // 2, y + height // 2
            draw.ellipse((cx - 53, cy - 53, cx + 53, cy + 53), outline="white", width=5)
            draw.polygon([(cx - 10, cy - 22), (cx - 10, cy + 22), (cx + 30, cy)], fill="white")
            duration = str(message.get("duration", "0:30"))
            draw.text((x0 + width - 18, y + height - 18), duration, anchor="rd", font=name_font, fill="white", stroke_width=2, stroke_fill="#333333")
        return y + height + 56
    if kind == "transfer":
        width, height = 760, 290
        x0 = body_left if side == "left" else body_right - width
        rounded_tail(draw, (x0, y, x0 + width, y + height), colors["card"], side, 16)
        icon_x = x0 + 84 if side == "left" else x0 + 98
        draw.ellipse((icon_x - 51, y + 50, icon_x + 51, y + 152), outline="white", width=7)
        draw.line((icon_x - 25, y + 102, icon_x + 22, y + 102), fill="white", width=7)
        draw.polygon([(icon_x + 22, y + 102), (icon_x + 3, y + 82), (icon_x + 3, y + 122)], fill="white")
        amount = str(message.get("amount", "¥0.10"))
        note = str(message.get("note", message.get("text", "转账")))
        draw.text((x0 + 170, y + 58), amount, font=get_font(48, font_path, True), fill="white")
        draw.text((x0 + 170, y + 126), note, font=get_font(37, font_path), fill="white")
        draw.text((x0 + 40, y + height - 62), str(message.get("label", "Transfer")), font=name_font, fill="white")
        return y + height + 58
    content = str(message.get("text", ""))
    if kind == "call":
        content = "☎  " + content
    lines = wrap_text(draw, content, text_font, max_bubble - 62)
    line_h = 60
    width = min(max_bubble, max(text_width(draw, line, text_font) for line in lines) + 64)
    height = max(88, len(lines) * line_h + 46)
    x0 = body_left if side == "left" else body_right - width
    rounded_tail(draw, (x0, y, x0 + width, y + height), colors["left"] if side == "left" else colors["right"], side)
    for index, line in enumerate(lines):
        draw.text((x0 + 32, y + 22 + index * line_h), line, font=text_font, fill=colors["text"])
    return y + height + 55


def render_content(project: dict[str, Any], colors: dict[str, str], font_path: str | None) -> tuple[Image.Image, int]:
    messages = project.get("messages", [])
    height = max(CHAT_H, 160 + sum(440 if item.get("type") in {"image", "gif", "video", "transfer"} else 190 for item in messages))
    content = Image.new("RGB", (W, height), colors["background"])
    draw = ImageDraw.Draw(content)
    avatars = {
        "left": avatar(project["participants"]["left"].get("avatar"), str(project["participants"]["left"].get("name", "对方"))),
        "right": avatar(project["participants"]["right"].get("avatar"), str(project["participants"]["right"].get("name", "我"))),
    }
    y = 45
    for item in messages:
        y = draw_message(draw, content, item, y, project, colors, font_path, avatars)
    return content.crop((0, 0, W, max(CHAT_H, y + 38))), y


def draw_header(screen: Image.Image, project: dict[str, Any], colors: dict[str, str], font_path: str | None) -> None:
    draw = ImageDraw.Draw(screen)
    draw.rectangle((0, 0, W, HEADER_H), fill=colors["bar"])
    draw.line((0, HEADER_H - 1, W, HEADER_H - 1), fill=colors["line"], width=2)
    status_font = get_font(47, font_path, True)
    title_font = get_font(47, font_path, True)
    draw.text((68, 45), "02:45", font=status_font, fill=colors["text"])
    draw.text((72, 153), "‹", font=get_font(96, font_path), fill=colors["icon"])
    draw.text((W // 2, 151), str(project.get("title", "聊天")), anchor="mm", font=title_font, fill=colors["text"])
    draw.text((W - 70, 153), "•••", anchor="mm", font=get_font(44, font_path, True), fill=colors["icon"])
    draw.text((W - 148, 48), "▮▮▮  ◒  ▰", anchor="lm", font=get_font(31, font_path, True), fill=colors["icon"])


def draw_input(screen: Image.Image, colors: dict[str, str], font_path: str | None) -> None:
    draw = ImageDraw.Draw(screen)
    y0 = H - INPUT_H
    draw.rectangle((0, y0, W, H), fill=colors["bar"])
    draw.line((0, y0, W, y0), fill=colors["line"], width=2)
    draw.ellipse((38, y0 + 67, 130, y0 + 159), outline=colors["icon"], width=5)
    draw.text((84, y0 + 112), "◖", anchor="mm", font=get_font(52, font_path), fill=colors["icon"])
    draw.rounded_rectangle((160, y0 + 53, W - 315, y0 + 179), radius=25, fill=colors["input"], outline=colors["line"], width=2)
    draw.text((W - 230, y0 + 114), "☺", anchor="mm", font=get_font(70, font_path), fill=colors["icon"])
    draw.ellipse((W - 124, y0 + 67, W - 32, y0 + 159), outline=colors["icon"], width=5)
    draw.text((W - 78, y0 + 108), "+", anchor="mm", font=get_font(70, font_path), fill=colors["icon"])


def screen_from_offset(content: Image.Image, offset: int, project: dict[str, Any], colors: dict[str, str], font_path: str | None) -> Image.Image:
    if project.get("chrome", "full") == "content":
        crop = content.crop((0, offset, W, min(offset + CHAT_H, content.height)))
        if crop.height < H:
            output = Image.new("RGB", (W, H), colors["background"])
            output.paste(crop, (0, 0))
            return output
        return crop.resize((W, H), Image.Resampling.LANCZOS)
    screen = Image.new("RGB", (W, H), colors["background"])
    draw_header(screen, project, colors, font_path)
    upper = min(content.height, offset + CHAT_H)
    crop = content.crop((0, offset, W, upper))
    screen.paste(crop, (0, HEADER_H))
    if crop.height < CHAT_H:
        ImageDraw.Draw(screen).rectangle((0, HEADER_H + crop.height, W, H - INPUT_H), fill=colors["background"])
    draw_input(screen, colors, font_path)
    return screen


def save_png(image: Image.Image, path: Path) -> None:
    image.save(path, "PNG", optimize=True)


def make_scroll(content: Image.Image, project: dict[str, Any], colors: dict[str, str], font_path: str | None, output_dir: Path, duration: float) -> tuple[str, int]:
    frames_dir = output_dir / "scroll-frames"
    if frames_dir.exists():
        shutil.rmtree(frames_dir)
    frames_dir.mkdir(parents=True)
    scroll_range = max(0, content.height - CHAT_H)
    total = max(2, int(max(0.5, duration) * 30))
    for index in range(total):
        t = index / (total - 1)
        eased = 0.5 - 0.5 * math.cos(math.pi * t)
        offset = int(scroll_range * eased)
        frame = screen_from_offset(content, offset, project, colors, font_path)
        save_png(frame, frames_dir / f"{index:04d}.png")
    video = output_dir / "chat-scroll-3s.mp4"
    command = ["ffmpeg", "-y", "-framerate", "30", "-i", str(frames_dir / "%04d.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(video)]
    result = subprocess.run(command, capture_output=True, text=True)
    (output_dir / "ffmpeg.log").write_text(result.stderr, encoding="utf-8")
    if result.returncode != 0:
        raise RuntimeError("ffmpeg could not create scroll video; see ffmpeg.log")
    return video.name, scroll_range


def main() -> int:
    args = parse_args()
    project = load_json(Path(args.project))
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    colors = PALETTES[str(project.get("theme", "light"))]
    content, natural_end = render_content(project, colors, args.font)
    starting = screen_from_offset(content, 0, project, colors, args.font)
    outputs = ["chat-capture.png"]
    save_png(starting, output_dir / outputs[0])
    overview_project = dict(project)
    overview_project["chrome"] = "content"
    overview = screen_from_offset(content, 0, overview_project, colors, args.font)
    save_png(overview, output_dir / "chat-content-full-9x16.png")
    outputs.append("chat-content-full-9x16.png")
    scroll_range = max(0, content.height - CHAT_H)
    if args.scroll:
        video_name, scroll_range = make_scroll(content, project, colors, args.font, output_dir, args.duration)
        outputs.append(video_name)
    manifest = {
        "renderer": "wechat-chat-generator-v1.2.0",
        "outputs": outputs,
        "dimensions": {"width": W, "height": H},
        "theme": project.get("theme", "light"),
        "chrome": project.get("chrome", "full"),
        "participants": project.get("participants", {}),
        "message_count": len(project.get("messages", [])),
        "content_height": content.height,
        "scroll_range_px": scroll_range,
        "font": args.font or os.getenv("WECHAT_CHAT_FONT") or "system fallback",
    }
    (output_dir / "render-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
