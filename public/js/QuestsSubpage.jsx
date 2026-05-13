/**
 * public/js/QuestsSubpage.jsx
 * Quests page content component.
 *
 * /quests              -> all joined quests
 * /quests?quid=<quid>  -> specific quest detail page
 */

function QuestsPageContent() {
  const [activeTab, setActiveTab] = React.useState("replies");

  const quests = [
    {
      quid: "quest-boba-run-001",
      createdBy: "Nadia",
      createdAt: "2026-05-12T19:30:00",
      title: "Boba run tonight",
      content:
        "Anyone want to grab boba after study hall? Planning to leave from Powell around 7:30 PM.",
      imageUrl: "",
      hive: "Howlin' Homies",
      status: "Open",
      usersJoined: ["Nadia", "Reuven", "Vince", "Julian"],
      usersCompleted: ["Nadia", "Reuven"],
      visibility: {
        users: [],
        teams: ["Howlin' Homies"],
        hives: ["PIES"],
      },
      fulfillmentConditions: {
        type: "first_x_completed",
        label: "First X Completed",
        description: "The first 5 users who complete the quest receive credit.",
        requiredCompletions: 5,
      },
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
      quid: "quest-umbrella-needed-001",
      createdBy: "Victoria",
      createdAt: "2026-05-12T16:45:00",
      title: "Umbrella needed!!",
      content:
        "It started raining and I'm stranded in biomed, can someone with an umbrella walk with me?",
      imageUrl: "",
      hive: "Ponyo Pals",
      status: "Closed",
      usersJoined: ["Alianna"],
      usersCompleted: ["Alianna"],
      visibility: {
        users: [],
        teams: ["Ponyo Pals"],
        hives: ["PIES"],
      },
      fulfillmentConditions: {
        type: "creator_picked",
        label: "Creator Picked",
        description: "The creator chooses who successfully completed the quest.",
        requiredCompletions: 1,
      },
      replies: [
        {
          name: "Alianna",
          text: "I can come in 10 minutes with an umbrella!",
        },
      ],
    },
    {
      quid: "quest-bruin-bear-photo-001",
      createdBy: "Reuven",
      createdAt: "2026-05-12T14:15:00",
      title: "PIES photo at Bruin Bear",
      content:
        "Take a group picture at the Bruin Bear before another org gets there!",
      imageUrl: "",
      hive: "PIES",
      status: "Open",
      usersJoined: ["Reuven"],
      usersCompleted: [],
      visibility: {
        users: [],
        teams: [],
        hives: ["PIES"],
      },
      fulfillmentConditions: {
        type: "first_to_join",
        label: "First to Join",
        description: "The first group/user to join and submit proof completes the quest.",
        requiredCompletions: 1,
      },
      replies: [],
    },
  ];

  const params = new URLSearchParams(window.location.search);

  // Primary route param is quid. The questId/id fallback is just for older links.
  const selectedQUID =
    params.get("quid") || params.get("questId") || params.get("id");

  const selectedQuest = quests.find((quest) => quest.quid === selectedQUID);

  function openQuest(quid) {
    window.location.href = `/quests?quid=${quid}`;
  }

  function goBackToQuestList() {
    window.location.href = "/quests";
  }

  if (selectedQUID && selectedQuest) {
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

  if (selectedQUID && !selectedQuest) {
    return (
      <main className="quests-page">
        <button className="back-button" onClick={goBackToQuestList}>
          ← Back to all quests
        </button>

        <section className="empty-state-card">
          <h2>Quest not found</h2>
          <p>
            We couldn’t find a quest with the QUID{" "}
            <strong>{selectedQUID}</strong>.
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
            key={quest.quid}
            onClick={() => openQuest(quest.quid)}
          >
            <div className="quest-preview-top">
              <p className="quest-type">{quest.fulfillmentConditions.label}</p>
              <span className="quest-status">{quest.status}</span>
            </div>

            <h3>{quest.title}</h3>
            <p className="quest-preview-description">{quest.content}</p>

            <div className="quest-preview-meta">
              <span>{quest.hive}</span>
              <span>{quest.usersJoined.length} joined</span>
            </div>

            <div className="quest-preview-meta quest-preview-meta-secondary">
              <span>{quest.usersCompleted.length} completed</span>
              <span>{formatQuestDate(quest.createdAt)}</span>
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
            <p className="quest-type">{quest.fulfillmentConditions.label}</p>
            <h2>{quest.title}</h2>

            <p className="quest-creator">
              Created by {quest.createdBy} · {formatQuestDate(quest.createdAt)}
            </p>
          </div>

          <button className="join-button">Join</button>
        </div>

        <p className="quest-description">{quest.content}</p>

        {quest.imageUrl ? (
          <img className="quest-image" src={quest.imageUrl} alt={quest.title} />
        ) : (
          <div className="quest-image-placeholder">
            Optional quest image goes here
          </div>
        )}

        <div className="quest-progress">
          {quest.usersJoined.length} joined · {quest.usersCompleted.length} completed
        </div>

        <div className="quest-completion-card">
          <p className="quest-completion-label">How to complete</p>
          <h3>{quest.fulfillmentConditions.label}</h3>
          <p>{quest.fulfillmentConditions.description}</p>
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
            <QuestReplies replies={quest.replies} />
          ) : (
            <QuestUserList
              usersJoined={quest.usersJoined}
              usersCompleted={quest.usersCompleted}
            />
          )}
        </div>

        <button className="reply-button">Reply</button>
      </section>
    </React.Fragment>
  );
}

function QuestReplies({ replies }) {
  if (replies.length === 0) {
    return <p className="empty-panel-text">No replies yet.</p>;
  }

  return (
    <div className="reply-list">
      {replies.map((reply, index) => (
        <article className="reply-card" key={index}>
          <strong>{reply.name}</strong>
          <p>{reply.text}</p>
        </article>
      ))}
    </div>
  );
}

function QuestUserList({ usersJoined, usersCompleted }) {
  return (
    <div className="participant-list">
      <h3 className="participant-section-title">Users Joined</h3>

      {usersJoined.length > 0 ? (
        usersJoined.map((person, index) => (
          <div className="participant-row" key={`joined-${index}`}>
            <div className="participant-avatar">{person.charAt(0)}</div>
            <span>{person}</span>
          </div>
        ))
      ) : (
        <p className="empty-panel-text">No users have joined yet.</p>
      )}

      <h3 className="participant-section-title">Users Completed</h3>

      {usersCompleted.length > 0 ? (
        usersCompleted.map((person, index) => (
          <div className="participant-row" key={`completed-${index}`}>
            <div className="participant-avatar">{person.charAt(0)}</div>
            <span>{person}</span>
          </div>
        ))
      ) : (
        <p className="empty-panel-text">No users have completed this quest yet.</p>
      )}
    </div>
  );
}

function formatQuestDate(dateString) {
  return new Date(dateString).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function formatList(items) {
  return items.length > 0 ? items.join(", ") : "None";
}