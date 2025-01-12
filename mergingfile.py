import osmnx as ox
import networkx as nx
import pandas as pd
import geopandas as gpd
from shapely.ops import unary_union
from geopy.distance import geodesic
import matplotlib.pyplot as plt

# Leggi grafo e file GeoJSON delle colonnine
graph = ox.load_graphml(r"C:\Users\pasqu\Desktop\Uni\Magistrale\MOTT\Progetto\grafocalabria.graphml")
charging_stations = gpd.read_file(r"C:\Users\pasqu\Desktop\Uni\Magistrale\MOTT\Progetto\colonninecalabria.geojson")

for idx, station in charging_stations.iterrows():
    try:
        # Controlla il tipo di geometria della colonnina
        if station.geometry.geom_type == "Point":
            station_coords = (station.geometry.y, station.geometry.x)
        elif station.geometry.geom_type == "Polygon":
            # Usa il centroide del poligono se è un poligono
            centroid = station.geometry.centroid
            station_coords = (centroid.y, centroid.x)
        else:
            print(f"Geometria non supportata alla riga {idx}: {station.geometry.geom_type}")
            continue

        # Trova l'arco stradale più vicino
        nearest_edge = ox.distance.nearest_edges(graph, X=station_coords[1], Y=station_coords[0], return_dist=False)
        u, v, key = nearest_edge  # Nodo iniziale, finale e chiave dell'arco

        # Creazione di un ID unico per il nuovo nodo
        new_node = max(graph.nodes) + 1

        # Aggiungi il nodo della colonnina al grafo
        graph.add_node(new_node, y=station_coords[0], x=station_coords[1], amenity="charging_station")
        print(f"Nodo {new_node} aggiunto al grafo come colonnina di ricarica.")

        # Calcola le distanze dal nodo della colonnina ai nodi u e v
        dist_u_to_colonnina = geodesic((graph.nodes[u]['y'], graph.nodes[u]['x']), station_coords).meters
        dist_colonnina_to_v = geodesic(station_coords, (graph.nodes[v]['y'], graph.nodes[v]['x'])).meters

        # Recupera il tipo di strada dell'arco originale
        edge_data = graph[u][v][key]
        highway_type = edge_data.get("highway", "unknown")

        # Rimuovi l'arco originale
        graph.remove_edge(u, v, key)

        # Aggiungi due nuovi archi
        graph.add_edge(u, new_node, length=dist_u_to_colonnina, highway=highway_type)
        graph.add_edge(new_node, v, length=dist_colonnina_to_v, highway=highway_type)
        print(f"Arco diviso: da {u} a {new_node} ({dist_u_to_colonnina:.2f} m) e da {new_node} a {v} ({dist_colonnina_to_v:.2f} m).")
    except Exception as e:
        print(f"Errore alla riga {idx}: {e}")
        continue

# Visualizza il grafo con le colonnine evidenziate
node_colors = [
    "red" if data.get("amenity") == "charging_station" else "blue"
    for node, data in graph.nodes(data=True)
]

fig, ax = ox.plot_graph(
    graph,
    node_color=node_colors,  # Usa la lista di colori
    node_size=10,            # Dimensione dei nodi
    edge_color="gray",       # Colore degli archi
    bgcolor="white",         # Sfondo bianco
    show=True,               # Mostra il grafico
    close=True               # Chiudi la figura automaticamente
)

# Salva il grafo aggiornato
ox.save_graphml(graph, r"C:\Users\pasqu\Desktop\Uni\Magistrale\MOTT\Progetto\grafo_con_colonnine.graphml")
print("Colonnine di ricarica aggiunte al grafo e grafo salvato.")
