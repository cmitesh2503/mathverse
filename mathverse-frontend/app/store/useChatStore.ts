import { create } from "zustand";

type Message = {
  role: "user" | "assistant";
  content: string;
};

type ChatState = {
  messages: Message[];
  isStreaming: boolean;

  addUserMessage: (text: string) => void;
  startAssistantMessage: () => void;
  appendToAssistant: (chunk: string) => void;
  endStreaming: () => void;
};

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  isStreaming: false,

  addUserMessage: (text) =>
    set((state) => ({
      messages: [...state.messages, { role: "user", content: text }],
    })),

  startAssistantMessage: () =>
    set((state) => ({
      isStreaming: true,
      messages: [...state.messages, { role: "assistant", content: "" }],
    })),

  appendToAssistant: (chunk) =>
    set((state) => {
      const messages = [...state.messages];
      messages[messages.length - 1].content += chunk;
      return { messages };
    }),

  endStreaming: () => set({ isStreaming: false }),
}));