/**
 * public/js/QuestsSubpage.jsx
 * Quests page content component.
 *
 * /quests                  -> all joined quests
 * /quests?questId=<id>     -> specific quest detail page
 */

function QuestsPageContent() {
  const [activeTab, setActiveTab] = React.useState("replies");

  const quests = [
    {
      id: "boba-run-tonight",
      title: "Boba run tonight",
      type: "Tag-a-Long Quest",
      description:
        "Anyone want to grab boba after study hall? Planning to leave from Powell around 7:30 PM.",
      imageUrl: "",
      creator: "Nadia",
      hive: "Howlin' Homies",
      status: "Open",
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
    },
    {
      id: "umbrella-needed",
      title: "Umbrella needed!!",
      type: "Fetch Quest",
      description:
        "It started raining and I'm stranded in biomed, can someone with an umbrella walk with me?",
      imageUrl: "",
      creator: "Victoria",
      hive: "Ponyo Pals",
      status: "Closed",
      participants: ["Alianna"],
      maxParticipants: 1,
      replies: [
        {
          name: "Alianna",
          text: "I can come in 10 minutes with an umbrella!",
        },
      ],
    },
    {
      id: "bruin-bear-photo",
      title: "PIES photo at Bruin Bear",
      type: "Race Quest",
      description:
        "Take a group picture at the Bruin Bear before another org gets there!",
      imageUrl: "",
      creator: "Reuven",
      hive: "PIES",
      status: "Open",
      participants: ["Reuven"],
      maxParticipants: 4,
      replies: [],
    },
  ];

  const params = new URLSearchParams(window.location.search);
  const selectedQuestId = params.get("questId") || params.get("id");

  const selectedQuest = quests.find((quest) => quest.id === selectedQuestId);

  function openQuest(questId) {
    window.location.href = `/quests?questId=${questId}`;
  }

  function goBackToQuestList() {
    window.location.href = "/quests";
  }

  if (selectedQuestId && selectedQuest) {
    return (
      <main className="quests-page">
        <button className="back-button" onClick={goBackToQuestList}>
          ← Back to all quests
        </button>

        <QuestDetail
          quest={selectedQuest}
          activeTab={activeTab}
          setActiveTab={setActiveTab}
        />
      </main>
    );
  }

  if (selectedQuestId && !selectedQuest) {
    return (
      <main className="quests-page">
        <button className="back-button" onClick={goBackToQuestList}>
          ← Back to all quests
        </button>

        <section className="empty-state-card">
          <h2>Quest not found</h2>
          <p>
            We couldn’t find a quest with the ID <strong>{selectedQuestId}</strong>.
          </p>
        </section>
      </main>
    );
  }

  return (
    <main className="quests-page">
      <section className="quests-landing-header">
        <div>
          <h2>My Quests</h2>
          <p>Quests you’ve joined across all your hives.</p>
        </div>
      </section>

      <section className="quest-grid">
        {quests.map((quest) => (
          <article
            className="quest-preview-card"
            key={quest.id}
            onClick={() => openQuest(quest.id)}
          >
            <div className="quest-preview-top">
              <p className="quest-type">{quest.type}</p>
              <span className="quest-status">{quest.status}</span>
            </div>

            <h3>{quest.title}</h3>
            <p className="quest-preview-description">{quest.description}</p>

            <div className="quest-preview-meta">
              <span>{quest.hive}</span>
              <span>
                {quest.participants.length}/{quest.maxParticipants} joined
              </span>
            </div>
          </article>
        ))}
      </section>
    </main>
  );
}

function QuestDetail({ quest, activeTab, setActiveTab }) {
  return (
    <React.Fragment>
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
              {quest.replies.length > 0 ? (
                quest.replies.map((reply, index) => (
                  <article className="reply-card" key={index}>
                    <strong>{reply.name}</strong>
                    <p>{reply.text}</p>
                  </article>
                ))
              ) : (
                <p className="empty-panel-text">No replies yet.</p>
              )}
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

        <button className="reply-button">Reply</button>
      </section>
    </React.Fragment>
  );
}