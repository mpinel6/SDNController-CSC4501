import networkx as nx
import heapq
import time
import matplotlib.pyplot as plt

class SDNController:
    def __init__(self):
        self.topology = nx.Graph()
        self.flow_tables = {}
        self.link_utilization = {}

    def add_link(self, src, dst, weight=1):
        self.topology.add_edge(src, dst, weight=weight)
        self._init_flow_table(src)
        self._init_flow_table(dst)

    def remove_link(self, src, dst):
        if self.topology.has_edge(src, dst):
            self.topology.remove_edge(src, dst)

    def _init_flow_table(self, node):
        if node not in self.flow_tables:
            self.flow_tables[node] = {}

    def compute_paths(self):
        for src in self.topology.nodes:
            for dst in self.topology.nodes:
                if src != dst:
                    try:
                        path = nx.shortest_path(self.topology, source=src, target=dst, weight='weight')
                        self._install_path(src, dst, path)
                    except nx.NetworkXNoPath:
                        continue

    def _install_path(self, src, dst, path):
        for i in range(len(path) - 1):
            current = path[i]
            next_hop = path[i + 1]
            self.flow_tables[current][dst] = next_hop

    def inject_traffic(self, src, dst):
        if src not in self.topology.nodes or dst not in self.topology.nodes:
            print("Invalid nodes.")
            return
        try:
            path = nx.shortest_path(self.topology, source=src, target=dst, weight='weight')
            print(f"Traffic from {src} to {dst} goes through: {' -> '.join(path)}")
            self._update_utilization(path)
        except nx.NetworkXNoPath:
            print(f"No path between {src} and {dst}")

    def _update_utilization(self, path):
        for i in range(len(path) - 1):
            link = tuple(sorted((path[i], path[i+1])))
            self.link_utilization[link] = self.link_utilization.get(link, 0) + 1

    def print_topology(self):
        print("\nCurrent Topology:")
        for edge in self.topology.edges(data=True):
            print(f"{edge[0]} <-> {edge[1]} (weight={edge[2]['weight']})")

    def print_flow_tables(self):
        print("\nFlow Tables:")
        for switch, table in self.flow_tables.items():
            print(f"{switch}:")
            for dest, next_hop in table.items():
                print(f"  to {dest} -> {next_hop}")

    def print_utilization(self):
        print("\nLink Utilization:")
        for link, count in self.link_utilization.items():
            print(f"{link}: {count} flows")

    def visualize_topology(self):
        pos = nx.spring_layout(self.topology)
        nx.draw(self.topology, pos, with_labels=True, node_color='skyblue', edge_color='gray')
        edge_labels = nx.get_edge_attributes(self.topology, 'weight')
        nx.draw_networkx_edge_labels(self.topology, pos, edge_labels=edge_labels)
        plt.title("Network Topology")
        plt.show()

def cli():
    controller = SDNController()

    while True:
        print("\n--- SDN Controller CLI ---")
        print("1. Add link")
        print("2. Remove link")
        print("3. Show topology")
        print("4. Compute paths")
        print("5. Inject traffic")
        print("6. Show flow tables")
        print("7. Show link utilization")
        print("8. Visualize topology")
        print("0. Exit")
        choice = input("Select an option: ")

        if choice == '1':
            src = input("Enter source node: ")
            dst = input("Enter destination node: ")
            weight = int(input("Enter weight (default=1): ") or 1)
            controller.add_link(src, dst, weight)

        elif choice == '2':
            src = input("Enter source node: ")
            dst = input("Enter destination node: ")
            controller.remove_link(src, dst)

        elif choice == '3':
            controller.print_topology()

        elif choice == '4':
            controller.compute_paths()
            print("Flow tables updated using Dijkstra.")

        elif choice == '5':
            src = input("Enter source node: ")
            dst = input("Enter destination node: ")
            controller.inject_traffic(src, dst)

        elif choice == '6':
            controller.print_flow_tables()

        elif choice == '7':
            controller.print_utilization()

        elif choice == '8':
            controller.visualize_topology()

        elif choice == '0':
            break

        else:
            print("Invalid option.")

if __name__ == "__main__":
    cli()
