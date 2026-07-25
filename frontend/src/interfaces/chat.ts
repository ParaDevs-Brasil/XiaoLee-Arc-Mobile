// Chat-related interfaces for Xiaolee project

export interface ChatMessage {
  content: string;
  role: "user" | "assistant";
  timestamp: string;
}

// Legacy chat format for backward compatibility
export interface ChatHistoryItem {
  user_message: {
    content: string;
    timestamp: string;
  };
  assistant_response: {
    content: string;
    timestamp: string;
  };
}

// Chat component props
export interface HistoricoProps {
  shouldOpen?: boolean;
  onClose?: () => void;
}
