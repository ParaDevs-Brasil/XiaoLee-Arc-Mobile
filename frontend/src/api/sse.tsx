/*
class SSEReceiver {
  private static instance: SSEReceiver | null = null;
  private eventSource: EventSource | null = null;

  private constructor() {}

  static getInstance(): SSEReceiver {
    if (!SSEReceiver.instance) {
      SSEReceiver.instance = new SSEReceiver();
    }
    return SSEReceiver.instance;
  }

  start(
    url: string, 
    onMessage: (data: any) => void,
    onError?: (error: any) => void,
    onOpen?: () => void
  ) {
    if (this.eventSource) {
     
      this.stop();
    }

    console.log("🚀 Creating new SSE connection to:", url);
    
    try {
      this.eventSource = new EventSource(url, {
        withCredentials: false // CORREÇÃO: Desabilitar credenciais para evitar CORS
      });

      this.eventSource.onopen = (event) => {
        console.log("✅ SSE Connection opened:", event);
        if (onOpen) onOpen();
      };

      this.eventSource.onmessage = (event) => {
        console.log("📨 SSE Message received:", event.data);
        onMessage(event.data);
      };

      this.eventSource.onerror = (error) => {
        console.error("❌ SSE Error occurred:", error);
        console.error("🔍 SSE ReadyState:", this.eventSource?.readyState);
        console.error("🔍 SSE URL:", this.eventSource?.url);
        
        // ReadyState: 0 = CONNECTING, 1 = OPEN, 2 = CLOSED
        const readyStateMap = {
          0: "CONNECTING",
          1: "OPEN", 
          2: "CLOSED"
        };
        
        console.error("🔍 Connection State:", readyStateMap[this.eventSource?.readyState as keyof typeof readyStateMap] || "UNKNOWN");
        
        if (onError) onError(error);
      };

    } catch (error) {
      console.error("❌ Failed to create SSE connection:", error);
      if (onError) onError(error);
    }
  }

  stop() {
    if (this.eventSource) {
      console.log("🛑 Stopping SSE connection");
      this.eventSource.close();
      this.eventSource = null;
    }
  }

  getReadyState(): number | null {
    return this.eventSource?.readyState || null;
  }

  isConnected(): boolean {
    return this.eventSource?.readyState === 1; // OPEN
  }
}

export default SSEReceiver;
*/