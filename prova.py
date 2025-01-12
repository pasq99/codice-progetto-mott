import osmnx as ox
import networkx as nx
import pandas as pd
import geopandas as gpd
from shapely.ops import unary_union

# Funzione per scaricare il grafo, strade e colonnine
def load_graph_roads_and_stations(regions):
    # Ottieni i poligoni delle regioni
    region_polygons = [ox.geocode_to_gdf(region).geometry[0] for region in regions]
    
    # Unisci i poligoni in un unico poligono
    combined_polygon = unary_union(region_polygons)
    
    print("Caricamento rete stradale per le regioni combinate...")
    # Scarica il grafo stradale utilizzando il poligono combinato
    combined_graph = ox.graph_from_polygon(combined_polygon, network_type="drive")
    #scarica anche come geojson
    print("Grafo caricato. Trovando colonnine di ricarica...")
    all_pois = gpd.GeoDataFrame()
    for region in regions:
        try:
            # Scarica i punti di interesse (POI) per le colonnine per ogni regione
            pois = ox.features_from_place(
                region,
                tags={"amenity": "charging_station"}
            )
            #unisci i punti di interesse
            all_pois= pd.concat([all_pois, pois], ignore_index=True)
            print(f"Trovate {len(pois)} colonnine di ricarica per la regione {region}.")
        except Exception as e:
            print(f"Errore durante il caricamento dei POI per la regione {region}: {e}")
    


           
    # Ottieni gli archi (strade) come GeoDataFrame
    edges = ox.graph_to_gdfs(combined_graph, nodes=False, edges=True)
    print(f"Trovate {len(edges)} strade.")
    
    # Ritorna grafo, strade e colonnine
    return combined_graph, edges, pois

# Definizione delle regioni
regions = ["Calabria"]

# Caricamento del grafo, strade e colonnine
graph, roads, charging_stations = load_graph_roads_and_stations(regions)
# Salvataggio del grafo in formato GraphML
ox.save_graphml(graph, r"C:\Users\pasqu\Desktop\Uni\Magistrale\MOTT\Progetto\grafocalabria.graphml")
# Salvataggio delle colonnine di ricarica in formato GeoJSON
charging_stations.to_file(r"C:\Users\pasqu\Desktop\Uni\Magistrale\MOTT\Progetto\colonninecalabria.geojson", driver="GeoJSON")
print("Salvataggio completato!")
