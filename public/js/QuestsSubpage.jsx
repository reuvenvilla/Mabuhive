/**
 * public/js/QuestsSubpage.jsx
 * Quests page content component.
 */

function QuestsPageContent() {
  const [activeTab, setActiveTab] = React.useState("replies");

  const quest = {
    title: "Boba run tonight",
    type: "Tag-a-Long Quest",
    description:
      "Anyone want to grab boba after study hall? Planning to leave from Powell around 7:30 PM.",
    imageUrl: "",
    creator: "Nadia",
    participants: ["Nadia", "Reuven", "Vince", "Julian"],
    maxParticipants: 5,
    replies: [
      {
        name: "Reuven",
        text: "Down! What place are we thinking?",
      },
      {
        name: "Vince",
        text: "I can join if it’s after 7!",
      },
    ],
  };

  return (
    <main className="quests-page">
      <section className="quest-card">
        <div className="quest-card-header">
          <div>
            <p className="quest-type">{quest.type}</p>
            <h2>{quest.title}</h2>
            <p className="quest-creator">Posted by {quest.creator}</p>
          </div>

          <button className="join-button">Join</button>
        </div>

        <p className="quest-description">{quest.description}</p>

        {quest.imageUrl ? (
          <img className="quest-image" src={quest.imageUrl} alt={quest.title} />
        ) : (
          <div className="quest-image-placeholder">
            Optional quest image goes here
          </div>
        )}

        <div className="quest-progress">
          {quest.participants.length}/{quest.maxParticipants} joined
        </div>
      </section>

      <section className="quest-panel">
        <div className="quest-tabs">
          <button
            className={activeTab === "replies" ? "tab active" : "tab"}
            onClick={() => setActiveTab("replies")}
          >
            Replies
          </button>

          <button
            className={activeTab === "participants" ? "tab active" : "tab"}
            onClick={() => setActiveTab("participants")}
          >
            List
          </button>
        </div>

        <div className="quest-panel-content">
          {activeTab === "replies" ? (
            <div className="reply-list">
              {quest.replies.map((reply, index) => (
                <article className="reply-card" key={index}>
                  <strong>{reply.name}</strong>
                  <p>{reply.text}</p>
                </article>
              ))}
            </div>
          ) : (
            <div className="participant-list">
              {quest.participants.map((person, index) => (
                <div className="participant-row" key={index}>
                  <div className="participant-avatar">
                    {person.charAt(0)}
                  </div>
                  <span>{person}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        <button className="reply-button">
          Reply
        </button>
      </section>
    </main>
  );
}
