import ChatWindow from "../components/ChatWindow";

export default function ChatAssistant() {
  return (
    <div className="p-6 md:p-8 max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-4">AI Assistant</h1>
      <p className="text-sm text-gray-500 mb-6">
        Ask about properties, budgets, or locations and get instant
        AI-powered suggestions.
      </p>
      <ChatWindow />
    </div>
  );
}