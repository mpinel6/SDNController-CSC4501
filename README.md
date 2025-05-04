# SDN Controller

A simplified Software-Defined Networking (SDN) controller implementation using the Ryu framework for configuring OpenFlow switches and implementing traffic engineering policies.

## Quick Start

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Start the controller:
```bash
ryu-manager sdn_controller.py
```

3. Start the CLI interface:
```python
from sdn_controller import SDNController
controller = SDNController()
controller.start_cli()
```

## Basic CLI Commands

```bash
# Add nodes
add_node switch s1
add_node host h1

# Create links
add_link s1 s2

# Inject traffic
inject_flow 00:00:00:00:00:01 00:00:00:00:00:02 200

# View network
show_topology
show_flows
show_stats

# Simulate failures
simulate_failure s1 s2
```

## Requirements

- Python 3.7+
- Ryu framework
- NetworkX
- Matplotlib

## Features

- OpenFlow switch management
- Traffic engineering
- Load balancing
- Link failure handling
- Network visualization
- Interactive CLI