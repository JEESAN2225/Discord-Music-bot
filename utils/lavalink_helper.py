"""
Lavalink connection helper with fallback servers
"""

import wavelink
import asyncio
import logging
from typing import List, Dict, Optional
from config.config import config

logger = logging.getLogger(__name__)

# Fallback Lavalink servers (public nodes)
FALLBACK_NODES = [
    {
        'host': 'lavalink.pericsq.ro',
        'port': 4499,
        'password': 'plamea',
        'secure': False,
        'name': 'fallback-1'
    },
    {
        'host': 'lavalink-v3.mizudev.tech',
        'port': 6969,
        'password': 'mizudev',
        'secure': False,
        'name': 'fallback-2'
    },
    {
        'host': 'node1.lavalink.rocks',
        'port': 2333,
        'password': 'lavalink.rocks',
        'secure': False,
        'name': 'fallback-3'
    }
]

async def connect_lavalink(bot) -> bool:
    """
    Connect to Lavalink servers with fallback support (Wavelink v3 API)
    Returns True if at least one connection is successful
    """
    
    # Try primary server first
    primary_node_config = {
        'host': config.LAVALINK_HOST,
        'port': config.LAVALINK_PORT,
        'password': config.LAVALINK_PASSWORD,
        'secure': config.LAVALINK_SECURE,
        'name': config.LAVALINK_NAME
    }

    nodes_to_try = [primary_node_config] + FALLBACK_NODES
    
    # Create list of nodes that successfully connect
    nodes_to_connect = []

    for node_config in nodes_to_try:
        try:
            logger.info(f"Attempting to connect to Lavalink node: {node_config['host']}:{node_config['port']}")

            # Wavelink v3 Node constructor expects uri and password
            protocol = 'https' if node_config.get('secure', False) else 'http'
            uri = f"{protocol}://{node_config['host']}:{node_config['port']}"
            
            node = wavelink.Node(
                uri=uri,
                password=node_config['password'],
                identifier=node_config.get('name', f"{node_config['host']}:{node_config['port']}"),
                client=bot
            )
            
            nodes_to_connect.append(node)
            logger.info(f"✅ Successfully created node for {node_config['host']}:{node_config['port']}")
            
            # For first working node, we can break (or collect all for redundancy)
            if node_config == primary_node_config:
                break

        except Exception as e:
            logger.warning(f"❌ Failed to create node for {node_config['host']}:{node_config['port']}: {e}")
            continue
    
    if nodes_to_connect:
        try:
            # Connect all nodes to the Pool
            await asyncio.wait_for(
                wavelink.Pool.connect(nodes=nodes_to_connect, client=bot),
                timeout=30.0
            )
            logger.info(f"🎵 Lavalink connected successfully ({len(nodes_to_connect)} nodes)")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect nodes to Pool: {e}")
    
    logger.error("❌ Failed to connect to any Lavalink servers")
    return False

def is_lavalink_available() -> bool:
    """Check if Lavalink is available"""
    try:
        # Wavelink v3 API - Pool.nodes is a list
        return len(wavelink.Pool.nodes) > 0
    except:
        return False

def get_node_status() -> Dict:
    """Get status of all connected nodes"""
    try:
        # Wavelink v3 API - Pool.nodes is a list
        nodes = wavelink.Pool.nodes
        if not nodes:
            return {"status": "disconnected", "nodes": 0}
        
        connected_nodes = [node for node in nodes if node.is_connected()]
        return {
            "status": "connected" if connected_nodes else "connecting",
            "nodes": len(connected_nodes),
            "total_nodes": len(nodes)
        }
    except:
        return {"status": "error", "nodes": 0}
