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
