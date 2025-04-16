# Distributed Password Cracking with ERPCT

ERPCT provides a powerful distributed password cracking capability, allowing you to harness multiple machines to significantly speed up the password discovery process.

## Overview

The distributed cracking architecture consists of:

1. **Controller Node**: Coordinates the attack and distributes work
2. **Worker Nodes**: Perform the actual password testing
3. **Task Distribution System**: Efficiently assigns work to available nodes
4. **Results Aggregation**: Collects and combines results from all nodes

## System Requirements

For optimal distributed cracking performance:

### Controller Node
- Minimum 4GB RAM
- High-speed network connection
- Stable, always-on system

### Worker Nodes
- Minimum 2GB RAM per node
- Network connectivity to the controller
- ERPCT installed and configured

## Basic Setup

### Starting the Controller

```bash
# Start the controller node
erpct --distributed-controller --listen 0.0.0.0:5000 \
      --target 192.168.1.100 --protocol ssh \
      --username admin --wordlist large_wordlist.txt \
      --threads 10
```

### Starting Worker Nodes

```bash
# Start worker nodes
erpct --distributed-worker --controller 192.168.1.5:5000 --worker-name worker1 --threads 8
```

You can start as many worker nodes as needed across different machines.

## Advanced Configuration

### Controller Configuration

```bash
# Advanced controller configuration
erpct --distributed-controller \
      --listen 0.0.0.0:5000 \
      --target 192.168.1.100 \
      --protocol ssh \
      --username admin \
      --wordlist large_wordlist.txt \
      --threads 10 \
      --chunk-size 1000 \
      --worker-timeout 120 \
      --persistence sqlite:///distributed.db \
      --require-auth \
      --auth-token "YOUR_SECRET_TOKEN" \
      --progress-update 5
```

Configuration options:

| Option | Description | Default |
|--------|-------------|---------|
| `--listen` | IP and port to listen on | 0.0.0.0:5000 |
| `--chunk-size` | Number of passwords per work unit | 500 |
| `--worker-timeout` | Worker node timeout in seconds | 60 |
| `--persistence` | Database for saving state | memory |
| `--require-auth` | Require authentication from workers | False |
| `--auth-token` | Authentication token for workers | None |
| `--progress-update` | Progress update interval (seconds) | 10 |

### Worker Configuration

```bash
# Advanced worker configuration
erpct --distributed-worker \
      --controller 192.168.1.5:5000 \
      --worker-name worker2 \
      --threads 8 \
      --max-chunks 10 \
      --reconnect-delay 5 \
      --auth-token "YOUR_SECRET_TOKEN" \
      --log-file worker.log
```

Configuration options:

| Option | Description | Default |
|--------|-------------|---------|
| `--controller` | Controller IP and port | None (required) |
| `--worker-name` | Unique worker identifier | hostname |
| `--threads` | Number of concurrent threads | 4 |
| `--max-chunks` | Maximum chunks to process at once | 5 |
| `--reconnect-delay` | Seconds to wait before reconnecting | 5 |
| `--auth-token` | Authentication token | None |
| `--log-file` | Worker log file | None |

## Security Considerations

When using distributed cracking:

1. **Network Security**: Traffic between nodes is sensitive
   ```bash
   # Enable encryption for communication
   erpct --distributed-controller --listen 0.0.0.0:5000 --use-tls --cert cert.pem --key key.pem
   
   # Worker with TLS enabled
   erpct --distributed-worker --controller 192.168.1.5:5000 --use-tls --verify-cert
   ```

2. **Authentication**: Always use authentication in production
   ```bash
   # Generate a secure token
   TOKEN=$(openssl rand -hex 32)
   echo "Use this token: $TOKEN"
   
   # Use the token with controllers and workers
   erpct --distributed-controller --require-auth --auth-token "$TOKEN"
   erpct --distributed-worker --auth-token "$TOKEN"
   ```

3. **Access Control**: Restrict access to the controller
   ```bash
   # Allow only specific IPs
   erpct --distributed-controller --allowed-ips 192.168.1.0/24,10.0.0.5
   ```

## Advanced Features

### Checkpoint and Resume

The distributed system can save its state and resume from interruptions:

```bash
# Enable checkpointing on the controller
erpct --distributed-controller --checkpoint-interval 300 --checkpoint-file attack.checkpoint

# Resume from a checkpoint
erpct --distributed-controller --resume-checkpoint attack.checkpoint
```

### Heterogeneous Workers

Workers can have different capabilities:

```bash
# High-performance worker
erpct --distributed-worker --controller 192.168.1.5:5000 --worker-name fast-worker --threads 16 --priority high

# Limited resource worker
erpct --distributed-worker --controller 192.168.1.5:5000 --worker-name slow-worker --threads 2 --priority low
```

### Protocol-Specific Distribution

Optimize distribution for specific protocols:

```bash
# HTTP form optimized distribution
erpct --distributed-controller --protocol http-form --adaptive-chunk-size --http-optimize
```

### Wordlist Segmentation

Split wordlists for more efficient distribution:

```bash
# Split wordlist by character distribution
erpct --distributed-controller --wordlist-segmentation balanced
```

## Monitoring and Management

### Web Interface

The controller provides a web interface for monitoring:

```bash
# Enable web interface
erpct --distributed-controller --web-interface --web-port 8080
```

Access the interface at http://controller-ip:8080/

### Status Commands

Monitor distributed attack progress:

```bash
# Get distributed attack status
erpct --distributed-status --controller 192.168.1.5:5000

# Get worker details
erpct --distributed-workers --controller 192.168.1.5:5000
```

### Worker Management

Manage worker nodes:

```bash
# Pause all workers
erpct --distributed-control --controller 192.168.1.5:5000 --pause-all

# Resume all workers
erpct --distributed-control --controller 192.168.1.5:5000 --resume-all

# Add priority target
erpct --distributed-control --controller 192.168.1.5:5000 --priority-password "likely_password"
```

## Architecture Details

### Work Distribution Algorithm

ERPCT uses a dynamic work distribution algorithm:

1. **Initial Distribution**: Equal-sized chunks to all workers
2. **Performance Tracking**: Monitors worker completion rates
3. **Adaptive Sizing**: Adjusts chunk sizes based on worker performance
4. **Load Balancing**: Distributes work to minimize idle time
5. **Prioritization**: Handles high-probability candidates first

### Communication Protocol

The distributed system uses a RESTful API with the following endpoints:

- `GET /api/work`: Workers request chunks of work
- `POST /api/result`: Workers submit results
- `GET /api/status`: Get overall attack status
- `POST /api/register`: Register a new worker
- `POST /api/heartbeat`: Worker reports it's still active

### Data Formats

Work chunks are distributed in JSON format:

```json
{
  "chunk_id": 123,
  "target": "192.168.1.100",
  "protocol": "ssh",
  "port": 22,
  "username": "admin",
  "passwords": ["password1", "password2", "..."],
  "options": {
    "timeout": 10,
    "banner_delay": 1
  }
}
```

## Performance Considerations

Optimizing distributed cracking performance:

1. **Network Bandwidth**: Ensure sufficient bandwidth between nodes
2. **Chunk Size**: Adjust based on network conditions and protocol
   - Small chunks (100-500): High network overhead, good load balancing
   - Large chunks (1000+): Lower overhead, less balanced
   
3. **Worker Resources**: Match thread count to available CPU cores
4. **Protocol Efficiency**: Some protocols benefit from different distribution strategies

## Example Deployments

### Small Office Deployment

```
Controller Node (Main Workstation)
↓
├── Worker 1 (Desktop PC)
├── Worker 2 (Laptop)
└── Worker 3 (Test Server)
```

### Cloud-Based Deployment

```
Controller Node (Instance with persistent storage)
↓
├── Worker Pool (Auto-scaling worker group)
│   ├── Worker 1
│   ├── Worker 2
│   └── Worker N (scales based on workload)
```

### High-Security Deployment

```
Controller Node (Behind firewall)
↓
├── Worker Management Proxy (DMZ)
    ↓
    ├── Worker 1 (Isolated network)
    ├── Worker 2 (Isolated network)
    └── Worker 3 (Isolated network)
```

## Troubleshooting

Common issues and solutions:

- **Workers not connecting**: Check network connectivity and authentication settings
- **Slow performance**: Adjust chunk size and thread count
- **High resource usage**: Reduce thread count or increase worker node resources
- **Lost connections**: Check network stability and increase timeout values

## Conclusion

Distributed password cracking with ERPCT provides a powerful way to scale your security testing capabilities. By properly configuring and tuning the system, you can achieve significantly faster results than with a single machine.
