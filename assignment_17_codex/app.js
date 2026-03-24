const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

const revealItems = Array.from(document.querySelectorAll(".reveal"));
const form = document.querySelector("#contact-form");
const statusEl = document.querySelector("#contact-status");
const pulseMetrics = document.querySelector("#pulse-metrics");
const pulseStatus = document.querySelector("#pulse-status");
const pulseCommit = document.querySelector("#pulse-commit");
const pulseCommitStatus = document.querySelector("#pulse-commit-status");

if (prefersReducedMotion) {
  revealItems.forEach((item) => item.classList.add("is-visible"));
} else {
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        const delay = entry.target.getAttribute("data-delay");
        if (delay) {
          entry.target.style.setProperty("--delay", `${delay}ms`);
        }
        entry.target.classList.add("is-visible");
        observer.unobserve(entry.target);
      });
    },
    { threshold: 0.2 }
  );

  revealItems.forEach((item) => observer.observe(item));
}

if (form && statusEl) {
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    statusEl.textContent = "Sending...";
    const formData = new FormData(form);
    const payload = Object.fromEntries(formData.entries());

    try {
      const response = await fetch("/api/contact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        const message = data.error || "Something went wrong. Please try again.";
        statusEl.textContent = message;
        return;
      }

      statusEl.textContent = "Sent! We'll be in touch soon.";
      form.reset();
    } catch (error) {
      statusEl.textContent = "Network error. Please try again.";
    }
  });
}

async function loadGitHubPulse() {
  if (!pulseMetrics || !pulseStatus || !pulseCommit || !pulseCommitStatus) return;

  const repoUrl = "https://api.github.com/repos/openai/codex";
  const commitsUrl = "https://api.github.com/repos/openai/codex/commits?per_page=1";

  try {
    const [repoResponse, commitsResponse] = await Promise.all([
      fetch(repoUrl),
      fetch(commitsUrl),
    ]);

    if (!repoResponse.ok || !commitsResponse.ok) {
      throw new Error("GitHub API error");
    }

    const repoData = await repoResponse.json();
    const commitsData = await commitsResponse.json();

    const starsEl = pulseMetrics.querySelector("[data-metric='stars']");
    const forksEl = pulseMetrics.querySelector("[data-metric='forks']");
    const issuesEl = pulseMetrics.querySelector("[data-metric='issues']");

    if (starsEl) starsEl.textContent = repoData.stargazers_count?.toLocaleString() ?? "—";
    if (forksEl) forksEl.textContent = repoData.forks_count?.toLocaleString() ?? "—";
    if (issuesEl) issuesEl.textContent = repoData.open_issues_count?.toLocaleString() ?? "—";

    pulseStatus.textContent = "Updated just now from GitHub.";

    const latestCommit = commitsData?.[0];
    const commitMessage = latestCommit?.commit?.message?.split("\n")[0];
    const commitDateRaw = latestCommit?.commit?.author?.date;
    const commitDate = commitDateRaw ? new Date(commitDateRaw).toLocaleDateString() : null;

    if (commitMessage) {
      pulseCommit.textContent = `${commitMessage}${commitDate ? ` — ${commitDate}` : ""}`;
      pulseCommitStatus.textContent = "Pulled from the latest commit.";
    } else {
      pulseCommit.textContent = "No recent commit data available.";
      pulseCommitStatus.textContent = "";
    }
  } catch (error) {
    pulseStatus.textContent = "Could not load GitHub stats right now.";
    pulseCommit.textContent = "Unable to fetch the latest commit.";
    pulseCommitStatus.textContent = "";
  }
}

loadGitHubPulse();
