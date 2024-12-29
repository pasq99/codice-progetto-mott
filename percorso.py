import osmnx as ox
import networkx as nx
from queue import PriorityQueue
 
# Carica il grafo
graph = ox.load_graphml(r"C:\Users\pasqu\Desktop\Uni\Magistrale\MOTT\Progetto\grafo_con_colonnine.graphml")
 
# Visualizza il grafo con i nodi delle colonnine evidenziati in rosso
node_colors = [
    "red" if data.get("amenity") == "charging_station" else "blue"
    for _, data in graph.nodes(data=True)
]
 
# Coordinate di partenza e arrivo
campobasso_coords = (41.5603, 14.6687)
pescara_coords = (42.4618, 14.2161)
 
# Trova i nodi più vicini alle coordinate
campobasso_node = ox.distance.nearest_nodes(graph, X=campobasso_coords[1], Y=campobasso_coords[0])
pescara_node = ox.distance.nearest_nodes(graph, X=pescara_coords[1], Y=pescara_coords[0])
 
# Parametri del problema
budget_massimo = 200.0  # Budget massimo (in €)
consumption_rate = 0.01  # Consumo specifico (kWh/km)
costo_energia = 0.30  # Costo dell'energia (€ per kWh)
battery_max = 10.0  # Capacità massima della batteria (in kWh)
 
def process_edges_with_costs(graph):
    """
    Aggiunge travel_time, energy_cost e toll_cost agli archi del grafo.
    """
    for u, v, data in graph.edges(data=True):
        try:
            # Lunghezza dell'arco e velocità
            length = data.get("length", 0)
            maxspeed = data.get("maxspeed", 50)  # Default: 50 km/h
 
            # Pulisce e converte la velocità
            if isinstance(maxspeed, list):
                maxspeed = maxspeed[0]
            if isinstance(maxspeed, str):
                if "km/h" in maxspeed:
                    maxspeed = float(maxspeed.replace("km/h", ""))
                elif maxspeed.isdigit():
                    maxspeed = float(maxspeed)
                else:
                    maxspeed = 50
            if maxspeed is None or maxspeed == 0:
                maxspeed = 50
 
            # Converti velocità da km/h a m/s
            speed_mps = maxspeed * 1000 / 3600
 
            # Calcola tempo di percorrenza
            travel_time = length / speed_mps  # Tempo in secondi
 
            # Calcola costo energetico
            energy_cost = (length / 1000) * consumption_rate * costo_energia  # Consumo in €/km
 
            # Calcola pedaggio (es. 0.05 €/km per autostrade)
            toll_cost = 0
            if "motorway" in data.get("highway", ""):
                toll_cost = length * 0.0001  # Costo pedaggio (€/metro)
 
            # Assegna i pesi
            data["travel_time"] = travel_time
            data["energy_cost"] = energy_cost
            data["toll_cost"] = toll_cost
            data["maxspeed"] = maxspeed
 
        except Exception as e:
            print(f"Errore su arco {u}-{v}: {e}")
 
# Processa gli archi con costi
process_edges_with_costs(graph)
 
def process_nodes(graph):
    """
    Aggiunge tempo di ricarica ai nodi che rappresentano colonnine di ricarica.
    """
    for node, data in graph.nodes(data=True):
        if data.get("amenity") == "charging_station":
            # Identifica se il nodo è connesso a un'autostrada
            is_motorway = any(
                "motorway" in edge_data.get("highway", "")
                for neighbor in graph[node]
                for edge_data in graph.get_edge_data(node, neighbor).values()
            )
 
            # Assegna il tempo di ricarica
            data["charging_time"] = 30 * 60 if is_motorway else 20 * 60  # Tempo in secondi
        else:
            data["charging_time"] = 0
 
# Processa i nodi
process_nodes(graph)
 
def branch_and_bound(graph, source, target, budget_massimo, battery_max):
    """
    Algoritmo Branch and Bound per trovare il percorso ottimale.
    """
    queue = PriorityQueue()
    best_solution = None
    best_cost = float('inf')
 
    # Nodo iniziale
    initial_state = (0, source, battery_max, 0, 0, [source])  # (tempo, nodo, batteria, pedaggio, energia, percorso)
    queue.put(initial_state)
 
    while not queue.empty():
        time, current_node, battery_left, toll_cost, energy_cost, path = queue.get()
 
        # Verifica se siamo arrivati al nodo target
        if current_node == target:
            if time < best_cost:
                best_solution = path
                best_cost = time
            continue
 
        # Esplora i vicini
        for neighbor, edge_data in graph[current_node].items():
            travel_time = edge_data[0].get("travel_time", 0)
            toll = edge_data[0].get("toll_cost", 0)
            length_km = edge_data[0].get("length", 0) / 1000
            energy = length_km * consumption_rate * costo_energia
 
            new_battery = battery_left - length_km * consumption_rate
            if new_battery < 0 and graph.nodes[current_node].get("amenity") != "charging_station":
                print(f"Percorso parziale non valido: {path} -> Batteria insufficiente verso {neighbor}")
                continue  # Batteria insufficiente
 
            new_time = time + travel_time
            new_toll = toll_cost + toll
            new_energy = energy_cost + energy
 
            if (new_toll + new_energy) > budget_massimo:
                print(f"Percorso parziale non valido: {path} -> Superato budget massimo verso {neighbor}")
                continue  # Supera il budget
 
            if new_time >= best_cost:
                print(f"Percorso parziale non valido: {path} -> Non migliora il costo attuale verso {neighbor}")
                continue  # Non migliora il costo attuale
 
            new_path = path + [neighbor]
            queue.put((new_time, neighbor, new_battery, new_toll, new_energy, new_path))
 
    return best_solution, best_cost
 
# Esegui il Branch and Bound
best_path, best_cost = branch_and_bound(graph, campobasso_node, pescara_node, budget_massimo, battery_max)
if best_path:
    print(f"Percorso migliore: {best_path}")
    print(f"Tempo totale: {best_cost:.2f} secondi")
else:
    print("Nessun percorso valido trovato.")