import re
import sys
from collections import defaultdict, deque

# Increase recursion limit for deep DFS in 2.7 (default is often 1000)
sys.setrecursionlimit(5000) 

# ---------- CONFIG ----------
netlist_file = "b01.v"
output_file = "loop_regs.txt"

# FF types in your netlist
ff_types = ["DFFARX1_LVT", "SDFFARX1_LVT"] 

# ---------- PARSE NETLIST ----------
ff_inputs = {}     
ff_outputs = {}    
net_drivers = {}   
net_fanout = defaultdict(list) 

with open(netlist_file, 'r') as f:
    for line in f:
        line = line.strip()
        # Parse FF
        for ff_type in ff_types:
            if line.startswith(ff_type):
                # FIX 1: Remove f-string (rf"...")
                # Construct regex pattern using string formatting
                pattern = r"{}\s+(\S+)\s*\(.*\.D\((\S+)\).*\.Q\((\S+)\)".format(ff_type)
                
                m = re.search(pattern, line)
                if m:
                    ff_name = m.group(1)
                    d_net = m.group(2)
                    q_net = m.group(3)
                    ff_inputs[ff_name] = d_net
                    ff_outputs[ff_name] = q_net
                    net_drivers[q_net] = ff_name

        # Parse gates
        if "(" in line and ");" in line:
            ports = re.findall(r"\.(?:A|B|D|Y)\((\S+)\)", line)
            if len(ports) >= 2:
                out_net = ports[-1]
                for in_net in ports[:-1]:
                    net_fanout[in_net].append(out_net)
                    net_drivers[out_net] = line 

# ---------- BUILD FF CONNECTION GRAPH ----------
ff_graph = defaultdict(list)
for ff_name, d_net in ff_inputs.items(): # .items() creates a list in 2.7, which is fine
    if d_net in net_drivers:
        driver = net_drivers[d_net]
        if driver in ff_outputs:
            ff_graph[driver].append(ff_name)

# ---------- CYCLE DETECTION ----------
def find_cycles(graph):
    visited = set()
    stack = set()
    cycles = []

    def dfs(node, path):
        if node in stack:
            # found cycle
            if node in path: # Safety check
                idx = path.index(node)
                cycles.append(path[idx:])
            return
        if node in visited:
            return
        visited.add(node)
        stack.add(node)
        for neigh in graph.get(node, []):
            dfs(neigh, path + [neigh])
        stack.remove(node)

    for n in graph:
        dfs(n, [n])
    return cycles

cycles = find_cycles(ff_graph)

# ---------- PICK ONE FF PER LOOP ----------
# FIX 2: Use a Set to avoid duplicates if an FF is in multiple loops
selected_ff = set()
for loop in cycles:
    selected_ff.add(loop[0]) 

# ---------- SAVE OUTPUT ----------
with open(output_file, "w") as f:
    for ff in selected_ff:
        f.write(ff + "\n")

# FIX 3: Python 2.7 style print or .format()
print "Found {} loops, saved {} unique FFs to {}".format(len(cycles), len(selected_ff), output_file)
