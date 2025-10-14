import os
import pandas as pd
import re

class BasicBlock:
    def __init__(self, name, statements, successors):
        self.name = name
        self.statements = statements
        self.successors = successors

# Example CFG (replace with your actual CFG)
blocks = {
    'B1': BasicBlock('B1', ['x = 1', 'y = 2'], ['B2']),
    'B2': BasicBlock('B2', ['x = y + 3'], ['B3', 'B4']),
    'B3': BasicBlock('B3', ['y = x + 4'], ['B5']),
    'B4': BasicBlock('B4', ['x = 5'], ['B5']),
    'B5': BasicBlock('B5', ['z = x + y'], [])
}

# Collect all definitions
all_defs = []
for block in blocks.values():
    for stmt in block.statements:
        var = stmt.split('=')[0].strip()
        all_defs.append((var, block.name, stmt))

# Compute GEN and KILL for each block
GEN = {}
KILL = {}
for block in blocks.values():
    gen = set()
    for stmt in block.statements:
        var = stmt.split('=')[0].strip()
        gen.add((var, block.name, stmt))
    kill = set([d for d in all_defs if d[0] in [g[0] for g in gen] and d not in gen])
    GEN[block.name] = gen
    KILL[block.name] = kill

# Initialize IN and OUT sets
IN = {name: set() for name in blocks}
OUT = {name: GEN[name].copy() for name in blocks}

changed = True
while changed:
    changed = False
    for name, block in blocks.items():
        preds = [b for b in blocks if name in blocks[b].successors]
        IN[name] = set()
        for p in preds:
            IN[name] |= OUT[p]
        new_out = GEN[name] | (IN[name] - KILL[name])
        if new_out != OUT[name]:
            OUT[name] = new_out
            changed = True

# Format sets for table display
def fmt(s):
    return "{" + ", ".join([f"{v}@{b}" for (v, b, stmt) in sorted(s)]) + "}"

# Store results in a DataFrame matching the assignment table
df = pd.DataFrame([
    {
        "Basic-Block": name,
        "gen[B]": fmt(GEN[name]),
        "kill[B]": fmt(KILL[name]),
        "in[B]": fmt(IN[name]),
        "out[B]": fmt(OUT[name])
    }
    for name in blocks
])

print(df)
df.to_csv("reaching_definitions_table.csv", index=False)

# Step 1: Parse C file and identify definitions
def parse_definitions(filename):
    with open(filename) as f:
        lines = f.readlines()
    defs = []
    def_id = 1
    for i, line in enumerate(lines):
        # Simple regex for assignments (not perfect, but works for most cases)
        m = re.findall(r'(\w+)\s*=\s*[^;]+;', line)
        for var in m:
            defs.append({'id': f'D{def_id}', 'var': var, 'line': i+1})
            def_id += 1
    return defs

# Step 2: Identify basic blocks (for demo, split at 'if', 'for', 'while', etc.)
def split_basic_blocks(lines):
    blocks = []
    block = []
    for line in lines:
        block.append(line)
        if re.search(r'\b(if|for|while|return|break|else)\b', line):
            blocks.append(block)
            block = []
    if block:
        blocks.append(block)
    return blocks

# Step 3: Compute gen/kill sets for each block
def compute_gen_kill(blocks, defs):
    gen = []
    kill = []
    for block in blocks:
        block_gen = set()
        block_kill = set()
        for defn in defs:
            for line in block:
                if re.search(rf'\b{defn["var"]}\s*=', line):
                    block_gen.add(defn['id'])
                else:
                    # If variable assigned elsewhere, kill previous defs
                    if re.search(rf'\b{defn["var"]}\s*=', line):
                        block_kill.add(defn['id'])
        gen.append(block_gen)
        kill.append(block_kill)
    return gen, kill

# Step 4: Dataflow equations (iterative)
def reaching_definitions(blocks, gen, kill):
    in_sets = [set() for _ in blocks]
    out_sets = [set() for _ in blocks]
    changed = True
    while changed:
        changed = False
        for i, block in enumerate(blocks):
            preds = [i-1] if i > 0 else []
            in_new = set()
            for p in preds:
                in_new |= out_sets[p]
            out_new = gen[i] | (in_new - kill[i])
            if in_new != in_sets[i] or out_new != out_sets[i]:
                changed = True
            in_sets[i] = in_new
            out_sets[i] = out_new
    return in_sets, out_sets

# Step 5: Print table
def print_table(blocks, gen, kill, in_sets, out_sets):
    print("Block | gen | kill | in | out")
    for i in range(len(blocks)):
        print(f"B{i+1} | {gen[i]} | {kill[i]} | {in_sets[i]} | {out_sets[i]}")

# Main
filename = "prog3_grid_bfs.c"
defs = parse_definitions(filename)
with open(filename) as f:
    lines = f.readlines()
blocks = split_basic_blocks(lines)
gen, kill = compute_gen_kill(blocks, defs)
in_sets, out_sets = reaching_definitions(blocks, gen, kill)
print_table(blocks, gen, kill, in_sets, out_sets)