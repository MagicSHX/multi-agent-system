import { useState, useEffect, useRef } from "react";
import {
  LayoutDashboard, Users, Plus, Star, Search, Wand2, Sparkles,
  Check, ChevronRight, X, ArrowLeft, Hexagon, Rocket, Trash2,
} from "lucide-react";

/* ------------------------------------------------------------------ *
 * Agent Studio — hackathon POC frontend (pure mock, no backend).
 * All state is in memory. The ONE place that talks to a backend later
 * is handleLaunch() — see the TODO seam marked below.
 * ------------------------------------------------------------------ */

// --- palette for agent avatars / category pills --------------------
const PALETTE = {
  purple: { bg: "#CECBF6", fg: "#26215C", soft: "#EEEDFE", line: "#534AB7" },
  teal:   { bg: "#9FE1CB", fg: "#04342C", soft: "#E1F5EE", line: "#0F6E56" },
  coral:  { bg: "#F5C4B3", fg: "#4A1B0C", soft: "#FAECE7", line: "#993C1D" },
  blue:   { bg: "#B5D4F4", fg: "#042C53", soft: "#E6F1FB", line: "#185FA5" },
  amber:  { bg: "#FAC775", fg: "#412402", soft: "#FAEEDA", line: "#854F0B" },
  pink:   { bg: "#F4C0D1", fg: "#4B1528", soft: "#FBEAF0", line: "#993556" },
};

const initials = (name) =>
  name.split(/\s+/).slice(0, 2).map((w) => w[0]).join("").replace(/[^A-Za-z]/g, "").slice(0, 2) ||
  name.slice(0, 2);

// --- seed data -----------------------------------------------------
const SEED_AGENTS = [
  { id: "a1", name: "Researcher", color: "purple", category: "Research", blurb: "Gathers sources and synthesises findings into briefs.", simple: "You research topics and pull together sources.", rating: 4.8, ratingCount: 32, used: 6, owned: true },
  { id: "a2", name: "Writer", color: "coral", category: "Content", blurb: "Turns outlines and notes into polished copy.", simple: "You write clear, engaging copy from notes.", rating: 4.6, ratingCount: 21, used: 9, owned: true },
  { id: "a3", name: "Analyst", color: "teal", category: "Data", blurb: "Crunches numbers and flags patterns in data.", simple: "You analyse data and surface key patterns.", rating: 4.5, ratingCount: 18, used: 4, owned: true },
  { id: "a4", name: "Editor", color: "blue", category: "Content", blurb: "Tightens drafts and enforces a consistent voice.", simple: "You edit drafts for clarity and consistency.", rating: 4.4, ratingCount: 12, used: 3, owned: true },
  { id: "a5", name: "Strategist", color: "amber", category: "Strategy", blurb: "Frames the problem and shapes the plan of attack.", simple: "You turn goals into a clear strategy.", rating: 4.7, ratingCount: 41, used: 0, owned: false },
  { id: "a6", name: "Fact Checker", color: "pink", category: "Research", blurb: "Verifies claims and catches unsupported statements.", simple: "You verify claims against reliable sources.", rating: 4.9, ratingCount: 27, used: 0, owned: false },
  { id: "a7", name: "Designer", color: "purple", category: "Design", blurb: "Proposes layouts, components, and visual direction.", simple: "You suggest clean, usable visual designs.", rating: 4.3, ratingCount: 15, used: 0, owned: false },
  { id: "a8", name: "Summarizer", color: "teal", category: "Content", blurb: "Compresses long material into tight takeaways.", simple: "You summarise long content into key points.", rating: 4.6, ratingCount: 9, used: 0, owned: false },
];

const SEED_PROJECTS = [
  { id: "p1", name: "Market research report", description: "Compile a report on the competitive landscape for our new product line.", status: "completed", agentIds: ["a1", "a3", "a2"], created: "2 days ago", ratingGiven: false },
  { id: "p2", name: "Landing page copy", description: "Draft and refine hero + feature copy for the launch page.", status: "active", agentIds: ["a2", "a4"], created: "running now", ratingGiven: false },
  { id: "p3", name: "Competitor teardown", description: "Break down three competitors' positioning and pricing.", status: "completed", agentIds: ["a1", "a4"], created: "1 week ago", ratingGiven: true },
];

// --- the "prompt magic": expand a one-liner into a full system prompt
function buildFullPrompt(name, desc) {
  const role = (name || "Assistant").trim();
  const d = desc.trim().replace(/\.+$/, "");
  const lead = d ? d.charAt(0).toLowerCase() + d.slice(1) : "helps the team complete its work";
  return `# Role
You are ${role}, an expert who ${lead}.

# Responsibilities
- Own tasks in your domain and see them through end to end.
- Collaborate with other agents, sharing context and handing off cleanly.
- Surface risks, gaps, and assumptions early instead of guessing silently.

# Constraints
- Stay within your expertise; defer to the right teammate when out of scope.
- Be concise and specific — cite concrete details over generalities.
- Never fabricate facts or sources.

# Output format
Structured, skimmable output with clear headers and the key takeaway first.

# Tone
Professional, direct, and collaborative.`;
}

// =================================================================== //
export default function AgentStudio() {
  const [view, setView] = useState("dashboard");
  const [agents, setAgents] = useState(SEED_AGENTS);
  const [projects, setProjects] = useState(SEED_PROJECTS);
  const [toast, setToast] = useState(null);
  const [rating, setRating] = useState(null); // project being rated

  const showToast = (msg) => {
    setToast(msg);
    setTimeout(() => setToast(null), 2600);
  };

  return (
    <div className="as-root">
      <style>{css}</style>

      <div className="as-shell">
        <Sidebar view={view} setView={setView} onBuild={() => setView("build")} />

        <main className="as-main">
          {view === "dashboard" && (
            <Dashboard
              agents={agents}
              projects={projects}
              onBuild={() => setView("build")}
              onSeeAgents={() => setView("agents")}
              onRate={(p) => setRating(p)}
            />
          )}
          {view === "agents" && (
            <AgentLibrary
              agents={agents}
              onCreate={() => setView("create-agent")}
            />
          )}
          {view === "create-agent" && (
            <CreateAgentPage
              onCancel={() => setView("agents")}
              onAdd={(agent) => {
                setAgents((prev) => [agent, ...prev]);
                setView("agents");
                showToast(`“${agent.name}” added to your agents.`);
              }}
            />
          )}
          {view === "build" && (
            <BuildProject
              agents={agents}
              setAgents={setAgents}
              onCancel={() => setView("dashboard")}
              onLaunch={(project) => {
                setProjects((p) => [project, ...p]);
                setView("dashboard");
                showToast(`“${project.name}” launched — agents are on it.`);
              }}
            />
          )}
        </main>
      </div>

      {rating && (
        <RateModal
          project={rating}
          agents={agents}
          onClose={() => setRating(null)}
          onSubmit={(scores) => {
            setAgents((prev) =>
              prev.map((a) => {
                const s = scores[a.id];
                if (!s) return a;
                const total = a.rating * a.ratingCount + s;
                const count = a.ratingCount + 1;
                return { ...a, rating: Math.round((total / count) * 10) / 10, ratingCount: count };
              })
            );
            setProjects((prev) => prev.map((p) => (p.id === rating.id ? { ...p, ratingGiven: true } : p)));
            setRating(null);
            showToast("Thanks — agent ratings updated.");
          }}
        />
      )}

      {toast && <div className="as-toast"><Check size={16} /> {toast}</div>}
    </div>
  );
}

// --- sidebar -------------------------------------------------------
function Sidebar({ view, setView, onBuild }) {
  const Item = ({ id, icon: Icon, label }) => (
    <button className={`as-nav ${view === id ? "is-active" : ""}`} onClick={() => setView(id)}>
      <Icon size={18} /> {label}
    </button>
  );
  return (
    <aside className="as-side">
      <div className="as-brand">
        <span className="as-logo"><Hexagon size={16} /></span>
        Agent Studio
      </div>
      <nav className="as-navgroup">
        <Item id="dashboard" icon={LayoutDashboard} label="Dashboard" />
        <Item id="agents" icon={Users} label="Agents" />
      </nav>
      <button className="as-build" onClick={onBuild}><Plus size={18} /> Build project</button>
    </aside>
  );
}

// --- shared bits ---------------------------------------------------
function Avatar({ name, color, size = 32 }) {
  const p = PALETTE[color] || PALETTE.purple;
  return (
    <span
      style={{
        width: size, height: size, borderRadius: "50%", background: p.bg, color: p.fg,
        fontSize: size * 0.36, fontWeight: 500, display: "inline-flex",
        alignItems: "center", justifyContent: "center", flexShrink: 0,
      }}
    >
      {initials(name)}
    </span>
  );
}

function AvatarStack({ ids, agents }) {
  return (
    <span style={{ display: "inline-flex" }}>
      {ids.map((id, i) => {
        const a = agents.find((x) => x.id === id);
        if (!a) return null;
        const p = PALETTE[a.color];
        return (
          <span key={id} title={a.name}
            style={{
              width: 26, height: 26, borderRadius: "50%", background: p.bg, color: p.fg,
              fontSize: 11, fontWeight: 500, display: "inline-flex", alignItems: "center",
              justifyContent: "center", border: "2px solid #fff", marginLeft: i ? -8 : 0,
            }}>
            {initials(a.name)}
          </span>
        );
      })}
    </span>
  );
}

const STATUS = {
  completed: { label: "Completed", bg: "#E1F5EE", fg: "#0F6E56" },
  active: { label: "Active", bg: "#E6F1FB", fg: "#185FA5" },
  draft: { label: "Draft", bg: "#F1EFE8", fg: "#5F5E5A" },
};
function StatusChip({ status }) {
  const s = STATUS[status] || STATUS.draft;
  return <span className="as-chip" style={{ background: s.bg, color: s.fg }}>{s.label}</span>;
}

function RatingLine({ value, count }) {
  return (
    <span className="as-rating">
      <Star size={13} fill="#BA7517" color="#BA7517" /> {value.toFixed(1)}
      {count != null && <span className="as-muted"> ({count})</span>}
    </span>
  );
}

// --- dashboard -----------------------------------------------------
function Dashboard({ agents, projects, onBuild, onSeeAgents, onRate }) {
  const trained = agents.filter((a) => a.owned);
  const stats = [
    { label: "Projects", value: projects.length },
    { label: "Agents trained", value: trained.length },
    { label: "Avg rating", value: (trained.reduce((s, a) => s + a.rating, 0) / trained.length).toFixed(1) },
  ];

  const active = projects.filter((p) => p.status === "active");
  const toRate = projects.filter((p) => p.status === "completed" && !p.ratingGiven);
  const past = projects.filter((p) => !active.includes(p) && !toRate.includes(p));

  const renderProject = (p) => (
    <div className="as-rowcard" key={p.id}>
      <div className="as-row-left">
        <p className="as-row-title">{p.name}</p>
        <p className="as-muted as-sm">{p.agentIds.length} agents · {p.created}</p>
      </div>
      <div className="as-row-right">
        <AvatarStack ids={p.agentIds} agents={agents} />
        {p.status === "completed" && !p.ratingGiven ? (
          <button className="as-rate-btn" onClick={() => onRate(p)}><Star size={18} /> Rate</button>
        ) : (
          <StatusChip status={p.status} />
        )}
      </div>
    </div>
  );

  return (
    <div className="as-page">
      <p className="as-eyebrow">Welcome back</p>
      <h1 className="as-h1">Your workspace</h1>

      <div className="as-stats">
        {stats.map((s) => (
          <div className="as-stat" key={s.label}>
            <p className="as-stat-label">{s.label}</p>
            <p className="as-stat-value">{s.value}</p>
          </div>
        ))}
      </div>

      {active.length > 0 && (
        <>
          <div className="as-section-head">
            <h2 className="as-h2">Active</h2>
          </div>
          <div className="as-list">{active.map(renderProject)}</div>
        </>
      )}

      {toRate.length > 0 && (
        <>
          <div className="as-section-head">
            <h2 className="as-h2">To Rate</h2>
          </div>
          <div className="as-list">{toRate.map(renderProject)}</div>
        </>
      )}

      <div className="as-section-head">
        <h2 className="as-h2">Past projects</h2>
      </div>
      <div className="as-list">
        {past.length > 0
          ? past.map(renderProject)
          : <div className="as-empty">No past projects yet.</div>}
      </div>

      <div className="as-section-head">
        <h2 className="as-h2">Your agents</h2>
        <button className="as-link" onClick={onSeeAgents}>View all</button>
      </div>
      <div className="as-grid2">
        {trained.map((a) => (
          <div className="as-miniagent" key={a.id}>
            <Avatar name={a.name} color={a.color} />
            <div>
              <p className="as-row-title">{a.name}</p>
              <p className="as-muted as-sm"><RatingLine value={a.rating} /> · used {a.used}×</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// --- agent library -------------------------------------------------
function AgentLibrary({ agents, onCreate }) {
  const [tab, setTab] = useState("yours");
  const [q, setQ] = useState("");
  const filtered = agents
    .filter((a) => (tab === "yours" ? a.owned : !a.owned))
    .filter((a) => (a.name + a.category + a.blurb).toLowerCase().includes(q.toLowerCase()));

  return (
    <div className="as-page">
      <div className="as-section-head" style={{ marginTop: 0 }}>
        <h1 className="as-h1" style={{ margin: 0 }}>Agents</h1>
        <button className="as-primary" onClick={onCreate}><Plus size={16} /> Create agent</button>
      </div>

      <div className="as-toolbar">
        <div className="as-search">
          <Search size={16} />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search agents" />
        </div>
        <div className="as-toggle">
          <button className={tab === "yours" ? "is-on" : ""} onClick={() => setTab("yours")}>Yours</button>
          <button className={tab === "shared" ? "is-on" : ""} onClick={() => setTab("shared")}>Shared</button>
        </div>
      </div>

      {filtered.length === 0 ? (
        <div className="as-empty">No agents match “{q}”. Try another search, or create one.</div>
      ) : (
        <div className="as-gridcards">
          {filtered.map((a) => {
            const p = PALETTE[a.color];
            return (
              <div className="as-agentcard" key={a.id}>
                <div className="as-agentcard-head">
                  <Avatar name={a.name} color={a.color} size={36} />
                  <div style={{ minWidth: 0 }}>
                    <p className="as-row-title">{a.name}</p>
                    <span className="as-pill" style={{ background: p.soft, color: p.line }}>{a.category}</span>
                  </div>
                </div>
                <p className="as-blurb">{a.blurb}</p>
                <div className="as-agentcard-foot">
                  <RatingLine value={a.rating} count={a.ratingCount} />
                  <span className="as-muted as-sm">{a.owned ? `used ${a.used}×` : "shared"}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// --- build project wizard -----------------------------------------
function BuildProject({ agents, setAgents, onCancel, onLaunch }) {
  const [step, setStep] = useState(1);
  const [name, setName] = useState("");
  const [desc, setDesc] = useState("");
  const [teamIds, setTeamIds] = useState([]);
  const [mode, setMode] = useState(null); // 'library' | 'create' | null

  const team = teamIds.map((id) => agents.find((a) => a.id === id)).filter(Boolean);
  const toggle = (id) => setTeamIds((t) => (t.includes(id) ? t.filter((x) => x !== id) : [...t, id]));

  const addNewAgent = (agent) => {
    setAgents((prev) => [agent, ...prev]);
    setTeamIds((t) => [...t, agent.id]);
    setMode(null);
  };

  const handleLaunch = () => {
    // ===== BACKEND SEAM ============================================
    // TODO(backend): replace this local mock with the real call:
    //   POST /api/projects { name, description, agentIds }
    // and route to the returned project workspace on success.
    // ===============================================================
    const project = {
      id: "p" + Date.now(),
      name: name.trim() || "Untitled project",
      description: desc.trim(),
      status: "active",
      agentIds: teamIds,
      created: "just now",
      ratingGiven: false,
    };
    onLaunch(project);
  };

  const steps = ["Describe", "Assemble team", "Launch"];

  return (
    <div className="as-page">
      <button className="as-back" onClick={onCancel}><ArrowLeft size={16} /> Cancel</button>

      <div className="as-stepper">
        {steps.map((label, i) => {
          const n = i + 1;
          const done = step > n, current = step === n;
          return (
            <div className="as-step-wrap" key={label}>
              <span className={`as-step ${current ? "is-current" : ""} ${done ? "is-done" : ""}`}>
                <span className="as-step-dot">{done ? <Check size={12} /> : n}</span>
                {label}
              </span>
              {i < steps.length - 1 && <ChevronRight size={14} className="as-step-sep" />}
            </div>
          );
        })}
      </div>

      {/* STEP 1 -------------------------------------------------- */}
      {step === 1 && (
        <div className="as-card-pad">
          <h2 className="as-h2" style={{ marginTop: 0 }}>Describe your project</h2>
          <label className="as-label">Project name</label>
          <input className="as-input" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Q3 market research report" />
          <label className="as-label">What needs to get done?</label>
          <textarea className="as-textarea" rows={5} value={desc} onChange={(e) => setDesc(e.target.value)}
            placeholder="Describe the goal and any context the agents should know…" />
          <div className="as-foot">
            <span />
            <button className="as-primary" disabled={!name.trim()} onClick={() => setStep(2)}>Continue</button>
          </div>
        </div>
      )}

      {/* STEP 2 -------------------------------------------------- */}
      {step === 2 && (
        <div className="as-card-pad">
          <div className="as-section-head" style={{ marginTop: 0 }}>
            <h2 className="as-h2" style={{ margin: 0 }}>Assemble your team</h2>
            <span className="as-muted as-sm">{team.length} agent{team.length === 1 ? "" : "s"} added</span>
          </div>

          {team.length > 0 && (
            <div className="as-team">
              {team.map((a) => (
                <span className="as-teamchip" key={a.id}>
                  <Avatar name={a.name} color={a.color} size={22} /> {a.name}
                  <button className="as-x" onClick={() => toggle(a.id)} aria-label={`Remove ${a.name}`}><X size={13} /></button>
                </span>
              ))}
            </div>
          )}

          {mode === null && (
            <div className="as-choices">
              <button className="as-choice" onClick={() => setMode("library")}>
                <Users size={18} /> <span>Add from library</span>
                <span className="as-muted as-sm">Reuse a proven agent</span>
              </button>
              <button className="as-choice" onClick={() => setMode("create")}>
                <Wand2 size={18} /> <span>Create new agent</span>
                <span className="as-muted as-sm">Write one line, we build the rest</span>
              </button>
            </div>
          )}

          {mode === "library" && (
            <LibraryPicker agents={agents} teamIds={teamIds} toggle={toggle} onDone={() => setMode(null)} />
          )}

          {mode === "create" && <CreateAgent onAdd={addNewAgent} onCancel={() => setMode(null)} />}

          <div className="as-foot">
            <button className="as-ghost" onClick={() => setStep(1)}>Back</button>
            <button className="as-primary" disabled={team.length === 0} onClick={() => setStep(3)}>Continue</button>
          </div>
        </div>
      )}

      {/* STEP 3 -------------------------------------------------- */}
      {step === 3 && (
        <div className="as-card-pad">
          <h2 className="as-h2" style={{ marginTop: 0 }}>Review &amp; launch</h2>
          <div className="as-review">
            <p className="as-label">Project</p>
            <p className="as-row-title">{name || "Untitled project"}</p>
            {desc && <p className="as-blurb" style={{ marginTop: 4 }}>{desc}</p>}
          </div>
          <div className="as-review">
            <p className="as-label">Team · {team.length} agents</p>
            <div className="as-team" style={{ marginBottom: 0 }}>
              {team.map((a) => (
                <span className="as-teamchip" key={a.id}><Avatar name={a.name} color={a.color} size={22} /> {a.name}</span>
              ))}
            </div>
          </div>
          <p className="as-note"><Sparkles size={14} /> Launching creates the project and puts your agents to work. Collaboration happens in Slack.</p>
          <div className="as-foot">
            <button className="as-ghost" onClick={() => setStep(2)}>Back</button>
            <button className="as-launch" onClick={handleLaunch}><Rocket size={16} /> Launch project</button>
          </div>
        </div>
      )}
    </div>
  );
}

function LibraryPicker({ agents, teamIds, toggle, onDone }) {
  return (
    <div className="as-picker">
      {agents.map((a) => {
        const on = teamIds.includes(a.id);
        return (
          <button key={a.id} className={`as-pickrow ${on ? "is-on" : ""}`} onClick={() => toggle(a.id)}>
            <Avatar name={a.name} color={a.color} size={30} />
            <div className="as-pickrow-text">
              <p className="as-row-title">{a.name}</p>
              <p className="as-muted as-sm">{a.category} · <RatingLine value={a.rating} /></p>
            </div>
            <span className={`as-check ${on ? "is-on" : ""}`}>{on && <Check size={13} />}</span>
          </button>
        );
      })}
      <button className="as-ghost as-pickdone" onClick={onDone}>Done adding</button>
    </div>
  );
}

function CreateAgent({ onAdd, onCancel, addLabel = "Add agent to team" }) {
  const [name, setName] = useState("");
  const [simple, setSimple] = useState("");
  const [phase, setPhase] = useState("input"); // input | generating | done
  const [full, setFull] = useState("");
  const timer = useRef(null);

  useEffect(() => () => clearTimeout(timer.current), []);

  const generate = () => {
    setPhase("generating");
    timer.current = setTimeout(() => {
      setFull(buildFullPrompt(name, simple));
      setPhase("done");
    }, 950);
  };

  const colorKeys = Object.keys(PALETTE);
  const save = () => {
    const color = colorKeys[Math.floor(Math.random() * colorKeys.length)];
    onAdd({
      id: "a" + Date.now(), name: name.trim() || "New agent", color,
      category: "Custom", blurb: simple.trim(), simple: simple.trim(),
      rating: 0, ratingCount: 0, used: 0, owned: true,
    });
  };

  return (
    <>
      <div className="as-create">
        <div className="as-create-left">
          <label className="as-label">Agent name</label>
          <input className="as-input" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. QA Reviewer" />
          <label className="as-label">Describe what it does (one line)</label>
          <textarea className="as-textarea" rows={4} value={simple} onChange={(e) => setSimple(e.target.value)}
            placeholder="You review code for bugs and suggest fixes." />
          <button className="as-magic" disabled={!name.trim() || !simple.trim() || phase === "generating"} onClick={generate}>
            <Wand2 size={16} /> {phase === "generating" ? "Generating…" : phase === "done" ? "Regenerate" : "Generate full prompt"}
          </button>
          <button className="as-ghost as-tiny" onClick={onCancel}>Cancel</button>
        </div>

        <div className="as-create-right">
          <div className="as-gen-head"><Sparkles size={14} /> Generated system prompt</div>
          {phase === "input" && <div className="as-gen-empty">Write a one-line description, then generate.<br />We expand it into a full structured prompt.</div>}
          {phase === "generating" && (
            <div className="as-gen-empty"><span className="as-spinner" /> Expanding your prompt…</div>
          )}
          {phase === "done" && <pre className="as-gen-out">{full}</pre>}
        </div>
      </div>

      {phase === "done" && (
        <div className="as-foot">
          <span />
          <button className="as-primary" onClick={save}><Plus size={16} /> {addLabel}</button>
        </div>
      )}
    </>
  );
}

// --- standalone "create new agent" page (from the Agents tab) ------
function CreateAgentPage({ onAdd, onCancel }) {
  return (
    <div className="as-page">
      <button className="as-back" onClick={onCancel}><ArrowLeft size={16} /> Back to agents</button>
      <h1 className="as-h1" style={{ marginTop: 0 }}>Create new agent</h1>
      <div className="as-card-pad">
        <CreateAgent onAdd={onAdd} onCancel={onCancel} addLabel="Add agent" />
      </div>
    </div>
  );
}

// --- rate-on-completion modal -------------------------------------
function RateModal({ project, agents, onClose, onSubmit }) {
  const team = project.agentIds.map((id) => agents.find((a) => a.id === id)).filter(Boolean);
  const [scores, setScores] = useState({});
  const allRated = team.every((a) => scores[a.id]);

  return (
    <div className="as-overlay" onClick={onClose}>
      <div className="as-modal" onClick={(e) => e.stopPropagation()}>
        <div className="as-modal-head">
          <div>
            <p className="as-eyebrow">Project complete</p>
            <h2 className="as-h2" style={{ margin: "2px 0 0" }}>{project.name}</h2>
          </div>
          <button className="as-x" onClick={onClose} aria-label="Close"><X size={18} /></button>
        </div>
        <p className="as-blurb">How did each agent do? Your rating updates their library score.</p>
        <div className="as-list" style={{ marginBottom: "1.25rem" }}>
          {team.map((a) => (
            <div className="as-raterow" key={a.id}>
              <div className="as-raterow-left">
                <Avatar name={a.name} color={a.color} size={30} />
                <div><p className="as-row-title">{a.name}</p><p className="as-muted as-sm">now {a.rating.toFixed(1)} ({a.ratingCount})</p></div>
              </div>
              <Stars value={scores[a.id] || 0} onChange={(v) => setScores((s) => ({ ...s, [a.id]: v }))} />
            </div>
          ))}
        </div>
        <div className="as-foot">
          <button className="as-ghost" onClick={onClose}>Maybe later</button>
          <button className="as-primary" disabled={!allRated} onClick={() => onSubmit(scores)}>Submit ratings</button>
        </div>
      </div>
    </div>
  );
}

function Stars({ value, onChange }) {
  const [hover, setHover] = useState(0);
  return (
    <div className="as-stars" onMouseLeave={() => setHover(0)}>
      {[1, 2, 3, 4, 5].map((n) => {
        const active = (hover || value) >= n;
        return (
          <button key={n} className="as-starbtn" onMouseEnter={() => setHover(n)} onClick={() => onChange(n)} aria-label={`${n} stars`}>
            <Star size={20} fill={active ? "#BA7517" : "none"} color={active ? "#BA7517" : "#B4B2A9"} />
          </button>
        );
      })}
    </div>
  );
}

// =================================================================== //
const css = `
html,body{ margin:0; }
.as-root{ --p:#534AB7; --p-soft:#EEEDFE; --p-mid:#CECBF6; --p-dark:#26215C;
  --text:#23221f; --sec:#6b6a63; --ter:#9a988d; --line:rgba(40,38,32,.12); --line2:rgba(40,38,32,.20);
  --bg:#ffffff; --bg2:#f6f4ee; --page:#fbfaf5;
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,sans-serif; color:var(--text);
  -webkit-font-smoothing:antialiased; line-height:1.45;
  min-height:100vh; padding:24px; background:var(--page);
  display:flex; justify-content:center; align-items:flex-start; }
.as-root *{ box-sizing:border-box; }
.as-shell{ display:flex; min-height:600px; height:calc(100vh - 48px); width:100%; max-width:1100px;
  background:var(--page); border:0.5px solid var(--line); border-radius:14px; overflow:hidden; }
.as-side{ width:188px; flex-shrink:0; background:var(--bg2); border-right:0.5px solid var(--line);
  padding:16px 12px; display:flex; flex-direction:column; gap:4px; }
.as-brand{ display:flex; align-items:center; gap:9px; padding:4px 8px 18px; font-size:15px; font-weight:500; }
.as-logo{ width:27px; height:27px; border-radius:8px; background:var(--text); color:#fff;
  display:flex; align-items:center; justify-content:center; }
.as-navgroup{ display:flex; flex-direction:column; gap:3px; }
.as-nav{ display:flex; align-items:center; gap:11px; padding:9px 11px; border-radius:8px; border:none;
  background:transparent; color:var(--sec); font-size:13.5px; cursor:pointer; width:100%; text-align:left;
  font-family:inherit; transition:background .12s; }
.as-nav:hover{ background:rgba(40,38,32,.05); }
.as-nav.is-active{ background:var(--bg); color:var(--text); font-weight:500; border:0.5px solid var(--line); }
.as-build{ margin-top:auto; display:flex; align-items:center; justify-content:center; gap:8px; padding:11px;
  border-radius:9px; background:var(--p); color:#fff; border:none; font-size:13.5px; font-weight:500;
  cursor:pointer; font-family:inherit; transition:filter .12s; }
.as-build:hover{ filter:brightness(1.08); }
.as-main{ flex:1; min-width:0; background:var(--bg); overflow:auto; }
.as-page{ padding:26px 30px 34px; max-width:760px; margin:0 auto; }
.as-eyebrow{ margin:0; font-size:12.5px; color:var(--sec); }
.as-h1{ margin:3px 0 20px; font-size:24px; font-weight:500; letter-spacing:-.01em; }
.as-h2{ margin:0; font-size:16px; font-weight:500; }
.as-muted{ color:var(--sec); }
.as-sm{ font-size:12px; }
.as-stats{ display:grid; grid-template-columns:repeat(3,1fr); gap:12px; margin-bottom:24px; }
.as-stat{ background:var(--bg2); border-radius:10px; padding:13px 15px; }
.as-stat-label{ margin:0; font-size:12.5px; color:var(--sec); }
.as-stat-value{ margin:3px 0 0; font-size:25px; font-weight:500; letter-spacing:-.01em; }
.as-section-head{ display:flex; align-items:center; justify-content:space-between; margin:24px 0 11px; }
.as-link{ background:none; border:none; color:var(--sec); font-size:12.5px; cursor:pointer; font-family:inherit; }
.as-link:hover{ color:var(--text); }
.as-list{ display:flex; flex-direction:column; gap:9px; }
.as-rowcard{ display:flex; align-items:center; justify-content:space-between; gap:12px;
  border:0.5px solid var(--line); border-radius:11px; padding:13px 15px; background:var(--bg); }
.as-row-left{ min-width:0; }
.as-row-title{ margin:0; font-size:14px; font-weight:500; }
.as-row-right{ display:flex; align-items:center; gap:11px; flex-shrink:0; }
.as-chip{ font-size:11px; font-weight:500; padding:3px 9px; border-radius:7px; }
.as-rate-btn{ display:inline-flex; align-items:center; gap:5px; font-size:11.5px; font-weight:500;
  color:var(--p-dark); background:var(--p-soft); border:none; padding:4px 10px; border-radius:7px;
  cursor:pointer; font-family:inherit; }
.as-rate-btn:hover{ background:var(--p-mid); }
.as-grid2{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px; }
.as-miniagent{ display:flex; align-items:center; gap:11px; border:0.5px solid var(--line);
  border-radius:11px; padding:11px 13px; }
.as-rating{ display:inline-flex; align-items:center; gap:3px; }
.as-rating svg{ vertical-align:-2px; }
.as-primary{ display:inline-flex; align-items:center; gap:6px; background:var(--p); color:#fff; border:none;
  padding:9px 15px; border-radius:9px; font-size:13px; font-weight:500; cursor:pointer; font-family:inherit;
  transition:filter .12s; }
.as-primary:hover:not(:disabled){ filter:brightness(1.08); }
.as-primary:disabled{ opacity:.4; cursor:not-allowed; }
.as-ghost{ background:var(--bg); border:0.5px solid var(--line2); padding:9px 15px; border-radius:9px;
  font-size:13px; cursor:pointer; font-family:inherit; color:var(--text); transition:background .12s; }
.as-ghost:hover{ background:var(--bg2); }
.as-tiny{ padding:7px 13px; font-size:12.5px; margin-top:10px; }
.as-toolbar{ display:flex; align-items:center; gap:11px; margin-bottom:20px; }
.as-search{ flex:1; display:flex; align-items:center; gap:8px; border:0.5px solid var(--line);
  border-radius:9px; padding:0 12px; color:var(--ter); }
.as-search input{ border:none; outline:none; background:none; font-size:13px; padding:9px 0; flex:1;
  font-family:inherit; color:var(--text); }
.as-toggle{ display:flex; border:0.5px solid var(--line); border-radius:9px; overflow:hidden; }
.as-toggle button{ padding:9px 16px; font-size:13px; border:none; background:var(--bg); color:var(--sec);
  cursor:pointer; font-family:inherit; }
.as-toggle button.is-on{ background:var(--bg2); color:var(--text); font-weight:500; }
.as-gridcards{ display:grid; grid-template-columns:repeat(auto-fit,minmax(210px,1fr)); gap:12px; }
.as-agentcard{ border:0.5px solid var(--line); border-radius:12px; padding:15px; background:var(--bg);
  transition:border-color .12s; }
.as-agentcard:hover{ border-color:var(--line2); }
.as-agentcard-head{ display:flex; align-items:center; gap:11px; margin-bottom:11px; }
.as-pill{ font-size:11px; padding:1px 9px; border-radius:7px; display:inline-block; margin-top:2px; }
.as-blurb{ margin:0; font-size:12.5px; color:var(--sec); line-height:1.5; }
.as-agentcard-foot{ display:flex; align-items:center; justify-content:space-between; font-size:11.5px;
  color:var(--sec); margin-top:12px; }
.as-empty{ border:0.5px dashed var(--line2); border-radius:12px; padding:30px; text-align:center;
  color:var(--sec); font-size:13.5px; }
.as-back{ display:inline-flex; align-items:center; gap:6px; background:none; border:none; color:var(--sec);
  font-size:13px; cursor:pointer; font-family:inherit; padding:0; margin-bottom:18px; }
.as-back:hover{ color:var(--text); }
.as-stepper{ display:flex; align-items:center; gap:8px; margin-bottom:22px; flex-wrap:wrap; }
.as-step-wrap{ display:flex; align-items:center; gap:8px; }
.as-step{ display:flex; align-items:center; gap:7px; font-size:13px; color:var(--ter); }
.as-step.is-current{ color:var(--text); font-weight:500; }
.as-step.is-done{ color:var(--sec); }
.as-step-dot{ width:21px; height:21px; border-radius:50%; display:flex; align-items:center;
  justify-content:center; font-size:11px; border:0.5px solid var(--line2); }
.as-step.is-current .as-step-dot{ background:var(--p); color:#fff; border-color:var(--p); }
.as-step.is-done .as-step-dot{ background:var(--bg2); border-color:var(--line); color:var(--sec); }
.as-step-sep{ color:var(--ter); }
.as-card-pad{ border:0.5px solid var(--line); border-radius:12px; padding:20px 22px; background:var(--bg); }
.as-label{ display:block; font-size:12px; color:var(--sec); margin:14px 0 6px; }
.as-card-pad .as-label:first-of-type{ margin-top:18px; }
.as-input,.as-textarea{ width:100%; border:0.5px solid var(--line2); border-radius:9px; padding:10px 12px;
  font-size:13.5px; font-family:inherit; color:var(--text); background:var(--bg); outline:none;
  transition:border-color .12s, box-shadow .12s; }
.as-input:focus,.as-textarea:focus{ border-color:var(--p); box-shadow:0 0 0 3px var(--p-soft); }
.as-textarea{ resize:vertical; line-height:1.55; }
.as-foot{ display:flex; align-items:center; justify-content:space-between; margin-top:20px;
  padding-top:16px; border-top:0.5px solid var(--line); }
.as-team{ display:flex; flex-wrap:wrap; gap:8px; margin-bottom:16px; }
.as-teamchip{ display:inline-flex; align-items:center; gap:7px; background:var(--bg2);
  border-radius:20px; padding:4px 6px 4px 5px; font-size:12.5px; font-weight:500; }
.as-x{ background:none; border:none; cursor:pointer; color:var(--ter); display:inline-flex; padding:2px;
  border-radius:50%; }
.as-x:hover{ color:var(--text); background:rgba(40,38,32,.08); }
.as-choices{ display:grid; grid-template-columns:1fr 1fr; gap:11px; }
.as-choice{ display:flex; flex-direction:column; gap:6px; align-items:flex-start; text-align:left;
  border:0.5px solid var(--line2); border-radius:11px; padding:16px; background:var(--bg); cursor:pointer;
  font-family:inherit; color:var(--text); transition:border-color .12s, background .12s; }
.as-choice:hover{ border-color:var(--p); background:var(--p-soft); }
.as-choice span:nth-child(2){ font-size:14px; font-weight:500; }
.as-picker{ display:flex; flex-direction:column; gap:7px; }
.as-pickrow{ display:flex; align-items:center; gap:11px; border:0.5px solid var(--line); border-radius:10px;
  padding:9px 12px; background:var(--bg); cursor:pointer; font-family:inherit; text-align:left;
  transition:border-color .12s; }
.as-pickrow:hover{ border-color:var(--line2); }
.as-pickrow.is-on{ border-color:var(--p); background:var(--p-soft); }
.as-pickrow-text{ flex:1; min-width:0; }
.as-check{ width:20px; height:20px; border-radius:50%; border:1px solid var(--line2);
  display:flex; align-items:center; justify-content:center; color:#fff; flex-shrink:0; }
.as-check.is-on{ background:var(--p); border-color:var(--p); }
.as-pickdone{ align-self:flex-start; margin-top:4px; }
.as-create{ display:grid; grid-template-columns:1fr 1fr; gap:14px; align-items:stretch; }
.as-create-left{ display:flex; flex-direction:column; }
.as-create-left .as-label:first-child{ margin-top:0; }
.as-magic{ display:flex; align-items:center; justify-content:center; gap:8px; background:var(--p);
  color:#fff; border:none; border-radius:9px; padding:10px; font-size:13px; font-weight:500;
  cursor:pointer; font-family:inherit; margin-top:14px; transition:filter .12s; }
.as-magic:hover:not(:disabled){ filter:brightness(1.08); }
.as-magic:disabled{ opacity:.4; cursor:not-allowed; }
.as-create-right{ background:var(--bg2); border-radius:10px; padding:14px 16px; min-width:0;
  display:flex; flex-direction:column; }
.as-gen-head{ display:flex; align-items:center; gap:6px; font-size:12px; font-weight:500; color:var(--p);
  margin-bottom:11px; }
.as-gen-empty{ flex:1; display:flex; flex-direction:column; align-items:center; justify-content:center;
  gap:10px; text-align:center; color:var(--ter); font-size:12px; line-height:1.6; padding:20px 0; }
.as-gen-out{ margin:0; font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:11px;
  line-height:1.6; color:var(--sec); white-space:pre-wrap; word-break:break-word;
  animation:asFade .4s ease; }
.as-spinner{ width:18px; height:18px; border:2px solid var(--p-mid); border-top-color:var(--p);
  border-radius:50%; animation:asSpin .7s linear infinite; }
.as-review{ background:var(--bg2); border-radius:10px; padding:13px 15px; margin-bottom:11px; }
.as-review .as-label{ margin:0 0 6px; }
.as-note{ display:flex; align-items:center; gap:8px; font-size:12.5px; color:var(--sec);
  background:var(--p-soft); padding:11px 13px; border-radius:9px; margin:4px 0 0; }
.as-note svg{ color:var(--p); flex-shrink:0; }
.as-launch{ display:inline-flex; align-items:center; gap:7px; background:var(--p-dark); color:#fff;
  border:none; padding:10px 18px; border-radius:9px; font-size:13.5px; font-weight:500; cursor:pointer;
  font-family:inherit; transition:filter .12s; }
.as-launch:hover{ filter:brightness(1.25); }
.as-overlay{ position:absolute; inset:0; background:rgba(30,28,24,.42); display:flex; align-items:center;
  justify-content:center; padding:24px; animation:asFade .15s ease; z-index:50; }
.as-root{ position:relative; }
.as-modal{ background:var(--bg); border-radius:14px; padding:22px 24px; width:100%; max-width:440px;
  border:0.5px solid var(--line); }
.as-modal-head{ display:flex; align-items:flex-start; justify-content:space-between; margin-bottom:8px; }
.as-raterow{ display:flex; align-items:center; justify-content:space-between; gap:12px;
  border:0.5px solid var(--line); border-radius:11px; padding:11px 14px; }
.as-raterow-left{ display:flex; align-items:center; gap:11px; }
.as-stars{ display:flex; gap:2px; }
.as-starbtn{ background:none; border:none; cursor:pointer; padding:2px; display:inline-flex; }
.as-toast{ position:absolute; top:20px; right:20px; background:var(--text);
  color:#fff; font-size:13px; padding:11px 17px; border-radius:10px; display:flex; align-items:center;
  gap:8px; animation:asRise .25s ease; z-index:60; box-shadow:0 8px 24px rgba(30,28,24,.18); }
@keyframes asSpin{ to{ transform:rotate(360deg); } }
@keyframes asFade{ from{ opacity:0; } to{ opacity:1; } }
@keyframes asRise{ from{ opacity:0; transform:translateX(16px); } to{ opacity:1; transform:translateX(0); } }
@media(max-width:640px){
  .as-side{ width:60px; }
  .as-brand span:last-child,.as-nav span,.as-build span{ display:none; }
  .as-brand{ justify-content:center; padding:4px 0 18px; }
  .as-nav,.as-build{ justify-content:center; }
  .as-stats,.as-choices,.as-create,.as-grid2{ grid-template-columns:1fr; }
  .as-page{ padding:20px 16px; }
}
`;
