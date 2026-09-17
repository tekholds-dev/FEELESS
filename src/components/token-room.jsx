import React, { useEffect, useState } from 'react';
import './token-room.css';
import { socialConfigured, supabase } from '../lib/social';

const relativeTime = (value) => {
  if (!value) return '—';
  const minutes = Math.max(0, Math.floor((Date.now() - new Date(value).getTime()) / 60000));
  return minutes < 60 ? `${minutes}m ago` : minutes < 1440 ? `${Math.floor(minutes / 60)}h ago` : `${Math.floor(minutes / 1440)}d ago`;
};

function useRoom(mint) {
  const [state, setState] = useState({ loading: true, posts: [], profiles: {}, comments: {}, reactions: {}, bookmarks: new Set(), watched: false, user: null, error: '' });
  useEffect(() => {
    if (!supabase) { setState((s) => ({ ...s, loading: false, error: 'Social features require the configured Supabase project.' })); return; }
    let live = true;
    const load = async () => {
      const { data: auth } = await supabase.auth.getUser();
      const user = auth.user || null;
      const { data: posts, error } = await supabase.from('posts').select('*').eq('mint', mint).order('created_at', { ascending: false });
      if (!live) return;
      if (error) { setState((s) => ({ ...s, loading: false, user, error: error.message })); return; }
      const ids = (posts || []).map((post) => post.id);
      const authorIds = [...new Set((posts || []).map((post) => post.author_id))];
      const [profilesResult, commentsResult, reactionsResult, bookmarksResult, watchResult] = await Promise.all([
        authorIds.length ? supabase.from('profiles').select('*').in('id', authorIds) : { data: [] },
        ids.length ? supabase.from('comments').select('*').in('post_id', ids).order('created_at') : { data: [] },
        ids.length ? supabase.from('reactions').select('*').in('post_id', ids) : { data: [] },
        user && ids.length ? supabase.from('bookmarks').select('post_id').eq('user_id', user.id).in('post_id', ids) : { data: [] },
        user ? supabase.from('watchlist').select('id').eq('user_id', user.id).eq('mint', mint).maybeSingle() : { data: null },
      ]);
      if (!live) return;
      const profiles = Object.fromEntries((profilesResult.data || []).map((profile) => [profile.id, profile]));
      const comments = {}; (commentsResult.data || []).forEach((comment) => { (comments[comment.post_id] ||= []).push(comment); });
      const reactions = {}; (reactionsResult.data || []).forEach((reaction) => { reactions[reaction.post_id] = (reactions[reaction.post_id] || 0) + 1; });
      setState({ loading: false, posts: posts || [], profiles, comments, reactions, bookmarks: new Set((bookmarksResult.data || []).map((bookmark) => bookmark.post_id)), watched: Boolean(watchResult.data), user, error: '' });
    };
    void load();
    const channel = supabase.channel(`token-room:${mint}`).on('postgres_changes', { event: '*', schema: 'public', table: 'posts', filter: `mint=eq.${mint}` }, load).on('postgres_changes', { event: '*', schema: 'public', table: 'comments' }, load).on('postgres_changes', { event: '*', schema: 'public', table: 'reactions' }, load).subscribe();
    const { data: listener } = supabase.auth.onAuthStateChange(() => void load());
    return () => { live = false; listener.subscription.unsubscribe(); supabase.removeChannel(channel); };
  }, [mint]);
  return state;
}

export function TokenRoom({ mint, symbol }) {
  const room = useRoom(mint); const [kind, setKind] = useState('callout'); const [title, setTitle] = useState(''); const [body, setBody] = useState(''); const [busy, setBusy] = useState(false); const [message, setMessage] = useState('');
  const requireUser = () => { if (!room.user) { setMessage('Sign in to participate.'); return false; } return true; };
  const publish = async (event) => { event.preventDefault(); if (!requireUser() || !title.trim()) return; setBusy(true); const { error } = await supabase.from('posts').insert({ author_id: room.user.id, kind, mint, symbol, title: title.trim(), body: body.trim() }); setBusy(false); if (error) setMessage(error.message); else { setTitle(''); setBody(''); setMessage('Published.'); } };
  const toggleWatch = async () => { if (!requireUser()) return; setBusy(true); const query = room.watched ? supabase.from('watchlist').delete().eq('user_id', room.user.id).eq('mint', mint) : supabase.from('watchlist').insert({ user_id: room.user.id, mint, symbol }); const { error } = await query; setBusy(false); if (error) setMessage(error.message); };
  const react = async (post) => { if (!requireUser()) return; const { error } = await supabase.from('reactions').upsert({ post_id: post.id, user_id: room.user.id, emoji: '🔥' }); if (error) setMessage(error.message); };
  const bookmark = async (post) => { if (!requireUser()) return; const query = room.bookmarks.has(post.id) ? supabase.from('bookmarks').delete().eq('post_id', post.id).eq('user_id', room.user.id) : supabase.from('bookmarks').insert({ post_id: post.id, user_id: room.user.id }); const { error } = await query; if (error) setMessage(error.message); };
  const signIn = async () => { if (!supabase) return; const { error } = await supabase.auth.signInWithOAuth({ provider: 'google', options: { redirectTo: window.location.href } }); if (error) setMessage(error.message); };
  return <section className="tokenRoom">
    <div className="roomHead"><div><small>LIVE TOKEN ROOM</small><h2>{symbol || 'TOKEN'} discussion</h2><p>Real posts and replies from authenticated FEELESS identities.</p></div><div>{room.user ? <button className="btn" disabled={busy} onClick={toggleWatch}>{room.watched ? '★ Watching' : '☆ Watch token'}</button> : <button className="btn" onClick={signIn} disabled={!socialConfigured}>Sign in to participate</button>}</div></div>
    {!socialConfigured ? <div className="roomNotice">Set VITE_SUPABASE_URL and VITE_SUPABASE_PUBLISHABLE_KEY to enable the live room.</div> : <><form className="postComposer" onSubmit={publish}><div className="postKinds">{['callout', 'thesis', 'meta', 'watch'].map((value) => <button type="button" className={kind === value ? 'picked' : ''} onClick={() => setKind(value)} key={value}>{value}</button>)}</div><input value={title} onChange={(event) => setTitle(event.target.value)} maxLength="180" placeholder="Title your idea" disabled={!room.user || busy}/><textarea value={body} onChange={(event) => setBody(event.target.value)} maxLength="4000" placeholder="Share your research. Never publish private keys or sensitive information." disabled={!room.user || busy}/><div><button className="green" disabled={!room.user || busy || !title.trim()}>{busy ? 'Publishing…' : 'Publish to room'}</button>{message && <small className="roomMessage">{message}</small>}</div></form><div className="postList">{room.loading ? <div className="empty">Loading real room activity…</div> : room.posts.length === 0 ? <div className="empty">No posts yet. Be the first authenticated trader to share a thesis or callout.</div> : room.posts.map((post) => <Post key={post.id} post={post} profile={room.profiles[post.author_id]} comments={room.comments[post.id] || []} commentCount={(room.comments[post.id] || []).length} reactions={room.reactions[post.id] || 0} bookmarked={room.bookmarks.has(post.id)} onReact={() => react(post)} onBookmark={() => bookmark(post)} onMessage={setMessage}/>)}</div></>}
  </section>;
}

function Post({ post, profile, comments, commentCount, reactions, bookmarked, onReact, onBookmark, onMessage }) {
  const [open, setOpen] = useState(false); const [body, setBody] = useState(''); const [sending, setSending] = useState(false);
  const comment = async (event) => { event.preventDefault(); if (!body.trim()) return; const { data: auth } = await supabase.auth.getUser(); if (!auth.user) { onMessage('Sign in to comment.'); return; } setSending(true); const { error } = await supabase.from('comments').insert({ post_id: post.id, author_id: auth.user.id, body: body.trim() }); setSending(false); if (error) onMessage(error.message); else setBody(''); };
  const share = async () => { try { await navigator.clipboard.writeText(`${window.location.origin}/token/${post.mint}`); onMessage('Token room link copied.'); } catch { onMessage('Copy is unavailable in this browser.'); } };
  return <article className="socialPost"><div className="postMeta"><span className="postKind">{post.kind}</span><button onClick={() => profile?.handle && (window.location.href = `/creator/${profile.handle}`)}>{profile?.display_name || profile?.handle || 'Unknown creator'}</button><small>{relativeTime(post.created_at)}</small></div><h3>{post.title}</h3>{post.body && <p>{post.body}</p>}<div className="postActions"><button onClick={onReact}>🔥 {reactions || 'React'}</button><button onClick={() => setOpen(!open)}>◌ {commentCount || 'Comment'}</button><button onClick={onBookmark}>{bookmarked ? '★ Saved' : '☆ Save'}</button><button onClick={share}>↗ Share</button></div>{open && <><div className="commentList">{comments.map((item) => <p key={item.id}><b>Reply</b> · {relativeTime(item.created_at)}<br/>{item.body}</p>)}</div><form className="commentForm" onSubmit={comment}><input value={body} onChange={(event) => setBody(event.target.value)} maxLength="2000" placeholder="Reply to this post"/><button className="btn" disabled={sending || !body.trim()}>{sending ? 'Sending…' : 'Reply'}</button></form></>}</article>;
}
