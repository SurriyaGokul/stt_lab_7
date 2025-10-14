"""
Reaching Definitions Analysis
Implements the dataflow analysis algorithm for reaching definitions as per the assignment.
"""

import re
from collections import defaultdict
import pandas as pd

class ReachingDefinitionsAnalysis:
    def __init__(self, cfg_data):
        """
        cfg_data: dictionary with keys:
            - 'blocks': list of basic block names
            - 'definitions': dict mapping definition_id to (block_name, variable, code_line)
            - 'edges': list of (from_block, to_block) tuples
            - 'gen': dict mapping block_name to list of definition_ids generated in that block
            - 'kill': dict mapping block_name to list of definition_ids killed in that block
        """
        self.blocks = cfg_data['blocks']
        self.definitions = cfg_data['definitions']
        self.edges = cfg_data['edges']
        self.gen = cfg_data['gen']
        self.kill = cfg_data['kill']
        
        # Build predecessors map
        self.predecessors = defaultdict(list)
        for src, dst in self.edges:
            self.predecessors[dst].append(src)
        
        # Initialize in[B] and out[B] as empty sets
        self.in_sets = {block: set() for block in self.blocks}
        self.out_sets = {block: set() for block in self.blocks}
        
        self.iterations = []
    
    def run_analysis(self):
        """Run the iterative dataflow analysis until convergence"""
        iteration = 0
        
        # Store initial state (iteration 0)
        self.iterations.append(self._capture_state(iteration))
        
        changed = True
        while changed:
            iteration += 1
            changed = False
            
            for block in self.blocks:
                # Compute in[B] = Union of out[P] for all predecessors P of B
                new_in = set()
                for pred in self.predecessors[block]:
                    new_in = new_in.union(self.out_sets[pred])
                
                # Compute out[B] = gen[B] U (in[B] - kill[B])
                new_out = set(self.gen[block]).union(new_in - set(self.kill[block]))
                
                # Check if anything changed
                if new_in != self.in_sets[block] or new_out != self.out_sets[block]:
                    changed = True
                    self.in_sets[block] = new_in
                    self.out_sets[block] = new_out
            
            # Store state after this iteration
            self.iterations.append(self._capture_state(iteration))
        
        return iteration  # Return number of iterations to convergence
    
    def _capture_state(self, iteration):
        """Capture the current state of in[B] and out[B] for all blocks"""
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
        """Print all iterations in a tabular format"""
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
        """Save all iterations to a CSV file"""
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
    
    def print_definition_mapping(self):
        """Print the mapping of definition IDs to code lines"""
        print("\n" + "="*80)
        print("DEFINITION MAPPING")
        print("="*80)
        for def_id in sorted(self.definitions.keys()):
            block, var, line = self.definitions[def_id]
            print(f"{def_id}: {var} = ... (Block {block}, Line: {line})")


def analyze_prog1_gradebook():
    """Analyze prog1_gradebook.c"""
    
    # Define all assignment statements (definitions) in the program
    # Format: def_id: (block, variable, code_line_description)
    definitions = {
        'D1': ('B1', 'n', 'scanf("%d", &n)'),
        'D2': ('B2', 'i', 'i = 0'),
        'D3': ('B3', 'i', 'scanf(..., &cls[i].m1, ...)'),
        'D4': ('B3', 'cls[i].m1', 'scanf(..., &cls[i].m1, ...)'),
        'D5': ('B3', 'cls[i].m2', 'scanf(..., &cls[i].m2, ...)'),
        'D6': ('B3', 'cls[i].m3', 'scanf(..., &cls[i].m3, ...)'),
        'D7': ('B3', 'cls[i].m1', 'cls[i].m1 = 0 (if negative)'),
        'D8': ('B3', 'cls[i].m2', 'cls[i].m2 = 0 (if negative)'),
        'D9': ('B3', 'cls[i].m3', 'cls[i].m3 = 0 (if negative)'),
        'D10': ('B3', 'cls[i].m1', 'cls[i].m1 = 100 (if > 100)'),
        'D11': ('B3', 'cls[i].m2', 'cls[i].m2 = 100 (if > 100)'),
        'D12': ('B3', 'cls[i].m3', 'cls[i].m3 = 100 (if > 100)'),
        'D13': ('B3', 'cls[i].avg', 'compute_avg_and_grade (avg assignment)'),
        'D14': ('B3', 'cls[i].grade', 'compute_avg_and_grade (grade assignment)'),
        'D15': ('B3', 'i', 'i++ (for loop increment)'),
        'D16': ('B4', 'desired', 'scanf("%f", &desired)'),
        'D17': ('B5', 'sum', 'sum = 0.0f'),
        'D18': ('B5', 'countA', 'countA = 0'),
        'D19': ('B5', 'countF', 'countF = 0'),
        'D20': ('B5', 'i', 'i = 0'),
        'D21': ('B6', 'sum', 'sum += cls[i].avg'),
        'D22': ('B6', 'countA', 'countA++ (if A)'),
        'D23': ('B6', 'countF', 'countF++ (if F)'),
        'D24': ('B6', 'i', 'i++ (for loop)'),
        'D25': ('B7', 'class_avg', 'class_avg = sum/n'),
    }
    
    # Simplified CFG blocks
    blocks = ['ENTRY', 'B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'EXIT']
    
    # CFG edges (control flow)
    edges = [
        ('ENTRY', 'B1'),
        ('B1', 'B2'),
        ('B2', 'B3'),
        ('B3', 'B3'),  # loop back
        ('B3', 'B4'),
        ('B4', 'B5'),
        ('B5', 'B6'),
        ('B6', 'B6'),  # loop back
        ('B6', 'B7'),
        ('B7', 'EXIT'),
    ]
    
    # gen[B]: definitions generated in each block
    gen = {
        'ENTRY': [],
        'B1': ['D1'],
        'B2': ['D2'],
        'B3': ['D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'D9', 'D10', 'D11', 'D12', 'D13', 'D14', 'D15'],
        'B4': ['D16'],
        'B5': ['D17', 'D18', 'D19', 'D20'],
        'B6': ['D21', 'D22', 'D23', 'D24'],
        'B7': ['D25'],
        'EXIT': [],
    }
    
    # kill[B]: definitions of the same variables killed by this block
    # A definition is killed if another definition of the same variable is generated
    kill = {
        'ENTRY': [],
        'B1': [],
        'B2': ['D3', 'D15', 'D20', 'D24'],  # kills other defs of i
        'B3': ['D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'D9', 'D10', 'D11', 'D12', 'D13', 'D14', 'D15', 'D20', 'D24'],  # multiple redefs
        'B4': [],
        'B5': ['D17', 'D18', 'D19', 'D2', 'D3', 'D15', 'D20', 'D24'],  # kills defs of sum, countA, countF, i
        'B6': ['D17', 'D18', 'D19', 'D20', 'D21', 'D22', 'D23', 'D24', 'D2', 'D3', 'D15'],  # kills own defs + i defs
        'B7': [],
        'EXIT': [],
    }
    
    cfg_data = {
        'blocks': blocks,
        'definitions': definitions,
        'edges': edges,
        'gen': gen,
        'kill': kill
    }
    
    print("\n" + "="*80)
    print("REACHING DEFINITIONS ANALYSIS: prog1_gradebook.c")
    print("="*80)
    
    analysis = ReachingDefinitionsAnalysis(cfg_data)
    analysis.print_definition_mapping()
    iterations = analysis.run_analysis()
    print(f"\n\nConverged after {iterations} iterations")
    analysis.print_iterations_table()
    analysis.save_to_csv('prog1_reaching_definitions.csv')
    
    return analysis


def analyze_prog2_string_analyzer():
    """Analyze prog2_string_analyzer.c"""
    
    definitions = {
        'D1': ('B1', 'wcount', 'wcount = 0'),
        'D2': ('B2', 'i', 'i = 0'),
        'D3': ('B3', 'i', 'i++ (skip non-alnum)'),
        'D4': ('B4', 'k', 'k = 0'),
        'D5': ('B5', 'words[wcount][k]', 'words[wcount][k++] = tolower(line[i])'),
        'D6': ('B5', 'k', 'k++ (implicit)'),
        'D7': ('B5', 'i', 'i++ (while reading)'),
        'D8': ('B6', 'words[wcount][k]', 'words[wcount][k] = \\0'),
        'D9': ('B6', 'wcount', 'wcount++'),
        'D10': ('B7', 'letters', 'letters = 0'),
        'D11': ('B7', 'digits', 'digits = 0'),
        'D12': ('B7', 'spaces', 'spaces = 0'),
        'D13': ('B7', 'vowels', 'vowels = 0'),
        'D14': ('B7', 'consonants', 'consonants = 0'),
        'D15': ('B7', 'i', 'i = 0'),
        'D16': ('B8', 'letters', 'letters++'),
        'D17': ('B8', 'vowels', 'vowels++'),
        'D18': ('B8', 'consonants', 'consonants++'),
        'D19': ('B8', 'digits', 'digits++'),
        'D20': ('B8', 'spaces', 'spaces++'),
        'D21': ('B8', 'i', 'i++ (char loop)'),
        'D22': ('B9', 'freq[c-a]', 'freq[c-a] = freq[c-a] + 1'),
        'D23': ('B10', 'pal_count', 'pal_count = 0'),
        'D24': ('B10', 'max_len', 'max_len = 0'),
        'D25': ('B10', 'max_idx', 'max_idx = -1'),
        'D26': ('B11', 'pal_count', 'pal_count++'),
        'D27': ('B11', 'max_len', 'max_len = L'),
        'D28': ('B11', 'max_idx', 'max_idx = i'),
    }
    
    blocks = ['ENTRY', 'B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B9', 'B10', 'B11', 'EXIT']
    
    edges = [
        ('ENTRY', 'B1'),
        ('B1', 'B2'),
        ('B2', 'B3'),
        ('B3', 'B3'),  # loop
        ('B3', 'B4'),
        ('B4', 'B5'),
        ('B5', 'B5'),  # loop
        ('B5', 'B6'),
        ('B6', 'B3'),  # back to outer loop
        ('B3', 'B7'),
        ('B7', 'B8'),
        ('B8', 'B8'),  # loop
        ('B8', 'B9'),
        ('B9', 'B10'),
        ('B10', 'B11'),
        ('B11', 'B11'),  # loop
        ('B11', 'EXIT'),
    ]
    
    gen = {
        'ENTRY': [],
        'B1': ['D1'],
        'B2': ['D2'],
        'B3': ['D3'],
        'B4': ['D4'],
        'B5': ['D5', 'D6', 'D7'],
        'B6': ['D8', 'D9'],
        'B7': ['D10', 'D11', 'D12', 'D13', 'D14', 'D15'],
        'B8': ['D16', 'D17', 'D18', 'D19', 'D20', 'D21'],
        'B9': ['D22'],
        'B10': ['D23', 'D24', 'D25'],
        'B11': ['D26', 'D27', 'D28'],
        'EXIT': [],
    }
    
    kill = {
        'ENTRY': [],
        'B1': ['D9'],
        'B2': ['D3', 'D7', 'D15', 'D21'],
        'B3': ['D2', 'D3', 'D7', 'D15', 'D21'],
        'B4': ['D6'],
        'B5': ['D4', 'D5', 'D6', 'D7', 'D2', 'D3', 'D15', 'D21'],
        'B6': ['D8', 'D9', 'D1'],
        'B7': ['D10', 'D11', 'D12', 'D13', 'D14', 'D15', 'D2', 'D3', 'D7', 'D21'],
        'B8': ['D10', 'D11', 'D12', 'D13', 'D14', 'D15', 'D16', 'D17', 'D18', 'D19', 'D20', 'D21'],
        'B9': ['D22'],
        'B10': ['D23', 'D24', 'D25'],
        'B11': ['D23', 'D24', 'D25', 'D26', 'D27', 'D28'],
        'EXIT': [],
    }
    
    cfg_data = {
        'blocks': blocks,
        'definitions': definitions,
        'edges': edges,
        'gen': gen,
        'kill': kill
    }
    
    print("\n" + "="*80)
    print("REACHING DEFINITIONS ANALYSIS: prog2_string_analyzer.c")
    print("="*80)
    
    analysis = ReachingDefinitionsAnalysis(cfg_data)
    analysis.print_definition_mapping()
    iterations = analysis.run_analysis()
    print(f"\n\nConverged after {iterations} iterations")
    analysis.print_iterations_table()
    analysis.save_to_csv('prog2_reaching_definitions.csv')
    
    return analysis


def analyze_prog3_grid_bfs():
    """Analyze prog3_grid_bfs.c"""
    
    definitions = {
        'D1': ('B1', 'i', 'i = 0 (outer loop init)'),
        'D2': ('B2', 'j', 'j = 0 (inner loop init)'),
        'D3': ('B3', 'grid[i][j]', 'scanf("%d", &grid[i][j])'),
        'D4': ('B3', 'grid[i][j]', 'grid[i][j] = 1 (sanitize)'),
        'D5': ('B3', 'j', 'j++ (inner loop)'),
        'D6': ('B4', 'i', 'i++ (outer loop)'),
        'D7': ('B5', 'sr', 'scanf("%d %d", &sr, &sc)'),
        'D8': ('B5', 'sc', 'scanf("%d %d", &sr, &sc)'),
        'D9': ('B6', 'tr', 'scanf("%d %d", &tr, &tc)'),
        'D10': ('B6', 'tc', 'scanf("%d %d", &tr, &tc)'),
        'D11': ('B7', 'i', 'i = 0 (dist/vis init)'),
        'D12': ('B8', 'j', 'j = 0 (dist/vis inner)'),
        'D13': ('B9', 'dist[i][j]', 'dist[i][j] = -1'),
        'D14': ('B9', 'vis[i][j]', 'vis[i][j] = 0'),
        'D15': ('B9', 'j', 'j++ (inner)'),
        'D16': ('B10', 'i', 'i++ (outer)'),
        'D17': ('B11', 'vis[sr][sc]', 'vis[sr][sc] = 1'),
        'D18': ('B11', 'dist[sr][sc]', 'dist[sr][sc] = 0'),
        'D19': ('B12', 'u', 'u = q_pop(&Q)'),
        'D20': ('B13', 'k', 'k = 0'),
        'D21': ('B14', 'nr', 'nr = u.r + dr[k]'),
        'D22': ('B14', 'nc', 'nc = u.c + dc[k]'),
        'D23': ('B15', 'vis[nr][nc]', 'vis[nr][nc] = 1'),
        'D24': ('B15', 'dist[nr][nc]', 'dist[nr][nc] = dist[u.r][u.c] + 1'),
        'D25': ('B16', 'k', 'k++'),
        'D26': ('B17', 'r', 'r = tr'),
        'D27': ('B17', 'c', 'c = tc'),
        'D28': ('B17', 'steps', 'steps = dist[tr][tc]'),
        'D29': ('B18', 'found', 'found = 0'),
        'D30': ('B19', 'k', 'k = 0 (reconstruct loop)'),
        'D31': ('B20', 'pr', 'pr = r - dr[k]'),
        'D32': ('B20', 'pc', 'pc = c - dc[k]'),
        'D33': ('B21', 'r', 'r = pr'),
        'D34': ('B21', 'c', 'c = pc'),
        'D35': ('B21', 'steps', 'steps = steps - 1'),
        'D36': ('B21', 'found', 'found = 1'),
        'D37': ('B22', 'k', 'k++ (reconstruct)'),
    }
    
    blocks = ['ENTRY', 'B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B9', 'B10', 
              'B11', 'B12', 'B13', 'B14', 'B15', 'B16', 'B17', 'B18', 'B19', 'B20', 'B21', 'B22', 'EXIT']
    
    edges = [
        ('ENTRY', 'B1'),
        ('B1', 'B2'),
        ('B2', 'B3'),
        ('B3', 'B3'),  # inner loop
        ('B3', 'B4'),
        ('B4', 'B2'),  # back to inner loop check
        ('B2', 'B5'),  # exit inner, continue
        ('B5', 'B6'),
        ('B6', 'B7'),
        ('B7', 'B8'),
        ('B8', 'B9'),
        ('B9', 'B9'),  # inner loop
        ('B9', 'B10'),
        ('B10', 'B8'),  # back to inner
        ('B8', 'B11'),  # exit both loops
        ('B11', 'B12'),
        ('B12', 'B12'),  # BFS loop
        ('B12', 'B13'),
        ('B13', 'B14'),
        ('B14', 'B15'),
        ('B15', 'B16'),
        ('B16', 'B14'),  # k loop
        ('B14', 'B12'),  # back to BFS
        ('B12', 'B17'),  # exit BFS
        ('B17', 'B18'),
        ('B18', 'B19'),
        ('B19', 'B20'),
        ('B20', 'B21'),
        ('B21', 'B22'),
        ('B22', 'B20'),  # k loop
        ('B20', 'B18'),  # back to while
        ('B18', 'EXIT'),
    ]
    
    gen = {
        'ENTRY': [],
        'B1': ['D1'],
        'B2': ['D2'],
        'B3': ['D3', 'D4', 'D5'],
        'B4': ['D6'],
        'B5': ['D7', 'D8'],
        'B6': ['D9', 'D10'],
        'B7': ['D11'],
        'B8': ['D12'],
        'B9': ['D13', 'D14', 'D15'],
        'B10': ['D16'],
        'B11': ['D17', 'D18'],
        'B12': ['D19'],
        'B13': ['D20'],
        'B14': ['D21', 'D22'],
        'B15': ['D23', 'D24'],
        'B16': ['D25'],
        'B17': ['D26', 'D27', 'D28'],
        'B18': ['D29'],
        'B19': ['D30'],
        'B20': ['D31', 'D32'],
        'B21': ['D33', 'D34', 'D35', 'D36'],
        'B22': ['D37'],
        'EXIT': [],
    }
    
    kill = {
        'ENTRY': [],
        'B1': ['D6', 'D11', 'D16'],
        'B2': ['D5', 'D12', 'D15'],
        'B3': ['D2', 'D3', 'D4', 'D5', 'D12', 'D15'],
        'B4': ['D1', 'D6', 'D11', 'D16'],
        'B5': [],
        'B6': [],
        'B7': ['D1', 'D6', 'D11', 'D16'],
        'B8': ['D2', 'D5', 'D12', 'D15'],
        'B9': ['D12', 'D13', 'D14', 'D15', 'D2', 'D5'],
        'B10': ['D1', 'D6', 'D11', 'D16'],
        'B11': ['D13', 'D14', 'D17', 'D18', 'D23', 'D24'],
        'B12': [],
        'B13': ['D20', 'D25', 'D30', 'D37'],
        'B14': ['D21', 'D22', 'D31', 'D32'],
        'B15': ['D13', 'D14', 'D17', 'D18', 'D23', 'D24'],
        'B16': ['D20', 'D25', 'D30', 'D37'],
        'B17': ['D26', 'D27', 'D28', 'D33', 'D34', 'D35'],
        'B18': ['D29', 'D36'],
        'B19': ['D20', 'D25', 'D30', 'D37'],
        'B20': ['D21', 'D22', 'D31', 'D32'],
        'B21': ['D26', 'D27', 'D28', 'D29', 'D33', 'D34', 'D35', 'D36'],
        'B22': ['D20', 'D25', 'D30', 'D37'],
        'EXIT': [],
    }
    
    cfg_data = {
        'blocks': blocks,
        'definitions': definitions,
        'edges': edges,
        'gen': gen,
        'kill': kill
    }
    
    print("\n" + "="*80)
    print("REACHING DEFINITIONS ANALYSIS: prog3_grid_bfs.c")
    print("="*80)
    
    analysis = ReachingDefinitionsAnalysis(cfg_data)
    analysis.print_definition_mapping()
    iterations = analysis.run_analysis()
    print(f"\n\nConverged after {iterations} iterations")
    analysis.print_iterations_table()
    analysis.save_to_csv('prog3_reaching_definitions.csv')
    
    return analysis


if __name__ == '__main__':
    print("="*80)
    print("REACHING DEFINITIONS ANALYSIS - LAB 7")
    print("="*80)
    
    # Analyze all three programs
    print("\n\n")
    analyze_prog1_gradebook()
    
    print("\n\n")
    analyze_prog2_string_analyzer()
    
    print("\n\n")
    analyze_prog3_grid_bfs()
    
    print("\n\n" + "="*80)
    print("ANALYSIS COMPLETE - Check the CSV files for detailed results")
    print("="*80)
