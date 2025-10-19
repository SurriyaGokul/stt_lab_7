import re
from collections import defaultdict
import pandas as pd

class ReachingDefinitionsAnalysis:
    def __init__(self, cfg_data):
        self.blocks = cfg_data['blocks']
        self.definitions = cfg_data['definitions']
        self.edges = cfg_data['edges']
        self.gen = cfg_data['gen']
        self.kill = cfg_data['kill']
        
        self.predecessors = defaultdict(list)
        for src, dst in self.edges:
            self.predecessors[dst].append(src)
        
        self.in_sets = {block: set() for block in self.blocks}
        self.out_sets = {block: set() for block in self.blocks}
        
        self.iterations = []
    
    def run_analysis(self):
        iteration = 0
        self.iterations.append(self._capture_state(iteration))
        
        changed = True
        while changed:
            iteration += 1
            changed = False
            
            for block in self.blocks:
                new_in = set()
                for pred in self.predecessors[block]:
                    new_in = new_in.union(self.out_sets[pred])
                
                new_out = set(self.gen[block]).union(new_in - set(self.kill[block]))
                
                if new_in != self.in_sets[block] or new_out != self.out_sets[block]:
                    changed = True
                    self.in_sets[block] = new_in
                    self.out_sets[block] = new_out
            
            self.iterations.append(self._capture_state(iteration))
        
        return iteration
    
    def _capture_state(self, iteration):
        state = {
            'iteration': iteration,
            'blocks': {}
        }
        for block in self.blocks:
            state['blocks'][block] = {
                'gen': sorted(self.gen[block]),
                'kill': sorted(self.kill[block]),
                'in': sorted(self.in_sets[block]),
                'out': sorted(self.out_sets[block])
            }
        return state
    
    def print_iterations_table(self):
        for iter_data in self.iterations:
            print(f"\n{'='*80}")
            print(f"ITERATION {iter_data['iteration']}")
            print(f"{'='*80}")
            
            rows = []
            for block in self.blocks:
                block_data = iter_data['blocks'][block]
                rows.append({
                    'Basic-Block': block,
                    'gen[B]': '{' + ', '.join(block_data['gen']) + '}',
                    'kill[B]': '{' + ', '.join(block_data['kill']) + '}',
                    'in[B]': '{' + ', '.join(block_data['in']) + '}',
                    'out[B]': '{' + ', '.join(block_data['out']) + '}'
                })
            
            df = pd.DataFrame(rows)
            print(df.to_string(index=False))
    
    def save_to_csv(self, filename):
        all_rows = []
        for iter_data in self.iterations:
            for block in self.blocks:
                block_data = iter_data['blocks'][block]
                all_rows.append({
                    'Iteration': iter_data['iteration'],
                    'Basic-Block': block,
                    'gen[B]': '{' + ', '.join(block_data['gen']) + '}',
                    'kill[B]': '{' + ', '.join(block_data['kill']) + '}',
                    'in[B]': '{' + ', '.join(block_data['in']) + '}',
                    'out[B]': '{' + ', '.join(block_data['out']) + '}'
                })
        
        df = pd.DataFrame(all_rows)
        df.to_csv(filename, index=False)
        print(f"\nResults saved to {filename}")


def compute_kill_from_defs(blocks, definitions, gen):
    var_to_defs = defaultdict(set)
    for def_id, (_block, var, _line) in definitions.items():
        var_to_defs[var].add(def_id)
    kill = {b: [] for b in blocks}
    for b in blocks:
        gen_defs = set(gen.get(b, []))
        vars_in_b = set(definitions[d][1] for d in gen_defs)
        kset = set()
        for v in vars_in_b:
            all_defs = var_to_defs.get(v, set())
            kset |= (all_defs - gen_defs)
        kill[b] = sorted(kset)
    return kill


def build_cfg_from_dot(dot_file):
    with open(dot_file, 'r') as f:
        content = f.read()
    
    blocks = set()
    block_pattern = re.compile(r'\b(B\d+|ENTRY|EXIT)\s*\[')
    for match in block_pattern.finditer(content):
        blocks.add(match.group(1))
    
    blocks_list = ['ENTRY'] if 'ENTRY' in blocks else []
    blocks_list += sorted([b for b in blocks if b.startswith('B')], key=lambda x: int(x[1:]))
    if 'EXIT' in blocks:
        blocks_list.append('EXIT')
    
    edges = []
    edge_pattern = re.compile(r'\b(B\d+|ENTRY|EXIT)\s*->\s*(B\d+|ENTRY|EXIT)')
    for match in edge_pattern.finditer(content):
        edges.append((match.group(1), match.group(2)))
    
    return blocks_list, edges


def extract_assignments_from_dot(dot_file):
    with open(dot_file, 'r') as f:
        content = f.read()
    
    block_pattern = re.compile(r'(B\d+|ENTRY|EXIT)\s*\[label="([^"]+)"\]', re.DOTALL)
    
    definitions = {}
    gen = defaultdict(list)
    def_id = 1
    
    for match in block_pattern.finditer(content):
        block_name = match.group(1)
        block_content = match.group(2)
        
        lines = block_content.replace('\\n', '\n').split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('//') or ':' not in line:
                continue
            
            if ':' in line:
                code_part = line.split(':', 1)[1].strip()
            else:
                code_part = line
            
            assign_patterns = [
                r'(\w+(?:\[[^\]]+\])*(?:\.\w+)*(?:->\w+)*)\s*=\s*[^=]',
                r'(\w+)\+\+',
                r'(\w+)--',
                r'\+\+(\w+)',
                r'--(\w+)'
            ]
            
            for pattern in assign_patterns:
                matches = re.finditer(pattern, code_part)
                for m in matches:
                    var = m.group(1)
                    if var and not var.startswith('if') and not var.startswith('for') and not var.startswith('while'):
                        def_name = f'D{def_id}'
                        short_line = code_part[:60] + ('...' if len(code_part) > 60 else '')
                        definitions[def_name] = (block_name, var, short_line)
                        gen[block_name].append(def_name)
                        def_id += 1
                        break
    
    return definitions, dict(gen)


def analyze_program(dot_file, output_csv, program_name):
    print(f"\n{'='*80}")
    print(f"REACHING DEFINITIONS ANALYSIS: {program_name}")
    print(f"{'='*80}")
    
    blocks, edges = build_cfg_from_dot(dot_file)
    definitions, gen = extract_assignments_from_dot(dot_file)
    
    for block in blocks:
        if block not in gen:
            gen[block] = []
    
    kill = compute_kill_from_defs(blocks, definitions, gen)
    
    cfg_data = {
        'blocks': blocks,
        'definitions': definitions,
        'edges': edges,
        'gen': gen,
        'kill': kill
    }
    
    analysis = ReachingDefinitionsAnalysis(cfg_data)
    
    print("\n" + "="*80)
    print(f"FOUND {len(definitions)} DEFINITIONS")
    print("="*80)
    for def_id in sorted(definitions.keys(), key=lambda x: int(x[1:])):
        block, var, line = definitions[def_id]
        print(f"{def_id}: {var} in {block}")
    
    iterations = analysis.run_analysis()
    print(f"\n\nConverged after {iterations} iterations")
    analysis.print_iterations_table()
    analysis.save_to_csv(output_csv)
    
    print("\n" + "="*80)
    print("VARIABLES WITH MULTIPLE REACHING DEFINITIONS")
    print("="*80)
    multi_def_found = False
    for block in blocks:
        in_set = analysis.in_sets[block]
        vars_in_block = defaultdict(list)
        for def_id in in_set:
            if def_id in definitions:
                var = definitions[def_id][1]
                vars_in_block[var].append(def_id)
        
        multi_def = {v: defs for v, defs in vars_in_block.items() if len(defs) > 1}
        if multi_def:
            multi_def_found = True
            print(f"\n{block}:")
            for var, defs in sorted(multi_def.items()):
                print(f"  {var}: {{{', '.join(sorted(defs, key=lambda x: int(x[1:])))}}} ")
    
    if not multi_def_found:
        print("No variables with multiple reaching definitions found.")
    
    return analysis


if __name__ == '__main__':
    print("="*80)
    print("REACHING DEFINITIONS ANALYSIS - LAB 7 (AUTOMATED)")
    print("="*80)
    
    analyze_program('prog1_gradebook.dot', 'prog1_reaching_definitions.csv', 'prog1_gradebook.c')
    analyze_program('prog2_string_analyzer.dot', 'prog2_reaching_definitions.csv', 'prog2_string_analyzer.c')
    analyze_program('prog3_grid_bfs.dot', 'prog3_grid_bfs.csv', 'prog3_grid_bfs.c')
    
    print("\n\n" + "="*80)
    print("ANALYSIS COMPLETE - Check the CSV files for detailed results")
    print("="*80)
