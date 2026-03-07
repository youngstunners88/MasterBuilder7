// CRDT (Conflict-free Replicated Data Types) for Offline-First State
// No coordination needed - all changes converge automatically

use std::collections::{HashMap, HashSet, BTreeMap};
use serde::{Serialize, Deserialize};
use std::cmp::Ordering;

/// Vector clock for causality tracking
#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq, Eq)]
pub struct VectorClock {
    /// Node ID -> logical timestamp
    pub clocks: HashMap<String, u64>,
}

impl VectorClock {
    pub fn new() -> Self {
        Self {
            clocks: HashMap::new(),
        }
    }

    /// Increment this node's clock
    pub fn increment(&mut self, node_id: &str) {
        let counter = self.clocks.entry(node_id.to_string()).or_insert(0);
        *counter += 1;
    }

    /// Merge with another vector clock (takes max of each entry)
    pub fn merge(&mut self, other: &VectorClock) {
        for (node, timestamp) in &other.clocks {
            let entry = self.clocks.entry(node.clone()).or_insert(0);
            *entry = (*entry).max(*timestamp);
        }
    }

    /// Compare two vector clocks
    pub fn compare(&self, other: &VectorClock) -> Ordering {
        let all_nodes: HashSet<_> = self.clocks.keys()
            .chain(other.clocks.keys())
            .collect();

        let mut has_less = false;
        let mut has_greater = false;

        for node in all_nodes {
            let self_val = self.clocks.get(node).copied().unwrap_or(0);
            let other_val = other.clocks.get(node).copied().unwrap_or(0);

            if self_val < other_val {
                has_less = true;
            } else if self_val > other_val {
                has_greater = true;
            }
        }

        match (has_less, has_greater) {
            (true, true) => Ordering::Equal, // Concurrent
            (true, false) => Ordering::Less,
            (false, true) => Ordering::Greater,
            (false, false) => Ordering::Equal, // Equal
        }
    }

    /// Check if this clock dominates another (happens-before)
    pub fn dominates(&self, other: &VectorClock) -> bool {
        self.compare(other) == Ordering::Greater
    }

    /// Check if clocks are concurrent
    pub fn is_concurrent(&self, other: &VectorClock) -> bool {
        self.compare(other) == Ordering::Equal && self != other
    }
}

/// Grow-only Counter (G-Counter) CRDT
/// Monotonically increasing counter per node
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct GCounter {
    /// Node ID -> count
    pub counts: HashMap<String, u64>,
}

impl GCounter {
    pub fn new() -> Self {
        Self {
            counts: HashMap::new(),
        }
    }

    /// Increment this node's counter
    pub fn increment(&mut self, node_id: &str) {
        let count = self.counts.entry(node_id.to_string()).or_insert(0);
        *count += 1;
    }

    /// Get total count
    pub fn value(&self) -> u64 {
        self.counts.values().sum()
    }

    /// Merge with another G-Counter
    pub fn merge(&mut self, other: &GCounter) {
        for (node, count) in &other.counts {
            let entry = self.counts.entry(node.clone()).or_insert(0);
            *entry = (*entry).max(*count);
        }
    }
}

/// Positive-Negative Counter (PN-Counter) CRDT
/// Supports increment and decrement
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct PNCounter {
    pub increments: GCounter,
    pub decrements: GCounter,
}

impl PNCounter {
    pub fn new() -> Self {
        Self {
            increments: GCounter::new(),
            decrements: GCounter::new(),
        }
    }

    pub fn increment(&mut self, node_id: &str) {
        self.increments.increment(node_id);
    }

    pub fn decrement(&mut self, node_id: &str) {
        self.decrements.increment(node_id);
    }

    pub fn value(&self) -> i64 {
        self.increments.value() as i64 - self.decrements.value() as i64
    }

    pub fn merge(&mut self, other: &PNCounter) {
        self.increments.merge(&other.increments);
        self.decrements.merge(&other.decrements);
    }
}

/// Last-Write-Wins Register (LWW-Register) CRDT
/// Stores single value with timestamp
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LWWRegister<T> {
    pub value: T,
    pub timestamp: u64,
    pub node_id: String,
}

impl<T: Clone + PartialEq> LWWRegister<T> {
    pub fn new(value: T, node_id: String) -> Self {
        let timestamp = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_millis() as u64;

        Self {
            value,
            timestamp,
            node_id,
        }
    }

    /// Set new value
    pub fn set(&mut self, value: T, node_id: String) {
        let timestamp = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_millis() as u64;

        // Tie-breaker: higher node_id wins if timestamps equal
        if timestamp > self.timestamp ||
           (timestamp == self.timestamp && node_id > self.node_id) {
            self.value = value;
            self.timestamp = timestamp;
            self.node_id = node_id;
        }
    }

    /// Merge with another register
    pub fn merge(&mut self, other: &LWWRegister<T>) {
        if other.timestamp > self.timestamp ||
           (other.timestamp == self.timestamp && other.node_id > self.node_id) {
            self.value = other.value.clone();
            self.timestamp = other.timestamp;
            self.node_id = other.node_id.clone();
        }
    }
}

/// Grow-only Set (G-Set) CRDT
/// Elements can only be added, never removed
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct GSet<T: Clone + Eq + std::hash::Hash> {
    pub elements: HashSet<T>,
}

impl<T: Clone + Eq + std::hash::Hash> GSet<T> {
    pub fn new() -> Self {
        Self {
            elements: HashSet::new(),
        }
    }

    pub fn add(&mut self, element: T) {
        self.elements.insert(element);
    }

    pub fn contains(&self, element: &T) -> bool {
        self.elements.contains(element)
    }

    pub fn merge(&mut self, other: &GSet<T>) {
        self.elements.extend(other.elements.iter().cloned());
    }

    pub fn value(&self) -> &HashSet<T> {
        &self.elements
    }
}

/// Two-Phase Set (2P-Set) CRDT
/// Supports add and remove
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct TwoPSet<T: Clone + Eq + std::hash::Hash> {
    pub adds: GSet<T>,
    pub removes: GSet<T>,
}

impl<T: Clone + Eq + std::hash::Hash> TwoPSet<T> {
    pub fn new() -> Self {
        Self {
            adds: GSet::new(),
            removes: GSet::new(),
        }
    }

    pub fn add(&mut self, element: T) {
        self.adds.add(element);
    }

    pub fn remove(&mut self, element: T) {
        if self.adds.contains(&element) {
            self.removes.add(element);
        }
    }

    pub fn contains(&self, element: &T) -> bool {
        self.adds.contains(element) && !self.removes.contains(element)
    }

    pub fn merge(&mut self, other: &TwoPSet<T>) {
        self.adds.merge(&other.adds);
        self.removes.merge(&other.removes);
    }

    pub fn value(&self) -> HashSet<T> {
        self.adds.elements
            .difference(&self.removes.elements)
            .cloned()
            .collect()
    }
}

/// OR-Set (Observed-Removed Set) CRDT
/// Supports add and remove with unique tags
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct ORSet<T: Clone + Eq + std::hash::Hash> {
    /// Element -> set of unique tags
    pub elements: HashMap<T, HashSet<uuid::Uuid>>,
    /// Tombstones for removed tags
    pub tombstones: HashSet<uuid::Uuid>,
}

impl<T: Clone + Eq + std::hash::Hash> ORSet<T> {
    pub fn new() -> Self {
        Self {
            elements: HashMap::new(),
            tombstones: HashSet::new(),
        }
    }

    pub fn add(&mut self, element: T) -> uuid::Uuid {
        let tag = uuid::Uuid::new_v4();
        self.elements
            .entry(element)
            .or_insert_with(HashSet::new)
            .insert(tag);
        tag
    }

    pub fn remove(&mut self, element: &T) {
        if let Some(tags) = self.elements.remove(element) {
            self.tombstones.extend(tags);
        }
    }

    pub fn contains(&self, element: &T) -> bool {
        self.elements.get(element)
            .map(|tags| !tags.is_empty())
            .unwrap_or(false)
    }

    pub fn merge(&mut self, other: &ORSet<T>) {
        // Merge tombstones
        self.tombstones.extend(other.tombstones.iter().cloned());

        // Merge elements
        for (element, tags) in &other.elements {
            let entry = self.elements.entry(element.clone()).or_insert_with(HashSet::new);
            entry.extend(tags.iter().cloned());
        }

        // Remove tombstoned tags
        for tags in self.elements.values_mut() {
            tags.retain(|tag| !self.tombstones.contains(tag));
        }

        // Remove elements with no tags
        self.elements.retain(|_, tags| !tags.is_empty());
    }

    pub fn value(&self) -> HashSet<T> {
        self.elements.keys().cloned().collect()
    }
}

/// Map CRDT with LWW values
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LWWMap<K: Clone + Eq + std::hash::Hash, V: Clone + PartialEq> {
    pub entries: HashMap<K, LWWRegister<V>>,
}

impl<K: Clone + Eq + std::hash::Hash, V: Clone + PartialEq> LWWMap<K, V> {
    pub fn new() -> Self {
        Self {
            entries: HashMap::new(),
        }
    }

    pub fn set(&mut self, key: K, value: V, node_id: String) {
        let register = LWWRegister::new(value, node_id);
        self.entries.insert(key, register);
    }

    pub fn get(&self, key: &K) -> Option<&V> {
        self.entries.get(key).map(|r| &r.value)
    }

    pub fn merge(&mut self, other: &LWWMap<K, V>) {
        for (key, register) in &other.entries {
            match self.entries.get_mut(key) {
                Some(existing) => existing.merge(register),
                None => { self.entries.insert(key.clone(), register.clone()); }
            }
        }
    }
}

/// Delta-state CRDT for efficient synchronization
/// Only send deltas instead of full state
#[derive(Debug, Clone)]
pub struct DeltaCRDT<T: CRDT> {
    pub state: T,
    pub delta_buffer: Vec<T::Delta>,
}

pub trait CRDT: Clone {
    type Delta: Clone;

    fn delta(&self, other: &Self) -> Option<Self::Delta>;
    fn apply_delta(&mut self, delta: &Self::Delta);
}

/// iHhashi-specific CRDTs

/// Order state CRDT
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OrderState {
    pub order_id: String,
    pub status: LWWRegister<String>,
    pub items: ORSet<String>,
    pub total_amount: PNCounter,
    pub updated_at: LWWRegister<u64>,
    pub vector_clock: VectorClock,
}

impl OrderState {
    pub fn new(order_id: String, node_id: String) -> Self {
        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_secs();

        Self {
            order_id,
            status: LWWRegister::new("created".to_string(), node_id.clone()),
            items: ORSet::new(),
            total_amount: PNCounter::new(),
            updated_at: LWWRegister::new(now, node_id.clone()),
            vector_clock: VectorClock::new(),
        }
    }

    pub fn update_status(&mut self, new_status: String, node_id: String) {
        self.status.set(new_status, node_id.clone());
        self.vector_clock.increment(&node_id);

        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_secs();
        self.updated_at.set(now, node_id);
    }

    pub fn add_item(&mut self, item_id: String, node_id: String) {
        self.items.add(item_id);
        self.vector_clock.increment(&node_id);
    }

    pub fn merge(&mut self, other: &OrderState) {
        self.status.merge(&other.status);
        self.items.merge(&other.items);
        self.total_amount.merge(&other.total_amount);
        self.updated_at.merge(&other.updated_at);
        self.vector_clock.merge(&other.vector_clock);
    }
}

/// Inventory CRDT - tracks item availability
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Inventory {
    pub merchant_id: String,
    pub items: HashMap<String, PNCounter>,
    pub reserved: HashMap<String, TwoPSet<String>>, // item_id -> set of order_ids
}

impl Inventory {
    pub fn new(merchant_id: String) -> Self {
        Self {
            merchant_id,
            items: HashMap::new(),
            reserved: HashMap::new(),
        }
    }

    pub fn restock(&mut self, item_id: &str, quantity: u64, node_id: &str) {
        let counter = self.items.entry(item_id.to_string()).or_insert_with(PNCounter::new);
        for _ in 0..quantity {
            counter.increment(node_id);
        }
    }

    pub fn reserve(&mut self, item_id: &str, order_id: String, node_id: &str) -> bool {
        let available = self.available(item_id);
        if available > 0 {
            let reserved = self.reserved.entry(item_id.to_string()).or_insert_with(TwoPSet::new);
            reserved.add(order_id);

            // Decrement available
            let counter = self.items.entry(item_id.to_string()).or_insert_with(PNCounter::new);
            counter.decrement(node_id);

            true
        } else {
            false
        }
    }

    pub fn available(&self, item_id: &str) -> i64 {
        let total = self.items.get(item_id).map(|c| c.value()).unwrap_or(0);
        let reserved_count = self.reserved.get(item_id)
            .map(|r| r.value().len() as i64)
            .unwrap_or(0);
        total - reserved_count
    }

    pub fn merge(&mut self, other: &Inventory) {
        for (item_id, counter) in &other.items {
            match self.items.get_mut(item_id) {
                Some(existing) => existing.merge(counter),
                None => { self.items.insert(item_id.clone(), counter.clone()); }
            }
        }

        for (item_id, reserved) in &other.reserved {
            match self.reserved.get_mut(item_id) {
                Some(existing) => existing.merge(reserved),
                None => { self.reserved.insert(item_id.clone(), reserved.clone()); }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_g_counter() {
        let mut counter1 = GCounter::new();
        let mut counter2 = GCounter::new();

        counter1.increment("node1");
        counter1.increment("node1");
        counter2.increment("node2");
        counter2.increment("node2");
        counter2.increment("node2");

        counter1.merge(&counter2);

        assert_eq!(counter1.value(), 5);
    }

    #[test]
    fn test_pn_counter() {
        let mut counter = PNCounter::new();

        counter.increment("node1");
        counter.increment("node1");
        counter.decrement("node1");

        assert_eq!(counter.value(), 1);
    }

    #[test]
    fn test_or_set() {
        let mut set1 = ORSet::new();
        let mut set2 = ORSet::new();

        set1.add("a");
        set1.add("b");
        set2.add("b");
        set2.add("c");

        set1.merge(&set2);

        assert!(set1.contains(&"a"));
        assert!(set1.contains(&"b"));
        assert!(set1.contains(&"c"));

        // Remove from set1
        set1.remove(&"b");
        assert!(!set1.contains(&"b"));

        // After merge, b should still be removed
        let mut set3 = ORSet::new();
        set3.merge(&set1);
        assert!(!set3.contains(&"b"));
    }

    #[test]
    fn test_order_state() {
        let mut order1 = OrderState::new("order123".to_string(), "node1".to_string());
        let mut order2 = OrderState::new("order123".to_string(), "node2".to_string());

        order1.update_status("preparing".to_string(), "node1".to_string());
        order2.add_item("item1".to_string(), "node2".to_string());

        order1.merge(&order2);

        assert_eq!(order1.status.value, "preparing");
        assert!(order1.items.contains(&"item1".to_string()));
    }

    #[test]
    fn test_inventory() {
        let mut inv = Inventory::new("merchant1".to_string());

        inv.restock("item1", 10, "node1");
        assert_eq!(inv.available("item1"), 10);

        let reserved = inv.reserve("item1", "order1".to_string(), "node1");
        assert!(reserved);
        assert_eq!(inv.available("item1"), 9);
    }
}
