# SDN Controller

A simplified Software-Defined Networking (SDN) controller implementation using the Ryu framework. This controller can configure OpenFlow switches to implement specific traffic engineering policies.

## Features

- Basic OpenFlow switch management
- MAC address learning
- Traffic engineering policy implementation
- Flow table management
- Packet handling and forwarding
- Network topology management and visualization
- Shortest path calculation
- Dynamic topology updates

## Requirements

- Python 3.7+
- Ryu framework
- Eventlet
- NetworkX
- Matplotlib

## Installation

1. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Starting the Controller

1. Start the controller:
```bash
ryu-manager sdn_controller.py
```

2. Connect your OpenFlow switches to the controller (typically on port 6653)

### Basic Operation

The controller will automatically:
- Learn MAC addresses
- Install default flow entries
- Handle packet-in events
- Implement traffic policies
- Maintain network topology
- Update topology on switch/port changes

### Topology Management

The controller maintains a graph representation of the network topology and provides several methods to interact with it:

```python
# Get the current network topology
topology = controller.get_topology()

# Visualize the topology and save to a file
controller.visualize_topology('network_topology.png')

# Calculate shortest path between two hosts
path = controller.get_shortest_path('00:00:00:00:00:01', '00:00:00:00:00:02')
```

The topology visualization includes:
- Switches (blue nodes)
- Hosts (green nodes)
- Connections between devices
- MAC addresses for hosts
- Switch IDs

### Implementing Traffic Policies

The controller provides several ways to implement traffic engineering policies:

#### 1. Basic Traffic Routing

```python
# Route traffic between two hosts through a specific port
actions = [parser.OFPActionOutput(port_number)]
controller.implement_traffic_policy(
    datapath=switch_datapath,
    src_ip="10.0.0.1",
    dst_ip="10.0.0.2",
    priority=100,
    actions=actions
)
```

#### 2. Load Balancing

```python
# Implement load balancing across multiple paths
controller.implement_load_balancing(
    src_mac='00:00:00:00:00:01',
    dst_mac='00:00:00:00:00:02',
    num_paths=3  # Use up to 3 paths
)
```

#### 3. QoS Policies

```python
# Implement QoS by setting DSCP values
actions = [
    parser.OFPActionSetField(ip_dscp=46),  # Expedited Forwarding
    parser.OFPActionOutput(port_number)
]
controller.implement_traffic_policy(
    datapath=switch_datapath,
    src_ip="10.0:0.1",
    dst_ip="10.0.0.2",
    priority=300,
    actions=actions
)
```

### Monitoring and Debugging

1. View switch connections:
```bash
ryu-manager --verbose sdn_controller.py
```

2. Check flow tables on switches:
```bash
ovs-ofctl dump-flows <switch-name>
```

3. Monitor packet statistics:
```bash
ovs-ofctl dump-flows <switch-name> -O OpenFlow13
```

4. View network topology:
```python
# Generate topology visualization
controller.visualize_topology()
```

### Path Computation and Installation

The controller provides comprehensive path computation and installation capabilities:

```python
# Compute and install the shortest path between two hosts
controller.compute_and_install_path(
    src_mac='00:00:00:00:00:01',
    dst_mac='00:00:00:00:00:02',
    priority=100
)

# Get k shortest paths between hosts
paths = controller.get_all_shortest_paths(
    src_mac='00:00:00:00:00:01',
    dst_mac='00:00:00:00:00:02',
    k=3  # Get 3 shortest paths
)

# Get metrics for a specific path
metrics = controller.get_path_metrics(path)
print(f"Path metrics: {metrics}")
```

Path computation features include:
- Shortest path calculation
- K-shortest paths computation
- Automatic flow entry installation
- Path metrics calculation
- Support for different routing priorities

### Flow Table Management

The controller provides comprehensive flow table management capabilities:

```python
# Add a basic flow entry
controller.add_flow(
    datapath=switch_datapath,
    priority=100,
    match=parser.OFPMatch(eth_dst='00:00:00:00:00:01'),
    actions=[parser.OFPActionOutput(port_number)],
    idle_timeout=60,  # Flow expires after 60 seconds of inactivity
    hard_timeout=300  # Flow expires after 300 seconds
)

# Add a QoS flow entry with rate limiting
controller.add_qos_flow(
    datapath=switch_datapath,
    match=parser.OFPMatch(eth_dst='00:00:00:00:00:01'),
    actions=[parser.OFPActionOutput(port_number)],
    priority=200,
    queue_id=1,
    max_rate=100  # 100 Mbps rate limit
)

# Modify an existing flow
controller.modify_flow(
    datapath=switch_datapath,
    match=parser.OFPMatch(eth_dst='00:00:00:00:00:01'),
    actions=[parser.OFPActionOutput(new_port)],
    priority=100
)

# Delete flows
controller.delete_flow(
    datapath=switch_datapath,
    match=parser.OFPMatch(eth_dst='00:00:00:00:00:01'),
    priority=100
)

# Get flow statistics
controller.get_flow_stats(switch_datapath)
```

Flow table features include:
- Flow entry addition with timeouts
- Flow modification
- Flow deletion
- Flow statistics collection
- QoS flow entries with rate limiting
- Priority-based flow management
- Automatic flow cleanup

### Link Failure Handling and Route Reconfiguration

The controller provides comprehensive link failure detection and route reconfiguration capabilities:

```python
# The controller automatically handles:
# 1. Link failure detection
# 2. Path reconfiguration
# 3. Link recovery
# 4. Backup path preparation
# 5. Optimal path restoration
```

Failure handling features include:
- Automatic link failure detection
- Immediate path reconfiguration
- Backup path preparation
- Link degradation monitoring
- Automatic path restoration on recovery
- Error rate monitoring
- Port statistics collection

The controller implements a three-phase approach to failure handling:

1. **Detection Phase**:
   - Monitors port status changes
   - Tracks link statistics
   - Detects link degradation
   - Identifies failed links

2. **Recovery Phase**:
   - Finds alternative paths
   - Installs backup routes
   - Updates flow tables
   - Maintains path information

3. **Restoration Phase**:
   - Monitors link recovery
   - Restores optimal paths
   - Removes backup routes
   - Updates topology

Example failure scenarios handled:
- Complete link failures
- Link degradation
- Port modifications
- Switch disconnections
- Path unavailability

## Common Use Cases

1. **Traffic Isolation**
   - Create separate paths for different types of traffic
   - Implement VLAN-based segmentation
   - Control access between network segments

2. **Load Balancing**
   - Distribute traffic across multiple paths
   - Implement failover mechanisms
   - Optimize network resource utilization

3. **QoS Management**
   - Prioritize critical traffic
   - Implement bandwidth limits
   - Set DSCP values for different traffic types

4. **Topology Management**
   - Monitor network structure
   - Calculate optimal paths
   - Visualize network layout
   - Track device connections

## Notes

- The controller uses OpenFlow 1.3 protocol
- Default flow entries are installed with priority 0
- Learned flows are installed with priority 1
- Custom traffic policies can have higher priorities
- Always test policies in a controlled environment first
- Monitor network performance after implementing new policies
- Topology visualization is automatically updated when network changes occur

### Routing Policies

The controller implements several advanced routing policies:

#### 1. Load Balancing

```python
# Implement load balancing across multiple paths
controller.implement_load_balancing(
    src_mac='00:00:00:00:00:01',
    dst_mac='00:00:00:00:00:02',
    num_paths=3  # Use up to 3 paths
)
```

Load balancing features:
- Dynamic path weight calculation
- Link utilization monitoring
- Multiple path support
- Automatic traffic distribution
- Path performance tracking

#### 2. Traffic Prioritization

```python
# Set traffic priority
controller.set_traffic_priority(
    src_mac='00:00:00:00:00:01',
    dst_mac='00:00:00:00:00:02',
    priority=200  # Higher priority
)

# Implement priority-based routing
controller.implement_traffic_policy(
    datapath=switch_datapath,
    src_ip='10.0.0.1',
    dst_ip='10.0.0.2',
    priority=200,
    actions=[parser.OFPActionOutput(port_number)]
)
```

Priority features:
- Multiple priority levels
- QoS marking (DSCP)
- Priority-based path selection
- Bandwidth allocation
- Traffic class support

#### 3. Critical Flow Management

```python
# Mark a flow as critical
controller.set_critical_flow(
    src_mac='00:00:00:00:00:01',
    dst_mac='00:00:00:00:00:02',
    is_critical=True
)
```

Critical flow features:
- Automatic backup path preparation
- Pre-installed backup routes
- Fast failover support
- Path redundancy
- Priority preservation

### Policy Implementation Examples

1. **Load Balancing with Priority**:
```python
# Set high priority
controller.set_traffic_priority('00:00:00:00:00:01', '00:00:00:00:00:02', 200)

# Implement load balancing
controller.implement_load_balancing('00:00:00:00:00:01', '00:00:00:00:00:02', num_paths=3)
```

2. **Critical Flow with Backup**:
```python
# Mark as critical flow
controller.set_critical_flow('00:00:00:00:00:01', '00:00:00:00:00:02', True)

# Set high priority
controller.set_traffic_priority('00:00:00:00:00:01', '00:00:00:00:00:02', 300)
```

3. **QoS with Load Balancing**:
```python
# Implement QoS policy with load balancing
controller.implement_traffic_policy(
    datapath=switch_datapath,
    src_ip='10.0.0.1',
    dst_ip='10.0.0.2',
    priority=200,
    actions=[
        parser.OFPActionSetField(ip_dscp=46),  # Expedited Forwarding
        parser.OFPActionOutput(port_number)
    ]
)
```

### Network Visualization

The controller provides comprehensive network visualization capabilities through the `NetworkVisualizer` class:

```python
# Generate all network visualizations
controller.visualize_network()
```

This will create three visualization files:
1. `network_topology.png`: Shows the current network topology
2. `network_flows.png`: Displays active flows and critical paths
3. `link_utilization.png`: Visualizes link utilization statistics

#### 1. Topology Visualization

The topology visualization shows:
- Switches (light blue nodes)
- Hosts (light green nodes)
- Physical connections (gray lines)
- MAC addresses for hosts
- Switch IDs

```python
# Generate only topology visualization
controller.visualizer.visualize_topology('custom_topology.png')
```

#### 2. Flow Visualization

The flow visualization displays:
- Active flows (red lines)
- Critical flows (purple dashed lines)
- Backup paths (orange dashed lines)
- Flow source and destination
- Path information

```python
# Generate only flow visualization
controller.visualizer.visualize_flows('custom_flows.png')
```

#### 3. Link Utilization Visualization

The link utilization visualization shows:
- Link utilization through color intensity
- Link capacity through line width
- Utilization scale (colorbar)
- Current traffic load
- Bottleneck identification

```python
# Generate only link utilization visualization
controller.visualizer.visualize_link_utilization('custom_utilization.png')
```

Visualization features:
- Interactive color schemes
- Automatic layout optimization
- Clear labeling and legends
- High-resolution output
- Customizable file names
- Comprehensive statistics

### Command Line Interface (CLI)

The controller provides a comprehensive CLI for network management and simulation:

```python
# Start the CLI
controller.start_cli()
```

#### Available Commands

1. **Node Management**:
```bash
# Add a switch
add_node switch s1

# Add a host
add_node host h1

# Remove a node
remove_node s1
```

2. **Link Management**:
```bash
# Add a link between nodes
add_link s1 s2

# Remove a link
remove_link s1 s2
```

3. **Flow Management**:
```bash
# Inject a traffic flow
inject_flow 00:00:00:00:00:01 00:00:00:00:00:02 200
```

4. **Failure Simulation**:
```bash
# Simulate a link failure
simulate_failure s1 s2
```

5. **Network Information**:
```bash
# Show current topology
show_topology

# Show active flows
show_flows

# Show link statistics
show_stats

# Query routing path
query_route 00:00:00:00:00:01 00:00:00:00:00:02
```

#### CLI Features

1. **Node Management**:
   - Add/remove switches and hosts
   - Automatic MAC address generation for hosts
   - Topology validation
   - Visual feedback

2. **Link Management**:
   - Add/remove links between nodes
   - Link existence validation
   - Automatic topology updates
   - Visualization updates

3. **Flow Management**:
   - Traffic flow injection
   - Priority-based routing
   - Load balancing support
   - Flow path visualization

4. **Failure Simulation**:
   - Link failure simulation
   - Automatic path reconfiguration
   - Backup path activation
   - Failure recovery testing

5. **Network Information**:
   - Real-time topology display
   - Active flow monitoring
   - Link statistics tracking
   - Path querying
   - Visual feedback

#### Example Usage

1. **Setting up a simple network**:
```bash
# Add switches
add_node switch s1
add_node switch s2
add_node switch s3

# Add hosts
add_node host h1
add_node host h2

# Create links
add_link s1 s2
add_link s2 s3
add_link s1 h1
add_link s3 h2

# Show topology
show_topology
```

2. **Injecting and monitoring flows**:
```bash
# Inject a high-priority flow
inject_flow 00:00:00:00:00:01 00:00:00:00:00:02 300

# Show active flows
show_flows

# Query the route
query_route 00:00:00:00:00:01 00:00:00:00:00:02
```

3. **Testing failure scenarios**:
```bash
# Simulate a link failure
simulate_failure s1 s2

# Check path reconfiguration
show_flows

# Monitor link statistics
show_stats
```

The CLI provides an interactive way to:
- Manage network topology
- Test routing policies
- Simulate failures
- Monitor network state
- Debug issues
- Visualize changes