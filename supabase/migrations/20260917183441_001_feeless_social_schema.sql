/*
# FEELESS Social & Token Platform Schema

This migration creates the core database tables for the FEELESS platform:
- User profiles linked to wallet addresses
- Token-specific chat rooms with messages, replies, and reactions
- Global chat channels with messages
- Callouts, thesis posts, and meta posts for the social intelligence layer
- Watchlists, alerts, and follows
- Token launch records with graduation status
- Fee-Back tracking records

## Tables Created

1. **profiles** — Maps wallet addresses to display names/avatars
2. **token_rooms** — One room per token mint for community discussion
3. **messages** — All chat messages (token rooms + global channels), with reply support
4. **reactions** — Emoji reactions on messages
5. **bookmarks** — User bookmarks on messages
6. **callouts** — Callout posts (bullish/bearish calls on tokens)
7. **theses** — Long-form thesis posts on tokens
8. **meta_posts** — Meta/narrative posts about market themes
9. **watchlist** — User watchlists for tokens
10. **alerts** — Price alerts for tokens
11. **follows** — Follower/following relationships
12. **launches** — Token launch records with graduation status
13. **feeback_records** — Fee-Back tracking records

## Security

- RLS enabled on all tables
- Policies use `auth.uid()` for owner-scoped data
- Public read on social content (messages, callouts, theses, meta_posts, reactions)
- Owner-scoped write for user-specific data (watchlist, alerts, follows, bookmarks)
- `DEFAULT auth.uid()` on owner columns so inserts work without explicit user_id

## Important Notes

1. Realtime is enabled on messages, reactions, callouts, theses, meta_posts tables
2. The app uses Supabase email/password auth — email confirmation stays OFF
3. No fake/sample/demo data is inserted — all tables start empty
4. Wallet addresses are stored as text (Solana base58 addresses)
*/

-- Profiles table: maps wallet addresses to display info
CREATE TABLE IF NOT EXISTS profiles (
  id uuid PRIMARY KEY DEFAULT auth.uid(),
  wallet_address text UNIQUE,
  display_name text,
  avatar_url text,
  bio text,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "select_profiles" ON profiles;
CREATE POLICY "select_profiles" ON profiles FOR SELECT
  TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "insert_own_profile" ON profiles;
CREATE POLICY "insert_own_profile" ON profiles FOR INSERT
  TO authenticated WITH CHECK (auth.uid() = id);

DROP POLICY IF EXISTS "update_own_profile" ON profiles;
CREATE POLICY "update_own_profile" ON profiles FOR UPDATE
  TO authenticated USING (auth.uid() = id) WITH CHECK (auth.uid() = id);

-- Token rooms: one per mint
CREATE TABLE IF NOT EXISTS token_rooms (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  mint text NOT NULL UNIQUE,
  created_at timestamptz DEFAULT now()
);

ALTER TABLE token_rooms ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "select_token_rooms" ON token_rooms;
CREATE POLICY "select_token_rooms" ON token_rooms FOR SELECT
  TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "insert_token_rooms" ON token_rooms;
CREATE POLICY "insert_token_rooms" ON token_rooms FOR INSERT
  TO anon, authenticated WITH CHECK (true);

-- Messages: unified chat for token rooms and global channels
CREATE TABLE IF NOT EXISTS messages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  room_id uuid REFERENCES token_rooms(id) ON DELETE CASCADE,
  channel text DEFAULT 'general',
  user_id uuid NOT NULL DEFAULT auth.uid() REFERENCES auth.users(id) ON DELETE CASCADE,
  content text NOT NULL,
  reply_to uuid REFERENCES messages(id) ON DELETE SET NULL,
  post_type text DEFAULT 'chat' CHECK (post_type IN ('chat','callout','thesis','meta','watch')),
  created_at timestamptz DEFAULT now()
);

ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "select_messages" ON messages;
CREATE POLICY "select_messages" ON messages FOR SELECT
  TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "insert_own_messages" ON messages;
CREATE POLICY "insert_own_messages" ON messages FOR INSERT
  TO authenticated WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "update_own_messages" ON messages;
CREATE POLICY "update_own_messages" ON messages FOR UPDATE
  TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "delete_own_messages" ON messages;
CREATE POLICY "delete_own_messages" ON messages FOR DELETE
  TO authenticated USING (auth.uid() = user_id);

CREATE INDEX IF NOT EXISTS idx_messages_room ON messages(room_id, created_at);
CREATE INDEX IF NOT EXISTS idx_messages_channel ON messages(channel, created_at);
CREATE INDEX IF NOT EXISTS idx_messages_user ON messages(user_id);

-- Reactions on messages
CREATE TABLE IF NOT EXISTS reactions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  message_id uuid NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
  user_id uuid NOT NULL DEFAULT auth.uid() REFERENCES auth.users(id) ON DELETE CASCADE,
  emoji text NOT NULL,
  created_at timestamptz DEFAULT now(),
  UNIQUE(message_id, user_id, emoji)
);

ALTER TABLE reactions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "select_reactions" ON reactions;
CREATE POLICY "select_reactions" ON reactions FOR SELECT
  TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "insert_own_reactions" ON reactions;
CREATE POLICY "insert_own_reactions" ON reactions FOR INSERT
  TO authenticated WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "delete_own_reactions" ON reactions;
CREATE POLICY "delete_own_reactions" ON reactions FOR DELETE
  TO authenticated USING (auth.uid() = user_id);

CREATE INDEX IF NOT EXISTS idx_reactions_message ON reactions(message_id);

-- Bookmarks on messages
CREATE TABLE IF NOT EXISTS bookmarks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  message_id uuid NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
  user_id uuid NOT NULL DEFAULT auth.uid() REFERENCES auth.users(id) ON DELETE CASCADE,
  created_at timestamptz DEFAULT now(),
  UNIQUE(message_id, user_id)
);

ALTER TABLE bookmarks ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "select_own_bookmarks" ON bookmarks;
CREATE POLICY "select_own_bookmarks" ON bookmarks FOR SELECT
  TO authenticated USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "insert_own_bookmarks" ON bookmarks;
CREATE POLICY "insert_own_bookmarks" ON bookmarks FOR INSERT
  TO authenticated WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "delete_own_bookmarks" ON bookmarks;
CREATE POLICY "delete_own_bookmarks" ON bookmarks FOR DELETE
  TO authenticated USING (auth.uid() = user_id);

-- Callouts: bullish/bearish calls on tokens
CREATE TABLE IF NOT EXISTS callouts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL DEFAULT auth.uid() REFERENCES auth.users(id) ON DELETE CASCADE,
  mint text NOT NULL,
  direction text NOT NULL CHECK (direction IN ('bullish','bearish')),
  content text,
  entry_price numeric,
  created_at timestamptz DEFAULT now()
);

ALTER TABLE callouts ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "select_callouts" ON callouts;
CREATE POLICY "select_callouts" ON callouts FOR SELECT
  TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "insert_own_callouts" ON callouts;
CREATE POLICY "insert_own_callouts" ON callouts FOR INSERT
  TO authenticated WITH CHECK (auth.uid() = user_id);

CREATE INDEX IF NOT EXISTS idx_callouts_mint ON callouts(mint, created_at);
CREATE INDEX IF NOT EXISTS idx_callouts_user ON callouts(user_id);

-- Theses: long-form posts on tokens
CREATE TABLE IF NOT EXISTS theses (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL DEFAULT auth.uid() REFERENCES auth.users(id) ON DELETE CASCADE,
  mint text NOT NULL,
  title text NOT NULL,
  body text NOT NULL,
  created_at timestamptz DEFAULT now()
);

ALTER TABLE theses ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "select_theses" ON theses;
CREATE POLICY "select_theses" ON theses FOR SELECT
  TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "insert_own_theses" ON theses;
CREATE POLICY "insert_own_theses" ON theses FOR INSERT
  TO authenticated WITH CHECK (auth.uid() = user_id);

CREATE INDEX IF NOT EXISTS idx_theses_mint ON theses(mint, created_at);

-- Meta posts: market narrative posts
CREATE TABLE IF NOT EXISTS meta_posts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL DEFAULT auth.uid() REFERENCES auth.users(id) ON DELETE CASCADE,
  title text NOT NULL,
  body text NOT NULL,
  tags text[],
  created_at timestamptz DEFAULT now()
);

ALTER TABLE meta_posts ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "select_meta_posts" ON meta_posts;
CREATE POLICY "select_meta_posts" ON meta_posts FOR SELECT
  TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "insert_own_meta_posts" ON meta_posts;
CREATE POLICY "insert_own_meta_posts" ON meta_posts FOR INSERT
  TO authenticated WITH CHECK (auth.uid() = user_id);

-- Watchlist
CREATE TABLE IF NOT EXISTS watchlist (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL DEFAULT auth.uid() REFERENCES auth.users(id) ON DELETE CASCADE,
  mint text NOT NULL,
  created_at timestamptz DEFAULT now(),
  UNIQUE(user_id, mint)
);

ALTER TABLE watchlist ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "select_own_watchlist" ON watchlist;
CREATE POLICY "select_own_watchlist" ON watchlist FOR SELECT
  TO authenticated USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "insert_own_watchlist" ON watchlist;
CREATE POLICY "insert_own_watchlist" ON watchlist FOR INSERT
  TO authenticated WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "delete_own_watchlist" ON watchlist;
CREATE POLICY "delete_own_watchlist" ON watchlist FOR DELETE
  TO authenticated USING (auth.uid() = user_id);

-- Alerts: price alerts
CREATE TABLE IF NOT EXISTS alerts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL DEFAULT auth.uid() REFERENCES auth.users(id) ON DELETE CASCADE,
  mint text NOT NULL,
  condition text NOT NULL CHECK (condition IN ('above','below')),
  target_price numeric NOT NULL,
  active boolean DEFAULT true,
  created_at timestamptz DEFAULT now()
);

ALTER TABLE alerts ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "select_own_alerts" ON alerts;
CREATE POLICY "select_own_alerts" ON alerts FOR SELECT
  TO authenticated USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "insert_own_alerts" ON alerts;
CREATE POLICY "insert_own_alerts" ON alerts FOR INSERT
  TO authenticated WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "update_own_alerts" ON alerts;
CREATE POLICY "update_own_alerts" ON alerts FOR UPDATE
  TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "delete_own_alerts" ON alerts;
CREATE POLICY "delete_own_alerts" ON alerts FOR DELETE
  TO authenticated USING (auth.uid() = user_id);

-- Follows: follower/following
CREATE TABLE IF NOT EXISTS follows (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  follower_id uuid NOT NULL DEFAULT auth.uid() REFERENCES auth.users(id) ON DELETE CASCADE,
  following_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  created_at timestamptz DEFAULT now(),
  UNIQUE(follower_id, following_id)
);

ALTER TABLE follows ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "select_follows" ON follows;
CREATE POLICY "select_follows" ON follows FOR SELECT
  TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "insert_own_follows" ON follows;
CREATE POLICY "insert_own_follows" ON follows FOR INSERT
  TO authenticated WITH CHECK (auth.uid() = follower_id);

DROP POLICY IF EXISTS "delete_own_follows" ON follows;
CREATE POLICY "delete_own_follows" ON follows FOR DELETE
  TO authenticated USING (auth.uid() = follower_id);

-- Launches: token launch records
CREATE TABLE IF NOT EXISTS launches (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL DEFAULT auth.uid() REFERENCES auth.users(id) ON DELETE CASCADE,
  mint text,
  name text NOT NULL,
  symbol text NOT NULL,
  description text,
  image_url text,
  website text,
  twitter text,
  telegram text,
  supply numeric,
  decimals integer,
  signature text,
  status text DEFAULT 'pending' CHECK (status IN ('pending','confirmed','failed','graduated')),
  created_at timestamptz DEFAULT now()
);

ALTER TABLE launches ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "select_launches" ON launches;
CREATE POLICY "select_launches" ON launches FOR SELECT
  TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "insert_own_launches" ON launches;
CREATE POLICY "insert_own_launches" ON launches FOR INSERT
  TO authenticated WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "update_own_launches" ON launches;
CREATE POLICY "update_own_launches" ON launches FOR UPDATE
  TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

-- Fee-Back records
CREATE TABLE IF NOT EXISTS feeback_records (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES auth.users(id) ON DELETE SET NULL,
  wallet_address text,
  mint text,
  swap_signature text,
  fee_amount numeric,
  status text DEFAULT 'swapped' CHECK (status IN ('swapped','detected','eligible','pending','returned')),
  created_at timestamptz DEFAULT now()
);

ALTER TABLE feeback_records ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "select_feeback" ON feeback_records;
CREATE POLICY "select_feeback" ON feeback_records FOR SELECT
  TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "insert_own_feeback" ON feeback_records;
CREATE POLICY "insert_own_feeback" ON feeback_records FOR INSERT
  TO authenticated WITH CHECK (auth.uid() = user_id);

-- Enable realtime on key tables
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_publication_tables WHERE pubname = 'supabase_realtime' AND tablename = 'messages') THEN
    ALTER PUBLICATION supabase_realtime ADD TABLE messages;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_publication_tables WHERE pubname = 'supabase_realtime' AND tablename = 'reactions') THEN
    ALTER PUBLICATION supabase_realtime ADD TABLE reactions;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_publication_tables WHERE pubname = 'supabase_realtime' AND tablename = 'callouts') THEN
    ALTER PUBLICATION supabase_realtime ADD TABLE callouts;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_publication_tables WHERE pubname = 'supabase_realtime' AND tablename = 'theses') THEN
    ALTER PUBLICATION supabase_realtime ADD TABLE theses;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_publication_tables WHERE pubname = 'supabase_realtime' AND tablename = 'meta_posts') THEN
    ALTER PUBLICATION supabase_realtime ADD TABLE meta_posts;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_publication_tables WHERE pubname = 'supabase_realtime' AND tablename = 'follows') THEN
    ALTER PUBLICATION supabase_realtime ADD TABLE follows;
  END IF;
END
$$;
