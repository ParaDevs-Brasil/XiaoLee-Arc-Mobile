import { ChatMessage } from "@/interfaces";

export const getRoleColor = (role: string) => {
  switch (role) {
    case "user":
      return "from-[var(--history-user-bg-start)] to-[var(--history-user-bg-end)] border-[var(--history-user-border)]";
    case "assistant":
      return "from-[var(--history-assistant-bg-start)] to-[var(--history-assistant-bg-end)] border-[var(--history-assistant-border)]";
    default:
      return "from-gray-50 to-white border-gray-200";
  }
};

export const getRoleIcon = (role: string) => {
  switch (role) {
    case "user":
      return "👤";
    case "assistant":
      return "🤖";
    default:
      return "💬";
  }
};

export const filterHistory = (history: ChatMessage[], filter: string) => {
  return history.filter((message) => {
    switch (filter) {
      case "user":
        return message.role === "user";
      case "assistant":
        return message.role === "assistant";
      default:
        return true;
    }
  });
};

export const typeOptions = [
  { value: "all", label: "All Messages", icon: "💬" },
  { value: "user", label: "Your Messages", icon: "👤" },
  { value: "assistant", label: "Xiaolee Messages", icon: "🤖" },
];
