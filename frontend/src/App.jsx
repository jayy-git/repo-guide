import { useEffect, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import "./App.css";


const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
const SAMPLE_BUGGY_CODE = `# Sample Python code with classic bug patterns\ndef process_data(items=[], config={}):\n    file = open("output.log", "w")\n    file.write("Processing started\\n")\n\n    if items == None:\n        return None\n        print("Unreachable code after return")\n\n    try:\n        total = 100 / len(items)\n    except:\n        pass\n\n    return total\n`;

const NAV_ITEMS = [
  { id: "dashboard", label: "Dashboard", icon: "⌂" },
  { id: "scanner", label: "Analyze Repository", icon: "⌕" },
  { id: "qa", label: "Q&A", icon: "◌" },
  { id: "workspace", label: "Repository Workspace", icon: "▤" },
  { id: "map", label: "Interactive Code Map", icon: "⌘" },
  { id: "repositories", label: "Repositories", icon: "▱" },
  { id: "reports", label: "Reports", icon: "▤" },
  { id: "settings", label: "Settings", icon: "⚙" },
];

function TechnologyStackPanel({ stack, title = "Technology Stack" }) {
  const groups = [
    ["Programming languages", stack?.languages],
    ["Frontend frameworks & libraries", stack?.frontend],
    ["Backend frameworks", stack?.backend],
    ["Databases", stack?.database],
    ["Build tools & package managers", stack?.package_managers],
  ];
  return <section className="panel technology-stack-panel">
    <div className="panel-title"><div><span className="panel-title-icon">⌘</span><h2>{title}</h2></div><span className="muted">Detected from repository files</span></div>
    <div className="technology-stack-grid">{groups.map(([label, values]) => <div className="technology-group" key={label}><h3>{label}</h3>{values?.length ? <div className="technology-tags">{values.map((value) => <span className="technology-tag" key={value}>{value}</span>)}</div> : <p className="muted">None detected</p>}</div>)}</div>
  </section>;
}

function App() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isSignUp, setIsSignUp] = useState(false);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [user, setUser] = useState(null);
  const [activeTab, setActiveTab] = useState("dashboard");
  const [analysisMode, setAnalysisMode] = useState("repository");
  const [repoPath, setRepoPath] = useState(".");
  const [includeAi, setIncludeAi] = useState(false);
  const [repoAnalysis, setRepoAnalysis] = useState(null);
  const [isAnalyzingRepo, setIsAnalyzingRepo] = useState(false);
  const [repoError, setRepoError] = useState("");
  const [severityFilter, setSeverityFilter] = useState("ALL");
  const [sandboxCode, setSandboxCode] = useState(SAMPLE_BUGGY_CODE);
  const [sandboxAnalysis, setSandboxAnalysis] = useState(null);
  const [isAnalyzingSandbox, setIsAnalyzingSandbox] = useState(false);
  const [sandboxError, setSandboxError] = useState("");
  const [copiedIndex, setCopiedIndex] = useState(null);
  const [theme, setTheme] = useState(() => localStorage.getItem("repoguide-theme") || "dark");
  const [palette, setPalette] = useState(() => {
  const savedPalette = localStorage.getItem("repoguide-palette");
  return savedPalette === "violet" || !savedPalette ? "blue" : savedPalette;
});
  const [search, setSearch] = useState("");
  const [question, setQuestion] = useState("");
  const [answers, setAnswers] = useState([]);
  const [selectedMapNode, setSelectedMapNode] = useState(null);
  const [mapFolderPath, setMapFolderPath] = useState("");
  const [workspaceFiles, setWorkspaceFiles] = useState([]);
  const [selectedWorkspaceFile, setSelectedWorkspaceFile] = useState(null);
  const [workspaceError, setWorkspaceError] = useState("");
  const [workspaceLoading, setWorkspaceLoading] = useState(false);
  const [workspaceFileLoading, setWorkspaceFileLoading] = useState(false);
  const [workspaceScoutQuestion, setWorkspaceScoutQuestion] = useState("");
  const [workspaceScoutAnswers, setWorkspaceScoutAnswers] = useState([]);
  const [workspaceScoutLoading, setWorkspaceScoutLoading] = useState(false);
  const [scanHistory, setScanHistory] = useState([]);
  const [scanHistoryError, setScanHistoryError] = useState("");

  useEffect(() => {
    localStorage.setItem("repoguide-theme", theme);
    localStorage.setItem("repoguide-palette", palette);
  }, [theme, palette]);

  useEffect(() => {
    let cancelled = false;
    fetch(`${API_URL}/auth/me`, { credentials: "include" })
      .then((response) => response.json())
      .then((data) => {
        if (!cancelled && data.logged_in) setUser(data);
      })
      .catch(() => {});
    return () => { cancelled = true; };
  }, []);

  async function handleLogin(event) {
    event.preventDefault(); setMessage(""); setLoading(true);
    try {
      const response = await fetch(`${API_URL}/auth/login`, {
        method: "POST", headers: { "Content-Type": "application/json" }, credentials: "include",
        body: JSON.stringify({ email, password }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Login failed.");
      const sessionResponse = await fetch(`${API_URL}/auth/me`, { credentials: "include" });
      const sessionData = await sessionResponse.json();
      if (!sessionResponse.ok || !sessionData.logged_in) throw new Error("Login succeeded, but the session was not recognized.");
      setUser({ ...sessionData, email }); setMessage(""); setActiveTab("dashboard");
    } catch (error) {
      setMessage(error.message === "Failed to fetch" ? "Cannot connect to the backend. Make sure FastAPI is running on port 8000." : error.message);
    } finally { setLoading(false); }
  }

  async function handleSignUp(event) {
    event.preventDefault(); setMessage("");
    if (password !== confirmPassword) { setMessage("Passwords do not match."); return; }
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/auth/register`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, email, password }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Registration failed.");
      setMessage("Account created successfully! You can now sign in."); setIsSignUp(false);
      setName(""); setConfirmPassword(""); setPassword("");
    } catch (error) {
      setMessage(error.message === "Failed to fetch" ? "Cannot connect to the backend. Make sure FastAPI is running on port 8000." : error.message);
    } finally { setLoading(false); }
  }

  async function handleAnalyzeRepository(event) {
    if (event) event.preventDefault(); setRepoError(""); setIsAnalyzingRepo(true);
    try {
      const response = await fetch(`${API_URL}/repository/analyze-bugs`, {
        method: "POST", headers: { "Content-Type": "application/json" }, credentials: "include",
        body: JSON.stringify({ repository_path: repoPath.trim() || ".", include_ai: includeAi }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Failed to analyze repository.");
      setRepoAnalysis(data); await loadScanHistory(); setActiveTab("scanner");
    } catch (error) { setRepoError(error.message); }
    finally { setIsAnalyzingRepo(false); }
  }

  async function handleAnalyzeSnippet(event) {
    if (event) event.preventDefault(); setSandboxError(""); setIsAnalyzingSandbox(true);
    try {
      const response = await fetch(`${API_URL}/code/analyze-snippet`, {
        method: "POST", headers: { "Content-Type": "application/json" }, credentials: "include",
        body: JSON.stringify({ code: sandboxCode, filename: "sandbox.py", include_ai: includeAi }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Failed to analyze code snippet.");
      setSandboxAnalysis(data);
    } catch (error) { setSandboxError(error.message); }
    finally { setIsAnalyzingSandbox(false); }
  }

  function handleDownloadReport() {
    if (!repoAnalysis?.report_markdown) return;
    const blob = new Blob([repoAnalysis.report_markdown], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob); const link = document.createElement("a");
    link.href = url; link.download = `BUG_REPORT_${repoAnalysis.repository_name || "RepoGuide"}.md`;
    document.body.appendChild(link); link.click(); document.body.removeChild(link); URL.revokeObjectURL(url);
  }

  function handleCopyFix(fixText, idx) {
    if (!fixText) return;
    navigator.clipboard?.writeText(fixText).then(() => { setCopiedIndex(idx); setTimeout(() => setCopiedIndex(null), 1800); });
  }

  async function handleSignOut() {
    try {
      await fetch(`${API_URL}/auth/logout`, { method: "POST", credentials: "include" });
    } catch (error) {
      console.warn("Could not reach the logout endpoint:", error);
    } finally {
      setUser(null); setRepoAnalysis(null); setSandboxAnalysis(null); setAnswers([]); setActiveTab("dashboard");
    }
  }

  const findings = useMemo(() => repoAnalysis?.findings || [], [repoAnalysis]);
  const displayedRepoFindings = findings.filter((finding) => severityFilter === "ALL" || String(finding.severity).toUpperCase() === severityFilter.toUpperCase());
  const severity = repoAnalysis?.severity_breakdown || {};
  const displayName = name || user?.name || (user?.email || email || "Developer").split("@")[0].replace(/[._-]/g, " ");
  const categoryStats = useMemo(() => {
  const counts = {};
  findings.forEach((item) => {
    const key = item.category || "Other";
    counts[key] = (counts[key] || 0) + 1;
  });
  return Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6);
}, [findings]);
  const mapNodes = useMemo(() => {
    const files = Array.isArray(workspaceFiles) ? workspaceFiles : [];
    const folders = new Set();

    files.forEach((file) => {
      const parts = file.split("/");
      for (let i = 1; i < parts.length; i++) {
        folders.add(parts.slice(0, i).join("/"));
      }
    });

    const currentFolder = mapFolderPath;
    const visibleFolders = [...folders]
      .filter((folder) => {
        const parent = folder.includes("/")
          ? folder.slice(0, folder.lastIndexOf("/"))
          : "";
        return parent === currentFolder;
      })
      .sort();

    const visibleFiles = files
      .filter((file) => {
        const parts = file.split("/");
        const parent = parts.length > 1
          ? parts.slice(0, -1).join("/")
          : "";
        return parent === currentFolder;
      })
      .sort();

    const items = [
      ...visibleFolders.map((folder) => ({
        id: `folder:${folder}`,
        label: folder.split("/").pop(),
        path: folder,
        kind: "folder",
        detail: `Folder containing repository files: ${folder}`,
      })),
      ...visibleFiles.map((file) => ({
        id: `file:${file}`,
        label: file.split("/").pop(),
        path: file,
        kind: "file",
        detail: `Repository file: ${file}`,
      })),
    ];

    const nodes = [
      {
        id: "root",
        label: repoAnalysis?.repository_name || "Repository",
        path: "",
        kind: "root",
        x: 50,
        y: 12,
        detail: currentFolder
          ? `Exploring folder: ${currentFolder}`
          : "Repository root. Select a folder to explore its contents.",
      },
    ];

    items.forEach((item, index) => {
  const columns = Math.min(items.length, 4);
  const row = Math.floor(index / columns);
  const column = index % columns;
  const itemsInRow = Math.min(columns, items.length - row * columns);

  nodes.push({
    ...item,
    x: 12 + column * (76 / Math.max(itemsInRow - 1, 1)),
    y: 32 + row * 18,
  });
});

    if (currentFolder) {
      nodes.push({
        id: "back",
        label: "← Back",
        path: currentFolder.includes("/")
          ? currentFolder.slice(0, currentFolder.lastIndexOf("/"))
          : "",
        kind: "folder",
        x: 12,
        y: 12,
        detail: "Return to the parent folder.",
      });
    }

    if (findings.length) {
      nodes.push({
        id: "findings",
        label: `${findings.length} findings`,
        kind: "issue",
        x: 88,
        y: 12,
        detail: "Detected code issues from your latest scan.",
      });
    }

    return nodes;
  }, [workspaceFiles, mapFolderPath, repoAnalysis, findings.length]);
  async function answerQuestion(event) {
    event.preventDefault();

    const q = question.trim();
    if (!q) return;

    setQuestion("");
    setAnswers((current) => [
      ...current,
      { question: q, answer: "Analyzing your repository..." },
    ]);

    try {
      const response = await fetch(`${API_URL}/repository/ask`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repository_path: repoPath || ".", question: q }),
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Unable to answer your question.");
      }

      const answer = typeof data.answer === "string"
        ? data.answer
        : "The backend did not return an answer. Please try rephrasing your question.";

      setAnswers((current) =>
        current.map((item, index) =>
          index === current.length - 1 && item.answer === "Analyzing your repository..."
            ? { ...item, answer }
            : item
        )
      );
    } catch (error) {
      setAnswers((current) =>
        current.map((item) =>
          item.question === q && item.answer === "Analyzing your repository..."
            ? { ...item, answer: `Could not get an answer: ${error.message}` }
            : item
        )
      );
    }
  }

async function loadWorkspaceFiles() {
  setWorkspaceLoading(true);
  setWorkspaceError("");
  try {
    const response = await fetch(`${API_URL}/repository/files?repository_path=${encodeURIComponent(repoPath || ".")}`, { credentials: "include" });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Unable to load repository files.");
    const rawFiles = Array.isArray(data.files) ? data.files : Array.isArray(data) ? data : [];
    const files = rawFiles.map((item) => typeof item === "string" ? item : item.path || item.file || item.name).filter((item) => typeof item === "string" && item.length > 0);
    setWorkspaceFiles(files);
    setSelectedWorkspaceFile(null);
  } catch (error) {
    setWorkspaceFiles([]);
    setWorkspaceError(error.message || "Unable to load repository files.");
  } finally {
    setWorkspaceLoading(false);
  }
}

async function openWorkspaceFile(filePath) {
  setWorkspaceFileLoading(true);
  setWorkspaceError("");
  try {
    const params = new URLSearchParams({ repository_path: repoPath || ".", file_path: filePath });
    const response = await fetch(`${API_URL}/repository/file-content?${params.toString()}`, { credentials: "include" });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Unable to open this file.");
    setSelectedWorkspaceFile(data);
  } catch (error) {
    setWorkspaceError(error.message || "Unable to open this file.");
    setSelectedWorkspaceFile(null);
  } finally {
    setWorkspaceFileLoading(false);
  }
}

async function loadScanHistory() {
  setScanHistoryError("");
  try {
    const response = await fetch(`${API_URL}/repository/scan-history?limit=20`, { credentials: "include" });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Unable to load scan history.");
    setScanHistory(Array.isArray(data.history) ? data.history : []);
  } catch (error) {
    setScanHistoryError(error.message || "Unable to load scan history.");
  }
}

async function askScoutInWorkspace(event) {
  event.preventDefault();
  const q = workspaceScoutQuestion.trim();
  if (!q || workspaceScoutLoading) return;
  setWorkspaceScoutQuestion("");
  setWorkspaceScoutAnswers((current) => [...current, { question: q, answer: "Scout is reviewing your repository…" }]);
  setWorkspaceScoutLoading(true);
  try {
    const response = await fetch(`${API_URL}/repository/ask`, {
      method: "POST", credentials: "include", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ repository_path: repoPath || ".", question: q }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Scout could not answer that question.");
    const answer = typeof data.answer === "string" ? data.answer : JSON.stringify(data, null, 2);
    setWorkspaceScoutAnswers((current) => current.map((item, index) => index === current.length - 1 ? { ...item, answer } : item));
  } catch (error) {
    setWorkspaceScoutAnswers((current) => current.map((item, index) => index === current.length - 1 ? { ...item, answer: `Could not get an answer: ${error.message}` } : item));
  } finally {
    setWorkspaceScoutLoading(false);
  }
}

useEffect(() => {
  if (user && (activeTab === "workspace" || activeTab === "map")) {
    loadWorkspaceFiles();
  }
  // Load files when the user opens Workspace or Code Map, or changes repository path.
  // eslint-disable-next-line react-hooks/exhaustive-deps
}, [user, activeTab, repoPath]);

useEffect(() => {
  if (user && activeTab === "dashboard") loadScanHistory();
}, [user, activeTab]);


  if (!user) return (
    <main className={`auth-shell theme-${theme} palette-${palette}`} data-theme={theme} data-palette={palette}>
      <div className="auth-brand"><span className="brand-mark">◇</span><span>RepoGuide</span></div>
      <div className="auth-layout">
        <section className="auth-hero">
          <span className="eyebrow">YOUR INTELLIGENT DEVELOPER WORKSPACE</span>
          <h1>Understand code.<br /><span>Ship smarter.</span></h1>
          <p>Analyze repositories, spot hidden bugs, and understand how your code fits together—all in one calm, focused workspace.</p>
          <div className="auth-feature"><span>⌕</span><div><strong>Repository intelligence</strong><small>Scan code and review findings with clear explanations.</small></div></div>
          <div className="auth-feature"><span>⌘</span><div><strong>Explore your codebase</strong><small>See files and modules as a connected system.</small></div></div>
          <div className="auth-feature"><span>▤</span><div><strong>Actionable reports</strong><small>Keep your review findings and suggested fixes close at hand.</small></div></div>
          <div className="auth-orbit orbit-one"/><div className="auth-orbit orbit-two"/>
        </section>
        <section className="auth-card">
          <div className="auth-card-icon">✦</div><span className="eyebrow">{isSignUp ? "START BUILDING" : "WELCOME BACK"}</span>
          <h2>{isSignUp ? "Create your account" : "Sign in to RepoGuide"}</h2>
          <p className="muted">{isSignUp ? "Set up your workspace in a moment." : "Your code workspace is waiting for you."}</p>
          <form onSubmit={isSignUp ? handleSignUp : handleLogin} className="auth-form">
            {isSignUp && <label>Full name<input value={name} onChange={(e) => setName(e.target.value)} placeholder="Your name" autoComplete="name" required /></label>}
            <label>Email address<input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" autoComplete="email" required /></label>
            <label>Password<input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Enter your password" autoComplete={isSignUp ? "new-password" : "current-password"} required /></label>
            {isSignUp && <label>Confirm password<input type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} placeholder="Repeat your password" autoComplete="new-password" required /></label>}
            <button className="primary-button auth-submit" disabled={loading}>{loading ? "Please wait…" : isSignUp ? "Create account" : "Sign in"}<span>→</span></button>
          </form>
          <div className="auth-switch">{isSignUp ? "Already have an account?" : "New to RepoGuide?"}<button onClick={() => { setIsSignUp(!isSignUp); setMessage(""); }}>{isSignUp ? "Sign in" : "Create account"}</button></div>
          {message && <div className={`notice ${message.toLowerCase().includes("success") ? "success" : "error"}`} role="status">{message}</div>}
          <div className="auth-footnote">Protected workspace · Session-based authentication</div>
        </section>
      </div>
    </main>
  );

  return (
    <main className={`app-shell theme-${theme} palette-${palette}`} data-theme={theme} data-palette={palette}>
      <aside className="sidebar">
        <button className="brand-button" onClick={() => setActiveTab("dashboard")}><span className="brand-mark">◇</span><span>RepoGuide</span></button>
        <div className="sidebar-label">WORKSPACE</div>
        <nav className="side-nav" aria-label="Main navigation">
          {NAV_ITEMS.map((item) => <button key={item.id} className={`nav-item ${activeTab === item.id ? "active" : ""}`} onClick={() => setActiveTab(item.id)}><span className="nav-icon">{item.icon}</span><span>{item.label}</span>{item.id === "scanner" && isAnalyzingRepo && <span className="nav-pulse"/>}</button>)}
        </nav>
        <div className="sidebar-spacer"/>
        <div className="sidebar-promo"><span className="promo-spark">✦</span><strong>Built for developers<br/>who ship smarter.</strong><small>Understand more. Debug less.</small></div>
        <div className="sidebar-bottom"><span className="status-dot"/> RepoGuide v1.0 <span className="sidebar-status">● Ready</span></div>
      </aside>

      <section className="main-area">
        <header className="topbar">
          <div className="global-search"><span>⌕</span><input aria-label="Search workspace" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search repositories, findings, or pages…" /> <kbd>Ctrl K</kbd></div>
          <div className="topbar-actions"><button className="icon-button" title="Notifications" aria-label="Notifications" onClick={() => setMessage("You're all caught up.")}>♧</button><div className="user-menu"><span className="avatar">{displayName.trim().charAt(0).toUpperCase() || "D"}</span><div className="user-meta"><strong>{displayName}</strong><small>{user.role || "Developer"}</small></div><button className="chevron-button" onClick={() => setActiveTab("settings")} aria-label="Open settings">⌄</button></div></div>
        </header>

        <div className="page-content">
          {message && <div className="inline-notice" role="status">{message}<button onClick={() => setMessage("")}>×</button></div>}

          {activeTab === "dashboard" && <>
            <section className="hero-banner"><div className="hero-copy"><span className="eyebrow">YOUR DEVELOPER WORKSPACE</span><p className="welcome-line">Welcome back,</p><h1>{displayName} <span className="wave">✦</span></h1><p className="hero-description">Your intelligent workspace to analyze repositories, detect bugs, and understand your code.</p><button className="primary-button hero-button" onClick={() => setActiveTab("scanner")}>Analyze Repository <span>→</span></button></div><div className="hero-art" aria-hidden="true"><div className="art-star star-a">✦</div><div className="art-star star-b">✧</div><div className="code-window back-window"><div className="window-dots"><i/><i/><i/></div><span className="code-line long"/><span className="code-line medium"/><span className="code-line short"/><span className="code-line long"/><span className="code-line tiny"/></div><div className="code-window front-window"><div className="window-dots"><i/><i/><i/></div><span className="code-line medium"/><span className="code-line long"/><span className="code-line short"/></div><div className="floating-tag bug-tag">✹ Detect bugs</div><div className="floating-tag understand-tag">▣ Understand code</div><div className="floating-tag structure-tag">⌘ Explore structure</div></div></section>
            <div className="stats-grid">
              <StatCard icon="▱" tone="violet" title="Repository scans" value={scanHistory.length || (repoAnalysis ? 1 : "—")} detail={scanHistory.length ? "Saved scans" : repoAnalysis ? "Latest scan available" : "Run your first scan"}/>
              <StatCard icon="✹" tone="pink" title="Bugs detected" value={repoAnalysis ? (repoAnalysis.total_findings ?? findings.length) : "—"} detail={repoAnalysis ? `${severity.Critical || severity.CRITICAL || 0} critical findings` : "Issues appear after analysis"}/>
              <StatCard icon="✓" tone="green" title="Code health" value={repoAnalysis?.health_score != null ? `${repoAnalysis.health_score}%` : "—"} detail={repoAnalysis ? "Latest health score" : "Awaiting your first scan"}/>
              <StatCard icon="▤" tone="blue" title="Reports ready" value={repoAnalysis?.report_markdown ? "1" : "—"} detail={repoAnalysis?.report_markdown ? "Latest report available" : "Reports from your scans"}/>
            </div>
            {repoAnalysis && <TechnologyStackPanel stack={repoAnalysis.technology_stack} />}
            <section className="panel health-trend-panel">
              <div className="panel-title"><div><span className="panel-title-icon">↗</span><h2>Repository health trend</h2></div><span className="muted">Saved scan history · 0–100</span></div>
              {scanHistoryError ? <div className="notice error">{scanHistoryError}</div> : scanHistory.length === 0 ? <EmptyChart title="No saved scan history yet" text="Run a repository scan. Its real health score will be saved here, and future scans will build the trend."/> : <HealthTrend history={scanHistory} />}
            </section>
            <div className="dashboard-grid overview-grid">
              <section className="panel chart-panel"><PanelTitle icon="▥" title="Findings by category" action="View analysis" onAction={() => setActiveTab("scanner")}/>{categoryStats.length ? <div className="bar-chart">{categoryStats.map(([label, count]) => <HorizontalBar key={label} label={label} value={count} max={Math.max(...categoryStats.map((row) => row[1]), 1)} tone="violet"/>)}</div> : <EmptyChart title="Your chart will appear here" text="Run a repository scan to see which issue categories need attention."/>}</section>
              <section className="panel chart-panel"><PanelTitle icon="⌁" title="Severity overview" action="View findings" onAction={() => setActiveTab("scanner")}/>{repoAnalysis ? <div className="bar-chart">{[ ["Critical", severity.Critical ?? severity.CRITICAL ?? 0, "pink"], ["High", severity.High ?? severity.HIGH ?? 0, "orange"], ["Medium", severity.Medium ?? severity.MEDIUM ?? 0, "blue"], ["Low", severity.Low ?? severity.LOW ?? 0, "violet"] ].map(([label, value, tone]) => <HorizontalBar key={label} label={label} value={value} max={Math.max(...[severity.Critical ?? severity.CRITICAL ?? 0, severity.High ?? severity.HIGH ?? 0, severity.Medium ?? severity.MEDIUM ?? 0, severity.Low ?? severity.LOW ?? 0], 1)} tone={tone}/> )}</div> : <EmptyChart title="No analysis yet" text="Severity comparisons are based on your real scan results—no demo data."/>}</section>
              <section className="panel activity-panel"><PanelTitle icon="◷" title="Recent activity" action="View all" onAction={() => setActiveTab("reports")}/>{repoAnalysis ? <div className="activity-row"><span className="activity-icon">✓</span><div><strong>Repository analysis completed</strong><small>{repoAnalysis.repository_name || repoPath}</small></div><span className="activity-time">Just now</span></div> : <div className="activity-empty"><span className="activity-icon">◷</span><div><strong>Nothing here just yet</strong><small>Your latest scans and reports will show up here.</small></div></div>}</section>
              <section className="panel quick-panel"><PanelTitle icon="ϟ" title="Quick actions" /><div className="quick-actions"><QuickAction icon="⌕" title="Analyze repository" text="Scan code for issues" onClick={() => setActiveTab("scanner")}/><QuickAction icon="◌" title="Ask a question" text="Understand scan results" onClick={() => setActiveTab("qa")}/><QuickAction icon="⌘" title="Explore code map" text="See how files connect" onClick={() => setActiveTab("map")}/><QuickAction icon="▤" title="View reports" text="Review and export results" onClick={() => setActiveTab("reports")}/></div></section>
            </div>
          </>}

          {activeTab === "scanner" && <>
            <PageHeading eyebrow="REPOSITORY INTELLIGENCE" title="Analyze Repository" description="Paste a public GitHub repository URL or enter a local project path to scan for bugs and code-quality issues."/>
            <div className="analysis-mode-switch"><button className={analysisMode === "repository" ? "selected" : ""} onClick={() => setAnalysisMode("repository")}>⌕ Repository scan</button><button className={analysisMode === "sandbox" ? "selected" : ""} onClick={() => setAnalysisMode("sandbox")}>‹› Interactive code sandbox</button></div>
            {analysisMode === "repository" ? <>
            <section className="panel scan-launch-panel"><form onSubmit={handleAnalyzeRepository} className="scan-form"><label className="field-label" htmlFor="repoPath">GitHub URL or repository directory <span>Paste a public GitHub URL, or enter a local path relative to the project root</span></label><div className="scan-input-row"><span className="input-prefix">⌁</span><input id="repoPath" value={repoPath} onChange={(e) => setRepoPath(e.target.value)} placeholder="https://github.com/owner/repository or . / backend"/><button className="primary-button" type="submit" disabled={isAnalyzingRepo}>{isAnalyzingRepo ? <><span className="spinner"/> Analyzing…</> : <>Analyze repository <span>→</span></>}</button></div><label className="ai-option"><input type="checkbox" checked={includeAi} onChange={(e) => setIncludeAi(e.target.checked)}/><span><strong>Include AI explanations</strong><small>Optional · Requires GEMINI_API_KEY configured in your backend environment</small></span></label></form>{repoError && <div className="notice error">{repoError}</div>}</section>
            {repoAnalysis ? <>
              <div className="stats-grid result-stats"><StatCard icon="✓" tone="green" title="Code health score" value={(repoAnalysis.total_analyzed_files ?? 0) === 0 || repoAnalysis.health_score == null ? "N/A" : `${repoAnalysis.health_score}/100`} detail={(repoAnalysis.total_analyzed_files ?? 0) === 0 ? "No supported source files were analyzed" : Number(repoAnalysis.health_score) >= 80 ? "Good quality" : Number(repoAnalysis.health_score) >= 50 ? "Room to improve" : "Needs attention"}/><StatCard icon="▱" tone="violet" title="Source files analyzed" value={repoAnalysis.total_analyzed_files ?? ((repoAnalysis.total_python_files ?? 0) + (repoAnalysis.total_javascript_files ?? 0))} detail={`${repoAnalysis.total_python_files ?? 0} Python · ${repoAnalysis.total_javascript_files ?? 0} JS/TS`}/><StatCard icon="✹" tone="pink" title="Total findings" value={repoAnalysis.total_findings ?? findings.length} detail="Detected code issues"/><StatCard icon="⌁" tone="orange" title="High / critical" value={(severity.Critical ?? severity.CRITICAL ?? 0) + (severity.High ?? severity.HIGH ?? 0)} detail="Prioritize these findings"/></div>
              <TechnologyStackPanel stack={repoAnalysis.technology_stack} />
              <section className="panel findings-panel"><div className="panel-heading-row"><div><span className="eyebrow">SCAN RESULTS</span><h2>Detailed code findings <span className="count-chip">{displayedRepoFindings.length}</span></h2></div><div className="result-toolbar"><select aria-label="Filter by severity" value={severityFilter} onChange={(e) => setSeverityFilter(e.target.value)}>{["ALL", "Critical", "High", "Medium", "Low"].map((item) => <option key={item} value={item}>{item === "ALL" ? "All severities" : item}</option>)}</select><button className="secondary-button" onClick={handleDownloadReport} disabled={!repoAnalysis.report_markdown}>↓ Download report</button></div></div>
                {displayedRepoFindings.length ? <div className="findings-list">{displayedRepoFindings.map((finding, index) => <FindingCard key={`${finding.file}-${finding.line}-${index}`} finding={finding} index={index} copiedIndex={copiedIndex} onCopy={handleCopyFix}/>)}</div> : (repoAnalysis.total_analyzed_files ?? ((repoAnalysis.total_python_files ?? 0) + (repoAnalysis.total_javascript_files ?? 0))) === 0 ? <EmptyChart title="No supported source files were analyzed" text={`No Python or JavaScript/TypeScript source files were successfully analyzed. JavaScript scan status: ${repoAnalysis.javascript_scan_status || "unknown"}. Zero findings does not mean the repository is bug-free if scanning failed.`}/> : <EmptyChart title="No findings match this filter" text="No findings were reported for the analyzed Python files with the selected severity. Try another severity filter."/>}
              </section>
            </> : <section className="empty-analysis"><div className="empty-illustration">⌁</div><h3>Ready when you are</h3><p>Start a scan to reveal your repository's health score, bug findings, severity breakdown, and suggested fixes.</p><button className="secondary-button" onClick={() => setRepoPath(".")}>Use project root</button></section>}
            </> : <div className="sandbox-layout"><section className="panel sandbox-editor-panel"><div className="panel-title"><div><span className="panel-title-icon">‹›</span><h2>Python code sandbox</h2></div><span className="sandbox-language">Python</span></div><p className="sandbox-intro">Paste a snippet to inspect it for common bug patterns. Analysis runs through your existing FastAPI endpoint.</p><textarea className="sandbox-textarea" value={sandboxCode} onChange={(e) => setSandboxCode(e.target.value)} spellCheck={false} aria-label="Python code snippet"/><div className="sandbox-actions"><button className="primary-button" onClick={handleAnalyzeSnippet} disabled={isAnalyzingSandbox}>{isAnalyzingSandbox ? "Analyzing snippet…" : "Analyze code snippet →"}</button><button className="secondary-button" onClick={() => { setSandboxCode(SAMPLE_BUGGY_CODE); setSandboxAnalysis(null); setSandboxError(""); }}>Load sample</button></div>{sandboxError && <div className="notice error">{sandboxError}</div>}</section><section className="panel sandbox-results"><div className="panel-title"><div><span className="panel-title-icon">✓</span><h2>Snippet findings</h2></div>{sandboxAnalysis && <span className="count-chip">{sandboxAnalysis.findings_count ?? sandboxAnalysis.findings?.length ?? 0}</span>}</div>{!sandboxAnalysis ? <EmptyChart title="Waiting for your snippet" text="Analyze your code to see findings, explanations, and suggested fixes."/> : sandboxAnalysis.findings_count === 0 ? <div className="clean-result"><span>✓</span><strong>Looking good!</strong><p>No issues were reported for this snippet.</p></div> : <div className="findings-list">{(sandboxAnalysis.findings || []).map((finding, index) => <FindingCard key={`${finding.line}-${index}`} finding={finding} index={`sandbox-${index}`} copiedIndex={copiedIndex} onCopy={handleCopyFix}/>)}</div>}</section></div>}
          </>}

          {activeTab === "qa" && <><PageHeading eyebrow="CODE COMPANION" title="Q&A" description="Ask questions about your latest repository scan and get answers grounded in its results."/><section className="panel qa-panel"><div className="qa-welcome"><span className="qa-avatar">✦</span><div><h2>Ask RepoGuide</h2><p>{repoAnalysis ? `I'm ready to help you understand ${repoAnalysis.repository_name || "your latest scan"}.` : "Run a repository analysis first to unlock answers based on your own code findings."}</p></div></div><div className="suggested-questions">{["What is my code health score?", "Which issues are most severe?", "How can I fix the findings?"].map((q) => <button key={q} onClick={() => setQuestion(q)}>{q}<span>↗</span></button>)}</div><div className="qa-conversation">{answers.map((item, index) => <div className="qa-pair" key={`${item.question}-${index}`}><div className="question-bubble">{item.question}</div><div className="answer-bubble">
  <span className="answer-sparkle">✦</span>
  <div className="markdown-answer">
    <ReactMarkdown remarkPlugins={[remarkGfm]}>
      {item.answer}
    </ReactMarkdown>
  </div>
</div>
</div>)}</div><form className="qa-input-row" onSubmit={answerQuestion}><input value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="Ask about bugs, quality, severity, or fixes…"/><button className="primary-button" type="submit">Ask <span>→</span></button></form><small className="qa-disclaimer">Answers use the latest scan data available in this session. This Q&A page does not execute code or modify files.</small></section></>}

{activeTab === "workspace" && <>
  <PageHeading eyebrow="REPOSITORY WORKSPACE" title="Explore your code" description="Browse real repository files, inspect source code, and ask Scout about your code." />
  <div className="workspace-toolbar panel">
    <div><strong>{repoAnalysis?.repository_name || "Repository"}</strong><small>Path: {repoPath || "."}</small></div>
    <button className="secondary-button" type="button" onClick={loadWorkspaceFiles} disabled={workspaceLoading}>{workspaceLoading ? "Refreshing…" : "↻ Refresh files"}</button>
    <button className="primary-button" type="button" onClick={() => setActiveTab("scanner")}>Run repository scan →</button>
  </div>
  {workspaceError && <div className="notice error workspace-notice" role="alert">{workspaceError}</div>}
  <section className="workspace-layout">
    <div className="panel workspace-explorer">
      <div className="workspace-panel-heading"><h2>Explorer</h2><span>{String(workspaceFiles.length).padStart(2, "0")}</span></div>
      <div className="workspace-repo-name"><span>📁</span> {repoAnalysis?.repository_name || "Your repository"}</div>
      {workspaceLoading ? <div className="workspace-state"><span className="spinner"/><p>Loading repository files…</p></div> : workspaceFiles.length ? <WorkspaceTree files={workspaceFiles} selectedPath={selectedWorkspaceFile?.file_path} onSelect={openWorkspaceFile} /> : <div className="workspace-state"><span>📂</span><h3>{workspaceError ? "Explorer unavailable" : "No files to display"}</h3><p>{workspaceError ? "Check the backend response above and refresh." : "The repository inventory is empty. Try a scan or refresh the file list."}</p></div>}
    </div>
    <div className="panel workspace-code">
      <div className="workspace-panel-heading"><h2>Code viewer</h2><span>{selectedWorkspaceFile ? selectedWorkspaceFile.file_path : "02"}</span></div>
      {workspaceFileLoading ? <div className="workspace-state"><span className="spinner"/><p>Opening file…</p></div> : selectedWorkspaceFile ? <pre className="workspace-code-content"><code>{selectedWorkspaceFile.content}</code></pre> : <div className="workspace-state workspace-code-empty"><span>⌘</span><h3>Choose a file to inspect</h3><p>The selected file's actual source code will appear here.</p></div>}
    </div>
    <div className="panel workspace-scout">
      <div className="workspace-panel-heading"><h2><span>✦</span> Scout AI</h2><span className="scout-status">Code companion</span></div>
      <p className="scout-intro">Ask Scout to explain your repository and help interpret your scan results.</p>
      <div className="scout-suggestions">
        {["Explain my repository structure", "What are the most important issues in my scan?", "How can I improve my code health?"].map((q) => <button key={q} type="button" onClick={() => setWorkspaceScoutQuestion(q)}>{q} ↗</button>)}
      </div>
      <div className="workspace-scout-conversation" aria-live="polite">
        {workspaceScoutAnswers.map((item, index) => <div className="workspace-scout-pair" key={`${item.question}-${index}`}><div className="workspace-scout-question">{item.question}</div><div className="workspace-scout-answer">
  <strong>✦ Scout</strong>
  <div className="markdown-answer">
    <ReactMarkdown remarkPlugins={[remarkGfm]}>
      {item.answer}
    </ReactMarkdown>
  </div>
</div>
</div>)}
      </div>
      <form className="workspace-scout-form" onSubmit={askScoutInWorkspace}><input value={workspaceScoutQuestion} onChange={(event) => setWorkspaceScoutQuestion(event.target.value)} placeholder="Ask Scout about this repository…" aria-label="Ask Scout"/><button className="primary-button" type="submit" disabled={workspaceScoutLoading || !workspaceScoutQuestion.trim()}>{workspaceScoutLoading ? "Thinking…" : "Ask Scout →"}</button></form>
      <small>Scout uses your existing authenticated repository Q&amp;A endpoint. It does not modify files.</small>
    </div>
  </section>
</>}


          {activeTab === "map" && <><PageHeading eyebrow="CODEBASE EXPLORER" title="Interactive Code Map" description="A constellation-style view of folders, modules, and relationships in your workspace."/><section className="cosmic-map-panel">
<div className="map-topline">
  <div>
    <span className="map-live-dot" />
    <span>{repoAnalysis ? "Latest scan connected" : "Exploration preview"}</span>
  </div>

  <div className="map-topline-actions">
    <span className="map-hint">
      Click a folder to explore • Click a file to inspect
    </span>
    <button
      type="button"
      className="map-expand-button"
      onClick={() => {
        const mapPanel = document.querySelector(".cosmic-map-panel");
        if (mapPanel?.requestFullscreen) {
          mapPanel.requestFullscreen();
        }
      }}
    >
      ⛶ Expand Map
    </button>
  </div>
</div>
<div className="cosmic-canvas"><div className="nebula nebula-one"/><div className="nebula nebula-two"/>{Array.from({length: 58}, (_, i) => <span key={i} className={`star star-${i % 4}`} style={{left: `${(i * 37 + 9) % 97}%`, top: `${(i * 53 + 7) % 92}%`, animationDelay: `${(i % 9) * -0.4}s`}}/>)}<svg className="map-lines" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
  {mapNodes
    .filter((node) => node.id !== "root" && node.id !== "back")
    .map((node) => (
      <line
        key={node.id}
        x1="50"
        y1="12"
        x2={node.x}
        y2={node.y}
      />
    ))}
</svg>{mapNodes.map((node) => <button key={node.id} className={`map-node node-${node.kind} ${selectedMapNode?.id === node.id ? "selected" : ""}`} style={{left: `${node.x}%`, top: `${node.y}%`}} onClick={() => {
  if (node.id === "root") {
    setMapFolderPath("");
    setSelectedMapNode(null);
  } else if (node.id === "back") {
    setMapFolderPath(node.path);
    setSelectedMapNode(null);
  } else if (node.kind === "folder") {
    setMapFolderPath(node.path);
    setSelectedMapNode(null);
  } else {
    setSelectedMapNode(node);
  }
}}><span className="node-orb">{node.kind === "root" ? "◇" : node.kind === "folder" ? "▱" : node.kind === "issue" ? "!" : "‹›"}</span><span className="node-label">{node.label}</span></button>)}</div><div className="map-legend"><span><i className="legend-root"/> Repository</span><span><i className="legend-folder"/> Folder</span><span><i className="legend-file"/> File / module</span><span><i className="legend-issue"/> Findings</span></div>{selectedMapNode && <div className="node-inspector"><div><span className="eyebrow">SELECTED NODE</span><h3>{selectedMapNode.label}</h3><p>{selectedMapNode.detail}</p></div><button className="icon-button" onClick={() => setSelectedMapNode(null)} aria-label="Close node details">×</button></div>}<p className="map-footnote">This view shows the actual discovered folder/file hierarchy. Lines indicate parent-folder membership, not verified imports or runtime dependencies.</p></section></>}

          {activeTab === "repositories" && <><PageHeading eyebrow="YOUR PROJECTS" title="Repositories" description="Manage the repository path you want RepoGuide to inspect."/><section className="panel repository-card"><div className="repository-icon">▱</div><div className="repository-details"><h2>{repoAnalysis?.repository_name || "Workspace repository"}</h2><p className="muted">{repoPath || "."}</p><div className="repository-meta"><span className="status-pill">{repoAnalysis ? "Analyzed" : "Ready to analyze"}</span>{repoAnalysis && <span>{repoAnalysis.total_python_files ?? 0} Python files · {repoAnalysis.total_findings ?? findings.length} findings</span>}</div></div><button className="primary-button" onClick={() => setActiveTab("scanner")}>{repoAnalysis ? "Scan again" : "Analyze repository"} <span>→</span></button></section><section className="panel path-panel"><h3>Analyze another directory</h3><p>Enter a path inside the backend project's permitted root directory.</p><form className="scan-input-row" onSubmit={handleAnalyzeRepository}><input aria-label="Repository path" value={repoPath} onChange={(e) => setRepoPath(e.target.value)} placeholder="Relative repository path"/><button className="primary-button" disabled={isAnalyzingRepo}>{isAnalyzingRepo ? "Analyzing…" : "Run scan"}</button></form>{repoError && <div className="notice error">{repoError}</div>}</section></>}

          {activeTab === "reports" && <><PageHeading eyebrow="REPORT LIBRARY" title="Reports" description="Download the latest repository analysis report and revisit key scan metrics."/><section className="panel report-card"><div className="report-file-icon">▤</div><div className="report-details"><h2>{repoAnalysis?.report_markdown ? `BUG_REPORT_${repoAnalysis.repository_name || "RepoGuide"}.md` : "No report generated yet"}</h2><p>{repoAnalysis?.report_markdown ? "Markdown report · Generated from your latest repository scan" : "Run an analysis to generate a downloadable Markdown report."}</p>{repoAnalysis && <div className="report-tags"><span>Health: {repoAnalysis.health_score ?? "—"}/100</span><span>Findings: {repoAnalysis.total_findings ?? findings.length}</span></div>}</div><button className="primary-button" disabled={!repoAnalysis?.report_markdown} onClick={handleDownloadReport}>↓ Download report</button></section><div className="report-tip"><span>✦</span><p><strong>Tip:</strong> Reports include detected issues, evidence, explanations, and proposed fixes when the analyzer provides them.</p></div></>}

          {activeTab === "settings" && <><PageHeading eyebrow="PERSONALIZE WORKSPACE" title="Settings" description="Choose the appearance that feels right. Your preferences are saved in this browser."/><section className="panel settings-panel"><div className="settings-section"><div><h2>Appearance</h2><p>Switch between light and dark workspace themes.</p></div><div className="theme-options"><button className={`theme-option light-preview ${theme === "light" ? "selected" : ""}`} onClick={() => setTheme("light")}><span className="theme-preview light-mini"><i/><i/><i/></span><strong>Light mode</strong>{theme === "light" && <span className="selected-check">✓</span>}</button><button className={`theme-option dark-preview ${theme === "dark" ? "selected" : ""}`} onClick={() => setTheme("dark")}><span className="theme-preview dark-mini"><i/><i/><i/></span><strong>Dark mode</strong>{theme === "dark" && <span className="selected-check">✓</span>}</button></div></div><div className="settings-divider"/><div className="settings-section"><div><h2>Colour palette</h2><p>Pick an accent colour for highlights, buttons, and active navigation.</p></div><div className="palette-options"><PaletteButton id="blue" label="Developer Blue" colors={["#2F81F7", "#58A6FF"]} palette={palette} onSelect={setPalette}/><PaletteButton id="ocean" label="Ocean Teal" colors={["#159DAB", "#39C5BB"]} palette={palette} onSelect={setPalette}/><PaletteButton id="mint" label="Mint Green" colors={["#239B67", "#4DD69A"]} palette={palette} onSelect={setPalette}/><PaletteButton id="orange" label="Amber Orange" colors={["#D97706", "#FBBF24"]} palette={palette} onSelect={setPalette}/></div></div><div className="settings-divider"/><div className="settings-section account-settings"><div><h2>Account & session</h2><p>Your current authenticated session details.</p></div><div className="settings-account-card"><span className="avatar">{displayName.trim().charAt(0).toUpperCase()}</span><div><strong>{displayName}</strong><small>{user.email || email || "Email is not included in the session response"}</small><small>Role: {user.role || "Developer"}</small></div><button className="secondary-button" onClick={handleSignOut}>Sign out</button></div></div></section></>}

          <footer className="page-footer"><span>© 2026 RepoGuide · Automated Code Quality & Onboarding</span><span>Built for developers who ship smarter.</span></footer>
        </div>
      </section>
    </main>
  );
}

function WorkspaceTree({ files, selectedPath, onSelect }) {
  const tree = useMemo(() => {
    const root = { name: "", path: "", children: {}, file: false };
    for (const rawPath of files) {
      const parts = rawPath.replace(/\\/g, "/").split("/").filter(Boolean);
      let node = root;
      parts.forEach((part, index) => {
        if (!node.children[part]) node.children[part] = { name: part, path: parts.slice(0, index + 1).join("/"), children: {}, file: index === parts.length - 1 };
        node = node.children[part];
        if (index === parts.length - 1) node.file = true;
      });
    }
    return root;
  }, [files]);
  function renderNodes(node, depth = 0) {
    return Object.values(node.children).sort((a, b) => Number(a.file) - Number(b.file) || a.name.localeCompare(b.name)).map((item) => <TreeItem key={item.path} item={item} depth={depth} selectedPath={selectedPath} onSelect={onSelect} renderNodes={renderNodes} />);
  }
  return <div className="workspace-tree">{renderNodes(tree)}</div>;
}

function TreeItem({ item, depth, selectedPath, onSelect, renderNodes }) {
  const [expanded, setExpanded] = useState(depth < 1);
  const hasChildren = Object.keys(item.children).length > 0;
  if (!item.file || hasChildren) return <div className="workspace-tree-folder"><button className="workspace-tree-row folder-row" style={{ paddingLeft: `${12 + depth * 15}px` }} onClick={() => setExpanded((value) => !value)} aria-expanded={expanded}><span>{expanded ? "▾" : "▸"}</span><span>📁</span><span>{item.name}</span></button>{expanded && <div>{renderNodes(item, depth + 1)}</div>}</div>;
  return <button className={`workspace-tree-row file-row ${selectedPath === item.path ? "selected" : ""}`} style={{ paddingLeft: `${28 + depth * 15}px` }} onClick={() => onSelect(item.path)} title={item.path}><span className="tree-file-icon">{item.name.split(".").pop()?.toLowerCase() === "py" ? "🐍" : "📄"}</span><span>{item.name}</span></button>;
}

function HealthTrend({ history }) {
  const points = history.filter((item) => item.health_score !== null && item.health_score !== undefined && item.health_score !== "" && Number.isFinite(Number(item.health_score))).slice(-12);
  if (!points.length) return <EmptyChart title="Health scores are not available" text="The saved scans do not contain numeric health scores yet. New scans will appear when the analyzer returns them." />;
  const width = 760, height = 210, left = 38, right = 18, top = 18, bottom = 34;
  const x = (index) => points.length === 1 ? width / 2 : left + index * (width - left - right) / (points.length - 1);
  const y = (score) => top + (100 - Math.max(0, Math.min(100, Number(score)))) * (height - top - bottom) / 100; 
  const polyline = points.map((item, index) => `${x(index)},${y(item.health_score)}`).join(" ");
  return <div className="health-trend-chart"><svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Repository health score across saved scans" preserveAspectRatio="xMidYMid meet"><line x1={left} y1={y(100)} x2={width-right} y2={y(100)} className="trend-gridline"/><line x1={left} y1={y(50)} x2={width-right} y2={y(50)} className="trend-gridline"/><line x1={left} y1={y(0)} x2={width-right} y2={y(0)} className="trend-gridline"/><text x="4" y={y(100)+4} className="trend-axis-label">100</text><text x="12" y={y(50)+4} className="trend-axis-label">50</text><text x="20" y={y(0)+4} className="trend-axis-label">0</text><polyline points={polyline} className="trend-line"/>{points.map((item,index)=><g key={`${item.scanned_at}-${index}`}><circle cx={x(index)} cy={y(item.health_score)} r="4.5" className="trend-point"><title>{`${item.repository_name}: ${item.health_score}/100`}</title></circle><text x={x(index)} y={height-10} textAnchor="middle" className="trend-axis-label">{item.scanned_at ? new Date(item.scanned_at).toLocaleDateString(undefined,{month:"short",day:"numeric"}) : `Scan ${index+1}`}</text></g>)}</svg><div className="trend-summary"><span>{points.length} real scan{points.length===1?"":"s"} shown</span><strong>Latest: {points[points.length-1].health_score}/100</strong></div></div>;
}

function StatCard({ icon, tone, title, value, detail }) { return <section className="stat-card"><span className={`stat-icon tone-${tone}`}>{icon}</span><div className="stat-copy"><span className="stat-title">{title}</span><strong className="stat-value">{value}</strong><span className="stat-detail">{detail}</span></div></section>; }
function PanelTitle({ icon, title, action, onAction }) { return <div className="panel-title"><div><span className="panel-title-icon">{icon}</span><h2>{title}</h2></div>{action && <button className="text-action" onClick={onAction}>{action} <span>→</span></button>}</div>; }
function HorizontalBar({ label, value, max, tone }) { const percent = Math.max(0, Math.min(100, (Number(value) / max) * 100)); return <div className="bar-row"><span className="bar-label" title={label}>{label}</span><div className="bar-track"><span className={`bar-fill bar-${tone}`} style={{ width: `${percent}%` }}/></div><strong className="bar-value">{value}</strong></div>; }
function EmptyChart({ title, text }) { return <div className="empty-chart"><span className="empty-chart-icon">▥</span><strong>{title}</strong><p>{text}</p></div>; }
function QuickAction({ icon, title, text, onClick }) { return <button className="quick-action" onClick={onClick}><span className="quick-icon">{icon}</span><span><strong>{title}</strong><small>{text}</small></span><span className="quick-arrow">↗</span></button>; }
function PageHeading({ eyebrow, title, description }) { return <div className="page-heading"><span className="eyebrow">{eyebrow}</span><h1>{title}</h1><p>{description}</p></div>; }
function PaletteButton({ id, label, colors, palette, onSelect }) { return <button className={`palette-option ${palette === id ? "selected" : ""}`} onClick={() => onSelect(id)}><span className="palette-swatches">{colors.map((color) => <i key={color} style={{ background: color }}/>)}</span><strong>{label}</strong>{palette === id && <span className="selected-check">✓</span>}</button>; }
function FindingCard({ finding, index, copiedIndex, onCopy }) { const sev = String(finding.severity || "low").toLowerCase(); return <article className={`finding-card severity-${sev}`}><div className="finding-heading"><span className={`severity-badge sev-${sev}`}>{finding.severity}</span><span className="category-chip">{finding.category || "Code quality"}</span><span className="finding-potential">{finding.is_potential ? "Heuristic pattern" : "Detected issue"}</span></div><h3>{finding.title}</h3><p className="finding-location">⌁ {finding.file || "Unknown file"} · Line {finding.line ?? "—"}{finding.column != null ? `, column ${finding.column}` : ""}</p>{finding.evidence && <div className="evidence-block"><span>OFFENDING CODE</span><pre><code>{finding.evidence}</code></pre></div>}<div className="finding-explanation"><strong>Why it matters</strong><p>{finding.explanation}</p></div>{finding.ai_explanation && <div className="ai-explanation"><strong>✦ AI explanation</strong><p>{finding.ai_explanation}</p></div>}{finding.proposed_fix && <div className="fix-block"><div><strong>Suggested fix</strong><button className="copy-button" onClick={() => onCopy(finding.proposed_fix, `finding-${index}`)}>{copiedIndex === `finding-${index}` ? "✓ Copied" : "Copy fix"}</button></div><pre><code>{finding.proposed_fix}</code></pre></div>}</article>; }

export default App;
