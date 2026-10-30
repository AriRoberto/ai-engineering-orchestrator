import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const sections = [
  ["executions", "Execuções"],
  ["knowledge", "Base RAG"],
  ["report", "Relatório técnico"],
  ["sources", "Fontes"],
  ["approvals", "Aprovações"],
  ["audits", "Auditoria"],
];

function statusClass(status) {
  return `status status-${String(status || "unknown").toLowerCase().replaceAll("_", "-")}`;
}

function reportMarkdown(execution, projectId) {
  return [
    `# Relatório técnico — ${execution.request?.project_id || projectId}`,
    `Execução: ${execution.id}`,
    `Estado: ${execution.status}`,
    `Revisão: ${execution.request?.context?.evidence?.revision || "não informada"}`,
    `LLM: ${execution.llm_usage?.provider || "não informado"} / ${execution.llm_usage?.model || "não informado"}`,
    `Tokens: ${(execution.llm_usage?.input_tokens || 0) + (execution.llm_usage?.output_tokens || 0)} (${execution.llm_usage?.estimated ? "estimados" : "medidos pelo provedor"})`,
    `Contexto RAG: ${execution.knowledge_input_tokens || 0} tokens estimados em ${execution.knowledge_context?.length || 0} trechos`,
    "",
    "## Resultado consolidado",
    execution.consolidated_result || "Sem resultado consolidado.",
    "",
    ...((execution.results || []).flatMap((result) => [
      `## ${result.agent}`,
      result.summary,
      ...(result.findings || []).map((finding) => `- ${finding}`),
      "",
    ])),
    "## Fontes",
    ...((execution.evidence_sources || []).map((source) => `- ${source}`)),
    ...((execution.knowledge_context || []).map((item) => `- ${item.citation} ${item.source}`)),
  ].join("\n");
}

function App() {
  const [projectId, setProjectId] = useState(() =>
    new URLSearchParams(window.location.search).get("project") || "app-financas");
  const [apiKey, setApiKey] = useState(() => sessionStorage.getItem("aieo-api-key") || "");
  const [projects, setProjects] = useState([]);
  const [agents, setAgents] = useState([]);
  const [runtime, setRuntime] = useState(null);
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
  const [reportAction, setReportAction] = useState("");
  const [showProjectForm, setShowProjectForm] = useState(false);
  const [repositoryInput, setRepositoryInput] = useState("");
  const [projectIdInput, setProjectIdInput] = useState("");
  const [ingestion, setIngestion] = useState(null);
  const [ingestionBranch, setIngestionBranch] = useState("");
  const [knowledgeQuery, setKnowledgeQuery] = useState("");
  const [knowledgeHits, setKnowledgeHits] = useState([]);
  const [knowledgeStatus, setKnowledgeStatus] = useState(null);
  const [ragMetrics, setRagMetrics] = useState(null);
  const [evaluationQuery, setEvaluationQuery] = useState("");
  const [expectedSources, setExpectedSources] = useState("");
  const [evaluationSpecialty, setEvaluationSpecialty] = useState("general");
  const [evaluationResult, setEvaluationResult] = useState(null);

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

  function clearWorkspace({ clearPrompt = true } = {}) {
    setExecutions([]);
    setInvocations([]);
    setAudits([]);
    setSelected(null);
    setReportAction("");
    setIngestion(null);
    setKnowledgeHits([]);
    setKnowledgeStatus(null);
    setRagMetrics(null);
    setEvaluationResult(null);
    setError("");
    if (clearPrompt) setPrompt("");
  }

  async function refresh(targetProjectId = projectId) {
    if (!targetProjectId) return;
    setLoading(true);
    setError("");
    try {
      const query = encodeURIComponent(targetProjectId);
      const [executionData, invocationData, auditData, knowledgeData, metricsData] = await Promise.all([
        request(`/v1/executions/summaries?project_id=${query}`),
        request(`/v1/mcp/invocations?project_id=${query}`),
        request(`/v1/evidence/audits?project_id=${query}`),
        request(`/v1/knowledge/status?project_id=${query}`),
        request(`/v1/knowledge/evaluations/metrics?project_id=${query}`),
      ]);
      setExecutions(executionData);
      setInvocations(invocationData);
      setAudits(auditData);
      setKnowledgeStatus(knowledgeData);
      setRagMetrics(metricsData);
      const firstExecution = executionData[0];
      setSelected(firstExecution
        ? await request(`/v1/executions/${firstExecution.id}?project_id=${query}`)
        : null);
      sessionStorage.setItem("aieo-api-key", apiKey);
    } catch (reason) {
      setError(reason.message);
    } finally {
      setLoading(false);
    }
  }

  async function changeProject(nextProjectId) {
    if (nextProjectId === projectId) return;
    clearWorkspace();
    setProjectId(nextProjectId);
    setSection("executions");
    await refresh(nextProjectId);
  }

  async function loadCatalog() {
    setError("");
    try {
      const [projectData, agentData, runtimeData] = await Promise.all([
        request("/v1/projects"),
        request("/v1/agents"),
        request("/runtime"),
      ]);
      setProjects(projectData);
      setAgents(agentData);
      setRuntime(runtimeData);
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
    clearWorkspace({ clearPrompt: false });
    setSection("executions");
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

  async function pollIngestion(jobId, targetProjectId) {
    const query = encodeURIComponent(targetProjectId);
    for (let attempt = 0; attempt < 120; attempt += 1) {
      const job = await request(`/v1/knowledge/repositories/ingestions/${jobId}?project_id=${query}`);
      setIngestion(job);
      if (["COMPLETED", "FAILED"].includes(job.status)) return job;
      await new Promise((resolve) => window.setTimeout(resolve, 1000));
    }
    throw new Error("A ingestão continua em processamento; use Atualizar para consultar depois.");
  }

  async function startIngestion(event) {
    event.preventDefault();
    setLoading(true);
    setError("");
    setKnowledgeHits([]);
    try {
      const job = await request("/v1/knowledge/repositories/ingestions", {
        method: "POST",
        body: JSON.stringify({
          project_id: projectId,
          branch: ingestionBranch.trim() || null,
          collection: "repository",
        }),
      });
      setIngestion(job);
      const completed = await pollIngestion(job.id, projectId);
      if (completed.status === "COMPLETED") {
        setKnowledgeStatus(await request(`/v1/knowledge/status?project_id=${encodeURIComponent(projectId)}`));
      }
    } catch (reason) {
      setError(reason.message);
    } finally {
      setLoading(false);
    }
  }

  async function searchKnowledge(event) {
    event.preventDefault();
    if (knowledgeQuery.trim().length < 2) return;
    setLoading(true);
    setError("");
    try {
      setKnowledgeHits(await request("/v1/knowledge/search", {
        method: "POST",
        body: JSON.stringify({
          project_id: projectId,
          query: knowledgeQuery.trim(),
          limit: 5,
          include_shared: false,
        }),
      }));
    } catch (reason) {
      setError(reason.message);
    } finally {
      setLoading(false);
    }
  }

  async function evaluateRag(event) {
    event.preventDefault();
    const expected = expectedSources.split("\n").map((item) => item.trim()).filter(Boolean);
    if (evaluationQuery.trim().length < 2 || !expected.length) return;
    setLoading(true);
    setError("");
    try {
      const result = await request("/v1/knowledge/evaluations", {
        method: "POST",
        body: JSON.stringify({ project_id: projectId, query: evaluationQuery.trim(), expected_sources: expected, specialty: evaluationSpecialty, limit: 5 }),
      });
      setEvaluationResult(result);
      setRagMetrics(await request(`/v1/knowledge/evaluations/metrics?project_id=${encodeURIComponent(projectId)}`));
    } catch (reason) {
      setError(reason.message);
    } finally {
      setLoading(false);
    }
  }

  async function rateRagHit(hit, relevance) {
    try {
      await request("/v1/knowledge/evaluations/feedback", {
        method: "POST",
        body: JSON.stringify({ project_id: projectId, evaluation_id: evaluationResult.id, chunk_id: hit.chunk_id, relevance, comment: "" }),
      });
      setRagMetrics(await request(`/v1/knowledge/evaluations/metrics?project_id=${encodeURIComponent(projectId)}`));
    } catch (reason) {
      setError(reason.message);
    }
  }

  async function registerProject(event) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const project = await request("/v1/projects", {
        method: "POST",
        body: JSON.stringify({
          repository: repositoryInput.trim(),
          project_id: projectIdInput.trim() || null,
        }),
      });
      setProjects((current) => [...current.filter((item) => item.id !== project.id), project]
        .sort((left, right) => left.id.localeCompare(right.id)));
      clearWorkspace();
      setProjectId(project.id);
      setSection("executions");
      setRepositoryInput("");
      setProjectIdInput("");
      setShowProjectForm(false);
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

  useEffect(() => {
    const url = new URL(window.location.href);
    url.searchParams.set("project", projectId);
    url.searchParams.set("section", section);
    window.history.replaceState({}, "", url);
  }, [projectId, section]);

  const sources = executions.flatMap((execution) =>
    execution.id === selected?.id
      ? (selected.evidence_sources || []).map((source) => ({ execution: execution.id, source }))
      : [],
  );
  const sourceCount = executions.reduce(
    (total, execution) => total + (execution.evidence_source_count || 0), 0,
  );
  const pending = invocations.filter((item) => item.status === "WAITING_APPROVAL");

  async function copyReport() {
    if (!selected) return;
    await navigator.clipboard.writeText(reportMarkdown(selected, projectId));
    setReportAction("Relatório copiado.");
  }

  function downloadReport() {
    if (!selected) return;
    const blob = new Blob([reportMarkdown(selected, projectId)], {
      type: "text/markdown;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `relatorio-${projectId}-${selected.id}.md`;
    anchor.click();
    URL.revokeObjectURL(url);
    setReportAction("Download Markdown iniciado.");
  }

  return (
    <div className="shell">
      <aside>
        <div className="brand"><span>AI</span><strong>Engineering<br />Orchestrator</strong></div>
        <nav>{sections.map(([id, label]) => (
          <button className={section === id ? "active" : ""} onClick={() => { setSection(id); setReportAction(""); }} key={id}>{label}</button>
        ))}</nav>
        <a className="grafana" href="http://localhost:3300/d/aieo-overview" target="_blank">Abrir Grafana ↗</a>
      </aside>
      <main>
        <header>
          <div>
            <p className="eyebrow">Fase 5 · Operação</p><h1>Painel operacional</h1>
            <div
              className={`llm-runtime llm-runtime-${runtime?.llm_mode || "loading"}`}
              title={runtime?.external_api
                ? "Chamadas externas habilitadas; tokens medidos pelo provedor."
                : "Sem chamada externa; tokens estimados localmente."}
            >
              <span>LLM ativo</span>
              <strong>{runtime
                ? `${runtime.llm_mode === "openai" ? "OPENAI" : "SIMULADO"} · ${runtime.llm_model}`
                : "VERIFICANDO…"}</strong>
              {runtime && <small>{runtime.usage_accounting === "measured" ? "tokens medidos" : "tokens estimados"}</small>}
            </div>
            <div
              className={`llm-runtime llm-runtime-${runtime?.embedding_mode === "openai" ? "openai" : "simulated"}`}
              title={runtime?.embedding_external_api
                ? "Ingestão e buscas RAG geram chamadas externas de embeddings."
                : "Embeddings determinísticos processados localmente, sem cobrança externa."}
            >
              <span>RAG embeddings</span>
              <strong>{runtime
                ? `${runtime.embedding_mode === "openai" ? "OPENAI" : "LOCAL"} · ${runtime.embedding_model}`
                : "VERIFICANDO…"}</strong>
              {runtime && <small>limite {runtime.max_rag_context_tokens} tokens/análise</small>}
            </div>
          </div>
          <div className="connection">
            <select aria-label="Projeto" value={projectId} onChange={(event) => changeProject(event.target.value)}>
              {!projects.length && <option value={projectId}>{projectId}</option>}
              {projects.map((project) => <option value={project.id} key={project.id}>{project.id}</option>)}
            </select>
            <input aria-label="API key" type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)} placeholder="X-API-Key" />
            {runtime?.project_registration_enabled && <button className="secondary" onClick={() => setShowProjectForm((current) => !current)}>+ Projeto</button>}
            <button className="secondary" onClick={() => clearWorkspace()} disabled={loading}>Limpar tela</button>
            <button onClick={() => refresh()} disabled={loading}>{loading ? "Atualizando…" : "Atualizar"}</button>
          </div>
        </header>
        {error && <div className="error">{error}</div>}
        {showProjectForm && <form className="panel project-form" onSubmit={registerProject}>
          <div><p className="eyebrow">Cadastro local</p><h2>Adicionar repositório público</h2><small>O GitHub será consultado e o projeto ficará restrito a somente leitura.</small></div>
          <label>Repositório GitHub<input required value={repositoryInput} onChange={(event) => setRepositoryInput(event.target.value)} placeholder="OWNER/REPO" pattern="[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9._-]{1,100}" /></label>
          <label>ID opcional<input value={projectIdInput} onChange={(event) => setProjectIdInput(event.target.value)} placeholder="derivado do repositório" pattern="[a-z0-9][a-z0-9-]{1,62}" /></label>
          <button type="submit" disabled={loading}>{loading ? "Validando…" : "Validar e cadastrar"}</button>
        </form>}
        <section className="metrics">
          <article><span>Execuções</span><strong>{executions.length}</strong></article>
          <article><span>Fontes citadas</span><strong>{sourceCount}</strong></article>
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
          {knowledgeStatus && <p className={knowledgeStatus.ready ? "rag-ready" : "rag-warning"}>{knowledgeStatus.ready
            ? `Base RAG pronta: ${knowledgeStatus.documents} documentos e ${knowledgeStatus.chunks} chunks serão consultados dentro do limite configurado.`
            : "Base RAG vazia para este projeto. A análise continuará somente com evidências do repositório; alimente a base na seção Base RAG."}</p>}
        </form>}

        {section === "executions" && <section className="grid">
          <div className="panel"><h2>Histórico de execuções</h2>{executions.map((item) => (
            <button className="row" onClick={async () => {
              try {
                setError("");
                setSelected(await request(`/v1/executions/${item.id}?project_id=${encodeURIComponent(projectId)}`));
              } catch (reason) {
                setError(reason.message);
              }
            }} key={item.id}>
              <span><b>{item.prompt || "Execução"}</b><small>{item.id}</small></span>
              <i className={statusClass(item.status)}>{item.status}</i>
            </button>
          ))}{!executions.length && <Empty />}</div>
          <div className="panel detail"><h2>Detalhes</h2>{selected ? <>
            <dl><dt>ID</dt><dd>{selected.id}</dd><dt>Estado</dt><dd>{selected.status}</dd><dt>Agentes</dt><dd>{selected.selected_agents?.join(", ") || "nenhum"}</dd><dt>Fontes</dt><dd>{selected.evidence_sources?.length || 0}</dd></dl>
            {!!selected.knowledge_context?.length && <><h3>Contexto RAG utilizado · {selected.knowledge_input_tokens} tokens estimados</h3><div className="knowledge-hits">{selected.knowledge_context.map((item) => <article key={item.citation}><div><strong>{item.citation} · {item.title}</strong><span>score {item.score.toFixed(4)}</span></div><small>{item.source}{item.start_line ? ` · linhas ${item.start_line}-${item.end_line}` : ""}</small><pre>{item.content}</pre></article>)}</div></>}
            <h3>Resultado consolidado</h3><pre>{selected.consolidated_result || "Sem resultado."}</pre>
          </> : <Empty />}</div>
        </section>}

        {section === "knowledge" && <section className="rag-workspace">
          <section className="panel rag-inventory">
            <div className="form-heading"><div><p className="eyebrow">Inventário persistente</p><h2>Estado da Base RAG</h2></div><strong className={statusClass(knowledgeStatus?.ready ? "COMPLETED" : "FAILED")}>{knowledgeStatus?.ready ? "PRONTA" : "VAZIA"}</strong></div>
            <div className="ingestion-status"><div><span>Documentos</span><strong>{knowledgeStatus?.documents ?? 0}</strong></div><div><span>Chunks</span><strong>{knowledgeStatus?.chunks ?? 0}</strong></div><div><span>Coleções</span><strong>{knowledgeStatus?.collections?.length ?? 0}</strong></div></div>
            <div className="rag-collections">{(knowledgeStatus?.collections || []).map((item) => <article key={`${item.collection}-${item.embedding_key}`}><div><strong>{item.collection}</strong><span>{item.documents} documentos · {item.chunks} chunks</span></div><code>{item.revision || "sem revisão única"}</code><small>{item.embedding_key}</small></article>)}{!knowledgeStatus?.collections?.length && <Empty text="Nenhuma coleção persistida para este projeto." />}</div>
          </section>
          <form className="panel rag-form" onSubmit={startIngestion}>
            <div className="form-heading">
              <div><p className="eyebrow">Alimentação governada</p><h2>Indexar repositório na Base RAG</h2></div>
              <button type="submit" disabled={loading}>{loading ? "Processando…" : "Iniciar ingestão"}</button>
            </div>
            <p className="rag-help">O repositório cadastrado é clonado em modo somente leitura, filtrado, sanitizado e removido do servidor após a indexação.</p>
            <div className="rag-fields">
              <label>Projeto<input value={projectId} disabled /></label>
              <label>Repositório<input value={projects.find((item) => item.id === projectId)?.repository || ""} disabled /></label>
              <label>Branch<input value={ingestionBranch} onChange={(event) => setIngestionBranch(event.target.value)} placeholder={projects.find((item) => item.id === projectId)?.default_branch || "main"} pattern="[A-Za-z0-9][A-Za-z0-9._/-]*" /></label>
            </div>
            {ingestion && <div className="ingestion-status">
              <div><span>Estado</span><strong className={statusClass(ingestion.status)}>{ingestion.status}</strong></div>
              <div><span>Revisão</span><code>{ingestion.report?.revision || "aguardando"}</code></div>
              <div><span>Documentos</span><strong>{ingestion.report?.documents ?? "—"}</strong></div>
              <div><span>Chunks</span><strong>{ingestion.report?.chunks ?? "—"}</strong></div>
              <div><span>Adicionados</span><strong>{ingestion.report?.sync?.added ?? "—"}</strong></div>
              <div><span>Removidos</span><strong>{ingestion.report?.sync?.removed ?? "—"}</strong></div>
              {ingestion.error && <p className="error">{ingestion.error}</p>}
            </div>}
            {!!ingestion?.report?.files?.length && <details className="ingestion-files"><summary>Arquivos relevantes ({ingestion.report.files.length} de {ingestion.report.total_files})</summary><div>{ingestion.report.files.map((file) => <p key={file.path}><code>{file.path}</code><span>{file.status}{file.reason ? ` · ${file.reason}` : ""}{file.chunks ? ` · ${file.chunks} chunks` : ""}</span></p>)}</div></details>}
            {!!ingestion?.report?.file_summary && <div className="rag-summary">{Object.entries(ingestion.report.file_summary).map(([label, count]) => <span key={label}>{label}: <strong>{count}</strong></span>)}</div>}
          </form>
          <form className="panel rag-form" onSubmit={searchKnowledge}>
            <div className="form-heading"><div><p className="eyebrow">Validação da recuperação</p><h2>Consultar conhecimento indexado</h2></div><button type="submit" disabled={loading || knowledgeQuery.trim().length < 2}>Buscar</button></div>
            <label className="prompt-field">Pergunta<input value={knowledgeQuery} onChange={(event) => setKnowledgeQuery(event.target.value)} placeholder="Ex.: Como a aplicação configura o banco de dados?" /></label>
            <div className="knowledge-hits">{knowledgeHits.map((hit) => <article key={hit.chunk_id}>
              <div><strong>{hit.title}</strong><span>score {hit.score.toFixed(4)}</span></div>
              <small>{hit.source}{hit.start_line ? ` · linhas ${hit.start_line}-${hit.end_line}` : ""}</small>
              <pre>{hit.content}</pre>
            </article>)}{!knowledgeHits.length && <Empty text="Faça uma busca para validar os trechos recuperados." />}</div>
          </form>
          <form className="panel rag-form" onSubmit={evaluateRag}>
            <div className="form-heading"><div><p className="eyebrow">Ciclo de aprendizado</p><h2>Avaliação RAG com resposta esperada</h2></div><button type="submit" disabled={loading || evaluationQuery.trim().length < 2 || !expectedSources.trim()}>Avaliar recuperação</button></div>
            <p className="rag-help">Defina uma pergunta e os caminhos ou fontes que deveriam aparecer. As métricas ficam persistidas por projeto e revisão.</p>
            <div className="rag-eval-fields"><label>Especialidade<select value={evaluationSpecialty} onChange={(event) => setEvaluationSpecialty(event.target.value)}><option value="general">Geral</option><option value="software-engineer">Arquitetura</option><option value="database">Banco de dados</option><option value="qa">QA</option><option value="security">Segurança</option><option value="documentation">Documentação</option><option value="devops">Operação/DevOps</option></select></label><label>Pergunta<input value={evaluationQuery} onChange={(event) => setEvaluationQuery(event.target.value)} placeholder="Como o banco é inicializado?" /></label><label>Fontes esperadas, uma por linha<textarea value={expectedSources} onChange={(event) => setExpectedSources(event.target.value)} placeholder="backend/migrations/001_members_and_transactions.sql" /></label></div>
            <div className="rag-metrics"><div><span>Casos</span><strong>{ragMetrics?.evaluations ?? 0}</strong></div><div><span>Hit@1</span><strong>{Math.round((ragMetrics?.hit_at_1 || 0) * 100)}%</strong></div><div><span>Hit@3</span><strong>{Math.round((ragMetrics?.hit_at_3 || 0) * 100)}%</strong></div><div><span>Hit@5</span><strong>{Math.round((ragMetrics?.hit_at_5 || 0) * 100)}%</strong></div><div><span>MRR</span><strong>{(ragMetrics?.mean_reciprocal_rank || 0).toFixed(3)}</strong></div></div>
            {evaluationResult && <div className="knowledge-hits"><p className={evaluationResult.hit_at_5 ? "rag-ready" : "rag-warning"}>Primeiro resultado relevante: {evaluationResult.first_relevant_rank ? `posição ${evaluationResult.first_relevant_rank}` : "não encontrado no top 5"} · revisão {evaluationResult.revision || "não identificada"}</p>{evaluationResult.hits.map((hit, index) => <article key={hit.chunk_id}><div><strong>#{index + 1} · {hit.title}</strong><span>score {hit.score.toFixed(4)}</span></div><small>{hit.source}</small><pre>{hit.content}</pre><div className="feedback-actions"><span>Este trecho é:</span><button type="button" onClick={() => rateRagHit(hit, "relevant")}>Relevante</button><button type="button" onClick={() => rateRagHit(hit, "partial")}>Parcial</button><button type="button" onClick={() => rateRagHit(hit, "irrelevant")}>Irrelevante</button></div></article>)}</div>}
          </form>
        </section>}

        {section === "report" && <TechnicalReport
          execution={selected}
          projectId={projectId}
          audit={audits.find((item) => item.execution_id === selected?.id)}
          onCopy={copyReport}
          onDownload={downloadReport}
          actionMessage={reportAction}
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

function TechnicalReport({ execution, projectId, audit, onCopy, onDownload, actionMessage }) {
  if (!execution) return <section className="panel"><Empty text="Selecione ou execute uma análise para gerar o relatório." /></section>;
  const evidence = execution.request?.context?.evidence || {};
  const revision = evidence.revision || audit?.revision || "não informada";
  const createdAt = execution.created_at
    ? new Date(execution.created_at).toLocaleString("pt-BR")
    : "não informado";
  const findingCount = (execution.results || []).reduce(
    (total, result) => total + (result.findings?.length || 0), 0,
  );
  const llmUsage = execution.llm_usage;
  const totalTokens = (llmUsage?.input_tokens || 0) + (llmUsage?.output_tokens || 0);
  return <article className="technical-report panel">
    <div className="report-heading">
      <div><p className="eyebrow">Relatório técnico</p><h2>{projectId}</h2><p className="report-subtitle">Análise rastreável do repositório · {createdAt}</p></div>
      <div className="report-actions"><button onClick={onCopy}>Copiar Markdown</button><button className="secondary" onClick={onDownload}>Baixar .md</button><button className="secondary" onClick={() => window.print()}>Imprimir / PDF</button></div>
    </div>
    {actionMessage && <p className="report-feedback" role="status">{actionMessage}</p>}
    <div className="report-summary">
      <div><span>Estado</span><strong className={statusClass(execution.status)}>{execution.status}</strong></div>
      <div><span>Revisão Git</span><code>{revision}</code></div>
      <div><span>Especialistas</span><strong>{execution.results?.length || 0}</strong></div>
      <div><span>Achados</span><strong>{findingCount}</strong></div>
      <div><span>Fontes</span><strong>{execution.evidence_sources?.length || 0}</strong></div>
      <div><span>Acesso</span><strong>{evidence.read_only === false ? "escrita" : "somente leitura"}</strong></div>
      <div><span>Consolidação LLM</span><strong>{llmUsage?.provider || "não informada"}</strong></div>
      <div><span>Tokens</span><strong>{totalTokens} {llmUsage?.estimated ? "estimados" : "medidos"}</strong></div>
      <div><span>Contexto RAG</span><strong>{execution.knowledge_input_tokens || 0} tokens</strong></div>
    </div>
    {llmUsage?.provider === "simulated" && <p className="report-notice">Consolidação gerada pelo provedor simulado. Valida orquestração e rastreabilidade; não representa parecer de um LLM externo.</p>}
    {llmUsage?.provider === "openai-agents" && <p className="report-feedback">Consolidação real via OpenAI Agents SDK: modelo {llmUsage.model}, {totalTokens} tokens medidos pelo provedor.</p>}
    <section className="report-section"><h3>Escopo solicitado</h3><p>{execution.request?.prompt}</p></section>
    <section className="report-section"><h3>Resultado consolidado</h3><pre>{execution.consolidated_result || "Sem resultado consolidado."}</pre></section>
    <section className="report-section"><h3>Contexto RAG recuperado</h3><div className="knowledge-hits">{(execution.knowledge_context || []).map((item) => <article key={item.citation}><div><strong>{item.citation} · {item.title}</strong><span>{item.estimated_tokens} tokens · score {item.score.toFixed(4)}</span></div><small>{item.source}{item.start_line ? ` · linhas ${item.start_line}-${item.end_line}` : ""}</small><pre>{item.content}</pre></article>)}{!execution.knowledge_context?.length && <Empty text="Nenhum trecho da Base RAG foi utilizado." />}</div></section>
    <section className="report-section"><h3>Análise por especialidade</h3><div className="specialist-grid">{(execution.results || []).map((result) => <article className="specialist" key={result.agent}>
      <div className="specialist-heading"><h4>{result.agent}</h4><span>{result.findings?.length || 0} achados</span></div>
      <p>{result.summary}</p>
      {!!result.findings?.length && <ul>{result.findings.map((finding, index) => <li key={`${result.agent}-${index}`}>{finding}</li>)}</ul>}
      {!!result.evidence?.length && <details><summary>Evidências do especialista</summary><ul>{result.evidence.map((item, index) => <li key={`${result.agent}-evidence-${index}`}>{item}</li>)}</ul></details>}
    </article>)}</div></section>
    <section className="report-section"><h3>Proveniência</h3><dl className="provenance">
      <dt>Execução</dt><dd>{execution.id}</dd><dt>Projeto</dt><dd>{execution.request?.project_id}</dd><dt>Revisão</dt><dd><code>{revision}</code></dd><dt>Auditoria</dt><dd>{audit?.status || "não localizada"}</dd><dt>Visibilidade</dt><dd>{audit?.visibility || evidence.visibility || "não informada"}</dd><dt>LLM</dt><dd>{llmUsage ? `${llmUsage.provider} / ${llmUsage.model}` : "não informado"}</dd><dt>Uso</dt><dd>{llmUsage ? `${llmUsage.input_tokens} entrada + ${llmUsage.output_tokens} saída` : "não informado"}</dd>
    </dl></section>
    <section className="report-section"><h3>Fontes consultadas</h3>{(execution.evidence_sources || []).map((source) => <a className="source" href={source} target="_blank" key={source}>{source}</a>)}{!execution.evidence_sources?.length && <Empty text="Nenhuma fonte registrada." />}</section>
  </article>;
}

function Empty({ text = "Nenhum registro encontrado para este projeto." }) {
  return <p className="empty">{text}</p>;
}

createRoot(document.getElementById("root")).render(<App />);
