// Message routing logic

use std::collections::HashMap;

/// Routing table entry
#[derive(Debug, Clone)]
pub struct RouteEntry {
    /// Destination
    pub destination: String,
    /// Next hop
    pub next_hop: String,
    /// Hop count
    pub hop_count: u8,
    /// Metric (lower is better)
    pub metric: u32,
    /// Last updated timestamp
    pub last_updated: u64,
}

/// Simple routing table
#[derive(Debug, Clone, Default)]
pub struct RoutingTable {
    routes: HashMap<String, RouteEntry>,
}

impl RoutingTable {
    /// Create new routing table
    pub fn new() -> Self {
        Self {
            routes: HashMap::new(),
        }
    }

    /// Add or update route
    pub fn update(&mut self, entry: RouteEntry) {
        // Only update if metric is better or entry is newer
        if let Some(existing) = self.routes.get(&entry.destination) {
            if entry.metric >= existing.metric && entry.hop_count >= existing.hop_count {
                return;
            }
        }

        self.routes.insert(entry.destination.clone(), entry);
    }

    /// Get route to destination
    pub fn get_route(&self, destination: &str) -> Option<&RouteEntry> {
        self.routes.get(destination)
    }

    /// Get next hop for destination
    pub fn get_next_hop(&self, destination: &str) -> Option<&str> {
        self.routes.get(destination).map(|e| e.next_hop.as_str())
    }

    /// Remove route
    pub fn remove(&mut self, destination: &str) {
        self.routes.remove(destination);
    }

    /// Clean up stale routes
    pub fn cleanup(&mut self, max_age_secs: u64) {
        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_secs();

        self.routes.retain(|_, entry| {
            now - entry.last_updated < max_age_secs
        });
    }

    /// Get all routes
    pub fn get_routes(&self) -> Vec<&RouteEntry> {
        self.routes.values().collect()
    }

    /// Get route count
    pub fn len(&self) -> usize {
        self.routes.len()
    }

    /// Check if empty
    pub fn is_empty(&self) -> bool {
        self.routes.is_empty()
    }
}

/// Flooding router (for broadcasts)
pub struct FloodingRouter;

impl FloodingRouter {
    /// Check if we should forward a broadcast message
    pub fn should_forward(message_id: &str, seen_messages: &mut std::collections::HashSet<String>) -> bool {
        seen_messages.insert(message_id.to_string())
    }
}

/// Distance vector router
pub struct DistanceVectorRouter {
    table: RoutingTable,
    node_id: String,
}

impl DistanceVectorRouter {
    /// Create new distance vector router
    pub fn new(node_id: String) -> Self {
        Self {
            table: RoutingTable::new(),
            node_id,
        }
    }

    /// Process routing update from neighbor
    pub fn process_update(&mut self, from: &str, routes: Vec<RouteEntry>) {
        for route in routes {
            // Don't route to ourselves
            if route.destination == self.node_id {
                continue;
            }

            // Increment hop count
            let new_entry = RouteEntry {
                destination: route.destination,
                next_hop: from.to_string(),
                hop_count: route.hop_count.saturating_add(1),
                metric: route.metric + 1,
                last_updated: std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH)
                    .unwrap()
                    .as_secs(),
            };

            self.table.update(new_entry);
        }
    }

    /// Get routing table for announcement
    pub fn get_announcement(&self) -> Vec<RouteEntry> {
        self.table.get_routes().into_iter().cloned().collect()
    }

    /// Get route
    pub fn get_route(&self, destination: &str) -> Option<&RouteEntry> {
        self.table.get_route(destination)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_routing_table() {
        let mut table = RoutingTable::new();

        let entry = RouteEntry {
            destination: "node2".to_string(),
            next_hop: "node1".to_string(),
            hop_count: 1,
            metric: 1,
            last_updated: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_secs(),
        };

        table.update(entry);

        assert_eq!(table.len(), 1);
        assert_eq!(table.get_next_hop("node2"), Some("node1"));
    }

    #[test]
    fn test_distance_vector_router() {
        let mut router = DistanceVectorRouter::new("node1".to_string());

        // Simulate receiving routes from neighbor
        let neighbor_routes = vec![
            RouteEntry {
                destination: "node3".to_string(),
                next_hop: "node2".to_string(),
                hop_count: 1,
                metric: 1,
                last_updated: 0,
            }
        ];

        router.process_update("node2", neighbor_routes);

        let route = router.get_route("node3");
        assert!(route.is_some());
        assert_eq!(route.unwrap().hop_count, 2);
        assert_eq!(route.unwrap().next_hop, "node2");
    }
}
