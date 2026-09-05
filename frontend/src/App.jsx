import React, { useEffect, useRef, useState } from "react";
import "./styles.css";

const API_URL = "http://127.0.0.1:8001";

const navItems = [
  ["⌂", "Dashboard"],
  ["◉", "Assistant"],
  ["▣", "Calendar"],
  ["✉", "Email"],
  ["◇", "Memory"],
  ["□", "Files"],
  ["⚙", "Settings"],
];

export default function App() {
  const [collapsed, setCollapsed] = useState(true);
  const [active, setActive] = useState("Dashboard");
  const [panel, setPanel] = useState("calendar");

  // ---------------------------------------------------------
  // Assistant
  // ---------------------------------------------------------

  const [chatOpen, setChatOpen] = useState(false);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);

  // ---------------------------------------------------------
  // Calendar
  // ---------------------------------------------------------

  const [events, setEvents] = useState([]);
  const [calendarLoading, setCalendarLoading] = useState(true);
  const [calendarError, setCalendarError] = useState("");

  // ---------------------------------------------------------
  // Gmail
  // ---------------------------------------------------------

  const [emails, setEmails] = useState([]);
  const [emailLoading, setEmailLoading] = useState(true);
  const [emailError, setEmailError] = useState("");

  // Full email reader
  const [selectedEmail, setSelectedEmail] = useState(null);
  const [emailReaderLoading, setEmailReaderLoading] = useState(false);
  const [emailReaderError, setEmailReaderError] = useState("");

  // ---------------------------------------------------------
  // New event modal
  // ---------------------------------------------------------

  const [eventModalOpen, setEventModalOpen] = useState(false);
  const [eventTitle, setEventTitle] = useState("");
  const [eventDate, setEventDate] = useState("");
  const [eventTime, setEventTime] = useState("");
  const [eventDuration, setEventDuration] = useState("60");
  const [eventDescription, setEventDescription] = useState("");
  const [eventCreating, setEventCreating] = useState(false);
  const [eventError, setEventError] = useState("");

  // ---------------------------------------------------------
  // Refs
  // ---------------------------------------------------------

  const inputRef = useRef(null);
  const messagesRef = useRef(null);
  const emailRequestIdRef = useRef(0);
  const emailReaderRequestIdRef = useRef(0);
  const calendarRequestIdRef = useRef(0);
  const recognitionRef = useRef(null);
  const voiceEnabledRef = useRef(false);
  const speakingRef = useRef(false);
  const [voiceSupported, setVoiceSupported] = useState(false);
  const [voiceEnabled, setVoiceEnabled] = useState(false);
  const [voiceListening, setVoiceListening] = useState(false);
  const [voiceStatus, setVoiceStatus] = useState("Voice off");
  const sendMessageTextRef = useRef(null);

  // ---------------------------------------------------------
  // Initial load
  // ---------------------------------------------------------

  useEffect(() => {
    loadCalendar();
    loadEmails();
  }, []);

  // ---------------------------------------------------------
  // Focus assistant
  // ---------------------------------------------------------

  useEffect(() => {
    if (chatOpen) {
      setTimeout(() => {
        inputRef.current?.focus();
      }, 60);
    }
  }, [chatOpen]);

  // ---------------------------------------------------------
  // Scroll assistant
  // ---------------------------------------------------------

  useEffect(() => {
    if (messagesRef.current) {
      messagesRef.current.scrollTop =
        messagesRef.current.scrollHeight;
    }
  }, [messages, loading]);

  // =========================================================
  // CALENDAR
  // =========================================================

  async function loadCalendar() {
    const requestId = ++calendarRequestIdRef.current;

    setCalendarLoading(true);
    setCalendarError("");

    try {
      const response = await fetch(
        `${API_URL}/calendar/today`
      );

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();

      if (requestId !== calendarRequestIdRef.current) {
        return;
      }

      setEvents(data.events || []);
    } catch (error) {
      if (requestId !== calendarRequestIdRef.current) {
        return;
      }

      console.error("Calendar loading error:", error);
      setCalendarError("Unable to load calendar.");
      // Keep previously loaded events on transient failures.
    } finally {
      if (requestId === calendarRequestIdRef.current) {
        setCalendarLoading(false);
      }
    }
  }

  // =========================================================
  // GMAIL
  // =========================================================

  async function loadEmails() {
    const requestId = ++emailRequestIdRef.current;

    setEmailLoading(true);
    setEmailError("");

    const maxAttempts = 3;
    let lastError = null;

    try {
      for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
        try {
          const response = await fetch(
            `${API_URL}/email/recent?limit=10`
          );

          if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
          }

          const data = await response.json();

          if (requestId !== emailRequestIdRef.current) {
            return;
          }

          setEmails(Array.isArray(data.emails) ? data.emails : []);
          setEmailError("");
          return;
        } catch (error) {
          lastError = error;

          if (attempt < maxAttempts) {
            await new Promise((resolve) =>
              setTimeout(resolve, 350 * attempt)
            );
          }
        }
      }

      if (requestId !== emailRequestIdRef.current) {
        return;
      }

      console.error("Email loading error:", lastError);
      // Do not erase a previously successful inbox because of a transient 502.
      if (emails.length === 0) {
        setEmailError("Unable to load Gmail.");
      }
    } finally {
      if (requestId === emailRequestIdRef.current) {
        setEmailLoading(false);
      }
    }
  }

  // =========================================================
  // READ FULL EMAIL
  // =========================================================

  async function openEmail(email) {
    if (!email?.id) {
      return;
    }

    const requestId = ++emailReaderRequestIdRef.current;
    const messageId = email.id;

    setSelectedEmail(null);
    setEmailReaderLoading(true);
    setEmailReaderError("");

    let lastError = null;

    try {
      for (let attempt = 1; attempt <= 3; attempt += 1) {
        try {
          const response = await fetch(
            `${API_URL}/email/${encodeURIComponent(messageId)}`
          );

          const data = await response.json().catch(() => ({}));

          if (!response.ok) {
            throw new Error(
              data?.detail || `HTTP ${response.status}`
            );
          }

          if (requestId !== emailReaderRequestIdRef.current) {
            return;
          }

          setSelectedEmail(data);
          return;
        } catch (error) {
          lastError = error;

          if (attempt < 3) {
            await new Promise((resolve) =>
              setTimeout(resolve, 350 * attempt)
            );
          }
        }
      }

      if (requestId !== emailReaderRequestIdRef.current) {
        return;
      }

      console.error("Email reader error:", lastError);
      setEmailReaderError(
        lastError?.message || "Unable to open this email."
      );
    } finally {
      if (requestId === emailReaderRequestIdRef.current) {
        setEmailReaderLoading(false);
      }
    }
  }

  function closeEmailReader() {
    emailReaderRequestIdRef.current += 1;
    setSelectedEmail(null);
    setEmailReaderError("");
    setEmailReaderLoading(false);
  }

  // =========================================================
  // DATE / TIME HELPERS
  // =========================================================

  function formatCalendarTime(value) {
    if (!value) {
      return "";
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
      return "";
    }

    return date.toLocaleTimeString(
      "en-IN",
      {
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
        timeZone: "Asia/Kolkata",
      }
    );
  }

  function formatEmailTime(value) {
    if (!value) {
      return "";
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
      return value;
    }

    const now = new Date();

    const sameDay =
      date.toLocaleDateString(
        "en-IN",
        {
          timeZone: "Asia/Kolkata",
        }
      ) ===
      now.toLocaleDateString(
        "en-IN",
        {
          timeZone: "Asia/Kolkata",
        }
      );

    if (sameDay) {
      return date.toLocaleTimeString(
        "en-IN",
        {
          hour: "2-digit",
          minute: "2-digit",
          hour12: false,
          timeZone: "Asia/Kolkata",
        }
      );
    }

    return date.toLocaleDateString(
      "en-IN",
      {
        day: "2-digit",
        month: "short",
        timeZone: "Asia/Kolkata",
      }
    );
  }

  function formatFullEmailDate(value) {
    if (!value) {
      return "";
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
      return value;
    }

    return date.toLocaleString(
      "en-IN",
      {
        day: "2-digit",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
        timeZone: "Asia/Kolkata",
      }
    );
  }

  function getEventStart(event) {
    if (!event) {
      return null;
    }

    if (event.start?.dateTime) {
      return event.start.dateTime;
    }

    if (event.start?.date) {
      return event.start.date;
    }

    if (event.start) {
      return event.start;
    }

    return null;
  }

  function getTodayLabel() {
    return new Date().toLocaleDateString(
      "en-IN",
      {
        day: "2-digit",
        month: "short",
        year: "numeric",
        timeZone: "Asia/Kolkata",
      }
    );
  }

  // =========================================================
  // VOICE ASSISTANT
  // =========================================================

  useEffect(() => {
    const SpeechRecognition =
      window.SpeechRecognition ||
      window.webkitSpeechRecognition;

    setVoiceSupported(Boolean(SpeechRecognition));

    if (!SpeechRecognition) {
      return undefined;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = false;
    recognition.lang = "en-IN";
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
      if (voiceEnabledRef.current) {
        setVoiceListening(true);
        setVoiceStatus("Listening for Hey Baby...");
      }
    };

    recognition.onend = () => {
      setVoiceListening(false);

      if (voiceEnabledRef.current && !speakingRef.current) {
        setVoiceStatus("Listening for Hey Baby...");
        setTimeout(() => {
          try {
            recognition.start();
          } catch (_) {
            // Browser may already be restarting recognition.
          }
        }, 250);
      }
    };

    recognition.onerror = (event) => {
      if (event.error === "not-allowed" || event.error === "service-not-allowed") {
        voiceEnabledRef.current = false;
        setVoiceEnabled(false);
        setVoiceListening(false);
        setVoiceStatus("Microphone permission required");
      } else if (voiceEnabledRef.current) {
        setVoiceStatus("Listening for Hey Baby...");
      }
    };

    recognition.onresult = (event) => {
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        if (!event.results[i].isFinal) continue;

        const transcript = event.results[i][0]?.transcript?.trim();
        if (!transcript) continue;

        const normalized = transcript
          .replace(/[.,!?]/g, " ")
          .replace(/\s+/g, " ")
          .trim();

        const wakeMatch = normalized.match(/^(?:hey\s+)?baby\b[,:-]?\s*(.*)$/i);
        if (!wakeMatch || !/^hey\s+baby\b/i.test(normalized)) {
          continue;
        }

        const command = wakeMatch[1].trim();

        if (!command) {
          speakBaby("Yes?", true);
          continue;
        }

        if (speakingRef.current) {
          continue;
        }

        setChatOpen(true);
        setInput(command);
        sendMessageTextRef.current?.(command, true);
      }
    };

    recognitionRef.current = recognition;

    return () => {
      voiceEnabledRef.current = false;
      try {
        recognition.stop();
      } catch (_) {
        // Ignore cleanup errors.
      }
      recognitionRef.current = null;
    };
  }, []);

  function speakBaby(text, restartListening = false) {
    if (!("speechSynthesis" in window) || !text) {
      if (restartListening && voiceEnabledRef.current) {
        startVoiceRecognition();
      }
      return;
    }

    speakingRef.current = true;

    try {
      recognitionRef.current?.stop();
    } catch (_) {
      // Ignore stop errors.
    }

    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = "en-IN";
    utterance.rate = 1;
    utterance.pitch = 1;

    utterance.onend = () => {
      speakingRef.current = false;
      if (restartListening && voiceEnabledRef.current) {
        startVoiceRecognition();
      }
    };

    utterance.onerror = () => {
      speakingRef.current = false;
      if (restartListening && voiceEnabledRef.current) {
        startVoiceRecognition();
      }
    };

    window.speechSynthesis.speak(utterance);
  }

  function startVoiceRecognition() {
    if (!recognitionRef.current || !voiceEnabledRef.current) return;
    try {
      recognitionRef.current.start();
    } catch (_) {
      // Already running.
    }
  }

  function toggleVoice() {
    if (!voiceSupported) return;

    if (voiceEnabled) {
      voiceEnabledRef.current = false;
      setVoiceEnabled(false);
      setVoiceListening(false);
      setVoiceStatus("Voice off");
      try {
        recognitionRef.current?.stop();
      } catch (_) {
        // Ignore stop errors.
      }
      window.speechSynthesis?.cancel();
      return;
    }

    voiceEnabledRef.current = true;
    setVoiceEnabled(true);
    setVoiceStatus("Starting microphone...");
    setChatOpen(true);
    startVoiceRecognition();
  }

  // =========================================================
  // ASSISTANT
  // =========================================================

  async function sendMessage() {
    return sendMessageText(input.trim(), false);
  }

  async function sendMessageText(text, fromVoice = false) {
    const cleanText = text?.trim();

    if (!cleanText || loading) {
      return;
    }

    setInput("");
    setChatOpen(true);

    setMessages((current) => [
      ...current,
      {
        role: "user",
        text: cleanText,
      },
    ]);

    setLoading(true);

    try {
      const payload = {
        message: cleanText,
      };

      if (sessionId) {
        payload.session_id = sessionId;
      }

      const response = await fetch(
        `${API_URL}/assistant/chat`,
        {
          method: "POST",
          headers: {
            "Content-Type":
              "application/json",
          },
          body: JSON.stringify(payload),
        }
      );

      if (!response.ok) {
        throw new Error(
          `HTTP ${response.status}`
        );
      }

      const data = await response.json();

      if (data.context?.session_id) {
        setSessionId(
          data.context.session_id
        );
      }

      const assistantResponse =
        data.response ||
        "No response returned.";

      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          text: assistantResponse,
        },
      ]);

      if (fromVoice && voiceEnabledRef.current) {
        speakBaby(assistantResponse, true);
      }

      await Promise.all([
        loadCalendar(),
        loadEmails(),
      ]);
    } catch (error) {
      console.error(
        "Assistant error:",
        error
      );

      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          text:
            "I couldn't connect to Baby's backend. " +
            "Make sure FastAPI is running on port 8001.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  sendMessageTextRef.current = sendMessageText;

  function keyDown(event) {
    if (
      event.key === "Enter" &&
      !event.shiftKey
    ) {
      event.preventDefault();
      sendMessage();
    }
  }

  // =========================================================
  // NAVIGATION
  // =========================================================

  function navigate(label) {
    setActive(label);

    if (label === "Assistant") {
      setChatOpen(true);
      return;
    }

    if (label === "Calendar") {
      setPanel("calendar");
      setSelectedEmail(null);
      loadCalendar();
      return;
    }

    if (label === "Email") {
      setPanel("email");
      loadEmails();
      return;
    }
  }

  // =========================================================
  // QUICK ACTION
  // =========================================================

  function quick(text) {
    setInput(text);
    setChatOpen(true);

    setTimeout(() => {
      inputRef.current?.focus();
    }, 60);
  }

  // =========================================================
  // NEW CALENDAR EVENT
  // =========================================================

  function openEventModal() {
    setEventError("");

    const now = new Date();

    const date = now.toLocaleDateString(
      "en-CA",
      {
        timeZone: "Asia/Kolkata",
      }
    );

    setEventDate(date);

    const indiaTimeString =
      now.toLocaleTimeString(
        "en-GB",
        {
          hour: "2-digit",
          minute: "2-digit",
          hour12: false,
          timeZone: "Asia/Kolkata",
        }
      );

    let [hour, minute] =
      indiaTimeString
        .split(":")
        .map(Number);

    minute =
      minute < 30
        ? 30
        : 0;

    if (minute === 0) {
      hour += 1;
    }

    if (hour >= 24) {
      hour = 0;
    }

    setEventTime(
      `${String(hour).padStart(2, "0")}:${String(
        minute
      ).padStart(2, "0")}`
    );

    setEventModalOpen(true);
  }

  async function createCalendarEvent() {
    if (!eventTitle.trim()) {
      setEventError(
        "Please enter an event title."
      );
      return;
    }

    if (!eventDate || !eventTime) {
      setEventError(
        "Please select a date and time."
      );
      return;
    }

    setEventCreating(true);
    setEventError("");

    try {
      const startString =
        `${eventDate}T${eventTime}:00+05:30`;

      const startDate =
        new Date(startString);

      if (
        Number.isNaN(
          startDate.getTime()
        )
      ) {
        throw new Error(
          "Invalid date or time."
        );
      }

      const durationMinutes =
        Number(eventDuration);

      if (
        !Number.isFinite(
          durationMinutes
        ) ||
        durationMinutes <= 0
      ) {
        throw new Error(
          "Invalid event duration."
        );
      }

      const endDate =
        new Date(
          startDate.getTime() +
            durationMinutes *
              60 *
              1000
        );

      const startISO =
        startDate.toISOString();

      const endISO =
        endDate.toISOString();

      const response =
        await fetch(
          `${API_URL}/calendar/events`,
          {
            method: "POST",
            headers: {
              "Content-Type":
                "application/json",
            },
            body: JSON.stringify({
              title:
                eventTitle.trim(),
              start: startISO,
              end: endISO,
              description:
                eventDescription.trim() ||
                null,
            }),
          }
        );

      const data =
        await response
          .json()
          .catch(() => null);

      if (!response.ok) {
        throw new Error(
          data?.detail ||
            `Calendar request failed: HTTP ${response.status}`
        );
      }

      await loadCalendar();

      setEventModalOpen(false);
      setEventTitle("");
      setEventDate("");
      setEventTime("");
      setEventDuration("60");
      setEventDescription("");
      setEventError("");
    } catch (error) {
      console.error(
        "Calendar creation error:",
        error
      );

      setEventError(
        error.message ||
          "Unable to create calendar event."
      );
    } finally {
      setEventCreating(false);
    }
  }

  // =========================================================
  // RENDER
  // =========================================================

  return (
    <div className="baby">

      {/* =====================================================
          SIDEBAR
      ====================================================== */}

      <aside
        className={`sidebar ${
          collapsed
            ? "is-collapsed"
            : "is-open"
        }`}
      >
        <button
          className="menu-button"
          onClick={() =>
            setCollapsed(
              (value) => !value
            )
          }
          title={
            collapsed
              ? "Expand navigation"
              : "Collapse navigation"
          }
        >
          ☰
        </button>

        {!collapsed && (
          <div className="brand">
            <div className="brand-mark">
              B
            </div>

            <div>
              <strong>
                Baby
              </strong>

              <span>
                Personal Assistant
              </span>
            </div>
          </div>
        )}

        <nav className="navigation">
          {navItems.map(
            ([icon, label]) => (
              <button
                key={label}
                className={`nav-link ${
                  active === label
                    ? "active"
                    : ""
                }`}
                onClick={() =>
                  navigate(label)
                }
                title={
                  collapsed
                    ? label
                    : ""
                }
              >
                <span>
                  {icon}
                </span>

                {!collapsed && (
                  <b>
                    {label}
                  </b>
                )}
              </button>
            )
          )}
        </nav>

        <div className="system-status">
          <i />

          {!collapsed && (
            <span>
              System ready
            </span>
          )}
        </div>
      </aside>

      {/* =====================================================
          MAIN
      ====================================================== */}

      <main className="content">

        {/* ===================================================
            CENTER
        ==================================================== */}

        <section className="core">

          <div className="online">
            <i />
            BABY ONLINE
          </div>

          <div
            className="core-orb"
            onClick={() =>
              setChatOpen(true)
            }
          >
            <div className="orbit orbit-a" />
            <div className="orbit orbit-b" />
            <div className="orbit orbit-c" />

            <div className="orb-glow" />

            <div className="orb-surface">
              <span className="orb-light" />
            </div>
          </div>

          <button
            className="core-chat-trigger"
            onClick={() =>
              setChatOpen(true)
            }
          >
            <span>
              Ask Baby anything...
            </span>

            <small>
              OPEN ASSISTANT
            </small>
          </button>

        </section>

        {/* ===================================================
            RIGHT SIDE
        ==================================================== */}

        <aside className="right-side">

          {/* Tabs */}

          <div className="switcher">

            <button
              className={
                panel === "calendar"
                  ? "selected"
                  : ""
              }
              onClick={() => {
                setPanel("calendar");
                setSelectedEmail(null);
                loadCalendar();
              }}
            >
              CALENDAR
            </button>

            <button
              className={
                panel === "email"
                  ? "selected"
                  : ""
              }
              onClick={() => {
                setPanel("email");
                loadEmails();
              }}
            >
              EMAIL
            </button>

          </div>

          {/* =================================================
              CALENDAR
          ================================================== */}

          {panel === "calendar" ? (

            <div className="information">

              <div className="section-heading">
                <strong>
                  Today
                </strong>

                <span>
                  {getTodayLabel()}
                </span>
              </div>

              {calendarLoading && (
                <div className="data-state">
                  Loading calendar...
                </div>
              )}

              {!calendarLoading &&
                calendarError && (
                  <div className="data-state error">
                    {calendarError}

                    <button
                      className="inline-refresh"
                      onClick={
                        loadCalendar
                      }
                    >
                      RETRY
                    </button>
                  </div>
                )}

              {!calendarLoading &&
                !calendarError &&
                events.length === 0 && (
                  <div className="data-state">
                    No events today.
                  </div>
                )}

              {!calendarLoading &&
                !calendarError &&
                events.map(
                  (event, index) => {
                    const start =
                      getEventStart(
                        event
                      );

                    return (
                      <div
                        className="event"
                        key={
                          event.id ||
                          `${start}-${index}`
                        }
                      >
                        <time>
                          {formatCalendarTime(
                            start
                          )}
                        </time>

                        <div>
                          <strong>
                            {event.title ||
                              event.summary ||
                              "Untitled event"}
                          </strong>

                          <span>
                            {event.description ||
                              "Calendar event"}
                          </span>
                        </div>
                      </div>
                    );
                  }
                )}

              <div className="calendar-actions">

                <button
                  className="text-action"
                  onClick={
                    openEventModal
                  }
                >
                  + NEW EVENT
                </button>

                <button
                  className="text-action"
                  onClick={
                    loadCalendar
                  }
                  disabled={
                    calendarLoading
                  }
                >
                  ↻ REFRESH
                </button>

              </div>

            </div>

          ) : (

            /* =================================================
               GMAIL
            ================================================== */

            <div className="information">

              <div className="section-heading">
                <strong>
                  Inbox
                </strong>

                <span>
                  {emails.length} recent
                </span>
              </div>

              {emailLoading && (
                <div className="data-state">
                  Loading Gmail...
                </div>
              )}

              {!emailLoading &&
                emailError &&
                emails.length === 0 && (
                  <div className="data-state error">
                    {emailError}

                    <button
                      className="inline-refresh"
                      onClick={loadEmails}
                    >
                      RETRY
                    </button>
                  </div>
                )}

              {!emailLoading &&
                !emailError &&
                emails.length === 0 && (
                  <div className="data-state">
                    No recent emails.
                  </div>
                )}

              {!emailLoading &&
                emails.map(
                  (email, index) => (
                    <button
                      className="email email-clickable"
                      key={
                        email.id ||
                        `${email.subject}-${index}`
                      }
                      onClick={() =>
                        openEmail(email)
                      }
                      type="button"
                    >
                      <div>
                        <strong>
                          {email.from ||
                            "Unknown sender"}
                        </strong>

                        <span>
                          {email.subject ||
                            "No subject"}
                        </span>

                        {email.snippet && (
                          <small>
                            {email.snippet}
                          </small>
                        )}
                      </div>

                      <time>
                        {formatEmailTime(
                          email.date
                        )}
                      </time>
                    </button>
                  )
                )}

              <button
                className="text-action"
                onClick={loadEmails}
                disabled={emailLoading}
              >
                ↻ REFRESH GMAIL
              </button>

            </div>

          )}

          {/* =================================================
              QUICK ACTIONS
          ================================================== */}

          <div className="quick">

            <span className="mini-label">
              QUICK ACTIONS
            </span>

            <button
              onClick={() =>
                quick(
                  "What is on my calendar today?"
                )
              }
            >
              <span>▣</span>
              Today's schedule
            </button>

            <button
              onClick={() =>
                quick(
                  "Show my recent emails."
                )
              }
            >
              <span>✉</span>
              Email summary
            </button>

            <button
              onClick={() =>
                quick(
                  "What do you remember about me?"
                )
              }
            >
              <span>◇</span>
              My memory
            </button>

          </div>

        </aside>
      </main>

      {/* =====================================================
          ASSISTANT CHAT
      ====================================================== */}

      {chatOpen && (
        <div
          className="chat-layer"
          onMouseDown={() =>
            setChatOpen(false)
          }
        >
          <section
            className="chat"
            onMouseDown={(event) =>
              event.stopPropagation()
            }
          >

            <header>

              <div>
                <span>
                  BABY / ASSISTANT
                </span>

                <strong>
                  Conversation
                </strong>
              </div>

              <button
                onClick={() =>
                  setChatOpen(false)
                }
              >
                ×
              </button>

            </header>

            <div
              className="messages"
              ref={messagesRef}
            >

              {messages.length === 0 && (
                <div className="empty">

                  <div className="mini-orb" />

                  <span>
                    Ask Baby anything.
                  </span>

                </div>
              )}

              {messages.map(
                (message, index) => (
                  <div
                    className={`message ${message.role}`}
                    key={index}
                  >
                    {message.text}
                  </div>
                )
              )}

              {loading && (
                <div className="message assistant typing">
                  <i />
                  <i />
                  <i />
                </div>
              )}

            </div>

            <div className="composer">

              <textarea
                ref={inputRef}
                value={input}
                onChange={(event) =>
                  setInput(
                    event.target.value
                  )
                }
                onKeyDown={keyDown}
                placeholder="Ask Baby..."
                rows="1"
              />

              <button
                type="button"
                className={`voice-button ${voiceEnabled ? "is-active" : ""}`}
                onClick={toggleVoice}
                title={
                  voiceSupported
                    ? voiceEnabled
                      ? voiceStatus
                      : "Enable always-listening voice mode"
                    : "Voice recognition is not supported in this browser"
                }
                disabled={!voiceSupported}
              >
                {voiceEnabled ? "●" : "🎙"}
              </button>

              <button
                onClick={
                  sendMessage
                }
                disabled={
                  loading ||
                  !input.trim()
                }
              >
                →
              </button>

            </div>

            {voiceEnabled && (
              <div className="voice-status">
                <span className={voiceListening ? "voice-pulse" : ""} />
                {voiceStatus}
              </div>
            )}

          </section>
        </div>
      )}

      {/* =====================================================
          EMAIL READER DIALOGUE
      ====================================================== */}

      {(selectedEmail || emailReaderLoading || emailReaderError) && (
        <div
          className="email-dialog-layer"
          onMouseDown={closeEmailReader}
        >
          <section
            className="email-dialog"
            onMouseDown={(event) =>
              event.stopPropagation()
            }
          >
            <header className="email-dialog-header">
              <div>
                <span>BABY / EMAIL</span>
                <strong>Message</strong>
              </div>

              <button
                type="button"
                onClick={closeEmailReader}
                title="Close email"
              >
                ×
              </button>
            </header>

            {emailReaderLoading && (
              <div className="email-dialog-loading">
                Opening email...
              </div>
            )}

            {!emailReaderLoading &&
              emailReaderError && (
                <div className="email-dialog-error">
                  <p>{emailReaderError}</p>

                  <button
                    type="button"
                    onClick={() => {
                      const current = selectedEmail;
                      if (current?.id) {
                        openEmail(current);
                      }
                    }}
                  >
                    RETRY
                  </button>
                </div>
              )}

            {!emailReaderLoading &&
              !emailReaderError &&
              selectedEmail && (
                <div className="email-dialog-content">
                  <div className="email-dialog-subject">
                    {selectedEmail.subject ||
                      "No subject"}
                  </div>

                  <div className="email-dialog-meta">
                    <div>
                      <span>FROM</span>
                      <strong>
                        {selectedEmail.from ||
                          "Unknown sender"}
                      </strong>
                    </div>

                    <div>
                      <span>TO</span>
                      <strong>
                        {selectedEmail.to ||
                          "Unknown recipient"}
                      </strong>
                    </div>

                    {selectedEmail.cc && (
                      <div>
                        <span>CC</span>
                        <strong>
                          {selectedEmail.cc}
                        </strong>
                      </div>
                    )}

                    <div>
                      <span>DATE</span>
                      <strong>
                        {formatFullEmailDate(
                          selectedEmail.date
                        )}
                      </strong>
                    </div>
                  </div>

                  <div className="email-dialog-divider" />

                  <div className="email-dialog-body">
                    {selectedEmail.body ||
                      selectedEmail.snippet ||
                      "This email has no readable body."}
                  </div>
                </div>
              )}
          </section>
        </div>
      )}

      {/* =====================================================
          NEW EVENT MODAL
      ====================================================== */}

      {eventModalOpen && (
        <div
          className="event-modal-layer"
          onMouseDown={() =>
            setEventModalOpen(false)
          }
        >
          <section
            className="event-modal"
            onMouseDown={(event) =>
              event.stopPropagation()
            }
          >

            <header className="event-modal-header">

              <div>
                <span>
                  CALENDAR
                </span>

                <strong>
                  New Event
                </strong>
              </div>

              <button
                onClick={() =>
                  setEventModalOpen(false)
                }
              >
                ×
              </button>

            </header>

            <div className="event-form">

              <label>
                <span>
                  Title
                </span>

                <input
                  type="text"
                  value={eventTitle}
                  onChange={(event) =>
                    setEventTitle(
                      event.target.value
                    )
                  }
                  placeholder="Project meeting"
                  autoFocus
                />
              </label>

              <div className="event-form-row">

                <label>
                  <span>
                    Date
                  </span>

                  <input
                    type="date"
                    value={eventDate}
                    onChange={(event) =>
                      setEventDate(
                        event.target.value
                      )
                    }
                  />
                </label>

                <label>
                  <span>
                    Time
                  </span>

                  <input
                    type="time"
                    value={eventTime}
                    onChange={(event) =>
                      setEventTime(
                        event.target.value
                      )
                    }
                  />
                </label>

              </div>

              <label>
                <span>
                  Duration
                </span>

                <select
                  value={eventDuration}
                  onChange={(event) =>
                    setEventDuration(
                      event.target.value
                    )
                  }
                >
                  <option value="30">
                    30 minutes
                  </option>

                  <option value="60">
                    1 hour
                  </option>

                  <option value="90">
                    1.5 hours
                  </option>

                  <option value="120">
                    2 hours
                  </option>
                </select>
              </label>

              <label>
                <span>
                  Description
                </span>

                <textarea
                  value={
                    eventDescription
                  }
                  onChange={(event) =>
                    setEventDescription(
                      event.target.value
                    )
                  }
                  placeholder="Optional"
                  rows="3"
                />
              </label>

              {eventError && (
                <div className="event-form-error">
                  {eventError}
                </div>
              )}

              <div className="event-form-actions">

                <button
                  type="button"
                  className="event-cancel"
                  onClick={() =>
                    setEventModalOpen(false)
                  }
                >
                  CANCEL
                </button>

                <button
                  type="button"
                  className="event-create"
                  onClick={
                    createCalendarEvent
                  }
                  disabled={
                    eventCreating
                  }
                >
                  {eventCreating
                    ? "CREATING..."
                    : "CREATE EVENT"}
                </button>

              </div>

            </div>

          </section>
        </div>
      )}

    </div>
  );
}