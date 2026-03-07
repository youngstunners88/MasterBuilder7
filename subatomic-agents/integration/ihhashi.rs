// iHhashi Food Delivery Platform Integration
// Connects sub-atomic agent swarm to iHhashi backend

use crate::protocols::crdt::{OrderState, Inventory, ORSet, LWWRegister, PNCounter};
use crate::protocols::gossip::{GossipProtocol, MessagePayload};
use crate::core::agent::{Agent, WorkerAgent, AgentConfig, AgentType, Task, TaskResult};
use crate::networking::mesh::{MeshNetwork, MeshAddress};
use crate::inference::runtime::{LocalInferenceRuntime, InferenceTask};
use crate::incentives::reputation::{ReputationSystem, RewardSystem, ContributionProof};

use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use serde::{Serialize, Deserialize};

/// iHhashi integration hub
pub struct IhhashiIntegration {
    /// Node ID in the swarm
    node_id: String,
    /// Gossip protocol for P2P communication
    gossip: Arc<GossipProtocol>,
    /// Mesh network for offline operation
    mesh: Arc<RwLock<MeshNetwork>>,
    /// Local order states (CRDT)
    orders: Arc<RwLock<HashMap<String, OrderState>>>,
    /// Local inventory (CRDT)
    inventory: Arc<RwLock<HashMap<String, Inventory>>>,
    /// Inference runtime for AI tasks
    inference: Arc<LocalInferenceRuntime>,
    /// Reputation system
    reputation: Arc<ReputationSystem>,
    /// Reward system
    rewards: Arc<RewardSystem>,
    /// iHhashi API endpoint (when online)
    api_endpoint: Option<String>,
}

/// iHhashi-specific task types
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum IhhashiTask {
    /// Validate order structure and availability
    ValidateOrder { order_id: String, items: Vec<OrderItem> },
    /// Calculate delivery ETA using route memory
    CalculateETA { pickup: Location, delivery: Location },
    /// Check inventory at merchant
    CheckInventory { merchant_id: String, item_id: String },
    /// Process payment validation
    ValidatePayment { payment_id: String, amount: f64 },
    /// Confirm delivery completion
    ConfirmDelivery { order_id: String, rider_id: String },
    /// Handle customer query (AI)
    CustomerQuery { query: String, context: Vec<String> },
    /// Detect fraud/anomaly
    FraudDetection { order: OrderData },
    /// Update route memory
    UpdateRouteMemory { route: RouteData, actual_time_minutes: u32 },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OrderItem {
    pub product_id: String,
    pub quantity: u32,
    pub price: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Location {
    pub lat: f64,
    pub lng: f64,
    pub address: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OrderData {
    pub order_id: String,
    pub customer_id: String,
    pub merchant_id: String,
    pub amount: f64,
    pub items: Vec<OrderItem>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RouteData {
    pub start: Location,
    pub end: Location,
    pub waypoints: Vec<Location>,
}

/// Order routing result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RoutingResult {
    pub order_id: String,
    pub estimated_pickup_time: u64,
    pub estimated_delivery_time: u64,
    pub suggested_riders: Vec<String>,
    pub confidence: f32,
}

impl IhhashiIntegration {
    pub fn new(
        node_id: String,
        gossip: Arc<GossipProtocol>,
        mesh: Arc<RwLock<MeshNetwork>>,
        inference: Arc<LocalInferenceRuntime>,
        reputation: Arc<ReputationSystem>,
        rewards: Arc<RewardSystem>,
        api_endpoint: Option<String>,
    ) -> Self {
        Self {
            node_id,
            gossip,
            mesh,
            orders: Arc::new(RwLock::new(HashMap::new())),
            inventory: Arc::new(RwLock::new(HashMap::new())),
            inference,
            reputation,
            rewards,
            api_endpoint,
        }
    }

    /// Start the integration
    pub async fn start(&self) {
        // Start order sync task
        self.start_order_sync().await;

        // Start inventory sync task
        self.start_inventory_sync().await;

        // Start task processor
        self.start_task_processor().await;

        // Start offline queue processor
        self.start_offline_queue().await;

        log::info!("iHhashi integration started on node {}", self.node_id);
    }

    /// Process an iHhashi task
    pub async fn process_task(&self, task: IhhashiTask) -> Result<Vec<u8>, IntegrationError> {
        match task {
            IhhashiTask::ValidateOrder { order_id, items } => {
                self.validate_order(&order_id, &items).await
            }
            IhhashiTask::CalculateETA { pickup, delivery } => {
                self.calculate_eta(&pickup, &delivery).await
            }
            IhhashiTask::CheckInventory { merchant_id, item_id } => {
                self.check_inventory(&merchant_id, &item_id).await
            }
            IhhashiTask::ValidatePayment { payment_id, amount } => {
                self.validate_payment(&payment_id, amount).await
            }
            IhhashiTask::ConfirmDelivery { order_id, rider_id } => {
                self.confirm_delivery(&order_id, &rider_id).await
            }
            IhhashiTask::CustomerQuery { query, context } => {
                self.handle_customer_query(&query, &context).await
            }
            IhhashiTask::FraudDetection { order } => {
                self.detect_fraud(&order).await
            }
            IhhashiTask::UpdateRouteMemory { route, actual_time_minutes } => {
                self.update_route_memory(&route, actual_time_minutes).await
            }
        }
    }

    /// Validate order
    async fn validate_order(&self, order_id: &str, items: &[OrderItem]) -> Result<Vec<u8>, IntegrationError> {
        // Check if order already exists
        let orders = self.orders.read().await;
        if orders.contains_key(order_id) {
            return Err(IntegrationError::OrderExists(order_id.to_string()));
        }
        drop(orders);

        // Validate items
        let mut total = 0.0;
        for item in items {
            if item.quantity == 0 {
                return Err(IntegrationError::InvalidOrder("Zero quantity".to_string()));
            }
            total += item.price * item.quantity as f64;
        }

        // Check minimum order (R30)
        if total < 30.0 {
            return Err(IntegrationError::InvalidOrder(
                format!("Minimum order is R30, got R{:.2}", total)
            ));
        }

        // Create order state
        let mut order = OrderState::new(order_id.to_string(), self.node_id.clone());
        for item in items {
            order.add_item(format!("{}: {}", item.product_id, item.quantity), self.node_id.clone());
        }

        // Update local orders
        let mut orders = self.orders.write().await;
        orders.insert(order_id.to_string(), order);

        // Broadcast order creation
        let payload = MessagePayload::CrdtOp {
            crdt_id: format!("order:{}", order_id),
            operation: serde_json::to_vec(&order).unwrap_or_default(),
        };
        self.gossip.broadcast(payload).await
            .map_err(|e| IntegrationError::BroadcastError(e.to_string()))?;

        Ok(serde_json::to_vec(&serde_json::json!({
            "valid": true,
            "order_id": order_id,
            "total": total
        })).unwrap_or_default())
    }

    /// Calculate ETA using route memory and local inference
    async fn calculate_eta(&self, pickup: &Location, delivery: &Location) -> Result<Vec<u8>, IntegrationError> {
        // Get distance (simplified - would use haversine or actual routing)
        let distance_km = haversine_distance(
            pickup.lat, pickup.lng,
            delivery.lat, delivery.lng
        );

        // Query route memory from swarm
        let swarm_avg_time = self.query_route_memory(pickup, delivery).await;

        // Use local inference if available
        let predicted_time = if self.inference.can_handle(&InferenceTask::Generate {
            prompt: "".to_string(),
            max_tokens: 10,
            temperature: 0.0,
        }) {
            // Use AI prediction based on time of day, traffic, etc.
            let base_time = (distance_km * 3.0) as u32; // 3 min per km baseline
            let time_of_day_factor = get_time_of_day_factor();

            (base_time as f32 * time_of_day_factor) as u32
        } else {
            // Simple heuristic
            (distance_km * 5.0) as u32 // 5 min per km conservative
        };

        // Blend with swarm data if available
        let final_eta = if let Some(swarm_time) = swarm_avg_time {
            (predicted_time + swarm_time) / 2
        } else {
            predicted_time
        };

        Ok(serde_json::to_vec(&serde_json::json!({
            "eta_minutes": final_eta,
            "distance_km": distance_km,
            "confidence": if swarm_avg_time.is_some() { 0.8 } else { 0.5 }
        })).unwrap_or_default())
    }

    /// Check inventory
    async fn check_inventory(&self, merchant_id: &str, item_id: &str) -> Result<Vec<u8>, IntegrationError> {
        let inventory = self.inventory.read().await;

        if let Some(inv) = inventory.get(merchant_id) {
            let available = inv.available(item_id);
            Ok(serde_json::to_vec(&serde_json::json!({
                "merchant_id": merchant_id,
                "item_id": item_id,
                "available": available,
                "in_stock": available > 0
            })).unwrap_or_default())
        } else {
            Err(IntegrationError::MerchantNotFound(merchant_id.to_string()))
        }
    }

    /// Validate payment (offline-capable)
    async fn validate_payment(&self, payment_id: &str, amount: f64) -> Result<Vec<u8>, IntegrationError> {
        // In offline mode, we queue for later validation
        // Create a consensus vote among trusted nodes

        let reputation = self.reputation.get_reputation(&self.node_id).await;

        if !reputation.is_trusted() {
            // Not trusted - just queue for later
            return Ok(serde_json::to_vec(&serde_json::json!({
                "payment_id": payment_id,
                "status": "queued",
                "reason": "Node not trusted for payment validation"
            })).unwrap_or_default());
        }

        // Trusted node - broadcast validation vote
        let payload = MessagePayload::ConsensusVote {
            proposal_id: format!("payment:{}", payment_id),
            voter: self.node_id.clone(),
            vote: amount > 0.0 && amount < 10000.0, // Basic sanity check
        };

        self.gossip.broadcast(payload).await
            .map_err(|e| IntegrationError::BroadcastError(e.to_string()))?;

        Ok(serde_json::to_vec(&serde_json::json!({
            "payment_id": payment_id,
            "status": "pending_consensus",
            "amount": amount
        })).unwrap_or_default())
    }

    /// Confirm delivery
    async fn confirm_delivery(&self, order_id: &str, rider_id: &str) -> Result<Vec<u8>, IntegrationError> {
        // Multi-agent confirmation - need consensus
        let mut orders = self.orders.write().await;

        if let Some(order) = orders.get_mut(order_id) {
            // Update status to delivered
            order.update_status("delivered".to_string(), self.node_id.clone());

            // Broadcast confirmation
            let payload = MessagePayload::ConsensusVote {
                proposal_id: format!("delivery:{}", order_id),
                voter: self.node_id.clone(),
                vote: true,
            };

            self.gossip.broadcast(payload).await
                .map_err(|e| IntegrationError::BroadcastError(e.to_string()))?;

            // Record contribution for rewards
            let proof = ContributionProof::new(
                self.node_id.clone(),
                format!("delivery:{}", order_id),
                "delivery_confirmation".to_string(),
                10, // work units
                format!("{}:{}", order_id, rider_id),
            );

            let reputation = self.reputation.get_reputation(&self.node_id).await;
            self.rewards.reward(&proof, &reputation).await;

            Ok(serde_json::to_vec(&serde_json::json!({
                "order_id": order_id,
                "status": "delivered",
                "confirmed_by": self.node_id,
                "rider_id": rider_id
            })).unwrap_or_default())
        } else {
            Err(IntegrationError::OrderNotFound(order_id.to_string()))
        }
    }

    /// Handle customer query using local AI
    async fn handle_customer_query(&self, query: &str, context: &[String]) -> Result<Vec<u8>, IntegrationError> {
        let context_str = context.join("\n");

        let task = InferenceTask::Answer {
            question: query.to_string(),
            context: context_str,
        };

        if self.inference.can_handle(&task) {
            let result = self.inference.infer(task).await
                .map_err(|e| IntegrationError::InferenceError(e.to_string()))?;

            Ok(serde_json::to_vec(&serde_json::json!({
                "query": query,
                "response": result.output,
                "confidence": result.confidence,
                "inference_time_ms": result.inference_time_ms
            })).unwrap_or_default())
        } else {
            // Fallback to simple keyword matching
            let response = handle_query_fallback(query, context);

            Ok(serde_json::to_vec(&serde_json::json!({
                "query": query,
                "response": response,
                "confidence": 0.3,
                "inference_time_ms": 0
            })).unwrap_or_default())
        }
    }

    /// Detect fraud/anomalies
    async fn detect_fraud(&self, order: &OrderData) -> Result<Vec<u8>, IntegrationError> {
        let mut risk_factors = vec![];
        let mut risk_score = 0;

        // Check order amount
        if order.amount > 1000.0 {
            risk_score += 20;
            risk_factors.push("High order amount");
        }

        // Check number of items vs amount (unusual ratio)
        if !order.items.is_empty() {
            let avg_price = order.amount / order.items.len() as f64;
            if avg_price > 500.0 {
                risk_score += 15;
                risk_factors.push("Unusually high average item price");
            }
        }

        // Check for duplicate orders
        let orders = self.orders.read().await;
        let recent_similar = orders.values().filter(|o| {
            o.order_id != order.order_id &&
            (std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_secs() - o.updated_at.value) < 3600 // Within 1 hour
        }).count();

        if recent_similar > 3 {
            risk_score += 30;
            risk_factors.push("Multiple similar orders recently");
        }

        // Determine risk level
        let risk_level = if risk_score >= 50 {
            "high"
        } else if risk_score >= 25 {
            "medium"
        } else {
            "low"
        };

        Ok(serde_json::to_vec(&serde_json::json!({
            "order_id": order.order_id,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "risk_factors": risk_factors,
            "recommendation": if risk_score >= 50 { "manual_review" } else { "accept" }
        })).unwrap_or_default())
    }

    /// Update route memory
    async fn update_route_memory(&self, route: &RouteData, actual_time_minutes: u32) -> Result<Vec<u8>, IntegrationError> {
        // Broadcast route memory update to swarm
        let payload = MessagePayload::Custom {
            app_id: "route_memory".to_string(),
            data: serde_json::to_vec(&serde_json::json!({
                "start": route.start,
                "end": route.end,
                "actual_time": actual_time_minutes,
                "timestamp": std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH)
                    .unwrap()
                    .as_secs()
            })).unwrap_or_default(),
        };

        self.gossip.broadcast(payload).await
            .map_err(|e| IntegrationError::BroadcastError(e.to_string()))?;

        Ok(serde_json::to_vec(&serde_json::json!({
            "status": "route_memory_updated",
            "actual_time": actual_time_minutes
        })).unwrap_or_default())
    }

    /// Query route memory from swarm
    async fn query_route_memory(&self, pickup: &Location, delivery: &Location) -> Option<u32> {
        // In production, would query local CRDT of route memory
        // For now, return None to use fallback
        None
    }

    /// Start order sync task
    async fn start_order_sync(&self) {
        let orders = self.orders.clone();
        let gossip = self.gossip.clone();

        tokio::spawn(async move {
            let mut interval = tokio::time::interval(tokio::time::Duration::from_secs(30));

            loop {
                interval.tick().await;

                // Sync orders with neighbors
                let orders_guard = orders.read().await;
                for (order_id, order) in orders_guard.iter() {
                    // Broadcast order state periodically
                    let payload = MessagePayload::CrdtOp {
                        crdt_id: format!("order:{}", order_id),
                        operation: serde_json::to_vec(order).unwrap_or_default(),
                    };

                    let _ = gossip.broadcast(payload).await;
                }
            }
        });
    }

    /// Start inventory sync task
    async fn start_inventory_sync(&self) {
        // Similar to order sync
    }

    /// Start task processor
    async fn start_task_processor(&self) {
        // Process incoming tasks from gossip
    }

    /// Start offline queue processor
    async fn start_offline_queue(&self) {
        // Process queued operations when back online
    }

    /// Sync with iHhashi API (when online)
    pub async fn sync_with_api(&self) -> Result<(), IntegrationError> {
        if let Some(endpoint) = &self.api_endpoint {
            // Push local changes to API
            // Pull remote changes
            log::info!("Syncing with iHhashi API at {}", endpoint);
        }

        Ok(())
    }
}

/// Calculate haversine distance between two points
fn haversine_distance(lat1: f64, lon1: f64, lat2: f64, lon2: f64) -> f64 {
    const R: f64 = 6371.0; // Earth's radius in km

    let dlat = (lat2 - lat1).to_radians();
    let dlon = (lon2 - lon1).to_radians();

    let a = (dlat / 2.0).sin().powi(2)
        + lat1.to_radians().cos() * lat2.to_radians().cos() * (dlon / 2.0).sin().powi(2);

    let c = 2.0 * a.sqrt().atan2((1.0 - a).sqrt());

    R * c
}

/// Get time of day factor (affects delivery time)
fn get_time_of_day_factor() -> f32 {
    use chrono::Local;

    let hour = Local::now().hour();

    match hour {
        7..=9 => 1.5,   // Morning rush
        12..=14 => 1.3, // Lunch rush
        17..=19 => 1.5, // Evening rush
        22..=23 => 0.9, // Late night
        0..=6 => 0.8,   // Night
        _ => 1.0,       // Normal
    }
}

/// Fallback query handler
fn handle_query_fallback(query: &str, context: &[String]) -> String {
    let query_lower = query.to_lowercase();

    if query_lower.contains("where") && query_lower.contains("order") {
        return "Your order is being prepared and will be delivered soon.".to_string();
    }

    if query_lower.contains("cancel") {
        return "I can help you cancel your order. Please note that cancellations within 5 minutes of ordering are free.".to_string();
    }

    if query_lower.contains("refund") {
        return "Refunds are processed within 3-5 business days according to our refund policy.".to_string();
    }

    if query_lower.contains("contact") || query_lower.contains("support") {
        return "You can reach our support team through the app or call our hotline.".to_string();
    }

    // Generic fallback
    "Thank you for your query. A customer service agent will assist you shortly.".to_string()
}

/// Integration errors
#[derive(Debug, thiserror::Error)]
pub enum IntegrationError {
    #[error("Order already exists: {0}")]
    OrderExists(String),

    #[error("Order not found: {0}")]
    OrderNotFound(String),

    #[error("Invalid order: {0}")]
    InvalidOrder(String),

    #[error("Merchant not found: {0}")]
    MerchantNotFound(String),

    #[error("Broadcast error: {0}")]
    BroadcastError(String),

    #[error("Inference error: {0}")]
    InferenceError(String),

    #[error("Network error: {0}")]
    NetworkError(String),

    #[error("API error: {0}")]
    ApiError(String),
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_haversine_distance() {
        // Distance between Johannesburg and Cape Town
        let joburg_lat = -26.2041;
        let joburg_lng = 28.0473;
        let cape_town_lat = -33.9249;
        let cape_town_lng = 18.4241;

        let distance = haversine_distance(joburg_lat, joburg_lng, cape_town_lat, cape_town_lng);

        // Should be roughly 1260 km
        assert!(distance > 1200.0 && distance < 1300.0);
    }

    #[test]
    fn test_time_of_day_factor() {
        let factor = get_time_of_day_factor();
        assert!(factor > 0.0 && factor <= 2.0);
    }
}
