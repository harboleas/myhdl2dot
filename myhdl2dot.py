# myhdl2dot.py
# ============
# 
# Description :
#   Modulo de Python que permite generar un conjunto de diagramas en bloques, 
#   a partir de la descripcion en MyHDL de un dispositivo de hardware. 
#   Este conjunto de diagramas documenta la dependencia e interconexion de 
#   los submodulos del dispositivo.
# 
# Author : 
#   Hugo Arboleas, <harboleas@citedef.gob.ar>
#
##############################################################################
# 
# Copyright 2014 Hugo Arboleas
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################

import myhdl
import pygraphviz as pgv 
from random import choice


class Modulo_HW :
    """Nodo de una estructura tipo arbol que representa un modulo de hardware"""

    ############

    def __init__(self, myhdl_hier, analyzed_term_objs, obj=None, padre=None) :
        """Crea una estructura tipo arbol partiendo de la jerarquia MyHDL"""
        
        if not obj :
            # top level, lista de instancias myhdl que describen la jerarquia del diseno
            self._obj = myhdl_hier.top    
        else :
            # generador o lista de instancias myhdl. (ver definicion de instancia myhdl)
            self._obj = obj     

        self.padre = padre
        
        self._graph = None    

        # Las senales del modulo
        self.inputs = {} 
        self.outputs = {}
        self._posibles_outputs = {}
        self._inter_sig = {}         # senales internas
        
        if isinstance(self._obj, list) :   
            # el modulo es un nodo no terminal del arbol.          

            self._get_info_nodo_no_term(myhdl_hier)  

            # crea de forma recursiva la lista de submodulos                       
            self.sub_modulos = [Modulo_HW(myhdl_hier, analyzed_term_objs, sub_obj, self) for sub_obj in self._obj]   

            self._clasif_signals_nodo_no_term()  # determina la direccion de cada senal 

            self._make_graph()  

        else :      
            # si _obj es un generador, entonces el modulo es un nodo terminal. 

            self._get_info_nodo_term()       
            
            self.sub_modulos = []            # sin submodulos
            
            self._clasif_signals_nodo_term(analyzed_term_objs) # determina la direccion de cada senal
            

    ###############

    def _get_info_nodo_no_term(self, myhdl_hier) :
        """Obtiene el nombre y las senales de un nodo no terminal"""

        # Busca el obj actual dentro de la jerarquia myhdl (non term. myhdl node)        
        for no_term_myhdl in myhdl_hier.hierarchy :        
            if self._obj is no_term_myhdl.obj :   
                break   # Encontrado         

        self._no_term_myhdl = no_term_myhdl  
        # obtiene la info 
        self.name = no_term_myhdl.name
        self._sigdict = no_term_myhdl.sigdict
 
    ###############

    def _get_info_nodo_term(self) :
        """Obtiene el nombre del nodo terminal"""

        # Obtiene el nombre del nodo a partir del nodo padre
        for name, sub_obj in self.padre._no_term_myhdl.subs : 
            if self._obj is sub_obj :                         
                self.name = name
                break
        
 
    ###############
    
    def _clasif_signals_nodo_term(self, analyzed_term_objs) :
        """Obtiene la direccion de las senales de un nodo terminal"""

        # Busca el modulo en analyzed terminal objs 
        for obj_term, obj_info in analyzed_term_objs :
            if self._obj is obj_term :
                break  # Lo encontre

        for sig_name in obj_info.inputs :    # inputs signals
            signal = obj_info.sigdict[sig_name]
            if sig_name not in obj_info.outputs :   
                self.inputs[sig_name] = signal    

        for sig_name in obj_info.outputs :   # outputs signals
            signal = obj_info.sigdict[sig_name]
            if sig_name not in obj_info.inputs :
                self.outputs[sig_name] = signal      # output real
            else :
                self._posibles_outputs[sig_name] = signal    # Posibles outputs

        for elem in obj_info.senslist :    # Miro la lista de sensibilidad por mas inputs
            if isinstance(elem, myhdl._Signal._Signal) : 
                signal = elem
            else :                                      
                signal = elem.sig
            # Obtengo, del padre, el nombre de las senales de la senslist
            for sig_name, padre_sig in self.padre._sigdict.items() : 
                if signal is padre_sig :
                    break
            self.inputs[sig_name] = signal

    ###############

    def _clasif_signals_nodo_no_term(self) :
        """Obtiene la direccion de las senales de un nodo no terminal"""

        # determina la direccion real de las posibles salidas de los submodulos  
        for sub_mod_A in self.sub_modulos :
            for sig_name_A, sig_A in sub_mod_A._posibles_outputs.items() :
                for sub_mod_B in self.sub_modulos :
                    if sub_mod_A is not sub_mod_B :   
                        for sig_name_B, sig_B in sub_mod_B.inputs.items() :
                            if sig_A is sig_B :  
                                # output real si sale de A y entra en B
                                sub_mod_A.outputs[sig_name_A] = sig_A  

        # Determina las senales de entrada, salida y las internas del nodo no term 
        for sig_name, signal in self._sigdict.items() :
            posible_in = True
            posible_out = True
            
            # Busco la senal en las entradas y salidas de los submodulos
            for sub_mod in self.sub_modulos :
                for sig_in in sub_mod.inputs.values() :
                    if signal is sig_in :                
                        # No puede ser una salida (ojo depende de la descripcion)
                        posible_out = False
                        break
                for sig_out in sub_mod.outputs.values() : 
                    if signal is sig_out :               
                        # No puede ser una entrada 
                        posible_in = False
                        break

            if posible_in and not posible_out :
                direc = self.inputs
            elif posible_out and not posible_in :
                direc = self.outputs
            else :
                direc = self._inter_sig

            direc[sig_name] = signal

    ###############
                    
    def _make_graph(self) :
        """Genera un grafo de interconexion de los submodulos"""

        self._graph = pgv.AGraph(name=self.name, strict=False, directed=True)

        self._graph.graph_attr["rankdir"] = "LR"
        self._graph.graph_attr["size"] = "11, 8"
        self._graph.graph_attr["ranksep"] = "1.2 equally"
       
        self._graph.node_attr["shape"] = "Mrecord" 

        attr = {}
        sigs_in = [ "<" + sig_name + "> " + sig_name for sig_name in sorted(self.inputs.keys()) ]
        label = "{ IN  | { " + " | ".join(sigs_in) + " } }"         
        attr["label"] = label      
        self._graph.add_node(0, **attr)  # Inputs


        attr = {}
        sigs_out = [ "<" + sig_name + "> " + sig_name for sig_name in sorted(self.outputs.keys()) ]
        label = "{ { " + " | ".join(sigs_out) + " } | OUT }"         
        attr["label"] = label      
        self._graph.add_node(1, **attr)  # Outputs
        
        for sub_mod in self.sub_modulos :
            
            attr = {}
            subm_sigs_in = [ "<" + sig_name + "> " + sig_name for sig_name in sorted(sub_mod.inputs.keys()) ]
            subm_sigs_out = [ "<" + sig_name + "> " + sig_name for sig_name in sorted(sub_mod.outputs.keys()) ]
            label = "{ { " + " | ".join(subm_sigs_in) + " } | " + sub_mod.name + " | { " + " | ".join(subm_sigs_out) + " } }"
            attr["label"] = label
            
            self._graph.add_node(sub_mod.name, **attr)    

        # Conexiones de entrada al modulo 
        for sig_name, sig_in in self.inputs.items() :
            # Busca los submodulos que tengan conexion con las entradas del padre  
            for sub_mod in self.sub_modulos :                    
                for sig_name_subm, sig_in_subm in sub_mod.inputs.items() :
                    if sig_in is sig_in_subm :
                        attr = {"key" : sig_name, "tailport" : sig_name, "headport" : sig_name_subm, "color" : rand_color()}
                        self._graph.add_edge(0, sub_mod.name, **attr )     


        # Conexion entre submodulos
        # Si una senal de salida del submodulo A esta conectada a una entrada del submodulo B
        for mod_A in self.sub_modulos :                 
            for sig_name_A, sig_out_A in mod_A.outputs.items() :                   
                for mod_B in self.sub_modulos :                           
                    for sig_name_B, sig_in_B in mod_B.inputs.items() :
                        if sig_out_A is sig_in_B :
                            attr = {"tailport" : sig_name_A, "headport" : sig_name_B, "color" : rand_color()}
                            self._graph.add_edge(mod_A.name, mod_B.name, **attr)     


        # Conexiones de salida del modulo
        for sig_name, sig_out in self.outputs.items() :
            # Busca los submodulos que tengan conexion con las salidas del padre  
            for sub_mod in self.sub_modulos :                    
                for sig_name_subm, sig_out_subm in sub_mod.outputs.items() :
                    if sig_out is sig_out_subm :
                        attr = {"key" : sig_name, "tailport" : sig_name_subm, "headport" : sig_name, "color" : rand_color()}
                        self._graph.add_edge(sub_mod.name, 1, **attr )     

    ###############

    def show_tree(self, n=0) :
        """Muestra las dependecias del modulo"""

        if n == 0 :
            print " " * len(self.name) + "  |In : " + ", ".join(sorted(self.inputs.keys()))
            print self.name + "--|"
            print " " * len(self.name) + "  |Out : " + ", ".join(sorted(self.outputs.keys()))
        else :
            print " " + " " * 5*(n - 1) + "|  "
            print " " + " " * 5*(n - 1) + "|  " + " " * len(self.name) + "  |In: " + ", ".join(sorted(self.inputs.keys())) 
            print " " + " " * 5*(n - 1) + "|_ " + self.name + "--|"
            print " " + " " * 5*(n - 1) + ".  " + " " * len(self.name) + "  |Out: " + ", ".join(sorted(self.outputs.keys())) 
        
        for sub_mod in self.sub_modulos :
            sub_mod.show_tree(n+1)
        
    ###############

    def draw(self, path, fmt) :
        """Genera el output file"""
        
        if self._graph :
            self._graph.draw(path + self.name + "." + fmt, format=fmt, prog="dot")
            # Recorre el arbol y dibuja un grafo con la interconexion de los submodulos
            for sub_mod in self.sub_modulos :
                sub_mod.draw(path, fmt)

###########################################################


def myhdl2dot(path, fmt, myhdl_top, *args, **kwargs) :
    """Crea un objeto Modulo_HW a partir de myhdl_top y genera un archiv dot, ps o jpg con los diagramas en bloques"""

    # Obtiene la jerarquia myhdl 
    myhdl_hier = myhdl._extractHierarchy._HierExtr(myhdl_top.func_name, myhdl_top, *args, **kwargs)  
        
    term_objs = myhdl._util._flatten(myhdl_hier.top)

    analyzed_term_objs = zip(term_objs, myhdl.conversion._analyze._analyzeGens(term_objs, myhdl_hier.absnames))
        
    top_mod = Modulo_HW(myhdl_hier, analyzed_term_objs)       
    
    top_mod.draw(path, fmt)    # Dibuja los grafos

    return top_mod


##################################################################################################################

def rand_color() :

    colors = ["blue", "red", "yellow", "green", "orange", "cyan", "magenta", "pink", "purple", "brown"]       
    return choice(colors)


# vim: set ts=8 sw=4 tw=0 et :
