/**
 * frontend/static/js/components/PostForm.jsx
 * Depends on: React (global)
 * Props: onSubmit(payload) — called with form data on submit
 */

function PostForm({ onSubmit }) {
  const { useState } = React;

  const empty = { topic: "", title: "", description: "", author: "", body: "" };
  const [fields, setFields]   = useState(empty);
  const [error, setError]     = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);

  function handleChange(e) {
    setFields(prev => ({ ...prev, [e.target.name]: e.target.value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError(""); setSuccess("");

    const required = ["topic", "title", "author", "body"];
    const missing  = required.filter(k => !fields[k].trim());
    if (missing.length) {
      setError(`Required: ${missing.join(", ")}`);
      return;
    }

    setLoading(true);
    try {
      await onSubmit(fields);
      setSuccess("Post created!");
      setFields(empty);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <form className="post-form" onSubmit={handleSubmit}>
      <h2>New Post</h2>

      {[
        { name: "topic",       placeholder: "e.g. tech, food",    label: "Topic"       },
        { name: "title",       placeholder: "Post title",          label: "Title"       },
        { name: "description", placeholder: "One-line summary",    label: "Description" },
        { name: "author",      placeholder: "Your name",           label: "Author"      },
      ].map(({ name, placeholder, label }) => (
        <label key={name}>
          {label}
          <input
            name={name}
            value={fields[name]}
            placeholder={placeholder}
            onChange={handleChange}
          />
        </label>
      ))}

      <label>
        Body
        <textarea
          name="body"
          rows={7}
          value={fields.body}
          placeholder="Write your post here…"
          onChange={handleChange}
        />
      </label>

      {error   && <p className="form-error">{error}</p>}
      {success && <p className="form-success">{success}</p>}

      <button type="submit" disabled={loading}>
        {loading ? "Posting…" : "Post"}
      </button>
    </form>
  );
}
