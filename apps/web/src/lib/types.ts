export type Role = "owner" | "admin" | "member";

export type User = {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
};

export type Workspace = {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  created_at: string;
  role: Role | null;
};

export type Member = {
  user_id: string;
  email: string;
  full_name: string | null;
  role: Role;
  status: string;
  joined_at: string;
};

export type Tokens = {
  access_token: string;
  refresh_token: string;
  token_type: string;
};

export type DocumentStatus =
  | "uploaded"
  | "extracting"
  | "chunking"
  | "embedding"
  | "ready"
  | "failed";

export type DocumentItem = {
  id: string;
  original_filename: string;
  mime_type: string;
  file_size_bytes: number;
  page_count: number | null;
  chunk_count: number;
  status: DocumentStatus;
  error_message: string | null;
  uploaded_by: string | null;
  created_at: string;
  processed_at: string | null;
};

export type Chunk = {
  id: string;
  chunk_index: number;
  page_number: number | null;
  token_count: number;
  content: string;
};

export const PROCESSING_STATUSES: DocumentStatus[] = [
  "uploaded",
  "extracting",
  "chunking",
  "embedding",
];

export type Citation = {
  index: number;
  document_id: string | null;
  document_filename: string;
  page_number: number | null;
  snippet: string;
  score: number;
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  created_at: string;
  citations: Citation[];
};

export type Conversation = {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
};

export type ConversationDetail = {
  conversation: Conversation;
  messages: ChatMessage[];
};

export type AskResponse = {
  conversation_id: string;
  message_id: string;
  answer: string;
  citations: Citation[];
  coverage: string;
  not_found: boolean;
};
