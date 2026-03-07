// Transport layer abstractions

use async_trait::async_trait;

/// Transport trait for different networking backends
#[async_trait]
pub trait Transport: Send + Sync {
    /// Start the transport
    async fn start(&mut self) -> Result<(), TransportError>;

    /// Stop the transport
    async fn stop(&mut self) -> Result<(), TransportError>;

    /// Send data to a peer
    async fn send(&self, peer: &str, data: &[u8]) -> Result<(), TransportError>;

    /// Receive data
    async fn recv(&mut self) -> Result<(String, Vec<u8>), TransportError>;

    /// Get local address
    fn local_addr(&self) -> String;

    /// Get transport type
    fn transport_type(&self) -> TransportType;
}

/// Transport types
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum TransportType {
    Tcp,
    Udp,
    WifiDirect,
    BluetoothLE,
    LoRa,
    WebRTC,
}

/// Transport errors
#[derive(Debug, thiserror::Error)]
pub enum TransportError {
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),

    #[error("Not connected")]
    NotConnected,

    #[error("Timeout")]
    Timeout,

    #[error("Invalid address: {0}")]
    InvalidAddress(String),
}

/// TCP transport implementation
pub struct TcpTransport {
    bind_addr: String,
}

impl TcpTransport {
    /// Create new TCP transport
    pub fn new(bind_addr: String) -> Self {
        Self { bind_addr }
    }
}

#[async_trait]
impl Transport for TcpTransport {
    async fn start(&mut self) -> Result<(), TransportError> {
        Ok(())
    }

    async fn stop(&mut self) -> Result<(), TransportError> {
        Ok(())
    }

    async fn send(&self, _peer: &str, _data: &[u8]) -> Result<(), TransportError> {
        Ok(())
    }

    async fn recv(&mut self) -> Result<(String, Vec<u8>), TransportError> {
        Ok((String::new(), Vec::new()))
    }

    fn local_addr(&self) -> String {
        self.bind_addr.clone()
    }

    fn transport_type(&self) -> TransportType {
        TransportType::Tcp
    }
}
