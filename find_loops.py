import re
from collections import defaultdict, deque

# ---------- CONFIG ----------
netlist_file = "b01.v"
output_file = "loop_regs.txt"

# FF types in your netlist
ff_types = ["DFFARX1_LVT", "SDFFARX1_LVT"]  # add other FF types if needed

# ---------- PARSE NETLIST ----------
ff_inputs = {}     # FF name -> input net
ff_outputs = {}    # FF name -> output net
net_drivers = {}   # net -> driving FF or gate
net_fanout = defaultdict(list)  # net -> list of destination FFs

with open(netlist_file) as f:
    for line in f:
        line = line.strip()
        # Parse FF
        for ff_type in ff_types:
            if line.startswith(ff_type):
                # Example: DFFARX1_LVT reg34 ( .D(n45), .CLK(clk), .Q(reg34), .RST(reset) );
                m = re.search(rf"{ff_type}\s+(\S+)\s*\(.*\.D\((\S+)\).*\.Q\((\S+)\)", line)
                if m:
                    ff_name = m.group(1)
                    d_net = m.group(2)
                    q_net = m.group(3)
                    ff_inputs[ff_name] = d_net
                    ff_outputs[ff_name] = q_net
                    net_drivers[q_net] = ff_name

        # Parse gates (any line ending with ");")
        if "(" in line and ");" in line:
            # crude net connection: net driving another net
            ports = re.findall(r"\.(?:A|B|D|Y)\((\S+)\)", line)
            if len(ports) >= 2:
                # assume last port is output
                out_net = ports[-1]
                for in_net in ports[:-1]:
                    net_fanout[in_net].append(out_net)
                    net_drivers[out_net] = line  # optional, store gate line

# ---------- BUILD FF CONNECTION GRAPH ----------
# FF -> FF edges through nets
ff_graph = defaultdict(list)
for ff_name, d_net in ff_inputs.items():
    if d_net in net_drivers:
        driver = net_drivers[d_net]
        # driver is FF? then FF -> FF edge
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

print(f"Found {len(cycles)} loops, saved {len(selected_ff)} FFs to {output_file}")
