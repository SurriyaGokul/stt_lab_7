import re, sys, os, argparse
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional

ASSIGN_RE = re.compile(r'^\s*[A-Za-z_]\w*\s*=\s*[^=].*;') 

def strip_comments(code: str) -> str:
    code = re.sub(r'//.*', '', code)
    code = re.sub(r'/\*.*?\*/', '', code, flags=re.S)
    return code

def normalize_lines(code: str) -> List[Tuple[int, str]]:
    # Keep non-empty lines with original numbers
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
    kind: str = "basic"  # "basic", "cond", "loop", "entry", "exit"
    cond_text: Optional[str] = None

@dataclass
class CFG:
    blocks: Dict[str, Block] = field(default_factory=dict)
    edges: List[Tuple[str, str, Optional[str]]] = field(default_factory=list)  # src, dst, label

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
        # Close current into a new cond/loop block
        cond = new_block("cond" if kind == "if" else "loop", cond_text=text.strip())
        cond.lines.append((line_no, text.strip()))
        # fallthrough edge from current to cond
        if current is not None and current.id != cond.id:
            cfg.add_edge(current.id, cond.id)
        # Push context; the 'join' will be created later
        stack.append((kind, cond.id, None))  # (type, cond_id, join_id)
        current = cond

    def start_body_block(edge_label: str) -> Block:
        nonlocal current
        body = new_block("basic")
        # find top cond/loop
        for k in range(len(stack)-1, -1, -1):
            t, cond_id, join_id = stack[k]
            if t in ("if", "loop"):
                cfg.add_edge(cond_id, body.id, label=edge_label)
                current = body
                return body
        # fallback
        current = body
        return body

    while i < n:
        ln, txt = tokens[i]

        # Conditionals and loops create condition blocks
        if is_else_if(txt) or is_if(txt):
            start_cond_block(ln, txt, "if")
            i += 1
            continue
        if is_else(txt):
            # else body from nearest if
            body = start_body_block("false")
            # Append the 'else' header itself into body (for labeling)
            body.lines.append((ln, txt.strip()))
            i += 1
            continue
        if is_while(txt) or is_for(txt):
            start_cond_block(ln, txt, "loop")
            i += 1
            continue

        # Handle braces to connect bodies and joins
        if opens_brace(txt) and not (is_if(txt) or is_else_if(txt) or is_else(txt) or is_while(txt) or is_for(txt)):
            # treat as code inside current block
            current.lines.append((ln, txt.strip()))
            i += 1
            continue

        if closes_brace(txt):

            if stack:
                # If top is a "body marker", pop it; (we model bodies as normal blocks)
                # Instead, we infer by last control in stack
                ctrl_type, cond_id, join_id = stack[-1]
                if ctrl_type == "loop":
                    # Add back edge from current (body) to cond
                    cfg.add_edge(current.id, cond_id, label="back")
                    # Add a join node for loop exit (if not created)
                    if join_id is None:
                        join = new_block("basic")
                        # cond false to join
                        cfg.add_edge(cond_id, join.id, label="exit")
                        stack[-1] = (ctrl_type, cond_id, join.id)
                    # After closing brace, control is the join
                    current = cfg.blocks[stack[-1][2]]
                    # loop context complete now
                    stack.pop()
                elif ctrl_type == "if":
                    # When if/else ends, create (or reuse) join node
                    if join_id is None:
                        join = new_block("basic")
                        # cond may already have true/false edges; ensure a fallthrough if missing
                        cfg.add_edge(cond_id, join.id, label="fallthrough")
                        stack[-1] = (ctrl_type, cond_id, join.id)
                    # connect current to join and pop
                    cfg.add_edge(current.id, stack[-1][2])
                    current = cfg.blocks[stack[-1][2]]
                    stack.pop()
            i += 1
            continue

        # Regular code line
        current.lines.append((ln, txt.strip()))

        # If this line ends with '{', it's the start of a body:
        if txt.strip().endswith('{'):
            # True body by default after a cond; for loops use "body"
            if stack:
                t, cond_id, join_id = stack[-1]
                edge_label = "true" if t == "if" else "body"
                # Create a fresh body block and move the upcoming statements there
                body = start_body_block(edge_label)
                # Keep the line we just appended inside the condition block? For labeling, it's ok;
                # move focus to body from next line
                # (No further action needed.)
        # If this is a `return`, create explicit exit block
        if is_return(txt):
            exitb = next((b for b in cfg.blocks.values() if b.kind == "exit"), None)
            if exitb is None:
                exitb = new_block("exit")
            cfg.add_edge(current.id, exitb.id, label="return")
            current = exitb

        i += 1

    # Connect any dangling basic blocks to a terminal exit node with fallthrough
    outgoing = {src for (src, _, _) in cfg.edges}
    dangling = [bid for bid, b in cfg.blocks.items() if bid not in outgoing and b.kind not in ("exit",)]
    if dangling:
        end = next((b for b in cfg.blocks.values() if b.kind == "exit"), None)
        if end is None:
            end = Block(id=f"B{len(cfg.blocks)}", kind="exit")
            cfg.add_block(end)
        for bid in dangling:
            cfg.add_edge(bid, end.id, label="fallthrough")

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
    # N, E
    N = len(cfg.blocks)
    E = len(cfg.edges)

    # Connected components on the UNDIRECTED version of the CFG
    g_und = defaultdict(set)
    for u, v, _ in cfg.edges:
        g_und[u].add(v)
        g_und[v].add(u)
    # include isolated nodes (no edges)
    for bid in cfg.blocks:
        g_und[bid]  # touch

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

    # McCabe cyclomatic complexity
    CC = E - N + 2 * C

    # Cross-check via decision points (sum over nodes of (outdeg - 1) when outdeg>1), plus 1 per component
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
