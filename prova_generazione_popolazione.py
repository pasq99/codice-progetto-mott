import osmnx as ox
import numpy as np
import xpress as xp
import networkx as nx
import random
import geopy.distance

# Carica il grafo
graph = ox.load_graphml(r"C:\Users\pasqu\Desktop\Uni\Magistrale\MOTT\Progetto\grafo_con_colonnine.graphml")

# Visualizza il grafo con i nodi delle colonnine evidenziati in rosso
node_colors = [
    "red" if data.get("amenity") == "charging_station" else "blue"
    for _, data in graph.nodes(data=True)]



# Funzione per processare gli archi con costi
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
            # Calcola consumo energetico (es. 0.2 kWh/km)
            energy_cost = 0.1 * (length/1000)  # Consumo in kWh
            
            # Calcola pedaggio (es. 0.05 €/km per autostrade)
            toll_cost = 0
            if "motorway" in data.get("highway", ""):
                toll_cost = length * 0.0001  # Costo pedaggio (€/metro)
                # Trova i nodi ricarica nell'arco che sono autostrada e setta il tempo di ricarica maggiore
                # Itera sui nodi dell'arco
                for node in [u, v]: 
                    if graph.nodes[node].get("amenity") == "charging_station":
                        graph.nodes[node]["charging_time"] = 30 * 60  # 30 minuti
            else:
                # Trova i nodi ricarica nell'arco e setta il tempo di ricarica minore
                for node in [u, v]:
                    if graph.nodes[node].get("amenity") == "charging_station":
                        graph.nodes[node]["charging_time"] = 20 * 60
                        

            # Assegna i pesi
            data["travel_time"] = travel_time
            data["toll_cost"] = toll_cost
            data["energy_cost"] = energy_cost
            data["maxspeed"] = maxspeed

        except Exception as e:
            print(f"Errore su arco {u}-{v}: {e}")

# Processa gli archi con costi
process_edges_with_costs(graph)

import networkx as nx

import osmnx as ox
import networkx as nx
import geopy.distance
autonomia=10 #kwh

# Funzione per contare le stazioni di ricarica lungo il percorso
def count_charging_stations(graph, path):
    return sum(1 for node in path if graph.nodes[node].get("amenity") == "charging_station")

# Funzione per trovare il nodo di ricarica più vicino a un dato nodo
def find_nearest_charging_station(graph, node,charging_stations):
    
    min_distance = float('inf')
    nearest_station = None
    for charging_station in charging_stations:
        # Calcola la distanza tra il nodo e ogni stazione di ricarica
        distance = geopy.distance.distance(
            (graph.nodes[node]['y'], graph.nodes[node]['x']),
            (graph.nodes[charging_station]['y'], graph.nodes[charging_station]['x'])
        ).meters
        if distance < min_distance:
            min_distance = distance
            nearest_station = charging_station
    print(nearest_station)
    return nearest_station

# Implementazione della ricerca greedy
def greedy_search(graph, start_node, end_node, autonomia, battery_threshold):
    """
    Algoritmo di ricerca greedy con controllo della batteria residua.
    
    :param graph: Il grafo che rappresenta il sistema stradale.
    :param start_node: Nodo di partenza.
    :param end_node: Nodo di destinazione.
    :param autonomia: Autonomia massima del veicolo (in unità di distanza).
    :param battery_threshold: Soglia di batteria minima per cercare una stazione di ricarica.
    :return: Percorso calcolato.
    """
    charging_stations = [
        n for n in graph.nodes if graph.nodes[n].get("amenity") == "charging_station"
    ]
    print("Inizio ricerca greedy...")

    # Inizializza il percorso e lo stato della batteria
    current_node = start_node
    path = [current_node]
    battery_level = autonomia  # Inizializza la batteria all'autonomia massima
    ricariche={}

    while current_node != end_node:
        # Ottieni i vicini del nodo corrente
        neighbors = list(graph.neighbors(current_node))
        neighbors=[node for node in neighbors if nx.has_path(graph, node, end_node)]
        neighbors.sort(key=lambda node: nx.shortest_path_length(graph, source=node, target=end_node, weight='travel_time'))
        top_neighbors = neighbors[:5]  # Prendi i primi 5 vicini
        if random.random() < 0.3:
            next_node = random.choice(top_neighbors)
        else:
            next_node = top_neighbors[0]
        
        
        # Calcola il consumo di batteria per raggiungere il nodo successivo
        energy_cost = graph[current_node][next_node][0].get('energy_cost')
        travel_time = graph[current_node][next_node][0].get('travel_time')
        battery_level -= energy_cost 
        print(f"Da {current_node} a {next_node}: Consumo {energy_cost} kWh, batteria residua: {battery_level}, tempo di percorrenza: {travel_time} secondi,lunghezza: {graph[current_node][next_node][0].get('length')/1000} km")

        # Controlla se la batteria è insufficiente per procedere
        if battery_level < 0:
            print(f"Batteria insufficiente per continuare il percorso! ({battery_level})")
            return None
        
        # Aggiungi il nodo al percorso e aggiornare il nodo corrente
        path.append(next_node)
        current_node = next_node
        
        # Controlla se la batteria è sotto la soglia
        if battery_level < battery_threshold:
            print(f"Batteria bassa! ({battery_level}/{autonomia}) - Cerco stazione di ricarica...")
            nearest_station = find_nearest_charging_station(graph, current_node,charging_stations)
            ricariche[nearest_station]=ricariche.get(nearest_station,0)
            while nearest_station in path:
                print("Stazione di ricarica già presente nel percorso! Cerco un'altra stazione...")
                charging_stations.remove(nearest_station)
                nearest_station = find_nearest_charging_station(graph, current_node,charging_stations)
                
            
            if nearest_station:
                # Trova il percorso verso la stazione di ricarica
                sub_path = nx.shortest_path(graph, source=current_node, target=nearest_station, weight='travel_time')
                
                for i in range(1, len(sub_path)):
                    previous_node = sub_path[i - 1]
                    current_node = sub_path[i]
                    energy_cost = graph[previous_node][current_node][0].get('energy_cost')
                    travel_time = graph[previous_node][current_node][0].get('length')/1000
                    print(f"Da {previous_node} a {current_node}: Consumo {energy_cost} kWh, batteria residua: {battery_level}")
                    
                    battery_level -= energy_cost 
                    
                    if battery_level < 0:
                        print("Batteria insufficiente per raggiungere la stazione di ricarica!")
                        print(battery_level)
                        return None
                    elif battery_level>=0:
                        path.append(current_node)
                        print(f"Avanzamento verso stazione: {current_node}, batteria residua: {battery_level}")
                
                # Ricarica la batteria una volta raggiunta la stazione
                print(f"Raggiunta stazione di ricarica: {nearest_station}. Batteria ricaricata.")
                #flag per ricarica da aggiungere al nodo ricarica se usato
                ricariche[nearest_station]=ricariche.get(nearest_station,0)+1

                battery_level = autonomia
            else:
                print("Nessuna stazione di ricarica trovata nelle vicinanze!")
                return None

    print("Percorso completato!")
    #calcola la distanza totale
    total_distance=0
    for i in range(len(path)-1):
        total_distance+=graph[path[i]][path[i+1]][0].get('length')
    print(f"Distanza totale: {total_distance} metri")
    return path, ricariche
import random

def generate_population(graph, start_node, end_node, autonomia, battery_threshold, population_size):
    """
    Genera una popolazione iniziale di percorsi utilizzando la ricerca greedy.

    :param graph: Il grafo che rappresenta il sistema stradale.
    :param start_node: Nodo di partenza.
    :param end_node: Nodo di destinazione.
    :param autonomia: Autonomia massima del veicolo (in unità di distanza).
    :param battery_threshold: Soglia di batteria minima per cercare una stazione di ricarica.
    :param population_size: Numero di individui nella popolazione.
    :return: Lista di percorsi che rappresentano la popolazione.
    """
    population = []
    
    for _ in range(population_size):
        # Modifica i parametri random per introdurre diversità
        random_autonomia = autonomia * random.uniform(0.8, 1.2)  # Introduce una variazione casuale nell'autonomia
        random_battery_threshold = battery_threshold * random.uniform(0.8, 1.2)
        
        # Genera un percorso usando greedy_search
        result = greedy_search(
            graph,
            start_node,
            end_node,
            random_autonomia,
            random_battery_threshold
        )
        
        if result is not None:
            path, ricariche = result
            population.append((path, ricariche))
        

    
    return population

def calculate_fitness(graph, path,ricariche):
    
    travel_time = 0
    for i in range(len(path) - 1):
        u = path[i]
        v = path[i + 1]
        #print(f"Da {u} a {v}")
        travel_time += graph[u][v][0].get('travel_time')
        if graph.nodes[v].get("amenity") == "charging_station":
            if ricariche.get(v, 0) >= 1:
                n_ricariche=ricariche.get(v, 0)
                travel_time+=graph.nodes[v].get("charging_time")*n_ricariche
                print(f"ricarica numero {n_ricariche} per tempo {graph.nodes[v].get('charging_time')}")
            else:
                print("stazione di ricarica non usata")
    return travel_time
                
import random
import networkx as nx

import random
import networkx as nx

def crossover_onepoint_with_validation(parent1, parent2, graph, autonomia, battery_threshold):
    '''
    Esegue il crossover one-point tra due genitori per generare 2 figli e verifica la validità dei figli.
    Il punto di crossover è scelto in modo che sia un nodo esistente e comune tra i due genitori nel grafo.
    '''
    while True:
        # Scegli un punto di crossover casuale
        crossover_point = random.randint(1, min(len(parent1[0]), len(parent2[0])) - 1)
        print(f"Punto di crossover scelto: {crossover_point}")
        node_from_parent1 = parent1[0][crossover_point]
    
        print(f"Nodo di crossover dal primo genitore: {node_from_parent1}")
        if node_from_parent1 not in parent2[0]:
            print(f"Nodo {node_from_parent1} non trovato nel secondo genitore, riprova...")
            continue
        else:
            # Trova l'indice del nodo di crossover nel secondo genitore
            crossover_point_parent2 = parent2[0].index(node_from_parent1)
            print(f"Indice del nodo di crossover nel secondo genitore: {crossover_point_parent2}")
            # Esegui il crossover
            child1_path = parent1[0][:crossover_point] + parent2[0][crossover_point_parent2:]
            child2_path = parent2[0][:crossover_point_parent2] + parent1[0][crossover_point:]
            print(f"Figlio 1 generato: {child1_path}")
            print(f"Figlio 2 generato: {child2_path}")
            
            # Verifica la validità dei figli sull'intero percorso
            #dict ricariche dei 2 genitori
            ricariche1=parent1[1]
            ricariche2=parent2[1]
            validpath1,_=is_valid_path(graph, child1_path, autonomia,ricariche1,ricariche2, battery_threshold)
            validpath2,_=is_valid_path(graph, child2_path, autonomia,ricariche1,ricariche2, battery_threshold)
            if validpath1 and validpath2:
                # Calcola la fitness dei figli
                
                return child1_path, child2_path
            else:
                print("Figli non validi, riprova il crossover...") 
                #mutuazione dei figli non validi

                continue


import osmnx as ox
import matplotlib.pyplot as plt

# Funzione per plottare il percorso migliore
def plot_best_path(graph, best_path):
    # Inizializza la figura
    fig, ax = ox.plot_graph(graph, node_color='gray', node_size=10, edge_linewidth=1, show=False, close=False)
    
    # Per ogni coppia di nodi consecutivi nel percorso
    for i in range(len(best_path) - 1):
        start_node = best_path[i]
        end_node = best_path[i + 1]
        
        # Ottieni le coordinate degli archi
        edge_data = graph.get_edge_data(start_node, end_node)
        
        if edge_data:  # Se l'arco esiste
            # Estrai le coordinate di partenza e arrivo dell'arco
            start_lat, start_lon = graph.nodes[start_node]['y'], graph.nodes[start_node]['x']
            end_lat, end_lon = graph.nodes[end_node]['y'], graph.nodes[end_node]['x']
            
            # Traccia l'arco effettivo
            ax.plot([start_lon, end_lon], [start_lat, end_lat], color='red', linewidth=2, marker='o', markersize=5)
    
    # Mostra il grafico
    plt.show()

import random

def roulette_wheel_selection(population, fitness_values, num_selected):
    """
    Executes roulette wheel selection to choose individuals from the population.

    :param population: List of individuals (paths).
    :param fitness_values: List of fitness values corresponding to the population.
    :param num_selected: Number of individuals to select.
    :return: List of selected individuals.
    """
    valori_fitness = []
    for fitness in fitness_values:
        if fitness == 0:
            fitness = float('inf')  # Set very high fitness value
        valori_fitness.append(fitness)
    inverted_fitness = [1 / fitness for fitness in valori_fitness if fitness != float('inf')]
    

    
    # Calcolare la somma cumulativa dei fitness invertiti
    total_fitness = sum(inverted_fitness)  
    probabilities = [fitness / total_fitness for fitness in inverted_fitness]
    
    # Creare la roulette wheel (distribuzione cumulativa)
    cumulative_probabilities = []
    cumulative_sum = 0
    for p in probabilities:
        cumulative_sum += p
        cumulative_probabilities.append(cumulative_sum)
    
    # Selezionare gli individui in base alle probabilità cumulative
    selected_individuals = []
    selected_set = set()
    for _ in range(num_selected):
     while True:  # Ciclo per cercare un individuo non ancora selezionato
            r = random.random()  # Genera un numero casuale tra 0 e 1
            for i, cp in enumerate(cumulative_probabilities):
                if r <= cp:
                    if i not in selected_set:  # Controlla se l'individuo è già stato selezionato
                        selected_individuals.append(population[i])
                        selected_set.add(i)
                        break
            # Se abbiamo trovato un individuo non selezionato, usciamo dal ciclo while
            if i in selected_set:
                break


    return selected_individuals

def mutate_path(path, graph, mutation_rate, autonomia, battery_threshold,ricariche1,ricariche2):

    n_cambiamenti = 0
   

    while n_cambiamenti < mutation_rate:
        # Scegli un nodo casuale da cambiare
        node_to_change = random.choice(path)
        # Scegli un altro nodo casuale nel path
        node_to_change_with = random.choice(path)
        while node_to_change_with == node_to_change or node_to_change > node_to_change_with:
            node_to_change_with = random.choice(path)

        # Trova gli indici dei nodi da cambiare
        index_to_change = path.index(node_to_change)
        index_to_change_with = path.index(node_to_change_with)

        # Calcola il percorso più breve tra i due nodi
        shortest_path = nx.shortest_path(graph, source=node_to_change, target=node_to_change_with, weight='travel_time')

        # Controlla se il percorso più breve coincide già con il percorso attuale
        if shortest_path == path[index_to_change:index_to_change_with + 1]:
            print("Il percorso più breve già coincide con il percorso in 'path'")
            continue

        # Valida la porzione di percorso mutata
        nuovo_path, ricariche = is_valid_path1(
            graph, path, autonomia, battery_threshold, 
            index_to_change, index_to_change_with, 
            ricariche1, ricariche2
        )

        # Se il percorso non è valido, salta questa mutazione
        if nuovo_path is None:
            print("La porzione mutata non è valida, si salta questa mutazione")
            continue

        # Applica il percorso mutato al path principale
        path[index_to_change:index_to_change_with + 1] = nuovo_path
        
            
        n_cambiamenti += 1

    return path,ricariche




def is_valid_path1(graph, path, autonomia, battery_threshold,index1,index2,ricariche1,ricariche2):
        """
        Verifica se un percorso è valido in termini di batteria.
       
        :param graph: Il grafo che rappresenta il sistema stradale.
        :param path: Il percorso da verificare.
        :param autonomia: Autonomia massima del veicolo (in unità di distanza).
        :param battery_threshold: Soglia di batteria minima per cercare una stazione di ricarica.
        :return: True se il percorso è valido, False altrimenti.
        """
        battery_level = autonomia
        ricariche={}     
        charging_stations = [
        n for n in graph.nodes if graph.nodes[n].get("amenity") == "charging_station"
    ]     
        _,battery_level=is_valid_path(graph, path[:index1+1], autonomia,ricariche1,ricariche2,battery_threshold)
        nuovo_path=[]
        path=path[index1:index2+1]
        for i in range(len(path) - 1):

            u = path[i]
            v = path[i + 1]
            nuovo_path.append(u)
            if i== len(path)-2:
                nuovo_path.append(v)
            if graph.has_edge(u, v):
                energy_cost = graph[u][v][0].get('energy_cost')
                battery_level -= energy_cost
            else:
                print(f"Arco mancante tra {u} e {v}")
                #crea un percorso tra i due nodi
                sub_path = nx.shortest_path(graph, source=u, target=v, weight='travel_time')
                for i in range(1, len(sub_path)):
                    
                    previous_node = sub_path[i - 1]
                    current_node = sub_path[i]
                    energy_cost = graph[previous_node][current_node][0].get('energy_cost')
                    travel_time = graph[previous_node][current_node][0].get('length') / 1000
                    print(f"Da {previous_node} a {current_node}: Consumo {energy_cost} kWh, batteria residua: {battery_level}")

                    battery_level -= energy_cost

                    if battery_level < 0:
                        print("Batteria insufficiente per raggiungere la stazione di ricarica!")
                        print(battery_level)
                        return None
                    else:
                        # inserisci la stazione di ricarica nel percorso all'indice corretto del path
                        nuovo_path.append(current_node)
                        print(f"Avanzamento verso stazione: {current_node}, batteria residua: {battery_level}")
                
            print(f"Verifica percorso: Da {u} a {v}, Consumo: {energy_cost}, Batteria residua: {battery_level}")
            if battery_level <= 0:
                print("Percorso non valido: batteria esaurita")
                return None

            if battery_level >= battery_threshold:
                print(f"Aggiunto nodo {v} al percorso")
            else:
                print(f"Batteria bassa! ({battery_level}/{autonomia}) - Cerco stazione di ricarica...")
                nearest_station = find_nearest_charging_station(graph, v, charging_stations)
                ricariche[nearest_station] = ricariche.get(nearest_station, 0)
                while nearest_station in path:
                    print("Stazione di ricarica già presente nel percorso! Cerco un'altra stazione...")
                    charging_stations.remove(nearest_station)
                    nearest_station = find_nearest_charging_station(graph, v, charging_stations)

                if nearest_station:
                    # Trova il percorso verso la stazione di ricarica
                    sub_path = nx.shortest_path(graph, source=v, target=nearest_station, weight='travel_time')

                    for i in range(1, len(sub_path)):
                        previous_node = sub_path[i - 1]
                        current_node = sub_path[i]
                        energy_cost = graph[previous_node][current_node][0].get('energy_cost')
                        travel_time = graph[previous_node][current_node][0].get('length') / 1000
                        print(f"Da {previous_node} a {current_node}: Consumo {energy_cost} kWh, batteria residua: {battery_level}")

                        battery_level -= energy_cost

                        if battery_level < 0:
                            print("Batteria insufficiente per raggiungere la stazione di ricarica!")
                            print(battery_level)
                            return None
                        else:
                            # inserisci la stazione di ricarica nel percorso all'indice corretto del path
                            nuovo_path.append(current_node)
                            print(f"Avanzamento verso stazione: {current_node}, batteria residua: {battery_level}")
                else:
                    print("Nessuna stazione di ricarica trovata nelle vicinanze!")
                    return None

                # Ricarica la batteria una volta raggiunta la stazione
                print(f"Raggiunta stazione di ricarica: {nearest_station}. Batteria ricaricata.")
                # flag per ricarica da aggiungere al nodo ricarica se usato
                ricariche[nearest_station] = ricariche.get(nearest_station, 0) + 1


                battery_level = autonomia
        #unisci le ricariche dei due genitori tranne tra index1 e index2
        for key in ricariche1.keys():
            if ricariche1[key] >= 1:
             ricariche[key] = ricariche.get(key, 0) + ricariche1[key]
        for key in ricariche2.keys():
            if ricariche2[key] >= 1:
             ricariche[key] = ricariche.get(key, 0) + ricariche2[key]
               
        return nuovo_path,ricariche
                

def is_valid_path(graph, path, autonomia, ricarica1,ricarica2,battery_threshold):
        """
        Verifica se un percorso è valido in termini di batteria.
        
        :param graph: Il grafo che rappresenta il sistema stradale.
        :param path: Il percorso da verificare.
        :param autonomia: Autonomia massima del veicolo (in unità di distanza).
        :param battery_threshold: Soglia di batteria minima per cercare una stazione di ricarica.
        :return: True se il percorso è valido, False altrimenti.
        """
        battery_level = autonomia
        for i in range(len(path) - 1):
            u = path[i]
            v = path[i + 1]
            if i== len(path)-2:
                print("ultimo nodo")
                print(u)
                print(v)
            if graph.has_edge(u, v):

                 energy_cost = graph[u][v][0].get('energy_cost')
                 battery_level -= energy_cost
            else:

                print(f"Arco mancante tra {u} e {v}")
                #crea un percorso tra i due nodi
                sub_path = nx.shortest_path(graph, source=u, target=v, weight='travel_time')
                for i in range(1, len(sub_path)):
                    previous_node = sub_path[i - 1]
                    current_node = sub_path[i]
                    energy_cost = graph[previous_node][current_node][0].get('energy_cost')
                    travel_time = graph[previous_node][current_node][0].get('length') / 1000
                    print(f"Da {previous_node} a {current_node}: Consumo {energy_cost} kWh, batteria residua: {battery_level}")

                    battery_level -= energy_cost

                    if battery_level < 0:
                        print("Batteria insufficiente per raggiungere la stazione di ricarica!")
                        print(battery_level)
                        return False, battery_level
                    else:
                        print(f"Avanzamento verso stazione: {current_node}, batteria residua: {battery_level}")
            print(f"Verifica percorso: Da {u} a {v}, Consumo: {energy_cost}, Batteria residua: {battery_level}")
            if battery_level < 0:
                print("Percorso non valido: batteria esaurita")
                return False, battery_level
            if battery_level < battery_threshold and graph.nodes[v].get("amenity") == "charging_station" and (ricarica1.get(v,0)+ricarica2.get(v,0))>=0 :
                battery_level = autonomia  # Ricarica la batteria
                print(f"Ricarica a stazione: {v}, Batteria ricaricata a: {battery_level}")
        return True, battery_level



# Esempio di utilizzo
def main():
    # Coordinate di partenza e arrivo
    napoli_coords = (40.8522, 14.2681)  
    salerno_coords = (40.6829, 14.7682)  


# Trova i nodi più vicini alle coordinate
    napoli_node = ox.distance.nearest_nodes(graph, X=napoli_coords[1], Y=napoli_coords[0])
    salerno_node = ox.distance.nearest_nodes(graph, X=salerno_coords[1], Y=salerno_coords[0])
    start_node = napoli_node  # Nodo di partenza
    end_node = salerno_node  # Nodo di destinazione

    # Supponendo che tu abbia un grafo 'graph' già definito
    #best_path = greedy_search(graph, start_node, end_node,10,5)

    # Controlla quanti nodi di ricarica ci sono nel percorso
    #print(f"Numero di stazioni di ricarica nel percorso: {count_charging_stations(graph, best_path)}")

    #riempi la popolazione
    population = generate_population(graph, start_node, end_node, autonomia, 5, 2)
    print(f"dimensione popolazione: {len(population)}")
    if len(population)==0:
        print("nessun percorso trovato")
        return 0


    #numero di stazioni di ricarica nel percorso
    for path,_ in population:
        print(f"Numero di stazioni di ricarica nel percorso: {count_charging_stations(graph, path)}")

    #visualizza tutti i percorsi
    '''
    for path,_ in population:
      plot_best_path(graph, path)
      '''
      

    # Calcola il fitness di ogni individuo
    fitness_values = [calculate_fitness(graph, path,ricariche) for path,ricariche in population]
    for i, fitness in enumerate(fitness_values):
        print(f"Individuo {i}: Fitness = {fitness}")

    # Seleziona i migliori individui
    selected_individuals = roulette_wheel_selection(population, fitness_values, 2)
    for i, individual in enumerate(selected_individuals):
        print(f"Individuo{i} selezionato: {individual}")
    if len(selected_individuals)==0:
        print("nessun individuo selezionato")
        return 0
    elif len(selected_individuals)==1:
        print("un solo individuo selezionato")
        return 0

    # Visualizza i percorsi selezionati
    '''
    for path,ricariche in selected_individuals:
        plot_best_path(graph, path)
    '''

    child1, child2 = crossover_onepoint_with_validation(selected_individuals[0], selected_individuals[1], graph, autonomia, 5)
    print(f"Figlio 1: {child1}")
    print(f"Figlio 2: {child2}")
    '''
    for path, _ in selected_individuals:
        print("stampa indivui selezionati")
        plot_best_path(graph, path)
    print("stampa figlio 1")
    plot_best_path(graph, child1)
    print("stampa figlio 2")
    plot_best_path(graph, child2)
    '''
    print("fitness figli")
    lista_child=[child1,child2]
    lista_child_mutated=[]
    fitness_values = [calculate_fitness(graph, path, selected_individuals[i][1]) for i, path in enumerate(lista_child)]
    for i, fitness in enumerate(fitness_values):
        print(f"figlio {i}: Fitness = {fitness}")
    # Mutazione di tutti i figli
    mutation_rate = 3
    ricariche_list = []
    for i, child in enumerate(lista_child):
        mutated_child,ricariche = mutate_path(child, graph, mutation_rate, autonomia, 5,selected_individuals[0][1],selected_individuals[1][1])
        lista_child_mutated.append(mutated_child)
        ricariche_list.append(ricariche)
    #print("fitness figli mutati")
    #fitness_values1 = [calculate_fitness(graph, path, ricariche) for path,ricariche in zip(lista_child_mutated,ricariche_list)]
    #plot dei figli mutati
    '''
    for i, path in enumerate(lista_child):
        print(f"Figlio {i}: Fitness = {fitness_values[i]}")
        plot_best_path(graph, path)
    '''
    #stampa figli non mutati
    for i, path in enumerate(lista_child):
        print("figli non mutati")
        print(f"Figlio {i}: {path}")
        print(f"Figlio {i}: Fitness = {fitness_values[i]}")
        plot_best_path(graph, path)
    
    
#fitness dei figli mutati

#controlla che i figli mutati siano validi

    for i, path in enumerate(lista_child_mutated):
        print("figli mutati")
        print(f"Figlio {i}: {path}")
        #controlla che il path sia connesso
        if nx.has_path(graph,path[0],path[-1]):
            print("path connesso")
            fitness=calculate_fitness(graph, path, ricariche_list[i])
            print(f"Fitness: {fitness}")
            plot_best_path(graph, path)

        else:
            print("path non connesso")


if __name__ == "__main__":
    main()



