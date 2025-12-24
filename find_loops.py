import re
from collections import defaultdict

# ---------- CONFIG ----------
netlist_file = "b04.v"  # Make sure this matches your filename
output_file = "partial_scan_candidates.txt"
ff_types = ["DFFARX1_LVT", "SDFFARX1_LVT"] 

# ---------- PARSE NETLIST (Your Logic) ----------
# (Keeping your parsing logic as it seems to work for your file format)
ff_inputs = {}     
ff_outputs = {}    
net_drivers = {}   
net_fanout = defaultdict(list) 

print "[*] Parsing Netlist..."
with open(netlist_file) as f:
    for line in f:
        line = line.strip()
        if line.startswith("//") or line == "": continue 

        # Parse FF
        for ff_type in ff_types:
            if line.startswith(ff_type):
                m_name = re.search(r"%s\s+(\S+)\s*\(" % ff_type, line)
                if m_name:
                    ff_name = m_name.group(1)
                    d_match = re.search(r"\.D\((\S+?)\)", line)
                    q_match = re.search(r"\.Q\((\S+?)\)", line)
                    if d_match and q_match:
                        d_net = d_match.group(1).rstrip(",")
                        q_net = q_match.group(1).rstrip(",")
                        ff_inputs[ff_name] = d_net
                        ff_outputs[ff_name] = q_net
                        net_drivers[q_net] = ff_name

        # Parse gates
        if "(" in line and ");" in line:
            ports = re.findall(r"\.(\w+)\((\S+?)\)", line)
            if len(ports) >= 2:
                # Assuming last port is output (Standard Cell convention)
                out_net = ports[-1][1].rstrip(",")
                for port_name, in_net in ports[:-1]:
                    net_fanout[in_net.rstrip(",")].append(out_net)

# ---------- BUILD FF GRAPH ----------
# Build the graph of FF -> FF connectivity
def get_ff_successors(ff_name, visited_nets=None):
    if visited_nets is None: visited_nets = set()
    successors = []
    q_net = ff_outputs[ff_name]
    stack = [q_net]

    while stack:
        net = stack.pop()
        if net in visited_nets: continue
        visited_nets.add(net)
        
        # If this net drives a FF's D-pin, we found a link!
        for successor_ff, d_net in ff_inputs.items():
            if net == d_net:
                successors.append(successor_ff)
        
        # Continue through combinational logic
        for f in net_fanout.get(net, []):
            stack.append(f)
            
    return list(set(successors)) # Remove duplicates

print "[*] Building S-Graph (FF Connectivity)..."
ff_graph = {}
for ff in ff_outputs:
    ff_graph[ff] = get_ff_successors(ff)

# ---------- GREEDY CYCLE BREAKER ----------
# Instead of finding ALL loops, we find ONE, break it, and repeat.

def find_cycle_path(graph, current_node, visited, stack):
    visited.add(current_node)
    stack.append(current_node)
    
    for neighbor in graph.get(current_node, []):
        if neighbor not in visited:
            result = find_cycle_path(graph, neighbor, visited, stack)
            if result: return result
        elif neighbor in stack:
            # Cycle Detected! Return the portion of the stack that forms the loop
            index = stack.index(neighbor)
            return stack[index:]
            
    stack.pop()
    return None

scan_candidates = []
working_graph = ff_graph.copy()

print "[*] Breaking Loops..."
while True:
    # 1. Clear search states
    visited = set()
    cycle_found = None
    
    # 2. Search for ANY cycle in the current graph
    nodes = list(working_graph.keys())
    for node in nodes:
        if node not in visited:
            stack = []
            cycle_found = find_cycle_path(working_graph, node, visited, stack)
            if cycle_found:
                break
    
    # 3. If no cycle found, we are done!
    if not cycle_found:
        break
        
    # 4. HEURISTIC: Pick the "Best" FF to scan from this cycle.
    # Simple Heuristic: Pick the first one. 
    # Better Heuristic: Pick the one with most connections (Fanout).
    victim = cycle_found[0]
    
    # 5. Add to scan list and REMOVE from graph (Break the loop)
    scan_candidates.append(victim)
    del working_graph[victim] # Remove the node entirely
    
    # Also remove any edges pointing to this victim
    for node in working_graph:
        if victim in working_graph[node]:
            working_graph[node].remove(victim)
            
    print "    - Found Loop (size {}). Scanning: {}".format(len(cycle_found), victim)

# ---------- OUTPUT ----------
print "========================================"
print "Total Scan Candidates Needed: {}".format(len(scan_candidates))
print "========================================"

with open(output_file, "w") as f:
    for ff in scan_candidates:
        f.write(ff + "\n")
