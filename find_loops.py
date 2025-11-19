import re
from collections import defaultdict

# ---------- CONFIG ----------
netlist_file = "b01.v"
output_file = "loop_regs.txt"

# FF types in your netlist
ff_types = ["DFFARX1_LVT", "SDFFARX1_LVT"]  # add other FF types if needed

# ---------- PARSE NETLIST ----------
ff_inputs = {}     # FF name -> input net
ff_outputs = {}    # FF name -> output net
net_drivers = {}   # net -> driving FF or gate
net_fanout = defaultdict(list)  # net -> list of nets it drives

with open(netlist_file) as f:
    for line in f:
        line = line.strip()
        if line.startswith("//") or line == "":
            continue  # skip comments and empty lines

        # Parse FF
        for ff_type in ff_types:
            if line.startswith(ff_type):
                # Match FF name
                m_name = re.search(r"%s\s+(\S+)\s*\(" % ff_type, line)
                if m_name:
                    ff_name = m_name.group(1)
                    # Match .D(...) and .Q(...) anywhere in the port list
                    d_match = re.search(r"\.D\((\S+?)\)", line)
                    q_match = re.search(r"\.Q\((\S+?)\)", line)
                    if d_match and q_match:
                        d_net = d_match.group(1).rstrip(",")
                        q_net = q_match.group(1).rstrip(",")
                        ff_inputs[ff_name] = d_net
                        ff_outputs[ff_name] = q_net
                        net_drivers[q_net] = ff_name

        # Parse gates (any line ending with ");")
        if "(" in line and ");" in line:
            # capture input and output nets
            ports = re.findall(r"\.(?:A|B|D|Y)\((\S+?)\)", line)
            if len(ports) >= 2:
                out_net = ports[-1].rstrip(",")
                for in_net in ports[:-1]:
                    net_fanout[in_net.rstrip(",")].append(out_net)

print "=== Net Fanout Graph ==="
for net, fans in net_fanout.items():
    print net, "fans out to", fans
print "======================="


# ---------- BUILD FF GRAPH THROUGH COMBINATIONAL LOGIC ----------
def get_ff_successors(ff_name, visited_nets=None):
    """Return all FFs reachable from ff_name through combinational nets."""
    if visited_nets is None:
        visited_nets = set()
    successors = []
    q_net = ff_outputs[ff_name]
    stack = [q_net]

    while stack:
        net = stack.pop()
        if net in visited_nets:
            continue
        visited_nets.add(net)
        for f in net_fanout.get(net, []):
            # check if net drives FF D
            for ff, d_net in ff_inputs.items():
                if f == d_net:
                    successors.append(ff)
            # continue traversing nets
            stack.append(f)
    return successors

ff_graph = defaultdict(list)
for ff in ff_outputs:
    succs = get_ff_successors(ff)
    ff_graph[ff].extend(succs)

print "=== FF Graph ==="
for ff, succs in ff_graph.items():
    print ff, "->", succs
print "================"


# ---------- CYCLE DETECTION ----------
def find_cycles(graph):
    visited = set()
    stack = set()
    cycles = []

    def dfs(node, path):
        if node in stack:
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
selected_ff = []
for loop in cycles:
    selected_ff.append(loop[0])  # pick first FF as scan candidate

# ---------- SAVE OUTPUT ----------
with open(output_file, "w") as f:
    for ff in selected_ff:
        f.write(ff + "\n")

print "Found %d loops, saved %d FFs to %s" % (len(cycles), len(selected_ff), output_file)

