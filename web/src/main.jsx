import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const sections = [
  ["executions", "Execuções"],
  ["report", "Relatório técnico"],
  ["sources", "Fontes"],
  ["approvals", "Aprovações"],
  ["audits", "Auditoria"],
];

function statusClass(status) {
  return `status status-${String(status || "unknown").toLowerCase().replaceAll("_", "-")}`;
}

function App() {
  const [projectId, setProjectId] = useState("app-financas");
  const [apiKey, setApiKey] = useState(() => sessionStorage.getItem("aieo-api-key") || "");
  const [projects, setProjects] = useState([]);
  const [agents, setAgents] = useState([]);
  const [prompt, setPrompt] = useState("");
  const [preferredAgents, setPreferredAgents] = useState([]);
  const [includeContent, setIncludeContent] = useState(false);
  const [section, setSection] = useState(() => {
    const requested = new URLSearchParams(window.location.search).get("section");
    return sections.some(([id]) => id === requested) ? requested : "executions";
  });
  const [executions, setExecutions] = useState([]);
  const [invocations, setInvocations] = useState([]);
  const [audits, setAudits] = useState([]);
  const [selected, setSelected] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function request(path, options = {}) {
    const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
    if (apiKey) headers["X-API-Key"] = apiKey;
    const response = await fetch(path, { ...options, headers });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.detail || `Falha HTTP ${response.status}`);
    }
    return response.status === 204 ? null : response.json();
  }

  async function refresh() {
    if (!projectId) return;
    setLoading(true);
    setError("");
    try {
      const query = encodeURIComponent(projectId);
      const [executionData, invocationData, auditData] = await Promise.all([
        request(`/v1/executions?project_id=${query}`),
        request(`/v1/mcp/invocations?project_id=${query}`),
        request(`/v1/evidence/audits?project_id=${query}`),
      ]);
      setExecutions(executionData);
      setInvocations(invocationData);
      setAudits(auditData);
      setSelected(executionData[0] || null);
      sessionStorage.setItem("aieo-api-key", apiKey);
    } catch (reason) {
      setError(reason.message);
    } finally {
      setLoading(false);
    }
  }

  async function loadCatalog() {
    setError("");
    try {
      const [projectData, agentData] = await Promise.all([
        request("/v1/projects"),
        request("/v1/agents"),
      ]);
      setProjects(projectData);
      setAgents(agentData);
      if (projectData.length && !projectData.some((project) => project.id === projectId)) {
        setProjectId(projectData[0].id);
      }
    } catch (reason) {
      setError(reason.message);
    }
  }

  function toggleAgent(agentId) {
    setPreferredAgents((current) => current.includes(agentId)
      ? current.filter((item) => item !== agentId)
      : [...current, agentId]);
  }

  async function createAnalysis(event) {
    event.preventDefault();
    if (!projectId || prompt.trim().length < 3) return;
    setLoading(true);
    setError("");
    try {
      const execution = await request("/v1/evidence/executions", {
        method: "POST",
        body: JSON.stringify({
          project_id: projectId,
          prompt: prompt.trim(),
          demo: true,
          include_content: includeContent,
          preferred_agents: preferredAgents,
        }),
      });
      setPrompt("");
      await refresh();
      setSelected(execution);
      setSection("executions");
    } catch (reason) {
      setError(reason.message);
    } finally {
      setLoading(false);
    }
  }

  async function approve(invocation) {
    const approvedBy = window.prompt("Identidade do aprovador:");
    if (!approvedBy) return;
    try {
      await request(`/v1/mcp/invocations/${invocation.id}/approve`, {
        method: "POST",
        body: JSON.stringify({ project_id: projectId, approved_by: approvedBy }),
      });
      await refresh();
    } catch (reason) {
      setError(reason.message);
    }
  }

  useEffect(() => {
    loadCatalog();
    refresh();
  }, []);

  const sources = executions.flatMap((execution) =>
    (execution.evidence_sources || []).map((source) => ({ execution: execution.id, source })),
  );
  const pending = invocations.filter((item) => item.status === "WAITING_APPROVAL");

  async function copyReport() {
    if (!selected) return;
    const lines = [
      `# Relatório técnico — ${selected.request?.project_id || projectId}`,
      `Execução: ${selected.id}`,
      `Estado: ${selected.status}`,
      `Revisão: ${selected.request?.context?.evidence?.revision || "não informada"}`,
      "",
      "## Resultado consolidado",
      selected.consolidated_result || "Sem resultado consolidado.",
      "",
      ...((selected.results || []).flatMap((result) => [
        `## ${result.agent}`,
        result.summary,
        ...(result.findings || []).map((finding) => `- ${finding}`),
        "",
      ])),
      "## Fontes",
      ...((selected.evidence_sources || []).map((source) => `- ${source}`)),
    ];
    await navigator.clipboard.writeText(lines.join("\n"));
  }

  return (
    <div className="shell">
      <aside>
        <div className="brand"><span>AI</span><strong>Engineering<br />Orchestrator</strong></div>
        <nav>{sections.map(([id, label]) => (
          <button className={section === id ? "active" : ""} onClick={() => setSection(id)} key={id}>{label}</button>
        ))}</nav>
        <a className="grafana" href="http://localhost:3300/d/aieo-overview" target="_blank">Abrir Grafana ↗</a>
      </aside>
      <main>
        <header>
          <div><p className="eyebrow">Fase 5 · Operação</p><h1>Painel operacional</h1></div>
          <div className="connection">
            <select aria-label="Projeto" value={projectId} onChange={(e) => setProjectId(e.target.value)}>
              {!projects.length && <option value={projectId}>{projectId}</option>}
              {projects.map((project) => <option value={project.id} key={project.id}>{project.id}</option>)}
            </select>
            <input aria-label="API key" type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)} placeholder="X-API-Key" />
            <button onClick={refresh} disabled={loading}>{loading ? "Atualizando…" : "Atualizar"}</button>
          </div>
        </header>
        {error && <div className="error">{error}</div>}
        <section className="metrics">
          <article><span>Execuções</span><strong>{executions.length}</strong></article>
          <article><span>Fontes citadas</span><strong>{sources.length}</strong></article>
          <article><span>Aprovações pendentes</span><strong>{pending.length}</strong></article>
          <article><span>Acessos auditados</span><strong>{audits.length}</strong></article>
        </section>

        {section === "executions" && <form className="panel analysis-form" onSubmit={createAnalysis}>
          <div className="form-heading">
            <div><p className="eyebrow">Nova análise</p><h2>Solicitar análise do repositório</h2></div>
            <button type="submit" disabled={loading || prompt.trim().length < 3}>{loading ? "Executando…" : "Executar análise"}</button>
          </div>
          <label className="prompt-field">Pedido
            <textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} maxLength="10000" placeholder="Ex.: Revise arquitetura, QA, segurança e documentação" />
          </label>
          <fieldset>
            <legend>Agentes <small>(nenhum selecionado = roteamento automático)</small></legend>
            <div className="agent-options">{agents.map((agent) => <label key={agent.id} title={agent.description}>
              <input type="checkbox" checked={preferredAgents.includes(agent.id)} onChange={() => toggleAgent(agent.id)} />
              <span>{agent.id}</span>
            </label>)}</div>
          </fieldset>
          <label className="content-option"><input type="checkbox" checked={includeContent} onChange={(event) => setIncludeContent(event.target.checked)} /> Incluir conteúdo permitido dos arquivos</label>
        </form>}

        {section === "executions" && <section className="grid">
          <div className="panel"><h2>Histórico de execuções</h2>{executions.map((item) => (
            <button className="row" onClick={() => setSelected(item)} key={item.id}>
              <span><b>{item.request?.prompt || "Execução"}</b><small>{item.id}</small></span>
              <i className={statusClass(item.status)}>{item.status}</i>
            </button>
          ))}{!executions.length && <Empty />}</div>
          <div className="panel detail"><h2>Detalhes</h2>{selected ? <>
            <dl><dt>ID</dt><dd>{selected.id}</dd><dt>Estado</dt><dd>{selected.status}</dd><dt>Agentes</dt><dd>{selected.selected_agents?.join(", ") || "nenhum"}</dd><dt>Fontes</dt><dd>{selected.evidence_sources?.length || 0}</dd></dl>
            <h3>Resultado consolidado</h3><pre>{selected.consolidated_result || "Sem resultado."}</pre>
          </> : <Empty />}</div>
        </section>}

        {section === "report" && <TechnicalReport
          execution={selected}
          projectId={projectId}
          audit={audits.find((item) => item.execution_id === selected?.id)}
          onCopy={copyReport}
        />}

        {section === "sources" && <section className="panel"><h2>Fontes de evidência</h2>{sources.map((item) => (
          <a className="source" href={item.source} target="_blank" key={`${item.execution}-${item.source}`}><span>{item.source}</span><small>execução {item.execution}</small></a>
        ))}{!sources.length && <Empty />}</section>}

        {section === "approvals" && <section className="panel"><h2>Aprovações MCP</h2>{pending.map((item) => (
          <div className="approval" key={item.id}><div><b>{item.server}:{item.tool}</b><small>{item.reason}</small><code>{JSON.stringify(item.arguments)}</code></div><button onClick={() => approve(item)}>Aprovar</button></div>
        ))}{!pending.length && <Empty text="Nenhuma aprovação pendente." />}</section>}

        {section === "audits" && <section className="panel"><h2>Auditoria de evidências</h2>{audits.map((item) => (
          <div className="row static" key={item.id}><span><b>{item.visibility} · {item.revision || "sem revisão"}</b><small>{new Date(item.created_at).toLocaleString("pt-BR")}</small></span><i className={statusClass(item.status)}>{item.status}</i></div>
        ))}{!audits.length && <Empty />}</section>}
      </main>
    </div>
  );
}

function TechnicalReport({ execution, projectId, audit, onCopy }) {
  if (!execution) return <section className="panel"><Empty text="Selecione ou execute uma análise para gerar o relatório." /></section>;
  const evidence = execution.request?.context?.evidence || {};
  const revision = evidence.revision || audit?.revision || "não informada";
  const createdAt = execution.created_at
    ? new Date(execution.created_at).toLocaleString("pt-BR")
    : "não informado";
  const findingCount = (execution.results || []).reduce(
    (total, result) => total + (result.findings?.length || 0), 0,
  );
  return <article className="technical-report panel">
    <div className="report-heading">
      <div><p className="eyebrow">Relatório técnico</p><h2>{projectId}</h2><p className="report-subtitle">Análise rastreável do repositório · {createdAt}</p></div>
      <div className="report-actions"><button onClick={onCopy}>Copiar Markdown</button><button className="secondary" onClick={() => window.print()}>Imprimir / PDF</button></div>
    </div>
    <div className="report-summary">
      <div><span>Estado</span><strong className={statusClass(execution.status)}>{execution.status}</strong></div>
      <div><span>Revisão Git</span><code>{revision}</code></div>
      <div><span>Especialistas</span><strong>{execution.results?.length || 0}</strong></div>
      <div><span>Achados</span><strong>{findingCount}</strong></div>
      <div><span>Fontes</span><strong>{execution.evidence_sources?.length || 0}</strong></div>
      <div><span>Acesso</span><strong>{evidence.read_only === false ? "escrita" : "somente leitura"}</strong></div>
    </div>
    {execution.results?.some((result) => result.simulated) && <p className="report-notice">Resultado gerado em modo simulado. Valida orquestração e rastreabilidade; não representa parecer de um LLM externo.</p>}
    <section className="report-section"><h3>Escopo solicitado</h3><p>{execution.request?.prompt}</p></section>
    <section className="report-section"><h3>Resultado consolidado</h3><pre>{execution.consolidated_result || "Sem resultado consolidado."}</pre></section>
    <section className="report-section"><h3>Análise por especialidade</h3><div className="specialist-grid">{(execution.results || []).map((result) => <article className="specialist" key={result.agent}>
      <div className="specialist-heading"><h4>{result.agent}</h4><span>{result.findings?.length || 0} achados</span></div>
      <p>{result.summary}</p>
      {!!result.findings?.length && <ul>{result.findings.map((finding, index) => <li key={`${result.agent}-${index}`}>{finding}</li>)}</ul>}
      {!!result.evidence?.length && <details><summary>Evidências do especialista</summary><ul>{result.evidence.map((item, index) => <li key={`${result.agent}-evidence-${index}`}>{item}</li>)}</ul></details>}
    </article>)}</div></section>
    <section className="report-section"><h3>Proveniência</h3><dl className="provenance">
      <dt>Execução</dt><dd>{execution.id}</dd><dt>Projeto</dt><dd>{execution.request?.project_id}</dd><dt>Revisão</dt><dd><code>{revision}</code></dd><dt>Auditoria</dt><dd>{audit?.status || "não localizada"}</dd><dt>Visibilidade</dt><dd>{audit?.visibility || evidence.visibility || "não informada"}</dd>
    </dl></section>
    <section className="report-section"><h3>Fontes consultadas</h3>{(execution.evidence_sources || []).map((source) => <a className="source" href={source} target="_blank" key={source}>{source}</a>)}{!execution.evidence_sources?.length && <Empty text="Nenhuma fonte registrada." />}</section>
  </article>;
}

function Empty({ text = "Nenhum registro encontrado para este projeto." }) {
  return <p className="empty">{text}</p>;
}

createRoot(document.getElementById("root")).render(<App />);
