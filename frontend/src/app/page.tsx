"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import {
  AlertCircle,
  Bot,
  CheckCircle2,
  ChevronDown,
  Copy,
  Database,
  ExternalLink,
  History,
  Loader2,
  MessageSquareText,
  PanelRight,
  Plus,
  RotateCcw,
  Send,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  ThumbsDown,
  ThumbsUp,
  X,
  UserRound
} from "lucide-react";
import {
  HealthResponse,
  QueryRequest,
  QueryResponse,
  SourceResponse,
  askSupportLens,
  getHealth,
  submitFeedback
} from "@/lib/api";

type FeedbackState = "idle" | "sending" | "stored" | "edited" | "failed";
type HealthState = "checking" | "online" | "offline";
type TrustState = "grounded" | "partial" | "missing";

type ConversationTurn = {
  id: string;
  createdAt: string;
  question: string;
  response: QueryResponse;
  filters: Omit<QueryRequest, "question" | "conversation_context">;
  feedbackState: FeedbackState;
  feedbackComment: string;
  feedbackRating?: 1 | 5;
};

const STORAGE_KEY = "supportlens.conversation.v1";

const examples = [
  "How do I set up TP-Link Archer AX21?",
  "I face Wi-Fi configuration issue. How do I solve this?",
  "What are the specifications for Archer AX55?",
  "What product data is missing from the knowledge base?"
];

const quickTopics = ["OpenWrt", "TP-Link", "NETGEAR", "ASUS", "Firmware", "Recovery"];

const filterFields: Array<{
  key: keyof Omit<QueryRequest, "question" | "conversation_context">;
  label: string;
  placeholder: string;
}> = [
  { key: "product", label: "Product", placeholder: "Any product" },
  { key: "category", label: "Category", placeholder: "Any category" },
  { key: "version", label: "Version", placeholder: "Any version" },
  { key: "language", label: "Language", placeholder: "Any language" },
  { key: "source_type", label: "Source type", placeholder: "Any source type" },
  { key: "document_id", label: "Document ID", placeholder: "Any document" }
];

function sourceLabel(source: SourceResponse): string {
  return (
    source.document ||
    source.title ||
    source.document_id ||
    source.chunk_id ||
    `Source ${source.source_id}`
  );
}

function formatTiming(value: number | null): string {
  return value === null ? "n/a" : `${Math.round(value)} ms`;
}

function confidenceLabel(score: number): string {
  if (score >= 0.85) {
    return "High";
  }
  if (score >= 0.65) {
    return "Medium";
  }
  return "Low";
}

function sourceKey(source: SourceResponse): string {
  return `${source.source_id}-${source.chunk_id || source.document_id || sourceLabel(source)}`;
}

function createTurnId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function trustStateFor(response: QueryResponse): TrustState {
  if (response.refused || response.sources.length === 0) {
    return "missing";
  }
  if (response.sources.some((source) => source.score < 0.65)) {
    return "partial";
  }
  return "grounded";
}

function trustCopy(state: TrustState): { label: string; detail: string } {
  if (state === "grounded") {
    return {
      label: "Grounded",
      detail: "Answer is backed by retrieved support sources."
    };
  }
  if (state === "partial") {
    return {
      label: "Partial evidence",
      detail: "Some evidence is weaker. Review the selected sources."
    };
  }
  return {
    label: "Not enough documentation",
    detail: "The knowledge base did not return enough source evidence."
  };
}

function filterSummary(filters: ConversationTurn["filters"]): string {
  const values = Object.entries(filters)
    .filter(([, value]) => value?.trim())
    .map(([key, value]) => `${key.replace("_", " ")}: ${value}`);
  return values.length ? values.join(" | ") : "All indexed sources";
}

function AnswerContent({ text }: { text: string }) {
  const lines = text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
  const intro = lines.find((line) => !line.startsWith("- "));
  const bullets = lines
    .filter((line) => line.startsWith("- "))
    .map((line) => line.replace(/^-+\s*/, ""));
  const paragraphs = lines.filter((line) => line !== intro && !line.startsWith("- "));

  if (bullets.length === 0) {
    return <p className="answer-text">{text}</p>;
  }

  return (
    <div className="answer-content">
      {intro ? <p>{intro}</p> : null}
      <ul>
        {bullets.map((bullet) => (
          <li key={bullet}>{bullet}</li>
        ))}
      </ul>
      {paragraphs.map((paragraph) => (
        <p key={paragraph}>{paragraph}</p>
      ))}
    </div>
  );
}

export default function Home() {
  const [question, setQuestion] = useState("");
  const [filters, setFilters] = useState<ConversationTurn["filters"]>({});
  const [turns, setTurns] = useState<ConversationTurn[]>([]);
  const [selectedTurnId, setSelectedTurnId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthState, setHealthState] = useState<HealthState>("checking");
  const [showFilters, setShowFilters] = useState(false);
  const [isLoadedFromStorage, setIsLoadedFromStorage] = useState(false);
  const transcriptEndRef = useRef<HTMLDivElement | null>(null);

  const trimmedQuestion = question.trim();
  const canAsk = trimmedQuestion.length > 0 && !isLoading;
  const activeFilterCount = Object.values(filters).filter(
    (value) => value?.trim()
  ).length;
  const activeFilters = Object.entries(filters).filter(([, value]) => value?.trim());

  const selectedTurn =
    turns.find((turn) => turn.id === selectedTurnId) || turns[turns.length - 1] || null;
  const selectedTrust = selectedTurn ? trustStateFor(selectedTurn.response) : null;
  const selectedTrustCopy = selectedTrust ? trustCopy(selectedTrust) : null;

  useEffect(() => {
    try {
      const saved = window.localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved) as ConversationTurn[];
        setTurns(parsed);
        setSelectedTurnId(parsed[parsed.length - 1]?.id || null);
      }
    } catch {
      window.localStorage.removeItem(STORAGE_KEY);
    } finally {
      setIsLoadedFromStorage(true);
    }
  }, []);

  useEffect(() => {
    if (!isLoadedFromStorage) {
      return;
    }
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(turns.slice(-25)));
  }, [isLoadedFromStorage, turns]);

  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ block: "end", behavior: "smooth" });
  }, [turns.length, isLoading]);

  useEffect(() => {
    let isMounted = true;

    getHealth()
      .then((response) => {
        if (!isMounted) {
          return;
        }
        setHealth(response);
        setHealthState("online");
      })
      .catch(() => {
        if (!isMounted) {
          return;
        }
        setHealthState("offline");
      });

    return () => {
      isMounted = false;
    };
  }, []);

  async function askQuestion(
    nextQuestion: string,
    filterOverride: ConversationTurn["filters"] = filters
  ) {
    const cleanQuestion = nextQuestion.trim();
    if (!cleanQuestion || isLoading) {
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const context = turns.slice(-4).map((turn) => ({
        question: turn.question,
        answer: turn.response.answer
      }));
      const response = await askSupportLens({
        question: cleanQuestion,
        ...filterOverride,
        conversation_context: context
      });
      const turn: ConversationTurn = {
        id: createTurnId(),
        createdAt: new Date().toISOString(),
        question: cleanQuestion,
        response,
        filters: filterOverride,
        feedbackState: "idle",
        feedbackComment: "",
        feedbackRating: undefined
      };
      setTurns((current) => [...current, turn]);
      setSelectedTurnId(turn.id);
      setQuestion("");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Query failed.");
    } finally {
      setIsLoading(false);
    }
  }

  async function onAsk(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await askQuestion(trimmedQuestion);
  }

  async function onRetry(turn: ConversationTurn) {
    setQuestion(turn.question);
    setFilters(turn.filters);
    await askQuestion(turn.question, turn.filters);
  }

  async function onFeedback(turnId: string, rating?: 1 | 5) {
    const turn = turns.find((item) => item.id === turnId);
    if (!turn || turn.feedbackState === "sending") {
      return;
    }
    const feedbackRating = rating || turn.feedbackRating;
    if (!feedbackRating) {
      updateTurn(turnId, { feedbackState: "failed" });
      return;
    }

    updateTurn(turnId, { feedbackState: "sending", feedbackRating });
    try {
      await submitFeedback(turn.response, feedbackRating, turn.feedbackComment);
      updateTurn(turnId, { feedbackState: "stored", feedbackRating });
    } catch {
      updateTurn(turnId, { feedbackState: "failed" });
    }
  }

  async function copyAnswer(text: string) {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      setError("Copy failed. Please select the answer text manually.");
    }
  }

  function updateTurn(turnId: string, patch: Partial<ConversationTurn>) {
    setTurns((current) =>
      current.map((turn) => (turn.id === turnId ? { ...turn, ...patch } : turn))
    );
  }

  function updateFilter(
    key: keyof Omit<QueryRequest, "question" | "conversation_context">,
    value: string
  ) {
    setFilters((current) => ({
      ...current,
      [key]: value
    }));
  }

  function clearFilters() {
    setFilters({});
  }

  function clearConversation() {
    setTurns([]);
    setSelectedTurnId(null);
    resetWorkspace();
    setError(null);
  }

  function resetWorkspace() {
    setQuestion("");
    setFilters({});
    setError(null);
    setShowFilters(false);
  }

  return (
    <main className="app-shell">
      <aside className="side-rail" aria-label="SupportLens controls">
        <div className="brand-lockup">
          <div className="brand-mark" aria-hidden="true">
            <svg viewBox="0 0 48 48" role="img">
              <defs>
                <linearGradient id="supportlens-mark" x1="8" x2="40" y1="6" y2="42">
                  <stop offset="0" stopColor="#0f9f95" />
                  <stop offset="1" stopColor="#075d58" />
                </linearGradient>
              </defs>
              <rect width="48" height="48" rx="12" fill="url(#supportlens-mark)" />
              <path
                d="M17 12.5h12.4L36 19.1V34c0 1.9-1.1 3-3 3H17c-1.9 0-3-1.1-3-3V15.5c0-1.9 1.1-3 3-3Z"
                fill="#ffffff"
                opacity="0.96"
              />
              <path d="M29 13v5.4c0 .9.5 1.4 1.4 1.4H36" fill="#d9f2ef" />
              <path
                d="M19 24h7.4M19 28h5.8M19 32h4.2"
                stroke="#0a766f"
                strokeLinecap="round"
                strokeWidth="2"
              />
              <circle
                cx="30.2"
                cy="30.2"
                r="6.2"
                fill="none"
                stroke="#0a766f"
                strokeWidth="3"
              />
              <path
                d="m34.8 34.8 4.7 4.7"
                stroke="#0a766f"
                strokeLinecap="round"
                strokeWidth="3"
              />
              <circle cx="18.5" cy="18.8" r="1.6" fill="#0a766f" />
              <circle cx="23.5" cy="18.8" r="1.6" fill="#0a766f" opacity="0.72" />
            </svg>
          </div>
          <div>
            <h1>SupportLens</h1>
            <p className="brand-subtitle">Grounded answers from router support docs</p>
          </div>
        </div>

        <section className="rail-section">
          <div className="section-heading">
            <Database size={17} aria-hidden="true" />
            <span>Knowledge base</span>
          </div>
          <div className={`health-card ${healthState}`}>
            <span className="health-dot" aria-hidden="true" />
            <div>
              <strong>
                {healthState === "checking"
                  ? "Checking sources"
                  : healthState === "online"
                    ? "Ready"
                    : "Unavailable"}
              </strong>
              <p>
                {healthState === "online"
                  ? "Router support knowledge base is connected."
                  : health
                    ? `${health.app} - ${health.environment}`
                    : "Answer service"}
              </p>
            </div>
          </div>
        </section>

        <section className="rail-section rail-actions">
          <button type="button" className="rail-action primary" onClick={clearConversation}>
            <Plus size={17} aria-hidden="true" />
            New chat
          </button>
          <button
            type="button"
            className="rail-action draft"
            onClick={resetWorkspace}
            title="Clear the message draft, filters, and filter panel only"
          >
            <X size={17} aria-hidden="true" />
            Clear draft
          </button>
        </section>

        <section className="rail-section">
          <div className="section-heading">
            <History size={17} aria-hidden="true" />
            <span>Conversation</span>
            <span className="count-pill">{turns.length}</span>
          </div>
          <div className="history-list">
            {turns.length ? (
              turns.slice(-8).map((turn) => (
                <button
                  key={turn.id}
                  type="button"
                  className={`history-item ${turn.id === selectedTurn?.id ? "selected" : ""}`}
                  onClick={() => setSelectedTurnId(turn.id)}
                >
                  <span>{turn.question}</span>
                  <small>{trustCopy(trustStateFor(turn.response)).label}</small>
                </button>
              ))
            ) : (
              <p className="muted small">No questions yet.</p>
            )}
          </div>
        </section>

        <section className="rail-section">
          <div className="section-heading">
            <Sparkles size={17} aria-hidden="true" />
            <span>Good questions</span>
          </div>
          <div className="topic-list" aria-label="Supported topics">
            {quickTopics.map((topic) => (
              <span key={topic}>{topic}</span>
            ))}
          </div>
        </section>

        <section className="rail-section">
          <div className="section-heading">
            <MessageSquareText size={17} aria-hidden="true" />
            <span>Examples</span>
          </div>
          <div className="example-stack">
            {examples.map((example) => (
              <button
                key={example}
                type="button"
                className="example-button"
                onClick={() => setQuestion(example)}
              >
                {example}
              </button>
            ))}
          </div>
        </section>
      </aside>

      <section className="workspace" aria-labelledby="page-title">
        <header className="workspace-header">
          <div>
            <p className="eyebrow">Grounded support assistant</p>
            <h2 id="page-title">Router support workspace</h2>
          </div>
          <div className="header-status">
            <span className="state-pill success">
              <ShieldCheck size={15} aria-hidden="true" />
              Cited answers
            </span>
            <span className="state-pill neutral">
              <PanelRight size={15} aria-hidden="true" />
              Selected evidence
            </span>
          </div>
        </header>

        <section className="conversation-layout" aria-live="polite">
          <div className="conversation-column">
            {error ? (
              <section className="notice error" role="alert">
                <AlertCircle size={18} aria-hidden="true" />
                <span>{error}</span>
              </section>
            ) : null}

            <div className="transcript">
              {turns.length ? (
                turns.map((turn) => {
                  const state = trustStateFor(turn.response);
                  const copy = trustCopy(state);
                  return (
                    <article
                      key={turn.id}
                      className={`turn-card ${turn.id === selectedTurn?.id ? "selected" : ""}`}
                      onClick={() => setSelectedTurnId(turn.id)}
                    >
                      <div className="message user-message">
                        <div className="avatar user">
                          <UserRound size={16} aria-hidden="true" />
                        </div>
                        <div className="bubble question-bubble">
                          <div className="bubble-meta">
                            <span>You</span>
                            <span>{filterSummary(turn.filters)}</span>
                          </div>
                          <p>{turn.question}</p>
                        </div>
                      </div>

                      <div className="message assistant-message">
                        <div className="avatar assistant">
                          <Bot size={16} aria-hidden="true" />
                        </div>
                        <div className="bubble answer-bubble">
                          <div className="answer-toolbar">
                            <span className={`state-pill ${state}`}>
                              {state === "missing" ? (
                                <AlertCircle size={15} aria-hidden="true" />
                              ) : (
                                <CheckCircle2 size={15} aria-hidden="true" />
                              )}
                              {copy.label}
                            </span>
                            <div className="icon-actions">
                              <button
                                type="button"
                                onClick={(event) => {
                                  event.stopPropagation();
                                  copyAnswer(turn.response.answer);
                                }}
                                title="Copy answer"
                              >
                                <Copy size={16} aria-hidden="true" />
                              </button>
                              <button
                                type="button"
                                onClick={(event) => {
                                  event.stopPropagation();
                                  onRetry(turn);
                                }}
                                title="Retry question"
                              >
                                <RotateCcw size={16} aria-hidden="true" />
                              </button>
                            </div>
                          </div>
                          {turn.response.no_answer_reason ? (
                            <p className="reason">
                              Reason: {turn.response.no_answer_reason.replaceAll("_", " ")}
                            </p>
                          ) : null}
                          <AnswerContent text={turn.response.answer} />
                          <div className="answer-footer">
                            <button
                              type="button"
                              className={turn.feedbackRating === 5 ? "selected" : ""}
                              onClick={(event) => {
                                event.stopPropagation();
                                onFeedback(turn.id, 5);
                              }}
                              disabled={turn.feedbackState === "sending"}
                              title="Mark answer as helpful"
                            >
                              <ThumbsUp size={16} aria-hidden="true" />
                            </button>
                            <button
                              type="button"
                              className={turn.feedbackRating === 1 ? "selected" : ""}
                              onClick={(event) => {
                                event.stopPropagation();
                                onFeedback(turn.id, 1);
                              }}
                              disabled={turn.feedbackState === "sending"}
                              title="Mark answer as not helpful"
                            >
                              <ThumbsDown size={16} aria-hidden="true" />
                            </button>
                            <span>{turn.response.sources.length} sources</span>
                            {turn.feedbackState === "stored" ? (
                              <span className="feedback-status success-text">Feedback saved</span>
                            ) : null}
                            {turn.feedbackState === "edited" ? (
                              <span className="feedback-status warning-text">Note not saved</span>
                            ) : null}
                            {turn.feedbackState === "failed" ? (
                              <span className="feedback-status error-text">Failed</span>
                            ) : null}
                          </div>

                          <details
                            className="feedback-panel"
                            onClick={(event) => event.stopPropagation()}
                          >
                            <summary>
                              <MessageSquareText size={15} aria-hidden="true" />
                              Add feedback note
                            </summary>
                            <textarea
                              id={`feedback-${turn.id}`}
                              value={turn.feedbackComment}
                              onChange={(event) =>
                                updateTurn(turn.id, {
                                  feedbackComment: event.target.value,
                                  feedbackState:
                                    turn.feedbackState === "stored"
                                      ? "edited"
                                      : turn.feedbackState
                                })
                              }
                              placeholder="Add context about what was helpful or missing."
                              maxLength={1000}
                              rows={2}
                            />
                            <div className="feedback-note-actions">
                              <span>
                                {turn.feedbackRating
                                  ? "This note will update your selected rating."
                                  : "Choose Helpful or Not helpful before sending a note."}
                              </span>
                              <button
                                type="button"
                                onClick={() => onFeedback(turn.id)}
                                disabled={
                                  turn.feedbackState === "sending" || !turn.feedbackRating
                                }
                              >
                                {turn.feedbackState === "stored"
                                  ? "Saved"
                                  : turn.feedbackState === "edited"
                                    ? "Update feedback"
                                    : "Send feedback"}
                              </button>
                            </div>
                          </details>
                        </div>
                      </div>
                    </article>
                  );
                })
              ) : (
                <div className="empty-state">
                  <ShieldCheck size={30} aria-hidden="true" />
                  <h3>Ask a router support question</h3>
                  <p>Select an example or type below.</p>
                </div>
              )}

              {isLoading ? (
                <div className="loading-turn">
                  <Loader2 className="spin" size={18} aria-hidden="true" />
                  <span>Retrieving sources and preparing a grounded answer...</span>
                </div>
              ) : null}
              <div ref={transcriptEndRef} aria-hidden="true" />
            </div>

            <form className="query-composer" onSubmit={onAsk}>
              <label htmlFor="question">Message</label>
              <div className="composer-box">
                <textarea
                  id="question"
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                  placeholder="Example: How do I configure Wi-Fi for this router?"
                  maxLength={8000}
                  rows={4}
                />
                <div className="composer-footer">
                  <button
                    type="button"
                    className={`filter-toggle ${showFilters ? "open" : ""}`}
                    onClick={() => setShowFilters((current) => !current)}
                  >
                    <SlidersHorizontal size={17} aria-hidden="true" />
                    Advanced filters
                    {activeFilterCount > 0 ? (
                      <span className="count-pill">{activeFilterCount}</span>
                    ) : null}
                    <ChevronDown size={16} aria-hidden="true" />
                  </button>
                  <span>{trimmedQuestion.length}/8000</span>
                  <button type="submit" disabled={!canAsk} className="primary-button">
                    {isLoading ? (
                      <Loader2 className="spin" size={18} aria-hidden="true" />
                    ) : (
                      <Send size={18} aria-hidden="true" />
                    )}
                    {isLoading ? "Asking" : "Ask"}
                  </button>
                </div>
              </div>
              {activeFilters.length ? (
                <div className="active-filter-list" aria-label="Active source filters">
                  {activeFilters.map(([key, value]) => (
                    <button
                      key={key}
                      type="button"
                      onClick={() =>
                        updateFilter(
                          key as keyof Omit<QueryRequest, "question" | "conversation_context">,
                          ""
                        )
                      }
                      title={`Remove ${key.replace("_", " ")} filter`}
                    >
                      {key.replace("_", " ")}: {value}
                      <X size={13} aria-hidden="true" />
                    </button>
                  ))}
                </div>
              ) : null}
              {showFilters ? (
                <div className="filter-panel">
                  <div className="filter-panel-copy">
                    <p>
                      Optional. Use this only when you want to limit the answer to a
                      known product, category, or document.
                    </p>
                    {activeFilterCount > 0 ? (
                      <button type="button" onClick={clearFilters}>
                        Clear filters
                      </button>
                    ) : null}
                  </div>
                  <div className="filter-grid">
                    {filterFields.map((field) => (
                      <label key={field.key}>
                        <span>{field.label}</span>
                        <input
                          value={filters[field.key] || ""}
                          onChange={(event) => updateFilter(field.key, event.target.value)}
                          placeholder={field.placeholder}
                        />
                      </label>
                    ))}
                  </div>
                </div>
              ) : null}
            </form>
          </div>

          <aside className="source-panel" aria-label="Sources">
            <div className="source-panel-header">
              <div>
                <p className="eyebrow">Evidence</p>
                <h3>Selected sources</h3>
              </div>
              <span className="count-pill">{selectedTurn?.response.sources.length || 0}</span>
            </div>

            {selectedTurn ? (
              <>
                <div className="evidence-summary">
                  {selectedTrustCopy ? (
                    <span className={`state-pill ${selectedTrust}`}>
                      {selectedTrust === "missing" ? (
                        <AlertCircle size={15} aria-hidden="true" />
                      ) : (
                        <CheckCircle2 size={15} aria-hidden="true" />
                      )}
                      {selectedTrustCopy.label}
                    </span>
                  ) : null}
                  <p>{selectedTurn.question}</p>
                  <small>Answered in {formatTiming(selectedTurn.response.total_time_ms)}</small>
                </div>
              </>
            ) : null}

            {selectedTurn?.response.sources.length ? (
              <ol className="source-list">
                {selectedTurn.response.sources.map((source, index) => (
                  <li key={sourceKey(source)} className="source-card">
                    <div className="source-card-top">
                      <span className="source-index">{index + 1}</span>
                      <span className="confidence">
                        {confidenceLabel(source.score)} - {source.score.toFixed(2)}
                      </span>
                    </div>
                    <h4>
                      {source.source_url ? (
                        <a href={source.source_url} target="_blank" rel="noreferrer">
                          {sourceLabel(source)}
                          <ExternalLink size={14} aria-hidden="true" />
                        </a>
                      ) : (
                        sourceLabel(source)
                      )}
                    </h4>
                    <dl className="source-meta">
                      <div>
                        <dt>Section</dt>
                        <dd>{source.section || "Referenced evidence"}</dd>
                      </div>
                      <div>
                        <dt>Document</dt>
                        <dd>{source.document_id || "n/a"}</dd>
                      </div>
                      <div>
                        <dt>Product</dt>
                        <dd>{source.product || "n/a"}</dd>
                      </div>
                      <div>
                        <dt>Page</dt>
                        <dd>{source.page ?? "n/a"}</dd>
                      </div>
                    </dl>
                  </li>
                ))}
              </ol>
            ) : (
              <p className="muted">
                {selectedTurn
                  ? "No sources were returned for this answer."
                  : "Ask a question to inspect evidence."}
              </p>
            )}
          </aside>
        </section>
      </section>
    </main>
  );
}
