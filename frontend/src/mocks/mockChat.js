// mockChat.js
// Mock data matching Part 4's chat shape exactly:
// { session_id, response_text, referenced_property_ids: [id] }
//
// ChatWindow.jsx should call getMockChatResponse(userMessage) the same
// way it will later call the real POST /chat/message endpoint — so
// swapping this out later is a one-line change.

const SESSION_ID = "mock-session-001";

// A few canned exchanges keyed by keywords likely to appear in a user's
// message, so the demo feels responsive rather than always saying the
// same thing.
const cannedResponses = [
  {
    keywords: ["3bhk", "3 bhk", "three bedroom"],
    response_text:
      "I found a few good 3BHK options. The Koramangala apartment and the Sarjapur Road flat both score well on price and location.",
    referenced_property_ids: [1, 9],
  },
  {
    keywords: ["budget", "cheap", "affordable", "under 50 lakh", "under 5000000"],
    response_text:
      "For budget-friendly options, check out the 1BHK in Banashankari or the 2BHK in Electronic City — both are well under 50 lakhs.",
    referenced_property_ids: [10, 8],
  },
  {
    keywords: ["luxury", "premium", "villa"],
    response_text:
      "If you're looking for something premium, the Whitefield villa and the Indiranagar penthouse are our top luxury listings.",
    referenced_property_ids: [3, 7],
  },
  {
    keywords: ["fraud", "trust", "safe", "verified"],
    response_text:
      "All listed properties go through document verification and fraud scoring. Properties with a trust score above 80 are generally low-risk.",
    referenced_property_ids: [],
  },
  {
    keywords: ["whitefield"],
    response_text:
      "In Whitefield, we currently have a spacious 4BHK villa listed near ITPL Main Road.",
    referenced_property_ids: [3],
  },
];

const fallbackResponse =
  "I can help you find properties by location, budget, or size — try asking something like 'show me 3BHK flats under 1 crore in Koramangala'.";

/**
 * Simulates a chat backend response.
 * @param {string} userMessage
 * @returns {{ session_id: string, response_text: string, referenced_property_ids: number[] }}
 */
export function getMockChatResponse(userMessage) {
  const normalized = (userMessage || "").toLowerCase();

  const match = cannedResponses.find((entry) =>
    entry.keywords.some((keyword) => normalized.includes(keyword))
  );

  return {
    session_id: SESSION_ID,
    response_text: match ? match.response_text : fallbackResponse,
    referenced_property_ids: match ? match.referenced_property_ids : [],
  };
}

// A starter message shown when the chat window first opens.
export const mockChatWelcome = {
  session_id: SESSION_ID,
  response_text:
    "Hi! 👋 I'm Luna, your AI assistant. I can help you find properties, compare options, and explore buying or selling.",
  referenced_property_ids: [],
};