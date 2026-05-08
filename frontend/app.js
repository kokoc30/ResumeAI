const _loc = window.location;
const _devFrontendPorts = new Set(["5500", "5501", "5173"]);
const API_BASE_URL = _devFrontendPorts.has(_loc.port)
  ? "http://127.0.0.1:8000/api"
  : `${_loc.origin}/api`;
const API_URL = `${API_BASE_URL}/analyze`;
const CHAT_URL = `${API_BASE_URL}/chat`;
const CHAT_STATUS_URL = `${API_BASE_URL}/chat/status`;

const form = document.querySelector("#analyzerForm");
const fileInput = document.querySelector("#resumeFile");
const uploadZone = document.querySelector("#uploadZone");
const fileStatus = document.querySelector("#fileStatus");
const fileError = document.querySelector("#fileError");
const jobDescription = document.querySelector("#jobDescription");
const jobError = document.querySelector("#jobError");
const jobCounter = document.querySelector("#jobCounter");
const formMessage = document.querySelector("#formMessage");
const analyzeButton = document.querySelector(".analyze-button");
const resetButton = document.querySelector("#resetButton");
const resultsStatus = document.querySelector("#resultsStatus");
const resultsAlert = document.querySelector("#resultsAlert");
const loadingCard = document.querySelector("#loadingCard");
const resultsGrid = document.querySelector("#resultsGrid");
const scoreRing = document.querySelector("#scoreRing");
const scoreValue = document.querySelector("#scoreValue");
const scoreLabel = document.querySelector("#scoreLabel");
const scoreBar = document.querySelector("#scoreBar");
const scoreNote = document.querySelector("#scoreNote");
const summaryText = document.querySelector("#summaryText");
const matchedSkillsList = document.querySelector("#matchedSkillsList");
const missingSkillsList = document.querySelector("#missingSkillsList");
const suggestionsList = document.querySelector("#suggestionsList");
const resultTabsSummary = document.querySelector("#resultTabsSummary");
const resultTabButtons = document.querySelectorAll("[data-result-tab]");
const resultTabPanels = document.querySelectorAll("[data-tab-panel]");
const resultTabCountElements = document.querySelectorAll("[data-result-count]");
const evidenceList = document.querySelector("#evidenceList");
const chatStatusText = document.querySelector("#chatStatusText");
const chatMessagesContainer = document.querySelector("#chatMessages");
const chatForm = document.querySelector("#chatForm");
const chatInput = document.querySelector("#chatInput");
const chatSendButton = document.querySelector("#chatSendButton");
const chatFeedback = document.querySelector("#chatFeedback");
const suggestedQuestionButtons = document.querySelectorAll(".suggested-question");
const quickQuestions = document.querySelector(".quick-questions");
const chatWidget = document.querySelector("#chatWidget");
const chatLauncher = document.querySelector("#chatLauncher");
const chatPopup = document.querySelector("#chatPopup");
const chatCloseBtn = document.querySelector("#chatCloseBtn");

const allowedExtensions = [".pdf", ".docx"];
const evidenceSnippetLimit = 260;
const resultTabKeys = ["matched", "missing", "actions"];
let isAnalyzing = false;
let latestAnalysisContext = null;
let chatMessages = [];
let chatIsSending = false;
let chatStatus = { state: "checking" };
let chatRequestId = 0;
let lastFailedChatMessage = "";
let selectedResultTab = "matched";
let chatPopupOpen = false;
let resultTabCounts = {
  matched: 0,
  missing: 0,
  actions: 0,
};

function openChatPopup() {
  chatPopupOpen = true;
  chatPopup.classList.remove("hidden");
  chatLauncher.setAttribute("aria-expanded", "true");
}

function closeChatPopup() {
  chatPopupOpen = false;
  chatPopup.classList.add("hidden");
  chatLauncher.setAttribute("aria-expanded", "false");
}

function toggleChatPopup() {
  if (chatPopupOpen) {
    closeChatPopup();
  } else {
    openChatPopup();
  }
}

function getFileExtension(fileName) {
  const dotIndex = fileName.lastIndexOf(".");
  return dotIndex >= 0 ? fileName.slice(dotIndex).toLowerCase() : "";
}

function formatFileSize(bytes) {
  if (!Number.isFinite(bytes) || bytes <= 0) {
    return "";
  }

  if (bytes < 1024 * 1024) {
    return `${Math.round(bytes / 1024)} KB`;
  }

  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function truncateText(text, maxLength = evidenceSnippetLimit) {
  const cleanText = String(text || "").replace(/\s+/g, " ").trim();
  if (cleanText.length <= maxLength) {
    return cleanText;
  }

  return `${cleanText.slice(0, maxLength - 3).trim()}...`;
}

function getScoreLabel(score) {
  if (score >= 85) {
    return "Excellent Match";
  }

  if (score >= 70) {
    return "Strong Match";
  }

  if (score >= 50) {
    return "Moderate Match";
  }

  if (score >= 30) {
    return "Partial Match";
  }

  return "Specialized Gap";
}

function setFormMessage(message, type = "neutral") {
  formMessage.textContent = message;
  formMessage.classList.remove("error", "success");

  if (type === "error") {
    formMessage.classList.add("error");
  }

  if (type === "success") {
    formMessage.classList.add("success");
  }
}

function setFileError(message) {
  fileError.textContent = message;
  uploadZone.classList.toggle("has-error", Boolean(message));
}

function setJobError(message) {
  jobError.textContent = message;
  jobDescription.classList.toggle("has-error", Boolean(message));
}

function updateJobCounter() {
  const count = jobDescription.value.length;
  const label = count === 1 ? "character" : "characters";
  jobCounter.textContent = `${count} ${label}`;
}

function updateSelectedFileText(file) {
  const fileSize = formatFileSize(file.size);
  fileStatus.textContent = fileSize
    ? `Selected: ${file.name} (${fileSize})`
    : `Selected: ${file.name}`;
}

function validateFile(showMessage = true) {
  const file = fileInput.files[0];

  if (!file) {
    uploadZone.classList.remove("has-file");
    fileStatus.textContent = "No resume selected yet.";
    if (showMessage) {
      setFileError("Please choose a PDF or DOCX resume before analyzing.");
    }
    return false;
  }

  const extension = getFileExtension(file.name);
  if (!allowedExtensions.includes(extension)) {
    uploadZone.classList.remove("has-file");
    fileStatus.textContent = file.name;
    setFileError("Unsupported file type. Please upload a .pdf or .docx file.");
    return false;
  }

  uploadZone.classList.add("has-file");
  setFileError("");
  updateSelectedFileText(file);
  return true;
}

function validateJobDescription() {
  if (!jobDescription.value.trim()) {
    setJobError("Please paste a job description before analyzing.");
    return false;
  }

  setJobError("");
  return true;
}

function clearElement(element) {
  while (element.firstChild) {
    element.removeChild(element.firstChild);
  }
}

function createElement(tagName, className, textContent) {
  const element = document.createElement(tagName);
  if (className) {
    element.className = className;
  }
  if (textContent !== undefined) {
    element.textContent = textContent;
  }
  return element;
}

function showElement(element) {
  if (!element) {
    return;
  }

  element.hidden = false;
  element.classList.remove("hidden");
}

function hideElement(element) {
  if (!element) {
    return;
  }

  element.hidden = true;
  element.classList.add("hidden");
}

function safeArray(value) {
  return Array.isArray(value) ? value : [];
}

function normalizeDisplayText(text, fallback = "") {
  return String(text || fallback).replace(/\s+/g, " ").trim();
}

function pluralize(count, singular, plural = `${singular}s`) {
  return `${count} ${count === 1 ? singular : plural}`;
}

function getActionSteps(result = {}) {
  const seen = new Set();
  return [...safeArray(result.resume_suggestions), ...safeArray(result.action_steps)]
    .map((item) => String(item || "").trim())
    .filter((item) => {
      if (!item || seen.has(item)) {
        return false;
      }
      seen.add(item);
      return true;
    });
}

function renderEmpty(container, message, tagName = "p") {
  clearElement(container);
  container.appendChild(createElement(tagName, "empty-state", message));
}

function setResultTabCounts(counts = {}) {
  resultTabCounts = {
    matched: Number(counts.matched) || 0,
    missing: Number(counts.missing) || 0,
    actions: Number(counts.actions) || 0,
  };
}

function getDefaultResultTab(counts = resultTabCounts) {
  if (counts.missing > 0) {
    return "missing";
  }

  if (counts.matched > 0) {
    return "matched";
  }

  if (counts.actions > 0) {
    return "actions";
  }

  return "matched";
}

function updateResultTabsUi() {
  if (!resultTabKeys.includes(selectedResultTab)) {
    selectedResultTab = getDefaultResultTab();
  }

  resultTabButtons.forEach((button) => {
    const isActive = button.dataset.resultTab === selectedResultTab;
    button.classList.toggle("active", isActive);
    button.setAttribute("aria-selected", String(isActive));
    button.tabIndex = isActive ? 0 : -1;
  });

  resultTabPanels.forEach((panel) => {
    const isActive = panel.dataset.tabPanel === selectedResultTab;
    panel.hidden = !isActive;
    panel.classList.toggle("hidden", !isActive);
  });

  resultTabCountElements.forEach((element) => {
    const key = element.dataset.resultCount;
    element.textContent = String(resultTabCounts[key] || 0);
  });

  resultTabsSummary.textContent = [
    `${resultTabCounts.matched} matched`,
    `${resultTabCounts.missing} missing`,
    pluralize(resultTabCounts.actions, "action step"),
  ].join(" / ");
}

function setSelectedResultTab(tabKey) {
  if (!resultTabKeys.includes(tabKey)) {
    return;
  }

  selectedResultTab = tabKey;
  updateResultTabsUi();
}

function initializeResultTabs(counts) {
  setResultTabCounts(counts);
  selectedResultTab = getDefaultResultTab(resultTabCounts);
  updateResultTabsUi();
}

function buildSafeAnalysisContext(data) {
  const result = data && typeof data === "object" ? data : {};

  return {
    match_score: result.match_score,
    summary: result.summary,
    matched_skills: safeArray(result.matched_skills).map((item = {}) => ({
      skill: item.skill,
      confidence: item.confidence,
      resume_evidence: item.resume_evidence,
    })),
    missing_skills: safeArray(result.missing_skills).map((item = {}) => ({
      skill: item.skill,
      importance: item.importance,
      suggestion: item.suggestion,
    })),
    resume_suggestions: safeArray(result.resume_suggestions),
    action_steps: safeArray(result.action_steps),
    top_resume_matches: safeArray(result.top_resume_matches).map((item = {}) => ({
      job_requirement: item.job_requirement,
      resume_chunk: item.resume_chunk,
      similarity_score: item.similarity_score,
    })),
  };
}

function setChatFeedback(message, type = "neutral") {
  chatFeedback.textContent = message;
  chatFeedback.classList.remove("error");

  if (type === "error") {
    chatFeedback.classList.add("error");
  }
}

function formatProviderName(provider) {
  const value = String(provider || "").trim();
  if (!value) {
    return "Ollama";
  }

  return value.charAt(0).toUpperCase() + value.slice(1).toLowerCase();
}

function normalizeChatMode(mode) {
  const value = String(mode || "").trim().toLowerCase();
  return ["local", "cloud"].includes(value) ? value : "";
}

function getChatStatusState() {
  if (chatStatus && chatStatus.state === "checking") {
    return {
      text: "Checking AI status...",
      className: "chat-status-chip chat-status--warning",
      launcherTitle: "Checking Resume Assistant status",
    };
  }

  if (chatStatus && chatStatus.state === "unavailable") {
    return {
      text: "AI status unavailable",
      className: "chat-status-chip chat-status--warning",
      launcherTitle: "Resume Assistant status unavailable",
    };
  }

  if (chatStatus && chatStatus.llm_enabled === true) {
    const mode = normalizeChatMode(chatStatus.mode);
    const provider = formatProviderName(chatStatus.provider);
    const model = chatStatus.model || "llama3.2:1b";
    if (mode === "cloud") {
      return {
        text: `Cloud AI: ${provider} / ${model}`,
        className: "chat-status-chip chat-status--cloud",
        launcherTitle: `Resume Assistant using Ollama Cloud (${model})`,
      };
    }

    if (mode === "local") {
      return {
        text: `Local AI: ${provider} / ${model}`,
        className: "chat-status-chip chat-status--local",
        launcherTitle: `Resume Assistant using local Ollama (${model})`,
      };
    }

    return {
      text: `AI enabled: ${provider} / ${model}`,
      className: "chat-status-chip chat-status--local",
      launcherTitle: `Resume Assistant using ${provider} (${model})`,
    };
  }

  if (chatStatus && chatStatus.llm_enabled === false) {
    return {
      text: "AI disabled: fallback guidance",
      className: "chat-status-chip chat-status--disabled",
      launcherTitle: "Resume Assistant using fallback guidance",
    };
  }

  return {
    text: "AI status unavailable",
    className: "chat-status-chip chat-status--warning",
    launcherTitle: "Resume Assistant status unavailable",
  };
}

function updateChatUi() {
  const hasContext = Boolean(latestAnalysisContext);
  const canSend = hasContext && !chatIsSending;
  const statusState = getChatStatusState();

  chatInput.disabled = !canSend;
  chatInput.placeholder = hasContext
    ? "Ask what to improve..."
    : "Run an analysis to ask AI";
  chatSendButton.disabled = !canSend;
  chatSendButton.textContent = chatIsSending ? "Sending..." : "Send";
  chatForm.setAttribute("aria-busy", String(chatIsSending));
  chatLauncher.classList.toggle("is-ready", hasContext);
  chatLauncher.setAttribute(
    "aria-label",
    hasContext
      ? statusState.launcherTitle || "Open Resume Assistant chat"
      : "Open Resume Assistant chat. Run an analysis first to use the assistant.",
  );
  chatLauncher.title = hasContext
    ? statusState.launcherTitle || "Open Resume Assistant chat"
    : "Run an analysis first to use the assistant.";
  if (quickQuestions) {
    quickQuestions.setAttribute("aria-disabled", String(!canSend));
  }
  if (chatStatusText) {
    chatStatusText.textContent = statusState.text;
    chatStatusText.className = statusState.className;
  }

  suggestedQuestionButtons.forEach((button) => {
    button.disabled = !canSend;
  });
}

function isBulletLine(line) {
  return /^\s*(?:[-*\u2022]\s+|\d+[.)]\s+)/.test(line);
}

function cleanBulletLine(line) {
  return line.replace(/^\s*(?:[-*\u2022]\s+|\d+[.)]\s+)/, "").trim();
}

function cleanChatDisplayText(text) {
  return String(text || "").replace(/\*\*([^*]+)\*\*/g, "$1").trim();
}

function normalizeAssistantContent(content) {
  return String(content || "")
    .replace(/\r\n/g, "\n")
    .replace(/(^|\s)(?:\u2022|\u00e2\u0080\u00a2)\s+/g, "$1\n- ")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function appendParagraph(container, lines) {
  const text = cleanChatDisplayText(
    lines.map((line) => line.trim()).filter(Boolean).join(" "),
  );
  if (text) {
    container.appendChild(createElement("p", "", text));
  }
}

function appendBulletList(container, lines) {
  const list = createElement("ul", "chat-bullet-list");
  lines.forEach((line) => {
    const text = cleanChatDisplayText(cleanBulletLine(line));
    if (text) {
      list.appendChild(createElement("li", "", text));
    }
  });

  if (list.children.length > 0) {
    container.appendChild(list);
  }
}

function appendFormattedMessageContent(container, content, role) {
  const text =
    role === "assistant"
      ? normalizeAssistantContent(content)
      : String(content || "").replace(/\r\n/g, "\n").trim();
  if (!text) {
    container.appendChild(createElement("p", "", ""));
    return;
  }

  if (role !== "assistant") {
    container.appendChild(createElement("p", "", text));
    return;
  }

  const lines = text.split("\n");
  let paragraphLines = [];
  let bulletLines = [];

  function flushParagraph() {
    if (paragraphLines.length > 0) {
      appendParagraph(container, paragraphLines);
      paragraphLines = [];
    }
  }

  function flushBullets() {
    if (bulletLines.length > 0) {
      appendBulletList(container, bulletLines);
      bulletLines = [];
    }
  }

  lines.forEach((line) => {
    const trimmed = line.trim();
    if (!trimmed) {
      flushParagraph();
      flushBullets();
      return;
    }

    if (isBulletLine(trimmed)) {
      flushParagraph();
      bulletLines.push(trimmed);
      return;
    }

    flushBullets();
    paragraphLines.push(trimmed);
  });

  flushParagraph();
  flushBullets();
}

function renderChatMessages() {
  clearElement(chatMessagesContainer);

  chatMessages.forEach((message = {}) => {
    const role = message.role || "system";
    const bubble = createElement("article", `chat-message ${role}`);
    appendFormattedMessageContent(bubble, message.content || "", role);

    if (message.canRetry) {
      const retryButton = createElement("button", "chat-retry-button", "Try again");
      retryButton.type = "button";
      retryButton.addEventListener("click", () => {
        retryLastChatMessage();
      });
      bubble.appendChild(retryButton);
    }

    chatMessagesContainer.appendChild(bubble);
  });

  if (chatIsSending) {
    const loadingBubble = createElement("article", "chat-message system");
    loadingBubble.appendChild(
      createElement("p", "", "Assistant is preparing a response..."),
    );
    chatMessagesContainer.appendChild(loadingBubble);
  }

  chatMessagesContainer.scrollTop = chatMessagesContainer.scrollHeight;
}

function setChatMessages(messages) {
  chatMessages = messages;
  renderChatMessages();
  updateChatUi();
}

function addChatMessage(role, content) {
  chatMessages.push({ role, content });
  renderChatMessages();
}

function addChatError(content, canRetry = false) {
  chatMessages.push({ role: "error", content, canRetry });
  renderChatMessages();
}

function resetChat(message = "Run an analysis first to enable chat.") {
  chatRequestId += 1;
  latestAnalysisContext = null;
  chatIsSending = false;
  lastFailedChatMessage = "";
  chatInput.value = "";
  setChatFeedback("");
  setChatMessages([{ role: "system", content: message }]);
}

function enableChatForAnalysis(data) {
  chatRequestId += 1;
  latestAnalysisContext = buildSafeAnalysisContext(data);
  chatIsSending = false;
  lastFailedChatMessage = "";
  chatInput.value = "";
  setChatFeedback("");
  setChatMessages([
    {
      role: "assistant",
      content:
        "Analysis complete. Ask me what to improve first, why your score changed, or how to tailor your resume.",
    },
  ]);
}

function clearResultAlert() {
  resultsAlert.textContent = "";
  resultsAlert.className = "result-alert";
  hideElement(resultsAlert);
}

function showResultError(message) {
  const cleanMessage = String(message || "").trim();
  if (!cleanMessage) {
    clearResultAlert();
    return;
  }

  resultsAlert.className = "result-alert error-box";
  resultsAlert.textContent = cleanMessage;
  showElement(resultsAlert);
}

function resetResults() {
  clearResultAlert();
  hideElement(loadingCard);
  resultsGrid.classList.remove("is-dimmed");
  resultsStatus.textContent = "Waiting for analysis";

  scoreValue.textContent = "--";
  scoreLabel.textContent = "Awaiting analysis";
  scoreRing.className = "score-ring";
  scoreRing.style.setProperty("--score-percent", "0%");
  scoreRing.setAttribute("aria-label", "No score yet");
  scoreBar.style.width = "0%";
  scoreNote.textContent =
    "Specialized roles may score lower when core domain requirements are missing. This score is an estimate, not a hiring decision.";
  summaryText.textContent =
    "Results will appear here after the backend analyzes your resume and job description.";
  renderEmpty(matchedSkillsList, "No matched skills found yet.");
  renderEmpty(
    missingSkillsList,
    "No major missing skills detected from the keyword list.",
  );
  renderEmpty(suggestionsList, "No suggestions returned yet.", "li");
  renderEmpty(evidenceList, "Selected semantic resume evidence will appear here.");
  initializeResultTabs({ matched: 0, missing: 0, actions: 0 });
}

function resetResultsForNewAnalysis() {
  resetResults();
  resetChat("Preparing a new analysis. Chat will reset when results are ready.");
  resultsStatus.textContent = "Preparing analysis";
}

function setLoading(isLoading) {
  isAnalyzing = isLoading;
  analyzeButton.disabled = isLoading;
  resetButton.disabled = isLoading;
  analyzeButton.textContent = isLoading ? "Analyzing..." : "Analyze match";
  form.setAttribute("aria-busy", String(isLoading));
  resultsGrid.classList.toggle("is-dimmed", isLoading);

  if (isLoading) {
    clearResultAlert();
    showElement(loadingCard);
    resultsStatus.textContent = "Analyzing";
    setFormMessage(
      "Analyzing resume, extracting skills, and searching semantic evidence...",
    );
  } else {
    hideElement(loadingCard);
  }
}

function formatApiDetail(detail) {
  if (!detail) {
    return "";
  }

  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail)) {
    return detail
      .map((item) => item.msg || item.detail || JSON.stringify(item))
      .join(" ");
  }

  if (typeof detail === "object") {
    return detail.message || detail.detail || JSON.stringify(detail);
  }

  return String(detail);
}

async function readJsonSafely(response) {
  const contentType = response.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) {
    return null;
  }
  return response.json();
}

function renderError(message) {
  resultsStatus.textContent = "Needs attention";
  resultsGrid.classList.remove("is-dimmed");
  hideElement(loadingCard);
  showResultError(message);
  setFormMessage(message || "Something went wrong while analyzing your resume.", "error");
}

function renderScore(score) {
  const safeScore = Math.max(0, Math.min(100, Number(score) || 0));
  const label = getScoreLabel(safeScore);
  scoreValue.textContent = `${safeScore}`;
  scoreLabel.textContent = label;
  scoreRing.className = `score-ring score-${label
    .toLowerCase()
    .replace(/\s+/g, "-")}`;
  scoreRing.style.setProperty("--score-percent", `${safeScore}%`);
  scoreRing.setAttribute(
    "aria-label",
    `Estimated match score ${safeScore} out of 100, ${label}`,
  );
  scoreBar.style.width = `${safeScore}%`;
  scoreNote.textContent =
    "Specialized roles may score lower when core domain requirements are missing. This score is an estimate, not a hiring decision.";
}

function renderMatchedSkills(skills) {
  const items = safeArray(skills);
  clearElement(matchedSkillsList);

  if (items.length === 0) {
    renderEmpty(matchedSkillsList, "No matched skills found yet.");
    return;
  }

  items.forEach((item = {}) => {
    const card = createElement("article", "data-card skill-card");
    const header = createElement("div", "data-card-header");
    header.appendChild(createElement("h3", "", item.skill || "Matched skill"));
    header.appendChild(
      createElement("span", "pill success", item.confidence || "matched"),
    );

    card.appendChild(header);
    card.appendChild(
      createElement(
        "p",
        "data-card-text",
        normalizeDisplayText(
          item.resume_evidence,
          "Resume evidence was detected for this skill.",
        ),
      ),
    );
    matchedSkillsList.appendChild(card);
  });
}

function renderMissingSkills(skills) {
  const items = safeArray(skills);
  clearElement(missingSkillsList);

  if (items.length === 0) {
    renderEmpty(
      missingSkillsList,
      "No major missing skills detected from the keyword list.",
    );
    return;
  }

  missingSkillsList.appendChild(
    createElement(
      "p",
      "honest-note",
      "Only add missing skills if you can support them with real experience.",
    ),
  );

  items.forEach((item = {}) => {
    const card = createElement("article", "data-card missing-card");
    const header = createElement("div", "data-card-header");
    header.appendChild(createElement("h3", "", item.skill || "Missing skill"));
    header.appendChild(
      createElement("span", "pill warning", item.importance || "missing"),
    );

    card.appendChild(header);
    card.appendChild(
      createElement(
        "p",
        "data-card-text",
        normalizeDisplayText(
          item.suggestion,
          "Add this only if you have real experience with it.",
        ),
      ),
    );

    missingSkillsList.appendChild(card);
  });
}

function renderSuggestions(suggestions) {
  const items = safeArray(suggestions);
  clearElement(suggestionsList);

  if (items.length === 0) {
    renderEmpty(suggestionsList, "No suggestions returned.", "li");
    return;
  }

  items.forEach((suggestion) => {
    suggestionsList.appendChild(
      createElement("li", "", normalizeDisplayText(suggestion)),
    );
  });
}

function renderEvidence(matches) {
  const items = safeArray(matches);
  clearElement(evidenceList);

  if (items.length === 0) {
    renderEmpty(evidenceList, "No semantic resume evidence returned.");
    return;
  }

  items.forEach((item = {}) => {
    const card = createElement("article", "evidence-card");
    const header = createElement("div", "evidence-header");
    header.appendChild(
      createElement("h3", "", item.job_requirement || "Job requirement"),
    );

    const similarity = Number(item.similarity_score);
    const scoreLabel = Number.isFinite(similarity)
      ? `${Math.round(similarity * 100)}% match`
      : "semantic match";
    header.appendChild(createElement("span", "pill neutral", scoreLabel));

    card.appendChild(header);
    card.appendChild(
      createElement(
        "p",
        "evidence-text",
        truncateText(
          item.resume_chunk || "No resume evidence text returned.",
          evidenceSnippetLimit,
        ),
      ),
    );
    evidenceList.appendChild(card);
  });
}

function renderResults(data) {
  hideElement(loadingCard);
  clearResultAlert();
  resultsStatus.textContent = "Analysis complete";
  resultsGrid.classList.remove("is-dimmed");

  const result = data && typeof data === "object" ? data : {};
  const matchedSkills = safeArray(result.matched_skills);
  const missingSkills = safeArray(result.missing_skills);
  const actionSteps = getActionSteps(result);

  renderScore(result.match_score);
  summaryText.textContent = result.summary || "No summary returned.";
  renderMatchedSkills(matchedSkills);
  renderMissingSkills(missingSkills);
  renderSuggestions(actionSteps);
  initializeResultTabs({
    matched: matchedSkills.length,
    missing: missingSkills.length,
    actions: actionSteps.length,
  });
  renderEvidence(result.top_resume_matches);
  enableChatForAnalysis(result);
}

async function analyzeResume() {
  const formData = new FormData();
  formData.append("resume_file", fileInput.files[0]);
  formData.append("job_description", jobDescription.value.trim());

  const response = await fetch(API_URL, {
    method: "POST",
    body: formData,
  });

  const data = await readJsonSafely(response);
  if (!response.ok) {
    const detail = data ? formatApiDetail(data.detail) : "";
    throw new Error(
      detail || "Something went wrong while analyzing your resume.",
    );
  }

  if (!data || typeof data !== "object") {
    throw new Error("Backend returned an unexpected response.");
  }

  return data;
}

async function loadChatStatus() {
  try {
    const response = await fetch(CHAT_STATUS_URL);
    const data = await readJsonSafely(response);
    if (!response.ok || !data || typeof data !== "object") {
      throw new Error("Chat status unavailable");
    }
    chatStatus = {
      state: "ready",
      llm_enabled: Boolean(data.llm_enabled),
      provider: data.provider || "ollama",
      mode: normalizeChatMode(data.mode),
      model: data.model || "llama3.2:1b",
    };
  } catch (_error) {
    chatStatus = { state: "unavailable" };
  } finally {
    updateChatUi();
  }
}

async function sendChatMessage(userMessage) {
  const sanitizedAnalysisContext = latestAnalysisContext;

  const response = await fetch(CHAT_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      message: userMessage,
      analysis_context: sanitizedAnalysisContext,
    }),
  });

  const data = await readJsonSafely(response);
  if (!response.ok) {
    const detail = data ? formatApiDetail(data.detail) : "";
    throw new Error(detail || "Chat request could not be completed.");
  }

  if (!data || typeof data !== "object" || typeof data.answer !== "string") {
    throw new Error("Chat returned an unexpected response.");
  }

  chatStatus = {
    state: "ready",
    llm_enabled: Boolean(data.llm_enabled),
    provider: data.provider || "ollama",
    mode: normalizeChatMode(data.mode) || normalizeChatMode(chatStatus.mode),
    model: data.model || "llama3.2:1b",
  };

  return data.answer;
}

async function submitChatMessage(userMessage, options = {}) {
  if (chatIsSending) {
    return;
  }

  const cleanMessage = String(userMessage || "").trim();
  if (!cleanMessage) {
    setChatFeedback("Enter a question before sending.", "error");
    return;
  }

  if (!latestAnalysisContext) {
    setChatFeedback("Run an analysis first to enable chat.", "error");
    addChatError("Run an analysis first to enable chat.");
    return;
  }

  const requestId = ++chatRequestId;
  chatInput.value = "";
  setChatFeedback("");
  lastFailedChatMessage = "";

  if (!options.isRetry) {
    addChatMessage("user", cleanMessage);
  }

  chatIsSending = true;
  renderChatMessages();
  updateChatUi();

  try {
    const answer = await sendChatMessage(cleanMessage);
    if (requestId !== chatRequestId) {
      return;
    }
    addChatMessage("assistant", answer);
  } catch (error) {
    if (requestId !== chatRequestId) {
      return;
    }
    const isNetworkError =
      error instanceof TypeError || error.message === "Failed to fetch";
    const message = isNetworkError
      ? "Chat is unavailable right now. Make sure the backend is running."
      : error.message || "Chat request could not be completed.";
    lastFailedChatMessage = cleanMessage;
    addChatError(message, isNetworkError);
    setChatFeedback(
      isNetworkError ? "Chat failed. You can try again." : message,
      "error",
    );
  } finally {
    if (requestId === chatRequestId) {
      chatIsSending = false;
      renderChatMessages();
      updateChatUi();
    }
  }
}

function retryLastChatMessage() {
  if (!lastFailedChatMessage || chatIsSending || !latestAnalysisContext) {
    return;
  }

  chatMessages = chatMessages.map((message) => ({
    ...message,
    canRetry: false,
  }));
  renderChatMessages();
  submitChatMessage(lastFailedChatMessage, { isRetry: true });
}

fileInput.addEventListener("change", () => {
  validateFile(false);
  setFormMessage("Complete both inputs to prepare an analysis.");
});

jobDescription.addEventListener("input", () => {
  updateJobCounter();
  if (jobDescription.value.trim()) {
    setJobError("");
  }
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  if (isAnalyzing) {
    return;
  }

  const hasValidFile = validateFile(true);
  const hasValidJobDescription = validateJobDescription();

  if (!hasValidFile || !hasValidJobDescription) {
    setFormMessage("Please fix the highlighted fields before continuing.", "error");
    return;
  }

  resetResultsForNewAnalysis();
  setLoading(true);

  try {
    const data = await analyzeResume();
    renderResults(data);
    setFormMessage("Analysis complete.", "success");
  } catch (error) {
    const isNetworkError =
      error instanceof TypeError || error.message === "Failed to fetch";
    const message = isNetworkError
      ? "Backend is not running. Make sure FastAPI is running on http://127.0.0.1:8000 and try again."
      : error.message || "Something went wrong while analyzing your resume.";
    renderError(message);
  } finally {
    setLoading(false);
  }
});

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  submitChatMessage(chatInput.value);
});

suggestedQuestionButtons.forEach((button) => {
  button.addEventListener("click", () => {
    if (button.disabled || chatIsSending || !latestAnalysisContext) {
      return;
    }

    chatInput.value = button.dataset.chatQuestion || "";
    if (typeof chatForm.requestSubmit === "function") {
      chatForm.requestSubmit();
    } else {
      chatForm.dispatchEvent(new Event("submit", { cancelable: true }));
    }
  });
});

resultTabButtons.forEach((button) => {
  button.addEventListener("click", () => {
    setSelectedResultTab(button.dataset.resultTab);
  });

  button.addEventListener("keydown", (event) => {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) {
      return;
    }

    event.preventDefault();
    const currentIndex = resultTabKeys.indexOf(selectedResultTab);
    let nextIndex = currentIndex;

    if (event.key === "ArrowLeft") {
      nextIndex = (currentIndex - 1 + resultTabKeys.length) % resultTabKeys.length;
    }

    if (event.key === "ArrowRight") {
      nextIndex = (currentIndex + 1) % resultTabKeys.length;
    }

    if (event.key === "Home") {
      nextIndex = 0;
    }

    if (event.key === "End") {
      nextIndex = resultTabKeys.length - 1;
    }

    setSelectedResultTab(resultTabKeys[nextIndex]);
    const nextButton = document.querySelector(
      `[data-result-tab="${resultTabKeys[nextIndex]}"]`,
    );
    if (nextButton) {
      nextButton.focus();
    }
  });
});

resetButton.addEventListener("click", () => {
  if (isAnalyzing) {
    return;
  }

  form.reset();
  uploadZone.classList.remove("has-file", "has-error", "is-dragging");
  fileStatus.textContent = "No resume selected yet.";
  setFileError("");
  setJobError("");
  updateJobCounter();
  resetResults();
  resetChat();
  setFormMessage("Complete both inputs to prepare an analysis.");
});

["dragenter", "dragover"].forEach((eventName) => {
  uploadZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    uploadZone.classList.add("is-dragging");
  });
});

["dragleave", "drop"].forEach((eventName) => {
  uploadZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    uploadZone.classList.remove("is-dragging");
  });
});

uploadZone.addEventListener("drop", (event) => {
  const droppedFile = event.dataTransfer.files[0];
  if (!droppedFile) {
    return;
  }

  const transfer = new DataTransfer();
  transfer.items.add(droppedFile);
  fileInput.files = transfer.files;
  validateFile(true);
  setFormMessage("Complete both inputs to prepare an analysis.");
});

updateJobCounter();
resetResults();
resetChat();
loadChatStatus();

chatLauncher.addEventListener("click", toggleChatPopup);
chatCloseBtn.addEventListener("click", closeChatPopup);
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && chatPopupOpen) {
    closeChatPopup();
  }
});
