/**
 * frontend/static/js/components/PostCard.jsx
 * Depends on: React (global), formatDate (global from utils.js)
 */

function PostCard({ post }) {
  return (
    <article className="post-card">
      <span className="post-topic">{post.topic}</span>
      <h2 className="post-title">{post.title}</h2>
      {post.description && <p className="post-description">{post.description}</p>}
      <p className="post-body">{post.body}</p>
      <footer className="post-meta">
        By <strong>{post.author}</strong> &middot; {formatDate(post.created_at)}
      </footer>
    </article>
  );
}
