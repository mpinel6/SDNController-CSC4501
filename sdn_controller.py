from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ipv4
import logging
import networkx as nx
import matplotlib.pyplot as plt
from collections import defaultdict
import random

class NetworkVisualizer:
    def __init__(self, controller):
        self.controller = controller
        self.fig = None
        self.ax = None
        self.pos = None
        self.colors = {
            'switch': 'lightblue',
            'host': 'lightgreen',
            'link': 'gray',
            'active_flow': 'red',
            'backup_flow': 'orange',
            'critical_flow': 'purple'
        }

    def visualize_topology(self, filename='network_topology.png'):
        """
        Visualize the current network topology.
        """
        self.fig, self.ax = plt.subplots(figsize=(15, 10))
        self.pos = nx.spring_layout(self.controller.topology)

        # Draw switches
        switch_nodes = [n for n in self.controller.topology.nodes() 
                       if self.controller.topology.nodes[n].get('type') == 'switch']
        nx.draw_networkx_nodes(self.controller.topology, self.pos, 
                             nodelist=switch_nodes, node_color=self.colors['switch'],
                             node_size=1000, label='Switches')

        # Draw hosts
        host_nodes = [n for n in self.controller.topology.nodes() 
                     if self.controller.topology.nodes[n].get('type') == 'host']
        nx.draw_networkx_nodes(self.controller.topology, self.pos, 
                             nodelist=host_nodes, node_color=self.colors['host'],
                             node_size=500, label='Hosts')

        # Draw edges
        nx.draw_networkx_edges(self.controller.topology, self.pos, 
                             edge_color=self.colors['link'])

        # Add labels
        labels = {node: f"{node}\n{self.controller.topology.nodes[node].get('mac', '')}"
                 for node in self.controller.topology.nodes()}
        nx.draw_networkx_labels(self.controller.topology, self.pos, labels)

        plt.title("Network Topology")
        plt.legend()
        plt.savefig(filename)
        plt.close()
        self.controller.logger.info(f"Topology visualization saved to {filename}")

    def visualize_flows(self, filename='network_flows.png'):
        """
        Visualize active flows in the network.
        """
        self.fig, self.ax = plt.subplots(figsize=(15, 10))
        self.pos = nx.spring_layout(self.controller.topology)

        # Draw basic topology
        self._draw_basic_topology()

        # Draw active flows
        for (src_mac, dst_mac), paths in self.controller.active_paths.items():
            for path in paths:
                # Draw flow path
                path_edges = list(zip(path[:-1], path[1:]))
                nx.draw_networkx_edges(self.controller.topology, self.pos,
                                     edgelist=path_edges,
                                     edge_color=self.colors['active_flow'],
                                     width=2,
                                     label=f"Flow: {src_mac} -> {dst_mac}")

        # Draw critical flows
        for (src_mac, dst_mac) in self.controller.critical_flows:
            if (src_mac, dst_mac) in self.controller.backup_paths:
                for path in self.controller.backup_paths[(src_mac, dst_mac)]:
                    path_edges = list(zip(path[:-1], path[1:]))
                    nx.draw_networkx_edges(self.controller.topology, self.pos,
                                         edgelist=path_edges,
                                         edge_color=self.colors['critical_flow'],
                                         width=1, style='dashed',
                                         label=f"Critical Flow: {src_mac} -> {dst_mac}")

        plt.title("Network Flows")
        plt.legend()
        plt.savefig(filename)
        plt.close()
        self.controller.logger.info(f"Flow visualization saved to {filename}")

    def visualize_link_utilization(self, filename='link_utilization.png'):
        """
        Visualize link utilization statistics.
        """
        self.fig, self.ax = plt.subplots(figsize=(15, 10))
        self.pos = nx.spring_layout(self.controller.topology)

        # Draw basic topology
        self._draw_basic_topology()

        # Calculate and draw link utilization
        edge_colors = []
        edge_widths = []
        for (u, v) in self.controller.topology.edges():
            if (u, v) in self.controller.link_stats:
                stats = self.controller.link_stats[(u, v)]
                utilization = (stats.get('rx_bytes', 0) + stats.get('tx_bytes', 0)) / (1024 * 1024)  # MB
                edge_colors.append(utilization)
                edge_widths.append(1 + utilization / 100)  # Scale width based on utilization

        # Draw edges with utilization colors
        edges = nx.draw_networkx_edges(self.controller.topology, self.pos,
                                     edge_color=edge_colors,
                                     width=edge_widths,
                                     edge_cmap=plt.cm.Reds)

        # Add colorbar
        plt.colorbar(edges, label='Link Utilization (MB)')

        plt.title("Link Utilization")
        plt.savefig(filename)
        plt.close()
        self.controller.logger.info(f"Link utilization visualization saved to {filename}")

    def _draw_basic_topology(self):
        """
        Draw the basic network topology (helper method).
        """
        # Draw switches
        switch_nodes = [n for n in self.controller.topology.nodes() 
                       if self.controller.topology.nodes[n].get('type') == 'switch']
        nx.draw_networkx_nodes(self.controller.topology, self.pos, 
                             nodelist=switch_nodes, node_color=self.colors['switch'],
                             node_size=1000, label='Switches')

        # Draw hosts
        host_nodes = [n for n in self.controller.topology.nodes() 
                     if self.controller.topology.nodes[n].get('type') == 'host']
        nx.draw_networkx_nodes(self.controller.topology, self.pos, 
                             nodelist=host_nodes, node_color=self.colors['host'],
                             node_size=500, label='Hosts')

        # Add labels
        labels = {node: f"{node}\n{self.controller.topology.nodes[node].get('mac', '')}"
                 for node in self.controller.topology.nodes()}
        nx.draw_networkx_labels(self.controller.topology, self.pos, labels)

class SDNControllerCLI:
    def __init__(self, controller):
        self.controller = controller
        self.running = True
        self.commands = {
            'help': self.show_help,
            'exit': self.exit_cli,
            'add_node': self.add_node,
            'remove_node': self.remove_node,
            'add_link': self.add_link,
            'remove_link': self.remove_link,
            'inject_flow': self.inject_flow,
            'simulate_failure': self.simulate_failure,
            'query_route': self.query_route,
            'show_topology': self.show_topology,
            'show_flows': self.show_flows,
            'show_stats': self.show_stats
        }

    def start(self):
        """
        Start the CLI interface.
        """
        print("SDN Controller CLI")
        print("Type 'help' for available commands")
        
        while self.running:
            try:
                command = input("\nSDN> ").strip()
                if not command:
                    continue
                
                parts = command.split()
                cmd = parts[0].lower()
                args = parts[1:]
                
                if cmd in self.commands:
                    self.commands[cmd](*args)
                else:
                    print(f"Unknown command: {cmd}")
                    print("Type 'help' for available commands")
            except Exception as e:
                print(f"Error: {str(e)}")

    def show_help(self, *args):
        """
        Show available commands and their usage.
        """
        print("\nAvailable commands:")
        print("  help                    - Show this help message")
        print("  exit                    - Exit the CLI")
        print("  add_node <type> <id>    - Add a node (type: switch/host)")
        print("  remove_node <id>        - Remove a node")
        print("  add_link <node1> <node2> - Add a link between nodes")
        print("  remove_link <node1> <node2> - Remove a link")
        print("  inject_flow <src> <dst> <priority> - Inject a traffic flow")
        print("  simulate_failure <node1> <node2> - Simulate a link failure")
        print("  query_route <src> <dst> - Query routing path")
        print("  show_topology           - Show current topology")
        print("  show_flows              - Show active flows")
        print("  show_stats              - Show link statistics")

    def exit_cli(self, *args):
        """
        Exit the CLI.
        """
        self.running = False
        print("Exiting SDN Controller CLI")

    def add_node(self, *args):
        """
        Add a node to the network.
        """
        if len(args) != 2:
            print("Usage: add_node <type> <id>")
            return
        
        node_type, node_id = args
        if node_type not in ['switch', 'host']:
            print("Node type must be 'switch' or 'host'")
            return
        
        if node_id in self.controller.topology:
            print(f"Node {node_id} already exists")
            return
        
        self.controller.topology.add_node(node_id, type=node_type)
        if node_type == 'host':
            # Generate a random MAC address for the host
            mac = ':'.join(['%02x' % random.randint(0, 255) for _ in range(6)])
            self.controller.topology.nodes[node_id]['mac'] = mac
        
        print(f"Added {node_type} {node_id}")
        self.controller.visualize_network()

    def remove_node(self, *args):
        """
        Remove a node from the network.
        """
        if len(args) != 1:
            print("Usage: remove_node <id>")
            return
        
        node_id = args[0]
        if node_id not in self.controller.topology:
            print(f"Node {node_id} does not exist")
            return
        
        self.controller.topology.remove_node(node_id)
        print(f"Removed node {node_id}")
        self.controller.visualize_network()

    def add_link(self, *args):
        """
        Add a link between two nodes.
        """
        if len(args) != 2:
            print("Usage: add_link <node1> <node2>")
            return
        
        node1, node2 = args
        if node1 not in self.controller.topology or node2 not in self.controller.topology:
            print("Both nodes must exist")
            return
        
        if self.controller.topology.has_edge(node1, node2):
            print("Link already exists")
            return
        
        self.controller.topology.add_edge(node1, node2)
        print(f"Added link between {node1} and {node2}")
        self.controller.visualize_network()

    def remove_link(self, *args):
        """
        Remove a link between two nodes.
        """
        if len(args) != 2:
            print("Usage: remove_link <node1> <node2>")
            return
        
        node1, node2 = args
        if not self.controller.topology.has_edge(node1, node2):
            print("Link does not exist")
            return
        
        self.controller.topology.remove_edge(node1, node2)
        print(f"Removed link between {node1} and {node2}")
        self.controller.visualize_network()

    def inject_flow(self, *args):
        """
        Inject a traffic flow between two hosts.
        """
        if len(args) != 3:
            print("Usage: inject_flow <src> <dst> <priority>")
            return
        
        src, dst, priority = args
        try:
            priority = int(priority)
        except ValueError:
            print("Priority must be an integer")
            return
        
        # Find host nodes by MAC address
        src_node = next((n for n in self.controller.topology.nodes() 
                        if self.controller.topology.nodes[n].get('mac') == src), None)
        dst_node = next((n for n in self.controller.topology.nodes() 
                        if self.controller.topology.nodes[n].get('mac') == dst), None)
        
        if not src_node or not dst_node:
            print("Source or destination host not found")
            return
        
        # Implement the flow
        self.controller.implement_load_balancing(src, dst)
        self.controller.set_traffic_priority(src, dst, priority)
        print(f"Injected flow from {src} to {dst} with priority {priority}")
        self.controller.visualize_network()

    def simulate_failure(self, *args):
        """
        Simulate a link failure.
        """
        if len(args) != 2:
            print("Usage: simulate_failure <node1> <node2>")
            return
        
        node1, node2 = args
        if not self.controller.topology.has_edge(node1, node2):
            print("Link does not exist")
            return
        
        # Simulate failure by removing the link
        self.controller.topology.remove_edge(node1, node2)
        print(f"Simulated failure of link between {node1} and {node2}")
        
        # Trigger failure handling
        self.controller._handle_link_failure(node1, node2)
        self.controller.visualize_network()

    def query_route(self, *args):
        """
        Query the routing path between two hosts.
        """
        if len(args) != 2:
            print("Usage: query_route <src> <dst>")
            return
        
        src, dst = args
        path = self.controller.get_shortest_path(src, dst)
        if path:
            print(f"Route from {src} to {dst}:")
            print(" -> ".join(path))
        else:
            print(f"No route found from {src} to {dst}")

    def show_topology(self, *args):
        """
        Show the current network topology.
        """
        print("\nCurrent Network Topology:")
        print("Nodes:")
        for node in self.controller.topology.nodes():
            node_type = self.controller.topology.nodes[node].get('type', 'unknown')
            mac = self.controller.topology.nodes[node].get('mac', 'N/A')
            print(f"  {node} (Type: {node_type}, MAC: {mac})")
        
        print("\nLinks:")
        for u, v in self.controller.topology.edges():
            print(f"  {u} <-> {v}")
        
        self.controller.visualize_network()

    def show_flows(self, *args):
        """
        Show active flows in the network.
        """
        print("\nActive Flows:")
        for (src_mac, dst_mac), paths in self.controller.active_paths.items():
            print(f"\nFlow: {src_mac} -> {dst_mac}")
            print("Paths:")
            for i, path in enumerate(paths, 1):
                print(f"  Path {i}: {' -> '.join(path)}")
        
        print("\nCritical Flows:")
        for src_mac, dst_mac in self.controller.critical_flows:
            print(f"  {src_mac} -> {dst_mac}")
            if (src_mac, dst_mac) in self.controller.backup_paths:
                print("  Backup paths:")
                for i, path in enumerate(self.controller.backup_paths[(src_mac, dst_mac)], 1):
                    print(f"    Backup {i}: {' -> '.join(path)}")

    def show_stats(self, *args):
        """
        Show link statistics.
        """
        print("\nLink Statistics:")
        for (u, v), stats in self.controller.link_stats.items():
            print(f"\nLink: {u} <-> {v}")
            print(f"  RX Packets: {stats.get('rx_packets', 0)}")
            print(f"  TX Packets: {stats.get('tx_packets', 0)}")
            print(f"  RX Bytes: {stats.get('rx_bytes', 0)}")
            print(f"  TX Bytes: {stats.get('tx_bytes', 0)}")
            print(f"  RX Errors: {stats.get('rx_errors', 0)}")
            print(f"  TX Errors: {stats.get('tx_errors', 0)}")

class SDNController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(SDNController, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.logger = logging.getLogger('SDNController')
        self.logger.setLevel(logging.INFO)
        
        # Initialize network topology graph
        self.topology = nx.Graph()
        self.switch_ports = defaultdict(dict)  # dpid -> {port_no -> (dpid, port_no)}
        self.host_mac_to_port = defaultdict(dict)  # dpid -> {mac -> port_no}
        
        # Link failure detection
        self.link_failures = set()  # Set of failed links
        self.flow_paths = defaultdict(list)  # src_mac -> dst_mac -> [path]
        self.backup_paths = defaultdict(list)  # src_mac -> dst_mac -> [backup_paths]
        self.link_stats = defaultdict(dict)  # (dpid1, dpid2) -> stats
        
        # Traffic management
        self.critical_flows = set()  # Set of (src_mac, dst_mac) tuples for critical flows
        self.traffic_priorities = defaultdict(int)  # (src_mac, dst_mac) -> priority
        self.path_weights = defaultdict(float)  # path -> weight for load balancing
        self.active_paths = defaultdict(list)  # (src_mac, dst_mac) -> [active_paths]

        # Initialize visualizer
        self.visualizer = NetworkVisualizer(self)
        
        # Initialize CLI
        self.cli = SDNControllerCLI(self)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Add switch to topology
        self.topology.add_node(datapath.id, type='switch')
        self.logger.info(f"Switch {datapath.id} connected")

        # Install default flow entry
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                        ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

    @set_ev_cls(ofp_event.EventOFPPortStatus, MAIN_DISPATCHER)
    def port_status_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        reason = msg.reason
        port_no = msg.desc.port_no

        if reason == ofproto.OFPPR_ADD:
            self.logger.info(f"Port {port_no} added on switch {datapath.id}")
            # Check if this port reconnects a failed link
            self._check_link_recovery(datapath.id, port_no)
        elif reason == ofproto.OFPPR_DELETE:
            self.logger.info(f"Port {port_no} deleted on switch {datapath.id}")
            # Handle link failure
            self._handle_link_failure(datapath.id, port_no)
        elif reason == ofproto.OFPPR_MODIFY:
            self.logger.info(f"Port {port_no} modified on switch {datapath.id}")
            # Check for link degradation
            self._check_link_degradation(datapath.id, port_no)

    def _handle_link_failure(self, dpid, port_no):
        """
        Handle a link failure by updating topology and reconfiguring affected paths.
        """
        if port_no in self.switch_ports[dpid]:
            peer = self.switch_ports[dpid][port_no]
            failed_link = (dpid, peer[0])
            self.link_failures.add(failed_link)
            
            # Remove the failed link from topology
            if self.topology.has_edge(dpid, peer[0]):
                self.topology.remove_edge(dpid, peer[0])
            
            # Find and reconfigure affected paths
            self._reconfigure_affected_paths(failed_link)
            
            self.logger.warning(f"Link failure detected: {dpid} -> {peer[0]}")
            del self.switch_ports[dpid][port_no]

    def _check_link_recovery(self, dpid, port_no):
        """
        Check if a port addition represents a link recovery.
        """
        # Check if this port connects to a known switch
        for other_dpid, other_ports in self.switch_ports.items():
            for other_port, (peer_dpid, _) in other_ports.items():
                if peer_dpid == dpid:
                    # Link recovered
                    recovered_link = (other_dpid, dpid)
                    if recovered_link in self.link_failures:
                        self.link_failures.remove(recovered_link)
                        self.topology.add_edge(other_dpid, dpid)
                        self.logger.info(f"Link recovered: {other_dpid} -> {dpid}")
                        # Reconfigure paths that were using backup routes
                        self._reconfigure_recovered_paths(recovered_link)

    def _check_link_degradation(self, dpid, port_no):
        """
        Check for link degradation based on port statistics.
        """
        if port_no in self.switch_ports[dpid]:
            peer = self.switch_ports[dpid][port_no]
            link = (dpid, peer[0])
            
            # Get port statistics
            self._request_port_stats(dpid, port_no)
            
            # If degradation detected, prepare backup paths
            if self._is_link_degraded(link):
                self._prepare_backup_paths(link)

    def _reconfigure_affected_paths(self, failed_link):
        """
        Reconfigure paths affected by a link failure.
        """
        for src_mac, dst_paths in self.flow_paths.items():
            for dst_mac, paths in dst_paths.items():
                for path in paths:
                    if self._path_uses_link(path, failed_link):
                        # Find alternative path
                        new_path = self._find_alternative_path(src_mac, dst_mac, failed_link)
                        if new_path:
                            # Install new path
                            self.install_path_flows(new_path, src_mac, dst_mac, priority=100)
                            # Update path information
                            self.flow_paths[src_mac][dst_mac] = [new_path]
                            self.logger.info(f"Reconfigured path for {src_mac} -> {dst_mac}")
                        else:
                            self.logger.warning(f"No alternative path found for {src_mac} -> {dst_mac}")

    def _reconfigure_recovered_paths(self, recovered_link):
        """
        Reconfigure paths when a link recovers.
        """
        for src_mac, dst_paths in self.flow_paths.items():
            for dst_mac, paths in dst_paths.items():
                # Check if current path is a backup path
                if paths and self._is_backup_path(paths[0]):
                    # Find optimal path using recovered link
                    optimal_path = self._find_optimal_path(src_mac, dst_mac)
                    if optimal_path:
                        # Install optimal path
                        self.install_path_flows(optimal_path, src_mac, dst_mac, priority=100)
                        # Update path information
                        self.flow_paths[src_mac][dst_mac] = [optimal_path]
                        self.logger.info(f"Restored optimal path for {src_mac} -> {dst_mac}")

    def _find_alternative_path(self, src_mac, dst_mac, failed_link):
        """
        Find an alternative path avoiding the failed link.
        """
        src_host = next((n for n in self.topology.nodes() 
                        if self.topology.nodes[n].get('mac') == src_mac), None)
        dst_host = next((n for n in self.topology.nodes() 
                        if self.topology.nodes[n].get('mac') == dst_mac), None)
        
        if src_host and dst_host:
            try:
                # Create a temporary graph without the failed link
                temp_graph = self.topology.copy()
                temp_graph.remove_edge(*failed_link)
                return nx.shortest_path(temp_graph, src_host, dst_host)
            except nx.NetworkXNoPath:
                return None
        return None

    def _find_optimal_path(self, src_mac, dst_mac):
        """
        Find the optimal path between two hosts.
        """
        src_host = next((n for n in self.topology.nodes() 
                        if self.topology.nodes[n].get('mac') == src_mac), None)
        dst_host = next((n for n in self.topology.nodes() 
                        if self.topology.nodes[n].get('mac') == dst_mac), None)
        
        if src_host and dst_host:
            try:
                return nx.shortest_path(self.topology, src_host, dst_host)
            except nx.NetworkXNoPath:
                return None
        return None

    def _path_uses_link(self, path, link):
        """
        Check if a path uses a specific link.
        """
        for i in range(len(path) - 1):
            if (path[i], path[i + 1]) == link or (path[i + 1], path[i]) == link:
                return True
        return False

    def _is_backup_path(self, path):
        """
        Check if a path is a backup path.
        """
        return path in self.backup_paths.values()

    def _prepare_backup_paths(self, link):
        """
        Prepare backup paths for paths using a degraded link.
        """
        for src_mac, dst_paths in self.flow_paths.items():
            for dst_mac, paths in dst_paths.items():
                for path in paths:
                    if self._path_uses_link(path, link):
                        # Find and store backup path
                        backup_path = self._find_alternative_path(src_mac, dst_mac, link)
                        if backup_path:
                            self.backup_paths[(src_mac, dst_mac)].append(backup_path)
                            self.logger.info(f"Prepared backup path for {src_mac} -> {dst_mac}")

    def _request_port_stats(self, dpid, port_no):
        """
        Request port statistics from a switch.
        """
        ofproto = self.datapaths[dpid].ofproto
        parser = self.datapaths[dpid].ofproto_parser
        req = parser.OFPPortStatsRequest(self.datapaths[dpid], 0, port_no)
        self.datapaths[dpid].send_msg(req)

    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def port_stats_reply_handler(self, ev):
        """
        Handle port statistics reply from switch.
        """
        body = ev.msg.body
        dpid = ev.msg.datapath.id
        
        for stat in body:
            port_no = stat.port_no
            if port_no in self.switch_ports[dpid]:
                peer = self.switch_ports[dpid][port_no]
                link = (dpid, peer[0])
                
                # Update link statistics
                self.link_stats[link].update({
                    'rx_packets': stat.rx_packets,
                    'tx_packets': stat.tx_packets,
                    'rx_bytes': stat.rx_bytes,
                    'tx_bytes': stat.tx_bytes,
                    'rx_errors': stat.rx_errors,
                    'tx_errors': stat.tx_errors
                })

    def _is_link_degraded(self, link):
        """
        Check if a link is degraded based on statistics.
        """
        if link in self.link_stats:
            stats = self.link_stats[link]
            # Check for high error rates or packet loss
            error_rate = (stats.get('rx_errors', 0) + stats.get('tx_errors', 0)) / \
                        (stats.get('rx_packets', 1) + stats.get('tx_packets', 1))
            return error_rate > 0.01  # 1% error rate threshold
        return False

    def add_flow(self, datapath, priority, match, actions, buffer_id=None, idle_timeout=0, hard_timeout=0):
        """
        Add a flow entry to the switch's flow table.
        
        Args:
            datapath: The switch datapath
            priority: Flow entry priority
            match: Flow match conditions
            actions: List of actions to apply
            buffer_id: Buffer ID for buffered packets
            idle_timeout: Idle timeout in seconds (0 means no timeout)
            hard_timeout: Hard timeout in seconds (0 means no timeout)
        """
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                           actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                  priority=priority, match=match,
                                  instructions=inst, idle_timeout=idle_timeout,
                                  hard_timeout=hard_timeout)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                  match=match, instructions=inst,
                                  idle_timeout=idle_timeout,
                                  hard_timeout=hard_timeout)
        datapath.send_msg(mod)
        self.logger.info(f"Added flow entry: priority={priority}, match={match}, actions={actions}")

    def delete_flow(self, datapath, match=None, priority=None):
        """
        Delete flow entries from the switch's flow table.
        
        Args:
            datapath: The switch datapath
            match: Flow match conditions (None for all flows)
            priority: Flow priority (None for all priorities)
        """
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        if match is None:
            match = parser.OFPMatch()
        
        mod = parser.OFPFlowMod(
            datapath=datapath,
            command=ofproto.OFPFC_DELETE,
            out_port=ofproto.OFPP_ANY,
            out_group=ofproto.OFPG_ANY,
            match=match,
            priority=priority if priority is not None else 0
        )
        datapath.send_msg(mod)
        self.logger.info(f"Deleted flow entries: match={match}, priority={priority}")

    def modify_flow(self, datapath, match, actions, priority, buffer_id=None):
        """
        Modify an existing flow entry.
        
        Args:
            datapath: The switch datapath
            match: Flow match conditions
            actions: New list of actions to apply
            priority: Flow entry priority
            buffer_id: Buffer ID for buffered packets
        """
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                           actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                  command=ofproto.OFPFC_MODIFY,
                                  priority=priority, match=match,
                                  instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath,
                                  command=ofproto.OFPFC_MODIFY,
                                  priority=priority, match=match,
                                  instructions=inst)
        datapath.send_msg(mod)
        self.logger.info(f"Modified flow entry: priority={priority}, match={match}, actions={actions}")

    def get_flow_stats(self, datapath):
        """
        Get flow statistics from the switch.
        
        Args:
            datapath: The switch datapath
            
        Returns:
            list: List of flow statistics
        """
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        req = parser.OFPFlowStatsRequest(datapath)
        datapath.send_msg(req)
        
        # Note: The actual flow stats will be received in the flow_stats_reply_handler
        # This method just sends the request
        self.logger.info(f"Requested flow statistics from switch {datapath.id}")

    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def flow_stats_reply_handler(self, ev):
        """
        Handle flow statistics reply from the switch.
        """
        body = ev.msg.body
        self.logger.info('Flow Stats:')
        self.logger.info('datapath         '
                        'in-port  eth-dst           '
                        'out-port packets  bytes')
        self.logger.info('---------------- '
                        '-------- ----------------- '
                        '-------- -------- --------')
        for stat in sorted([flow for flow in body if flow.priority == 1],
                          key=lambda flow: (flow.match['in_port'],
                                          flow.match['eth_dst'])):
            self.logger.info('%016x %8x %17s %8x %8d %8d',
                           ev.msg.datapath.id,
                           stat.match['in_port'], stat.match['eth_dst'],
                           stat.instructions[0].actions[0].port,
                           stat.packet_count, stat.byte_count)

    def add_qos_flow(self, datapath, match, actions, priority, queue_id, max_rate):
        """
        Add a QoS flow entry with rate limiting.
        
        Args:
            datapath: The switch datapath
            match: Flow match conditions
            actions: List of actions to apply
            priority: Flow entry priority
            queue_id: Queue ID for rate limiting
            max_rate: Maximum rate in Mbps
        """
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Add meter entry for rate limiting
        meter_id = queue_id
        bands = [parser.OFPMeterBandDrop(rate=max_rate, burst_size=0)]
        meter_mod = parser.OFPMeterMod(
            datapath=datapath,
            command=ofproto.OFPMC_ADD,
            flags=ofproto.OFPMF_KBPS,
            meter_id=meter_id,
            bands=bands
        )
        datapath.send_msg(meter_mod)

        # Add flow entry with meter
        inst = [
            parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions),
            parser.OFPInstructionMeter(meter_id, ofproto.OFPIT_METER)
        ]
        mod = parser.OFPFlowMod(
            datapath=datapath,
            priority=priority,
            match=match,
            instructions=inst
        )
        datapath.send_msg(mod)
        self.logger.info(f"Added QoS flow entry: priority={priority}, meter_id={meter_id}, max_rate={max_rate}Mbps")

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        dst = eth.dst
        src = eth.src

        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})

        # Learn MAC address
        self.mac_to_port[dpid][src] = in_port
        self.host_mac_to_port[dpid][src] = in_port

        # Add host to topology if it's a new host
        if not any(self.topology.nodes[n].get('mac') == src for n in self.topology.nodes()):
            host_id = f"host_{src.replace(':', '')}"
            self.topology.add_node(host_id, type='host', mac=src)
            self.topology.add_edge(dpid, host_id, port=in_port)
            self.logger.info(f"New host {host_id} connected to switch {dpid} on port {in_port}")

        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]

        # Install flow entry
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst)
            if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                self.add_flow(datapath, 1, match, actions, msg.buffer_id)
                return
            else:
                self.add_flow(datapath, 1, match, actions)

        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)

    def implement_traffic_policy(self, datapath, src_ip, dst_ip, priority, actions):
        """
        Implement a traffic engineering policy with priority.
        
        Args:
            datapath: The switch datapath
            src_ip: Source IP address
            dst_ip: Destination IP address
            priority: Flow entry priority
            actions: List of actions to apply
        """
        parser = datapath.ofproto_parser
        match = parser.OFPMatch(
            eth_type=0x0800,  # IPv4
            ipv4_src=src_ip,
            ipv4_dst=dst_ip
        )
        
        # Add priority-based actions
        if priority > 0:
            # Add QoS actions for high-priority traffic
            actions.insert(0, parser.OFPActionSetField(ip_dscp=46))  # Expedited Forwarding
        
        self.add_flow(datapath, priority, match, actions)
        self.logger.info(f"Added traffic policy: {src_ip} -> {dst_ip} with priority {priority}")

    def get_topology(self):
        """
        Get the current network topology.
        
        Returns:
            networkx.Graph: The current network topology graph
        """
        return self.topology

    def visualize_network(self):
        """
        Generate all network visualizations.
        """
        self.visualizer.visualize_topology()
        self.visualizer.visualize_flows()
        self.visualizer.visualize_link_utilization()
        self.logger.info("Network visualizations generated")

    def get_shortest_path(self, src_mac, dst_mac):
        """
        Calculate the shortest path between two hosts based on their MAC addresses.
        
        Args:
            src_mac: Source host MAC address
            dst_mac: Destination host MAC address
            
        Returns:
            list: List of nodes in the shortest path
        """
        src_host = next((n for n in self.topology.nodes() 
                        if self.topology.nodes[n].get('mac') == src_mac), None)
        dst_host = next((n for n in self.topology.nodes() 
                        if self.topology.nodes[n].get('mac') == dst_mac), None)
        
        if src_host and dst_host:
            try:
                return nx.shortest_path(self.topology, src_host, dst_host)
            except nx.NetworkXNoPath:
                self.logger.warning(f"No path found between {src_mac} and {dst_mac}")
                return None
        return None

    def install_path_flows(self, path, src_mac, dst_mac, priority=100):
        """
        Install flow entries for a computed path between two hosts.
        
        Args:
            path: List of nodes in the path
            src_mac: Source host MAC address
            dst_mac: Destination host MAC address
            priority: Priority for the flow entries
        """
        if not path or len(path) < 2:
            self.logger.warning("Invalid path provided")
            return

        # Get all switches in the path
        switches = [node for node in path if self.topology.nodes[node].get('type') == 'switch']
        
        for i in range(len(switches) - 1):
            current_switch = switches[i]
            next_switch = switches[i + 1]
            
            # Get the datapath for the current switch
            datapath = None
            for dpid in self.datapaths:
                if dpid == current_switch:
                    datapath = self.datapaths[dpid]
                    break
            
            if not datapath:
                self.logger.warning(f"Could not find datapath for switch {current_switch}")
                continue

            # Get the port that connects to the next switch
            out_port = None
            for port, (peer_dpid, peer_port) in self.switch_ports[current_switch].items():
                if peer_dpid == next_switch:
                    out_port = port
                    break

            if not out_port:
                self.logger.warning(f"Could not find port from {current_switch} to {next_switch}")
                continue

            # Create and install flow entry
            parser = datapath.ofproto_parser
            match = parser.OFPMatch(
                eth_src=src_mac,
                eth_dst=dst_mac
            )
            actions = [parser.OFPActionOutput(out_port)]
            self.add_flow(datapath, priority, match, actions)
            self.logger.info(f"Installed flow entry on switch {current_switch} for path {src_mac} -> {dst_mac}")

    def compute_and_install_path(self, src_mac, dst_mac, priority=100):
        """
        Compute the shortest path between two hosts and install the necessary flow entries.
        
        Args:
            src_mac: Source host MAC address
            dst_mac: Destination host MAC address
            priority: Priority for the flow entries
            
        Returns:
            bool: True if path was successfully computed and installed, False otherwise
        """
        path = self.get_shortest_path(src_mac, dst_mac)
        if path:
            self.install_path_flows(path, src_mac, dst_mac, priority)
            self.logger.info(f"Successfully installed path from {src_mac} to {dst_mac}")
            return True
        return False

    def get_all_shortest_paths(self, src_mac, dst_mac, k=3):
        """
        Calculate k shortest paths between two hosts.
        
        Args:
            src_mac: Source host MAC address
            dst_mac: Destination host MAC address
            k: Number of paths to compute
            
        Returns:
            list: List of k shortest paths
        """
        src_host = next((n for n in self.topology.nodes() 
                        if self.topology.nodes[n].get('mac') == src_mac), None)
        dst_host = next((n for n in self.topology.nodes() 
                        if self.topology.nodes[n].get('mac') == dst_mac), None)
        
        if src_host and dst_host:
            try:
                return list(nx.shortest_simple_paths(self.topology, src_host, dst_host, k))
            except nx.NetworkXNoPath:
                self.logger.warning(f"No paths found between {src_mac} and {dst_mac}")
                return []
        return []

    def get_path_metrics(self, path):
        """
        Calculate metrics for a given path.
        
        Args:
            path: List of nodes in the path
            
        Returns:
            dict: Dictionary containing path metrics
        """
        if not path or len(path) < 2:
            return None

        metrics = {
            'hop_count': len(path) - 1,
            'switches': [node for node in path if self.topology.nodes[node].get('type') == 'switch'],
            'hosts': [node for node in path if self.topology.nodes[node].get('type') == 'host']
        }
        
        return metrics

    def set_critical_flow(self, src_mac, dst_mac, is_critical=True):
        """
        Mark a flow as critical, ensuring it always has backup paths.
        
        Args:
            src_mac: Source MAC address
            dst_mac: Destination MAC address
            is_critical: Whether the flow is critical
        """
        flow = (src_mac, dst_mac)
        if is_critical:
            self.critical_flows.add(flow)
            # Ensure backup paths exist
            self._ensure_backup_paths(src_mac, dst_mac)
        else:
            self.critical_flows.discard(flow)
        self.logger.info(f"Flow {flow} {'marked as' if is_critical else 'unmarked as'} critical")

    def set_traffic_priority(self, src_mac, dst_mac, priority):
        """
        Set priority for traffic between source and destination.
        
        Args:
            src_mac: Source MAC address
            dst_mac: Destination MAC address
            priority: Priority level (higher number = higher priority)
        """
        self.traffic_priorities[(src_mac, dst_mac)] = priority
        self.logger.info(f"Set priority {priority} for flow {src_mac} -> {dst_mac}")

    def implement_load_balancing(self, src_mac, dst_mac, num_paths=3):
        """
        Implement load balancing across multiple paths.
        
        Args:
            src_mac: Source MAC address
            dst_mac: Destination MAC address
            num_paths: Number of paths to use for load balancing
        """
        # Get all possible paths
        paths = self.get_all_shortest_paths(src_mac, dst_mac, k=num_paths)
        if not paths:
            self.logger.warning(f"No paths found for {src_mac} -> {dst_mac}")
            return

        # Calculate path weights based on current load
        total_weight = 0
        for path in paths:
            weight = self._calculate_path_weight(path)
            self.path_weights[tuple(path)] = weight
            total_weight += weight

        # Normalize weights
        for path in paths:
            self.path_weights[tuple(path)] /= total_weight

        # Install flows for each path with appropriate weights
        for path in paths:
            # Create match with probability
            match = self._create_weighted_match(src_mac, dst_mac, self.path_weights[tuple(path)])
            actions = self._get_path_actions(path)
            
            # Install flow entry on each switch in the path
            for i in range(len(path) - 1):
                if self.topology.nodes[path[i]].get('type') == 'switch':
                    datapath = self._get_datapath(path[i])
                    if datapath:
                        self.add_flow(
                            datapath=datapath,
                            priority=self.traffic_priorities.get((src_mac, dst_mac), 100),
                            match=match,
                            actions=[actions[i]]
                        )

        self.active_paths[(src_mac, dst_mac)] = paths
        self.logger.info(f"Implemented load balancing for {src_mac} -> {dst_mac} across {len(paths)} paths")

    def _calculate_path_weight(self, path):
        """
        Calculate weight for a path based on current load and path characteristics.
        """
        weight = 1.0
        for i in range(len(path) - 1):
            if self.topology.nodes[path[i]].get('type') == 'switch':
                # Consider link capacity and current load
                link = (path[i], path[i + 1])
                if link in self.link_stats:
                    stats = self.link_stats[link]
                    # Calculate link utilization
                    rx_bytes = stats.get('rx_bytes', 0)
                    tx_bytes = stats.get('tx_bytes', 0)
                    # Adjust weight based on utilization (lower utilization = higher weight)
                    utilization = (rx_bytes + tx_bytes) / (1024 * 1024)  # Convert to MB
                    weight *= (1.0 / (1.0 + utilization))
        return weight

    def _create_weighted_match(self, src_mac, dst_mac, weight):
        """
        Create a match with probability for load balancing.
        """
        parser = self.datapaths[list(self.datapaths.keys())[0]].ofproto_parser
        return parser.OFPMatch(
            eth_src=src_mac,
            eth_dst=dst_mac,
            # Add probability for load balancing
            metadata=hash(f"{src_mac}{dst_mac}") % 100 < (weight * 100)
        )

    def _get_path_actions(self, path):
        """
        Get actions for each hop in the path.
        """
        actions = []
        for i in range(len(path) - 1):
            if self.topology.nodes[path[i]].get('type') == 'switch':
                # Find the port that leads to the next hop
                port = self._get_port_to_next_hop(path[i], path[i + 1])
                if port:
                    parser = self.datapaths[path[i]].ofproto_parser
                    actions.append(parser.OFPActionOutput(port))
        return actions

    def _ensure_backup_paths(self, src_mac, dst_mac):
        """
        Ensure backup paths exist for critical flows.
        """
        # Get all possible paths
        paths = self.get_all_shortest_paths(src_mac, dst_mac, k=3)
        if len(paths) > 1:
            # Store backup paths
            self.backup_paths[(src_mac, dst_mac)] = paths[1:]
            self.logger.info(f"Stored {len(paths)-1} backup paths for critical flow {src_mac} -> {dst_mac}")
            
            # Pre-install backup paths with lower priority
            for path in paths[1:]:
                self.install_path_flows(
                    path=path,
                    src_mac=src_mac,
                    dst_mac=dst_mac,
                    priority=self.traffic_priorities.get((src_mac, dst_mac), 100) - 10
                )

    def _get_port_to_next_hop(self, current_switch, next_hop):
        """
        Get the port number that leads to the next hop.
        """
        for port, (peer_dpid, _) in self.switch_ports[current_switch].items():
            if peer_dpid == next_hop:
                return port
        return None

    def _get_datapath(self, dpid):
        """
        Get the datapath object for a switch.
        """
        return self.datapaths.get(dpid)

    def start_cli(self):
        """
        Start the CLI interface.
        """
        self.cli.start()
