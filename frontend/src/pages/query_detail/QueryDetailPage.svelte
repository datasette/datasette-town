<script lang="ts">
  import { loadPageData } from "../../page_data/load";
  import { appState } from "../../store.svelte";
  import SqlEditor from "../../components/SqlEditor.svelte";
  import QueryResults from "../../components/QueryResults.svelte";
  import ShareDialog from "../../components/ShareDialog.svelte";
  import type { QueryDetailPageData } from "../../page_data/QueryDetailPageData.types";

  const pageData = loadPageData<QueryDetailPageData>();
  const db = appState.selectedDatabase;

  let query = $state({ ...pageData.query });
  let shares = $state([...(pageData.shares ?? [])]);
  let isOwner = pageData.is_owner;
  let canEdit = pageData.can_edit;

  let editing = $state(false);
  let saving = $state(false);
  let error: string | null = $state(null);

  // Edit state
  let editTitle = $state(query.title);
  let editDescription = $state(query.description);
  let editSql = $state(query.sql);
  let editIsPublic = $state(query.is_public);

  // Execute state
  let columns: string[] = $state([]);
  let rows: unknown[][] = $state([]);
  let execError: string | null = $state(null);
  let execLoading = $state(false);
  let truncated = $state(false);

  // Share dialog
  let shareOpen = $state(false);

  function startEdit() {
    editTitle = query.title;
    editDescription = query.description;
    editSql = query.sql;
    editIsPublic = query.is_public;
    editing = true;
  }

  function cancelEdit() {
    editing = false;
  }

  async function handleSave() {
    saving = true;
    error = null;
    try {
      const res = await fetch(`/${db}/-/api/town/queries/${query.id}/update`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: editTitle,
          description: editDescription,
          sql: editSql,
          is_public: editIsPublic,
        }),
      });
      const data = await res.json();
      if (data.ok) {
        query.title = editTitle;
        query.description = editDescription;
        query.sql = editSql;
        query.is_public = editIsPublic;
        editing = false;
      } else {
        error = data.error || "Failed to save";
      }
    } catch (e) {
      error = String(e);
    } finally {
      saving = false;
    }
  }

  async function handleDelete() {
    if (!confirm("Delete this query?")) return;
    try {
      const res = await fetch(`/${db}/-/api/town/queries/${query.id}/delete`, {
        method: "POST",
      });
      const data = await res.json();
      if (data.ok) {
        window.location.href = `/${db}/-/town`;
      } else {
        error = data.error || "Failed to delete";
      }
    } catch (e) {
      error = String(e);
    }
  }

  async function handleExecute() {
    execLoading = true;
    execError = null;
    try {
      const res = await fetch(
        `/${db}/-/api/town/queries/${query.id}/execute`,
        { method: "POST" },
      );
      const data = await res.json();
      columns = data.columns ?? [];
      rows = data.rows ?? [];
      truncated = data.truncated ?? false;
      execError = data.error ?? null;
    } catch (e) {
      execError = String(e);
    } finally {
      execLoading = false;
    }
  }

  async function handleAddShare(actorId: string, canEdit: boolean) {
    const res = await fetch(
      `/${db}/-/api/town/queries/${query.id}/shares/add`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ actor_id: actorId, can_edit: canEdit }),
      },
    );
    const data = await res.json();
    if (data.ok) {
      shares = [
        ...shares,
        {
          id: data.id,
          query_id: query.id,
          actor_id: actorId,
          can_edit: canEdit,
          created_at: new Date().toISOString(),
        },
      ];
    }
  }

  async function handleRemoveShare(shareId: string) {
    const res = await fetch(
      `/${db}/-/api/town/queries/${query.id}/shares/${shareId}/remove`,
      { method: "POST" },
    );
    const data = await res.json();
    if (data.ok) {
      shares = shares.filter((s) => s.id !== shareId);
    }
  }

  async function handleToggleShare(shareId: string, canEdit: boolean) {
    const res = await fetch(
      `/${db}/-/api/town/queries/${query.id}/shares/${shareId}/update`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ can_edit: canEdit }),
      },
    );
    const data = await res.json();
    if (data.ok) {
      shares = shares.map((s) => (s.id === shareId ? { ...s, can_edit: canEdit } : s));
    }
  }
</script>

<div class="query-detail">
  <div class="header">
    <a href="/{db}/-/town" class="back-link">← Back to Town</a>
  </div>

  {#if error}
    <div class="error-banner">{error}</div>
  {/if}

  {#if editing}
    <div class="form">
      <div class="field">
        <label for="title">Title</label>
        <input id="title" type="text" bind:value={editTitle} />
      </div>
      <div class="field">
        <label for="desc">Description</label>
        <textarea id="desc" bind:value={editDescription} rows="2"></textarea>
      </div>
      <div class="field">
        <label>SQL</label>
        <SqlEditor bind:value={editSql} onexecute={handleExecute} />
      </div>
      <div class="field-row">
        <label class="checkbox-label">
          <input type="checkbox" bind:checked={editIsPublic} />
          Public
        </label>
      </div>
      <div class="actions">
        <button class="btn btn-secondary" onclick={cancelEdit}>Cancel</button>
        <button class="btn btn-primary" onclick={handleSave} disabled={saving}>
          {saving ? "Saving..." : "Save"}
        </button>
      </div>
    </div>
  {:else}
    <div class="view">
      <div class="title-row">
        <h2>{query.title || "Untitled"}</h2>
        <div class="title-actions">
          {#if canEdit}
            <button class="btn btn-secondary" onclick={startEdit}>Edit</button>
          {/if}
          {#if isOwner}
            <button class="btn btn-secondary" onclick={() => (shareOpen = true)}>Share</button>
            <button class="btn btn-danger" onclick={handleDelete}>Delete</button>
          {/if}
        </div>
      </div>

      {#if query.description}
        <p class="description">{query.description}</p>
      {/if}

      <div class="meta">
        <span>by {query.actor_id}</span>
        {#if query.is_public}<span class="badge public">Public</span>{/if}
        <span class="timestamp">Updated {query.updated_at}</span>
      </div>

      <div class="sql-section">
        <SqlEditor value={query.sql} readonly={true} onexecute={handleExecute} />
      </div>

      <div class="execute-row">
        <button class="btn btn-primary" onclick={handleExecute} disabled={execLoading}>
          {execLoading ? "Running..." : "Execute"}
        </button>
      </div>
    </div>
  {/if}

  <QueryResults {columns} {rows} error={execError} loading={execLoading} {truncated} />

  <ShareDialog
    queryId={query.id}
    {shares}
    open={shareOpen}
    onclose={() => (shareOpen = false)}
    onadd={handleAddShare}
    onremove={handleRemoveShare}
    ontoggle={handleToggleShare}
  />
</div>

<style>
  .query-detail {
    max-width: 800px;
    margin: 0 auto;
  }
  .header {
    margin-bottom: 1rem;
  }
  .back-link {
    color: #2563eb;
    text-decoration: none;
  }
  .title-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.5rem;
  }
  .title-row h2 {
    margin: 0;
  }
  .title-actions {
    display: flex;
    gap: 0.5rem;
  }
  .description {
    color: #555;
    margin: 0 0 1rem 0;
  }
  .meta {
    display: flex;
    gap: 12px;
    align-items: center;
    font-size: 0.85em;
    color: #888;
    margin-bottom: 1rem;
  }
  .badge.public {
    background: #dcfce7;
    color: #166534;
    padding: 1px 6px;
    border-radius: 3px;
  }
  .sql-section {
    margin-bottom: 1rem;
  }
  .execute-row {
    margin-bottom: 1rem;
  }
  .form {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }
  .field {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .field label {
    font-weight: 600;
    font-size: 0.9em;
  }
  .field input[type="text"],
  .field textarea {
    padding: 8px 10px;
    border: 1px solid #ccc;
    border-radius: 4px;
    font-size: 14px;
  }
  .field-row {
    display: flex;
    align-items: center;
  }
  .checkbox-label {
    display: flex;
    align-items: center;
    gap: 6px;
    cursor: pointer;
  }
  .actions {
    display: flex;
    gap: 0.5rem;
    justify-content: flex-end;
  }
  .btn {
    padding: 8px 16px;
    border-radius: 4px;
    font-size: 14px;
    cursor: pointer;
    border: none;
  }
  .btn-primary {
    background: #2563eb;
    color: white;
  }
  .btn-primary:hover {
    background: #1d4ed8;
  }
  .btn-secondary {
    background: #f3f4f6;
    color: #374151;
    border: 1px solid #d1d5db;
  }
  .btn-secondary:hover {
    background: #e5e7eb;
  }
  .btn-danger {
    background: #fee2e2;
    color: #991b1b;
    border: 1px solid #fca5a5;
  }
  .btn-danger:hover {
    background: #fecaca;
  }
  .btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  .error-banner {
    background: #fff0f0;
    color: #c00;
    border: 1px solid #fcc;
    padding: 8px 12px;
    border-radius: 4px;
    margin-bottom: 1rem;
  }
</style>
