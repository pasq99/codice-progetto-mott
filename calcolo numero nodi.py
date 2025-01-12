import networkx as nx
import pandas as pd
import osmnx as ox
import math
import sys

graph = ox.load_graphml(r"C:\Users\pasqu\Desktop\Uni\Magistrale\MOTT\Progetto\grafo_con_colonnine.graphml")

# Calcola il numero di nodi nel grafo
num_nodes = graph.number_of_nodes()
print(f"Il grafo contiene {num_nodes} nodi.")
log_fatorial = math.log(math.factorial(num_nodes))
print(f"Logaritmo del fattoriale del numero di nodi: {log_fatorial:.2f}")
