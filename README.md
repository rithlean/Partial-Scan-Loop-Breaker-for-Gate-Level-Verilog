# Partial-Scan-Loop-Breaker-for-Gate-Level-Verilog
This repository provides a Python-based utility to assist in partial scan insertion for complex gate-level Verilog designs, particularly for ITC-99 or Nangate-style benchmarks. It helps identify flip-flops (FFs) involved in combinational feedback loops and outputs a list of candidate FFs for partial scan insertion in Synopsys Design Compiler (DC).

##Features

- Automated loop detection: Parses the netlist and constructs a simplified FF-to-FF connectivity graph through combinational logic.
- Cycle detection: Uses depth-first search (DFS) to identify combinational loops.
- Partial scan candidate selection: Picks one FF per loop to break feedback cycles, ready for DC partial scan insertion.
- Output ready for DC: Produces a text file listing scan candidate FFs (loop_regs.txt) compatible with set_scan_register_type and set_scan_path commands.
- Lightweight & adaptable: Works with standard gate-level Verilog and can be extended to other FF types or more complex selection heuristics.

##Usage

1. Place your gate-level netlist (e.g., b01.v) in the repository.
2. Configure the Python script to include the FF types used in your design.
3. Run the script:

```
python find_loops.py
```

4. The script outputs loop_regs.txt, containing one FF per detected loop.
5. In Design Compiler:

```
set loop_ff [split [read_file loop_regs.txt] "\n"]
set_scan_register_type [get_registers $loop_ff] -type scan
set_scan_register_type [all_registers] -exclude [get_registers $loop_ff] -type functional
set_scan_path -chain chain0 -scan_in scan_in0 -scan_out scan_out0 -scan_cells [get_registers $loop_ff]
insert_scan
compile_ultra -incremental
write -format verilog -hierarchy -output b01_partial_scan.v
```
##Advantages

- Reduces manual tracing of feedback loops in large designs.
- Semi-automates loop-breaking for partial scan, improving testability while preserving design integrity.
- Fully compatible with older DC versions lacking all_fanin / all_fanout commands.

##Notes

- This tool does not automatically optimize scan selection; the first FF in each loop is chosen by default.
- Users can extend the Python script to implement FF ranking heuristics (e.g., lowest fanout, closest to primary inputs).
