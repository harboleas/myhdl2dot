# Example 

from myhdl import *

def reg(clk_i,
        rst_i,
        ce_i,
        d_i,
        q_o) :

    @always(clk_i.posedge, rst_i.posedge) 
    def rtl() :
        if rst_i :
            q_o.next = 0
        else :
            if ce_i :
                q_o.next = d_i

    return instances()

def reg_adder(clk_i, 
              rst_i, 
              ce_i, 
              a_i, 
              b_i, 
              q_o) :

    n = len(q_o)

    s_aux = Signal(intbv(0)[n:])

    @always_comb
    def adder() :
        s_aux.next = a_i + b_i

    reg_s = reg(clk_i = clk_i,
                rst_i = rst_i,
                ce_i = ce_i,
                d_i = s_aux,
                q_o = q_o)

    return instances()


