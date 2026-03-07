// Message formats for inter-agent communication

use serde::{Serialize, Deserialize};

/// Protocol version
pub const PROTOCOL_VERSION: u8 = 1;

/// Message envelope
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MessageEnvelope {
    /// Protocol version
    pub version: u8,
    /// Message ID (for deduplication)
    pub id: String,
    /// Source node
    pub source: String,
    /// Destination node (None for broadcast)
    pub destination: Option<String>,
    /// Timestamp
    pub timestamp: u64,
    /// TTL (time to live)
    pub ttl: u8,
    /// Message payload
    pub payload: MessagePayload,
}

impl MessageEnvelope {
    /// Create new message
    pub fn new(source: String, destination: Option<String>, payload: MessagePayload) -> Self {
        Self {
            version: PROTOCOL_VERSION,
            id: uuid::Uuid::new_v4().to_string(),
            source,
            destination,
            timestamp: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_secs(),
            ttl: 10,
            payload,
        }
    }

    /// Create broadcast message
    pub fn broadcast(source: String, payload: MessagePayload) -> Self {
        Self::new(source, None, payload)
    }

    /// Create unicast message
    pub fn unicast(source: String, destination: String, payload: MessagePayload) -> Self {
        Self::new(source, Some(destination), payload)
    }

    /// Decrement TTL
    pub fn decrement_ttl(mut self) -> Option<Self> {
        if self.ttl > 0 {
            self.ttl -= 1;
            Some(self)
        } else {
            None
        }
    }
}

/// Message payload types
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", content = "data")]
pub enum MessagePayload {
    /// Ping/heartbeat
    Ping { nonce: u64 },
    /// Pong response
    Pong { nonce: u64 },
    /// Task announcement
    TaskAnnounce {
        task_id: String,
        task_type: String,
        priority: u8,
        capabilities_required: u32,
    },
    /// Task assignment
    TaskAssign {
        task_id: String,
        assignee: String,
    },
    /// Task result
    TaskResult {
        task_id: String,
        success: bool,
        result_hash: String,
    },
    /// Data sync
    DataSync {
        crdt_id: String,
        delta: Vec<u8>,
    },
    /// Reputation update
    ReputationUpdate {
        node_id: String,
        delta: i32,
        reason: String,
    },
    /// Custom application message
    Custom {
        app_id: String,
        data: Vec<u8>,
    },
}

/// Message handler trait
#[async_trait::async_trait]
pub trait MessageHandler: Send + Sync {
    /// Handle incoming message
    async fn handle(&self, envelope: MessageEnvelope) -> Option<MessagePayload>;
}

/// Message codec
pub struct MessageCodec;

impl MessageCodec {
    /// Encode message to bytes
    pub fn encode(envelope: &MessageEnvelope) -> Result<Vec<u8>, MessageError> {
        bincode::serialize(envelope)
            .map_err(|e| MessageError::EncodeError(e.to_string()))
    }

    /// Decode bytes to message
    pub fn decode(bytes: &[u8]) -> Result<MessageEnvelope, MessageError> {
        bincode::deserialize(bytes)
            .map_err(|e| MessageError::DecodeError(e.to_string()))
    }
}

/// Message errors
#[derive(Debug, thiserror::Error)]
pub enum MessageError {
    #[error("Encode error: {0}")]
    EncodeError(String),

    #[error("Decode error: {0}")]
    DecodeError(String),

    #[error("Invalid version: {0}")]
    InvalidVersion(u8),

    #[error("TTL expired")]
    TtlExpired,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_message_encode_decode() {
        let envelope = MessageEnvelope::broadcast(
            "node1".to_string(),
            MessagePayload::Ping { nonce: 12345 }
        );

        let encoded = MessageCodec::encode(&envelope).unwrap();
        let decoded = MessageCodec::decode(&encoded).unwrap();

        assert_eq!(decoded.source, "node1");
        assert!(matches!(decoded.payload, MessagePayload::Ping { nonce: 12345 }));
    }

    #[test]
    fn test_ttl_decrement() {
        let envelope = MessageEnvelope::broadcast(
            "node1".to_string(),
            MessagePayload::Ping { nonce: 1 }
        );

        assert_eq!(envelope.ttl, 10);

        let mut current = Some(envelope);
        for i in (0..10).rev() {
            if let Some(env) = current {
                assert_eq!(env.ttl, i + 1);
                current = env.decrement_ttl();
            }
        }

        assert!(current.is_none());
    }
}
