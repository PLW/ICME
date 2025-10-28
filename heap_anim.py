#!/usr/bin/env python3
import argparse, json, math, os, sys
from typing import Dict, List, Tuple, Optional
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import patches
from matplotlib.animation import FuncAnimation, PillowWriter

# ---------- parsing (same as before) ----------
def load_snapshot(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        txt = f.read()
    try:
        return json.loads(txt)
    except Exception:
        pass
    try:
        out_zones = []
        cursor = 0
        while True:
            i = txt.find('{"index":', cursor)
            if i == -1: break
            j = txt.find('"blocks":[', i)
            if j == -1: break
            zone_header = txt[i:j]
            idx_key = '"index":'
            idx_pos = zone_header.find(idx_key)
            comma_pos = zone_header.find(",", idx_pos)
            zindex = int(zone_header[idx_pos+len(idx_key):comma_pos].strip())
            name_key = '"name":"'
            name_pos = zone_header.find(name_key)
            name_end = zone_header.find('"', name_pos + len(name_key))
            zname = zone_header[name_pos+len(name_key):name_end]
            bstart = j + len('"blocks":[')
            bend = txt.find("]}", bstart)
            if bend == -1:
                bend = txt.find("]},", bstart)
                if bend == -1: bend = len(txt)
            blocks_lines = txt[bstart:bend].strip().splitlines()
            blocks = []
            for line in blocks_lines:
                line = line.strip().rstrip(",")
                if not line: continue
                if line.startswith("{") and line.endswith("}"):
                    try:
                        blocks.append(json.loads(line))
                    except Exception:
                        continue
            out_zones.append({"index": zindex, "name": zname, "blocks": blocks})
            cursor = bend + 2
        return {"zones": out_zones}
    except Exception as e:
        raise RuntimeError(f"Failed to parse {path}: {e}") from e

def gather_blocks_for_zone(snapshot: Dict, zone_name: Optional[str]) -> List[Dict]:
    zones = snapshot.get("zones", [])
    if zone_name is None and zones:
        return zones[0].get("blocks", [])
    if zone_name is not None:
        for z in zones:
            if z.get("name") == zone_name:
                return z.get("blocks", [])
    return []

def compute_address_span(frames: List[List[Dict]]) -> Tuple[int, int]:
    min_a = None; max_a = None
    for blocks in frames:
        for b in blocks:
            if int(b.get("type", 0)) != 1: continue
            a = int(b["address"]); s = int(b["size"])
            if min_a is None or a < min_a: min_a = a
            if max_a is None or a + s > max_a: max_a = a + s
    if min_a is None: min_a, max_a = 0, 1
    return min_a, max_a

def split_block_into_row_segments(addr0: int, size: int, base: int, row_bytes: int) -> List[Tuple[int,int,int]]:
    segs = []
    start_off = addr0 - base
    end_off = start_off + size
    row = start_off // row_bytes
    while start_off < end_off:
        row_start = row * row_bytes
        row_end   = row_start + row_bytes
        seg_start = max(start_off, row_start)
        seg_end   = min(end_off, row_end)
        segs.append((row, seg_start - row_start, seg_end - seg_start))
        row += 1
        start_off = row_start + row_bytes
    return segs

# ---------- animation (UPDATED) ----------
def make_animation(frames_blocks: List[List[Dict]],
                   base_addr: int,
                   max_addr: int,
                   row_bytes: int,
                   out_gif: str,
                   png_dir: Optional[str],
                   title_prefix: str,
                   min_px: int = 4):
    span = max(1, max_addr - base_addr)
    rows = math.ceil(span / row_bytes)
    cols = row_bytes

    fig, ax = plt.subplots(figsize=(12, 8))

#   ax.set_xlim(0, cols)
#   ax.set_ylim(rows, 0)   # higher addresses at top
#   ax.set_xlabel("Byte offset within row")
#   ax.set_ylabel("Row (higher addresses at top)")

#---------
    ax.set_xlim(0, cols)
    ax.set_xlabel("Byte offset within row")

    ax.set_ylim(rows, 0)  # keep drawing top-down
    ax.set_yticks(range(0, rows, max(1, rows // 10)))
    ax.set_yticklabels(reversed(range(0, rows, max(1, rows // 10))))
    ax.set_ylabel("Row (higher addresses at top)")
#---------

    ax.set_title(f"{title_prefix} (frame 0)")
    ax.grid(True, which="both", linestyle="--", linewidth=0.25, alpha=0.5)

    # Precompute “new vs existing” sets
    prev_set = set()
    frame_sets = []
    new_sets = []
    for blocks in frames_blocks:
        cur = {(int(b["address"]), int(b["size"])) for b in blocks if int(b.get("type", 0)) == 1}
        new = cur - prev_set
        frame_sets.append(cur)
        new_sets.append(new)
        prev_set = cur

    rects_existing = []
    rects_new = []

    def data_units_per_pixel():
        # Compute “data units per pixel” for x & y, so we can enforce >= min_px thickness
        bbox = ax.get_window_extent().transformed(fig.dpi_scale_trans.inverted())
        px_w = bbox.width * fig.dpi
        px_h = bbox.height * fig.dpi
        x_units_per_px = cols / max(px_w, 1)
        y_units_per_px = rows / max(px_h, 1)
        return x_units_per_px, y_units_per_px

    def clamp_seg(col_start, seg_len):
        # Clamp to [0, cols]
        x0 = max(0, min(cols, col_start))
        x1 = max(0, min(cols, col_start + seg_len))
        return x0, max(0, x1 - x0)

    def draw_frame(k: int):
        nonlocal rects_existing, rects_new
        for r in rects_existing + rects_new:
            r.remove()
        rects_existing, rects_new = [], []

        cur_set = frame_sets[k]
        new_set = new_sets[k]

        xppu, yppu = data_units_per_pixel()
        min_w = min_px * xppu         # ensure min visible width in data units
        min_h = max(1.0, min_px * yppu)  # height >= 1 row unit, but allow thicker for visibility

        # 1) EXISTING blocks (light gray with black outline)
        for (addr, size) in (cur_set - new_set):
            for (row, col_start, seg_len) in split_block_into_row_segments(addr, size, base_addr, row_bytes):
                if row < 0 or row >= rows: continue
                col_start, seg_len = clamp_seg(col_start, seg_len)
                if seg_len <= 0: continue
                seg_len = max(seg_len, min_w)
                rect = patches.Rectangle((col_start, row),
                                         seg_len, min_h,
                                         linewidth=0.5, edgecolor="black",
                                         facecolor="0.85", alpha=0.9,
                                         clip_on=True)
                ax.add_patch(rect)
                rects_existing.append(rect)

        # 2) NEW blocks (red, drawn on top)
        for (addr, size) in new_set:
            for (row, col_start, seg_len) in split_block_into_row_segments(addr, size, base_addr, row_bytes):
                if row < 0 or row >= rows: continue
                col_start, seg_len = clamp_seg(col_start, seg_len)
                if seg_len <= 0: continue
                seg_len = max(seg_len, min_w)
                rect = patches.Rectangle((col_start, row),
                                         seg_len, min_h,
                                         linewidth=0.5, edgecolor="black",
                                         facecolor="red", alpha=0.9,
                                         clip_on=True)
                ax.add_patch(rect)
                rects_new.append(rect)

        ax.set_title(f"{title_prefix} (frame {k})")

    if png_dir: os.makedirs(png_dir, exist_ok=True)

    def init():
        draw_frame(0)
        if png_dir:
            fig.savefig(os.path.join(png_dir, f"frame_{0:04d}.png"), dpi=120, bbox_inches="tight")
        return []

    def update(k):
        draw_frame(k)
        if png_dir:
            fig.savefig(os.path.join(png_dir, f"frame_{k:04d}.png"), dpi=120, bbox_inches="tight")
        return []

    anim = FuncAnimation(fig, update, init_func=init, frames=len(frames_blocks),
                         interval=100, blit=False, repeat=False)
    if out_gif:
        writer = PillowWriter(fps=1)
        anim.save(out_gif, writer=writer)
        print(f"[heap_anim] wrote GIF -> {out_gif}")
    if not png_dir:
        fig.savefig((out_gif or "heap_anim.png").replace(".gif", ".png"),
                    dpi=140, bbox_inches="tight")
    plt.close(fig)

# ---------- CLI (same as before, plus --min-px) ----------
def main():
    ap = argparse.ArgumentParser(description="Animate heap blocks across snapshots.")
    ap.add_argument("--start", type=int, required=True)
    ap.add_argument("--end", type=int, required=True)
    ap.add_argument("--pattern", type=str, default="heapdump.{k}.json")
    ap.add_argument("--zone", type=str, default="DefaultMallocZone")
    ap.add_argument("--row-bytes", type=int, default=1<<20)
    ap.add_argument("--out", type=str, default="heap_anim.gif")
    ap.add_argument("--png-dir", type=str, default=None)
    ap.add_argument("--min-px", type=int, default=4, help="min visual thickness/width in pixels (default 4)")
    args = ap.parse_args()

    frames_blocks = []
    paths = []
    for k in range(args.start, args.end + 1):
        path = args.pattern.format(k=k)
        if not os.path.exists(path):
            print(f"[heap_anim] warn: missing file {path}, skipping")
            continue
        snap = load_snapshot(path)
        blocks_all = gather_blocks_for_zone(snap, args.zone)
        blocks = [b for b in blocks_all if int(b.get("type", 0)) == 1]
        frames_blocks.append(blocks)
        paths.append(path)

    if not frames_blocks:
        print("[heap_anim] no frames loaded; check --pattern/--start/--end and zone name")
        sys.exit(1)

    base, limit = compute_address_span(frames_blocks)
    span = max(1, limit - base)
    rows = math.ceil(span / args.row_bytes)
    approx_mb = span / (1024.0*1024.0)
    title = f"{args.zone}  |  base=0x{base:x} span≈{approx_mb:.2f} MiB  rows={rows} row_bytes={args.row_bytes}"

    print(f"[heap_anim] frames: {len(frames_blocks)} from {paths[0]} .. {paths[-1]}")
    print(f"[heap_anim] addr base=0x{base:x}, limit=0x{limit:x}, span={span} bytes (~{approx_mb:.2f} MiB)")
    print(f"[heap_anim] rows={rows}, row_bytes={args.row_bytes}")

    make_animation(frames_blocks, base, limit, args.row_bytes,
                   args.out, args.png_dir, title, min_px=args.min_px)

if __name__ == "__main__":
    main()
