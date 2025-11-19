# ==============================
# partial_scan_insert.tcl
# ==============================
# Usage: source this in Design Vision
# Set chain_count variable below to control number of chains
# ==============================

# ------------------------------
# Config
# ------------------------------
set chain_count 4             ;# Adjust number of chains
set netlist_file "b04.v"
set output_netlist "b04_partial_scan.v"
set candidate_file "loop_regs.txt"

# ------------------------------
# Load design
# ------------------------------
puts "Loading netlist: $netlist_file"
read_verilog $netlist_file
current_design [file rootname $netlist_file]
compile_ultra

# ------------------------------
# Read FF candidate list
# ------------------------------
set fh [open $candidate_file r]
set list_txt [read $fh]
close $fh

set loop_ff [list]
foreach l [split $list_txt "\n"] {
    if {$l ne ""} {
        lappend loop_ff $l
    }
}

puts "Read [llength $loop_ff] candidate FFs from $candidate_file"

# ------------------------------
# Mark scan and functional registers
# ------------------------------
puts "Marking candidate registers as scan"
set_scan_register_type [get_registers $loop_ff] -type scan
puts "Marking remaining registers as functional"
set_scan_register_type [all_registers] -exclude [get_registers $loop_ff] -type functional

# ------------------------------
# Split candidates into chains
# ------------------------------
puts "Splitting candidates into $chain_count scan chains"
set total [llength $loop_ff]
for {set i 0} {$i < $total} {incr i} {
    set ff [lindex $loop_ff $i]
    set chain_index [expr {$i % $chain_count}]
    set chain_name "chain${chain_index}"
    if {![info exists CH_${chain_name}]} {
        set CH_${chain_name} [list]
    }
    set tmp [eval set CH_${chain_name}]
    set tmp [linsert $tmp end $ff]
    eval set CH_${chain_name} $tmp
}

# ------------------------------
# Create scan paths
# ------------------------------
for {set i 0} {$i < $chain_count} {incr i} {
    set chain_name "chain${i}"
    set regs [eval set CH_${chain_name}]
    if {[llength $regs] > 0} {
        set si "scan_in${i}"
        set so "scan_out${i}"
        puts "Creating scan path $chain_name with [llength $regs] registers"
        set_scan_path -chain $chain_name -scan_in $si -scan_out $so -scan_cells $regs
    }
}

# ------------------------------
# Insert scan
# ------------------------------
puts "Inserting scan registers..."
insert_scan

# ------------------------------
# Check design
# ------------------------------
puts "Checking design for combinational integrity..."
if {[check_design] == 0} {
    puts "No combinational issues detected."
} else {
    puts "Warning: combinational issues detected!"
}

# ------------------------------
# Timing check
# ------------------------------
puts "Updating timing and reporting top 20 paths..."
update_timing
report_timing -max_paths 20

# ------------------------------
# Save modified netlist
# ------------------------------
puts "Writing partial-scan netlist to $output_netlist"
write -format verilog -hierarchy -output $output_netlist

puts "Partial-scan insertion completed."
