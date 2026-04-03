import { create } from "zustand";

type Message = {
  role: "user" | "assistant";
  content: string;
  timestamp?: string;
  transport?: string;
};

type ChatState = {
  messages: Message[];
  isStreaming: boolean;

  addUserMessage: (text: string, meta?: Omit<Message, "role" | "content">) => void;
  hydrateMessages: (messages: Message[]) => void;
  clearMessages: () => void;
  startAssistantMessage: () => void;
  appendToAssistant: (chunk: string) => void;
  endStreaming: () => void;
};

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  isStreaming: false,

  addUserMessage: (text, meta) =>
    set((state) => ({
      messages: [...state.messages, { role: "user", content: text, ...meta }],
    })),

  hydrateMessages: (messages) => set({ messages, isStreaming: false }),

  clearMessages: () => set({ messages: [], isStreaming: false }),

  startAssistantMessage: () =>
    set((state) => ({
      isStreaming: true,
      messages: [...state.messages, { role: "assistant", content: "" }],
    })),

  appendToAssistant: (chunk) =>
    set((state) => {
      const messages = [...state.messages];
      if (messages.length === 0 || messages[messages.length - 1].role !== "assistant") {
        messages.push({ role: "assistant", content: chunk });
        return { messages };
      }
      messages[messages.length - 1].content += chunk;
      return { messages };
    }),

  endStreaming: () => set({ isStreaming: false }),
}));
