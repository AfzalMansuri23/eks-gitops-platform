"""Architecture diagram tooling.

    python tools/architecture.py route   # recompute every edge path in architecture.json
    python tools/architecture.py build   # write docs/architecture.html (self-contained)

Node positions live in app/static/data/architecture.json. `route` draws
orthogonal paths with A* on a 10px grid: lines never cross a node or a zone
label, prefer few bends, keep a gap from lines already drawn, and use their
own port on each node side.
"""

import heapq
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "app" / "static" / "data" / "architecture.json"
STATIC = ROOT / "app" / "static"
DOCS = ROOT.parents[1] / "docs" / "architecture.html"

GRID = 10
NODE_W, NODE_H = 200, 60
CLEAR = 14  # min distance from a line to a node
STUB = 20  # straight run out of a port before the first bend
TURN, OVERLAP, CROSS, NEAR, BORDER, FOREIGN = 70, 500, 50, 35, 60, 8
DIRS = {"R": (1, 0), "L": (-1, 0), "D": (0, 1), "U": (0, -1)}
OUTWARD = {"L": "L", "R": "R", "T": "U", "B": "D"}
INWARD = {"L": "R", "R": "L", "T": "D", "B": "U"}


def label_box(zone):
    # matches the CSS: 11px uppercase monospace with letter spacing
    return (zone["x"] + 10, zone["y"] + 6, zone["x"] + 22 + len(zone["label"]) * 7.6, zone["y"] + 26)


def ports(node):
    x, y = node["x"], node["y"]
    out = []
    for dy in range(10, NODE_H - 9, GRID):
        out += [("L", x, y + dy, dy - NODE_H / 2), ("R", x + NODE_W, y + dy, dy - NODE_H / 2)]
    for dx in range(20, NODE_W - 19, GRID):
        out += [("T", x + dx, y, dx - NODE_W / 2), ("B", x + dx, y + NODE_H, dx - NODE_W / 2)]
    return out


def stub_point(side, px, py):
    dx, dy = DIRS[OUTWARD[side]]
    return px + dx * STUB, py + dy * STUB


class Router:
    def __init__(self, cfg):
        self.w, self.h = cfg["canvas"]["width"], cfg["canvas"]["height"]
        self.nodes = {n["id"]: n for n in cfg["nodes"]}
        self.boxes = [(n["x"] - CLEAR, n["y"] - CLEAR, n["x"] + NODE_W + CLEAR, n["y"] + NODE_H + CLEAR) for n in cfg["nodes"]]
        self.boxes += [(a - 4, b - 4, c + 4, d + 4) for a, b, c, d in map(label_box, cfg["zones"])]
        self.zones = cfg["zones"]
        self.occ: dict[tuple[int, int], set[str]] = {}
        self.used_ports: set[tuple[int, int]] = set()

    def blocked(self, x, y):
        if x < GRID or y < GRID or x > self.w - GRID or y > self.h - GRID:
            return True
        return any(a < x < c and b < y < d for a, b, c, d in self.boxes)

    def step_cost(self, x, y, axis, home=()):
        cost = GRID
        for z in self.zones:
            x1, y1, x2, y2 = z["x"], z["y"], z["x"] + z["w"], z["y"] + z["h"]
            if axis == "H" and y in (y1, y2) and x1 <= x <= x2 or axis == "V" and x in (x1, x2) and y1 <= y <= y2:
                cost += BORDER  # never run along a zone outline
            if x1 < x < x2 and y1 < y < y2 and z["id"] not in home:
                cost += FOREIGN  # stay out of zones the edge has no business in
        here = self.occ.get((x, y), ())
        if axis in here:
            cost += OVERLAP
        elif here:
            cost += CROSS
        nx, ny = (0, GRID) if axis == "H" else (GRID, 0)
        for p in ((x + nx, y + ny), (x - nx, y - ny)):
            if axis in self.occ.get(p, ()):
                cost += NEAR
        return cost

    def free_ports(self, node):
        return [p for p in ports(node) if (p[1], p[2]) not in self.used_ports and not self.blocked(*stub_point(p[0], p[1], p[2]))]

    def route(self, edge):
        src, dst = self.nodes[edge["from"]], self.nodes[edge["to"]]
        home = self.home(src) | self.home(dst)
        goals = {stub_point(s, px, py): (s, px, py, off) for s, px, py, off in self.free_ports(dst)}
        heap, best, came = [], {}, {}
        for s, px, py, off in self.free_ports(src):
            sx, sy = stub_point(s, px, py)
            state = (sx, sy, OUTWARD[s])
            cost = STUB + abs(off) * 0.4
            if cost < best.get(state, 1e18):
                best[state] = cost
                came[state] = ("start", (px, py))
                heapq.heappush(heap, (cost + self.h_cost(sx, sy, goals), cost, state))
        while heap:
            _, cost, state = heapq.heappop(heap)
            if cost > best.get(state, 1e18):
                continue
            x, y, d = state
            if (x, y) in goals:
                s, px, py, off = goals[(x, y)]
                if d == INWARD[s]:
                    return self.finish(state, came, (px, py))
            for nd, (dx, dy) in DIRS.items():
                if (dx, dy) == (-DIRS[d][0], -DIRS[d][1]):
                    continue
                nx, ny = x + dx * GRID, y + dy * GRID
                if self.blocked(nx, ny) and (nx, ny) not in goals:
                    continue
                ncost = cost + self.step_cost(nx, ny, "H" if dy == 0 else "V", home) + (TURN if nd != d else 0)
                if (nx, ny) in goals:
                    s, _, _, off = goals[(nx, ny)]
                    ncost += abs(off) * 0.4 + (TURN if nd != INWARD[s] else 0)
                nstate = (nx, ny, nd)
                if ncost < best.get(nstate, 1e18):
                    best[nstate] = ncost
                    came[nstate] = state
                    heapq.heappush(heap, (ncost + self.h_cost(nx, ny, goals), ncost, nstate))
        raise RuntimeError(f"no route for {edge['id']}")

    def home(self, node):
        cx, cy = center(node)
        return {z["id"] for z in self.zones if z["x"] < cx < z["x"] + z["w"] and z["y"] < cy < z["y"] + z["h"]}

    @staticmethod
    def h_cost(x, y, goals):
        return min(abs(x - gx) + abs(y - gy) for gx, gy in goals)

    def finish(self, state, came, end):
        pts = [end]
        while True:
            pts.append(state[:2])
            prev = came[state]
            if prev[0] == "start":
                pts.append(prev[1])
                break
            state = prev
        pts.reverse()
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            axis = "H" if y1 == y2 else "V"
            steps = max(abs(x2 - x1), abs(y2 - y1)) // GRID
            for i in range(steps + 1):
                p = (x1 + (x2 - x1) * i // max(steps, 1), y1 + (y2 - y1) * i // max(steps, 1))
                self.occ.setdefault(p, set()).add(axis)
        for px, py in (pts[0], pts[-1]):
            for k in (-GRID, 0, GRID):
                self.used_ports.update({(px + k, py), (px, py + k)})
        return simplify(pts)


def simplify(pts):
    out = [pts[0]]
    for i in range(1, len(pts) - 1):
        (ax, ay), (bx, by), (cx, cy) = out[-1], pts[i], pts[i + 1]
        if (ax == bx == cx) or (ay == by == cy):
            continue
        out.append(pts[i])
    out.append(pts[-1])
    return [list(map(int, p)) for p in out]


def center(n):
    return n["x"] + NODE_W / 2, n["y"] + NODE_H / 2


def route(cfg):
    router = Router(cfg)
    nodes = router.nodes

    def span(e):
        (ax, ay), (bx, by) = center(nodes[e["from"]]), center(nodes[e["to"]])
        return abs(ax - bx) + abs(ay - by)

    for edge in sorted(cfg["edges"], key=span):
        edge["path"] = router.route(edge)
    return cfg


def build():
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    css = (STATIC / "css" / "tokens.css").read_text(encoding="utf-8") + (STATIC / "css" / "architecture.css").read_text(encoding="utf-8")
    js = (STATIC / "js" / "architecture.js").read_text(encoding="utf-8")
    template = (ROOT / "tools" / "architecture.template.html").read_text(encoding="utf-8")
    data = json.dumps(cfg, separators=(",", ":")).replace("</", "<\\/")
    html = template.replace("/*CSS*/", css).replace("/*JS*/", js).replace("/*DATA*/", data)
    DOCS.parent.mkdir(exist_ok=True)
    DOCS.write_text(html, encoding="utf-8", newline="\n")
    print(f"wrote {DOCS.relative_to(ROOT.parents[1])} ({len(html) // 1024} KiB)")


def dump(cfg):
    # one edge per line keeps diffs readable
    text = json.dumps(cfg, indent=2, ensure_ascii=False)
    for e in cfg["edges"]:
        block = json.dumps(e, indent=2, ensure_ascii=False).replace("\n", "\n    ")
        text = text.replace(block, json.dumps(e, ensure_ascii=False))
    return text + "\n"


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "route":
        cfg = route(json.loads(CONFIG.read_text(encoding="utf-8")))
        CONFIG.write_text(dump(cfg), encoding="utf-8", newline="\n")
        print(f"routed {len(cfg['edges'])} edges")
    elif cmd == "build":
        build()
    else:
        sys.exit(__doc__)
