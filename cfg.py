import re, sys, os, argparse
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional

ASSIGN_RE = re.compile(r'^\s*[A-Za-z_]\w*\s*=\s*[^=].*;') 

def strip_comments(code: str) -> str:
    code = re.sub(r'//.*', '', code)
    code = re.sub(r'/\*.*?\*/', '', code, flags=re.S)
    return code

def normalize_lines(code: str) -> List[Tuple[int, str]]:
    lines = code.splitlines()
    toks = []
    for i, ln in enumerate(lines, 1):
        if ln.strip() != '':
            toks.append((i, ln.rstrip()))
    return toks

def is_if(line: str) -> bool:
    return re.match(r'\s*if\s*\(', line) is not None

def is_else_if(line: str) -> bool:
    return re.match(r'\s*else\s+if\s*\(', line) is not None

def is_else(line: str) -> bool:
    return re.match(r'\s*else\b', line) is not None

def is_while(line: str) -> bool:
    return re.match(r'\s*while\s*\(', line) is not None

def is_for(line: str) -> bool:
    return re.match(r'\s*for\s*\(', line) is not None

def is_return(line: str) -> bool:
    return re.match(r'\s*return\b', line) is not None

def opens_brace(line: str) -> bool:
    return '{' in line

def closes_brace(line: str) -> bool:
    return '}' in line

@dataclass
class Block:
    id: str
    lines: List[Tuple[int, str]] = field(default_factory=list)
    kind: str = "basic"
    cond_text: Optional[str] = None

@dataclass
class CFG:
    blocks: Dict[str, Block] = field(default_factory=dict)
    edges: List[Tuple[str, str, Optional[str]]] = field(default_factory=list)

    def add_block(self, b: Block):
        self.blocks[b.id] = b

    def add_edge(self, src: str, dst: str, label: Optional[str] = None):
        self.edges.append((src, dst, label))


def build_cfg(tokens: List[Tuple[int, str]]) -> CFG:

    cfg = CFG()
    next_id = 0

    def new_block(kind="basic", cond_text=None) -> Block:
        nonlocal next_id
        b = Block(id=f"B{next_id}", kind=kind, cond_text=cond_text)
        next_id += 1
        cfg.add_block(b)
        return b

    entry = new_block("entry")
    current = entry
    stack = []
    i = 0
    n = len(tokens)

    def start_cond_block(line_no: int, text: str, kind: str):
        nonlocal current
        cond = new_block("cond" if kind == "if" else "loop", cond_text=text.strip())
        cond.lines.append((line_no, text.strip()))
        if current is not None and current.id != cond.id:
            cfg.add_edge(current.id, cond.id)
        stack.append((kind, cond.id, None))
        current = cond

    def start_body_block(edge_label: str) -> Block:
        nonlocal current
        body = new_block("basic")
        for k in range(len(stack)-1, -1, -1):
            t, cond_id, join_id = stack[k]
            if t in ("if", "loop"):
                cfg.add_edge(cond_id, body.id, label=edge_label)
                current = body
                return body
        current = body
        return body

    while i < n:
        ln, txt = tokens[i]

        if is_else_if(txt) or is_if(txt):
            if is_else_if(txt) and stack and stack[-1][0] == "if":
                _, prev_cond_id, prev_join_id = stack[-1]
                new_cond = new_block("cond", cond_text=txt.strip())
                new_cond.lines.append((ln, txt.strip()))
                cfg.add_edge(prev_cond_id, new_cond.id, label="false")
                stack[-1] = ("if", new_cond.id, prev_join_id)
                current = new_cond
                if txt.strip().endswith('{'):
                    start_body_block("true")
            else:
                start_cond_block(ln, txt, "if")
                if txt.strip().endswith('{'):
                    start_body_block("true")
            i += 1
            continue
        if is_else(txt):
            body = start_body_block("false")
            body.lines.append((ln, txt.strip()))
            i += 1
            continue
        if is_while(txt) or is_for(txt):
            start_cond_block(ln, txt, "loop")
            if txt.strip().endswith('{'):
                start_body_block("true")
            i += 1
            continue

        if opens_brace(txt) and not (is_if(txt) or is_else_if(txt) or is_else(txt) or is_while(txt) or is_for(txt)):
            current.lines.append((ln, txt.strip()))
            i += 1
            continue

        if closes_brace(txt):

            if stack:
                def next_is_else() -> bool:
                    j = i + 1
                    while j < n:
                        _ln2, _txt2 = tokens[j]
                        s2 = _txt2.strip()
                        if s2 == "":
                            j += 1
                            continue
                        return is_else(s2) or is_else_if(s2)
                    return False

                ctrl_type, cond_id, join_id = stack[-1]
                if ctrl_type == "loop":
                    cfg.add_edge(current.id, cond_id, label="back")
                    if join_id is None:
                        join = new_block("basic")
                        cfg.add_edge(cond_id, join.id, label="false")
                        stack[-1] = (ctrl_type, cond_id, join.id)
                        join_id = join.id
                    current = cfg.blocks[join_id]
                    stack.pop()
                elif ctrl_type == "if":
                    if join_id is None:
                        join = new_block("basic")
                        stack[-1] = (ctrl_type, cond_id, join.id)
                        join_id = join.id
                    cfg.add_edge(current.id, join_id)

                    if next_is_else():
                        current = cfg.blocks[join_id]
                    else:
                        has_false = any((u == cond_id and lbl == "false") for (u, v, lbl) in cfg.edges)
                        if not has_false:
                            cfg.add_edge(cond_id, join_id, label="false")
                        current = cfg.blocks[join_id]
                        stack.pop()
            i += 1
            continue

        current.lines.append((ln, txt.strip()))

        if txt.strip().endswith('{'):
            if stack:
                t, cond_id, join_id = stack[-1]
                edge_label = "true"
                body = start_body_block(edge_label)
        if is_return(txt):
            exitb = next((b for b in cfg.blocks.values() if b.kind == "exit"), None)
            if exitb is None:
                exitb = new_block("exit")
            cfg.add_edge(current.id, exitb.id, label="return")
            current = exitb

        i += 1

    outgoing = {src for (src, _, _) in cfg.edges}
    dangling = [bid for bid, b in cfg.blocks.items() if bid not in outgoing and b.kind not in ("exit",)]
    if dangling:
        end = next((b for b in cfg.blocks.values() if b.kind == "exit"), None)
        if end is None:
            end = Block(id=f"B{len(cfg.blocks)}", kind="exit")
            cfg.add_block(end)
        for bid in dangling:
            cfg.add_edge(bid, end.id)

    return cfg

def to_dot(cfg: CFG) -> str:
    def esc(s: str) -> str:
        return s.replace('"', r'\"')
    lines = ['digraph CFG {', '  node [shape=box];']
    for bid, b in cfg.blocks.items():
        body = "\\n".join(f"{ln}: {txt}" for (ln, txt) in b.lines) if b.lines else b.kind.upper()
        label = f"{bid}: {body}" if body else f"{bid}: {b.kind.upper()}"
        lines.append(f'  {bid} [label="{esc(label)}"];')
    for (src, dst, lbl) in cfg.edges:
        if lbl:
            lines.append(f'  {src} -> {dst} [label="{esc(lbl)}"];')
        else:
            lines.append(f'  {src} -> {dst};')
    lines.append('}')
    return "\n".join(lines)

from collections import defaultdict, deque

def compute_metrics(cfg) -> dict:
    N = len(cfg.blocks)
    E = len(cfg.edges)

    g_und = defaultdict(set)
    for u, v, _ in cfg.edges:
        g_und[u].add(v)
        g_und[v].add(u)
    for bid in cfg.blocks:
        g_und[bid]

    visited = set()
    C = 0
    for node in g_und:
        if node in visited:
            continue
        C += 1
        q = deque([node])
        visited.add(node)
        while q:
            x = q.popleft()
            for y in g_und[x]:
                if y not in visited:
                    visited.add(y)
                    q.append(y)

    CC = E - N + 2 * C

    outdeg = defaultdict(int)
    for u, v, _ in cfg.edges:
        outdeg[u] += 1
    decision_sum = sum(max(0, outdeg[b] - 1) for b in cfg.blocks)
    CC_alt = decision_sum + C  

    return {
        "N": N,
        "E": E,
        "components": C,
        "CC": CC,
        "CC_alt_check": CC_alt
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cfile", help="Path to C source file")
    ap.add_argument("-o", "--out", help="Path to write DOT file", default=None)
    args = ap.parse_args()

    with open(args.cfile, "r", encoding="utf-8", errors="ignore") as f:
        raw = f.read()

    code = strip_comments(raw)
    toks = normalize_lines(code)
    cfg = build_cfg(toks)
    metrics = compute_metrics(cfg)
    print("Nodes (N):", metrics["N"])
    print("Edges (E):", metrics["E"])
    print("Components (C):", metrics["components"])
    print("Cyclomatic Complexity (CC = E - N + 2*C):", metrics["CC"])
    print("CC (decision-point cross-check):", metrics["CC_alt_check"])

    if hasattr(args, 'metrics_json') and args.metrics_json:
        import json
        os.makedirs(os.path.dirname(args.metrics_json) or ".", exist_ok=True)
        with open(args.metrics_json, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2)

    dot = to_dot(cfg)
    out_path = args.out or (os.path.splitext(args.cfile)[0] + ".dot")
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(dot)

    print(f"Wrote DOT to: {out_path}")
    print('Render with: dot -Tpng "{}" -o "{}.png"'.format(out_path, out_path))

if __name__ == "__main__":
    main()
