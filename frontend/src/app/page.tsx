"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  ChevronDown,
  CheckCircle2,
  Clock3,
  Database,
  ExternalLink,
  FileSearch,
  Gauge,
  Loader2,
  MessageSquareText,
  RotateCcw,
  Search,
  Send,
  SlidersHorizontal,
  Sparkles,
  ThumbsDown,
  ThumbsUp
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

type FeedbackState = "idle" | "sending" | "stored" | "failed";
type HealthState = "checking" | "online" | "offline";

const examples = [
  "I can't open routerlogin.net. What else can I try?",
  "My TP-Link router has no internet. Where do I start?",
  "ASUS firmware update failed. Is there a rescue mode?",
  "What is OpenWrt and why would I use it?"
];

const quickTopics = ["OpenWrt", "TP-Link", "NETGEAR", "ASUS", "Firmware", "Recovery"];

const filterFields: Array<{
  key: keyof Omit<QueryRequest, "question">;
  label: string;
  placeholder: string;
}> = [
  { key: "product", label: "Product", placeholder: "OpenWrt" },
  { key: "version", label: "Version", placeholder: "current" },
  { key: "category", label: "Category", placeholder: "troubleshooting" },
  { key: "language", label: "Language", placeholder: "English" },
  { key: "source_type", label: "Source type", placeholder: "html" },
  { key: "document_id", label: "Document ID", placeholder: "DOC003" }
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
  const [filters, setFilters] = useState<Omit<QueryRequest, "question">>({});
  const [answer, setAnswer] = useState<QueryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [feedbackState, setFeedbackState] = useState<FeedbackState>("idle");
  const [feedbackComment, setFeedbackComment] = useState("");
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthState, setHealthState] = useState<HealthState>("checking");
  const [showFilters, setShowFilters] = useState(false);

  const trimmedQuestion = question.trim();
  const canAsk = trimmedQuestion.length > 0 && !isLoading;
  const activeFilterCount = Object.values(filters).filter(
    (value) => value?.trim()
  ).length;

  const timing = useMemo(() => {
    if (!answer) {
      return [];
    }

    return [
      {
        label: "Retrieval",
        value: formatTiming(answer.retrieval_time_ms),
        icon: Search
      },
      {
        label: "Generation",
        value: formatTiming(answer.generation_time_ms),
        icon: Sparkles
      },
      {
        label: "Total",
        value: formatTiming(answer.total_time_ms),
        icon: Clock3
      }
    ];
  }, [answer]);

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

  async function onAsk(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canAsk) {
      return;
    }

    setIsLoading(true);
    setError(null);
    setFeedbackState("idle");
    setFeedbackComment("");

    try {
      const response = await askSupportLens({
        question: trimmedQuestion,
        ...filters
      });
      setAnswer(response);
    } catch (caught) {
      setAnswer(null);
      setError(caught instanceof Error ? caught.message : "Query failed.");
    } finally {
      setIsLoading(false);
    }
  }

  async function onFeedback(rating: 1 | 5) {
    if (!answer || feedbackState === "sending") {
      return;
    }

    setFeedbackState("sending");
    try {
      await submitFeedback(answer, rating, feedbackComment);
      setFeedbackState("stored");
    } catch {
      setFeedbackState("failed");
    }
  }

  function updateFilter(key: keyof Omit<QueryRequest, "question">, value: string) {
    setFilters((current) => ({
      ...current,
      [key]: value
    }));
  }

  function resetWorkspace() {
    setQuestion("");
    setFilters({});
    setAnswer(null);
    setError(null);
    setFeedbackState("idle");
    setFeedbackComment("");
  }

  return (
    <main className="app-shell">
      <aside className="side-rail" aria-label="SupportLens controls">
        <div className="brand-lockup">
          <div className="brand-mark" aria-hidden="true">
            <FileSearch size={24} />
          </div>
          <div>
            <p className="eyebrow">SupportLens</p>
            <h1>Support Console</h1>
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
                  ? "OpenWrt support articles with cited answers"
                  : health
                    ? `${health.app} - ${health.environment}`
                    : "Answer service"}
              </p>
            </div>
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
            <p className="eyebrow">Support assistant</p>
            <h2 id="page-title">Ask an OpenWrt support question</h2>
          </div>
          <button
            type="button"
            className="ghost-button"
            onClick={resetWorkspace}
            title="Reset workspace"
          >
            <RotateCcw size={17} aria-hidden="true" />
            Reset
          </button>
        </header>

        <form className="query-composer" onSubmit={onAsk}>
          <label htmlFor="question">Question</label>
          <div className="composer-box">
            <textarea
              id="question"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Ask about setup, troubleshooting, firmware, configuration, policies, or recovery."
              maxLength={8000}
              rows={5}
            />
            <div className="composer-footer">
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
          <div className="advanced-controls">
            <button
              type="button"
              className={`filter-toggle ${showFilters ? "open" : ""}`}
              onClick={() => setShowFilters((current) => !current)}
            >
              <SlidersHorizontal size={17} aria-hidden="true" />
              Narrow sources
              {activeFilterCount > 0 ? (
                <span className="count-pill">{activeFilterCount}</span>
              ) : null}
              <ChevronDown size={16} aria-hidden="true" />
            </button>
            {showFilters ? (
              <div className="filter-panel">
                <p>
                  Use these only when you already know the product, category, or source
                  you want to search.
                </p>
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
          </div>
        </form>

        {error ? (
          <section className="notice error" role="alert">
            <AlertCircle size={18} aria-hidden="true" />
            <span>{error}</span>
          </section>
        ) : null}

        <section className="answer-layout" aria-live="polite">
          <div className="answer-surface">
            <div className="answer-title-row">
              <div>
                <p className="eyebrow">Question</p>
                <h3>{answer ? answer.question : "Ask a support question"}</h3>
              </div>
              {answer?.refused ? (
                <span className="state-pill warning">
                  <AlertCircle size={15} aria-hidden="true" />
                  No answer
                </span>
              ) : answer ? (
                <span className="state-pill success">
                  <CheckCircle2 size={15} aria-hidden="true" />
                  Grounded
                </span>
              ) : null}
            </div>

            {isLoading ? (
              <div className="skeleton-stack" aria-label="Loading answer">
                <div />
                <div />
                <div />
              </div>
            ) : answer ? (
              <>
                {answer.no_answer_reason ? (
                  <p className="reason">{answer.no_answer_reason}</p>
                ) : null}
                <div className="direct-answer">
                  <p className="eyebrow">Answer</p>
                  <AnswerContent text={answer.answer} />
                </div>

                <dl className="timing-grid">
                  {timing.map((item) => {
                    const Icon = item.icon;
                    return (
                      <div key={item.label} className="metric-tile">
                        <Icon size={18} aria-hidden="true" />
                        <div>
                          <dt>{item.label}</dt>
                          <dd>{item.value}</dd>
                        </div>
                      </div>
                    );
                  })}
                </dl>

                <div className="feedback-panel">
                  <label htmlFor="feedback-comment">Feedback note</label>
                  <textarea
                    id="feedback-comment"
                    value={feedbackComment}
                    onChange={(event) => setFeedbackComment(event.target.value)}
                    placeholder="Optional"
                    maxLength={1000}
                    rows={2}
                  />
                  <div className="feedback-actions">
                    <button
                      type="button"
                      onClick={() => onFeedback(5)}
                      disabled={feedbackState === "sending"}
                      title="Mark answer as helpful"
                    >
                      <ThumbsUp size={17} aria-hidden="true" />
                      Helpful
                    </button>
                    <button
                      type="button"
                      onClick={() => onFeedback(1)}
                      disabled={feedbackState === "sending"}
                      title="Mark answer as not helpful"
                    >
                      <ThumbsDown size={17} aria-hidden="true" />
                      Not helpful
                    </button>
                    {feedbackState === "stored" ? (
                      <span className="feedback-status success-text">Stored</span>
                    ) : null}
                    {feedbackState === "failed" ? (
                      <span className="feedback-status error-text">Failed</span>
                    ) : null}
                  </div>
                </div>
              </>
            ) : (
              <div className="empty-state">
                <Gauge size={28} aria-hidden="true" />
                <p>Select filters if needed, ask a question, and review the cited answer.</p>
              </div>
            )}
          </div>

          <aside className="source-panel" aria-label="Sources">
            <div className="source-panel-header">
              <div>
                <p className="eyebrow">Evidence</p>
                <h3>Sources</h3>
              </div>
              <span className="count-pill">{answer?.sources.length || 0}</span>
            </div>

            {isLoading ? (
              <div className="source-skeleton">
                <div />
                <div />
              </div>
            ) : answer?.sources.length ? (
              <ol className="source-list">
                {answer.sources.map((source, index) => (
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
              <p className="muted">No sources returned yet.</p>
            )}
          </aside>
        </section>
      </section>
    </main>
  );
}
