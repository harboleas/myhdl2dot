from myhdl import * 
from myhdl2dot import myhdl2dot 
from reg_adder import reg_adder

clk = Signal(False)
rst = Signal(False)
ce = Signal(False)
a = Signal(intbv(0)[4:])
b = Signal(intbv(0)[4:])
q = Signal(intbv(0)[4:])

top_mod = myhdl2dot("./", "jpg", reg_adder, clk, rst, ce, a, b, q)

top_mod.show_tree()

#  vim: set ts=8 sw=4 tw=0 et :
