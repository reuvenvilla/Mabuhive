"use strict";

function DefaultPage({ activePage, title, children }) {
  return (
    <div className="page">
      <NavBar activePage={activePage} />
      <main className="container">
        <h1>{title}</h1>
        {children}
      </main>
    </div>
  );
}


function renderPage() {
  const pageName = document.body.dataset.page;
  const root = ReactDOM.createRoot(document.getElementById("root"));

  switch (pageName) {
    case "home":
      root.render(
        <DefaultPage activePage="home" title="Welcome">
          <HomePageContent />
        </DefaultPage>
      );
      break;
    case "hives":
      root.render(
        <DefaultPage activePage="hives" title="Hives">
          <HivesPageContent />
        </DefaultPage>
      );
      break;
    case "quests":
      root.render(
        <DefaultPage activePage="quests" title="Quests">
          <QuestsPageContent />
        </DefaultPage>
      );
      break;
    case "journal":
      root.render(
        <DefaultPage activePage="journal" title="Journal">
          <JournalPageContent />
        </DefaultPage>
      );
      break;
    case "profile":
      root.render(
        <DefaultPage activePage="profile" title="Profile">
          <ProfilePageContent />
        </DefaultPage>
      );
      break;
    default:
      root.render(
        <DefaultPage activePage="" title="Page Not Found">
          <p>Unknown page: {pageName || "(missing)"}.</p>
        </DefaultPage>
      );
  }
}

renderPage();
