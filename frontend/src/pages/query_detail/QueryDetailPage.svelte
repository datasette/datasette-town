<script lang="ts">
  import { loadPageData } from "../../page_data/load";
  import { appState } from "../../store.svelte";
  import { client } from "../../api";
  import SqlEditor from "../../components/SqlEditor.svelte";
  import QueryResults from "../../components/QueryResults.svelte";
  import ShareDialog from "../../components/ShareDialog.svelte";
  import Timestamp from "../../components/Timestamp.svelte";
  import type { QueryDetailPageData } from "../../page_data/QueryDetailPageData.types";

  const pageData = loadPageData<QueryDetailPageData>();
  const db = appState.selectedDatabase;

  let query = $state({ ...pageData.query });
  let shares = $state([...(pageData.shares ?? [])]);
  let isOwner = pageData.is_owner;
  let canEdit = pageData.can_edit;

  let error: string | null = $state(null);

  // Inline editing state
  let editingTitle = $state(false);
  let editingDescription = $state(false);
  let editingSql = $state(false);
  let editTitle = $state(query.title);
  let editDescription = $state(query.description);
  let editSql = $state(query.sql);

  // Execute state
  let columns: string[] = $state([]);
  let rows: unknown[][] = $state([]);
  let execError: string | null = $state(null);
  let execLoading = $state(false);
  let truncated = $state(false);

  // Share dialog
  let shareOpen = $state(false);

  // Three-dot menu
  let menuOpen = $state(false);

  const pathParams = { database: db, query_id: query.id };

  async function patchField(fields: Record<string, any>) {
    try {
      const { data } = await client.POST(
        "/{database}/-/api/town/queries/{query_id}/patch",
        {
          params: { path: pathParams },
          body: fields,
          parseAs: "json",
        },
      );
      if ((data as any)?.ok) {
        Object.assign(query, fields);
        return true;
      } else {
        error = (data as any)?.error || "Failed to save";
        return false;
      }
    } catch (e) {
      error = String(e);
      return false;
    }
  }

  async function saveTitle() {
    if (await patchField({ title: editTitle })) {
      editingTitle = false;
    }
  }

  async function saveDescription() {
    if (await patchField({ description: editDescription })) {
      editingDescription = false;
    }
  }

  async function saveSql() {
    if (await patchField({ sql: editSql })) {
      editingSql = false;
    }
  }

  function startEditTitle() {
    editTitle = query.title;
    editingTitle = true;
  }

  function startEditDescription() {
    editDescription = query.description;
    editingDescription = true;
  }

  function startEditSql() {
    editSql = query.sql;
    editingSql = true;
  }

  async function handleDelete() {
    if (!confirm("Delete this query?")) return;
    menuOpen = false;
    try {
      const { data } = await client.POST(
        "/{database}/-/api/town/queries/{query_id}/delete",
        {
          params: { path: pathParams },
          parseAs: "json",
        },
      );
      if ((data as any)?.ok) {
        window.location.href = `/${db}/-/town`;
      } else {
        error = (data as any)?.error || "Failed to delete";
      }
    } catch (e) {
      error = String(e);
    }
  }

  async function handleExecute() {
    const sqlToRun = editingSql ? editSql : query.sql;
    execLoading = true;
    execError = null;
    try {
      const url = `/${db}/-/query.json?sql=${encodeURIComponent(sqlToRun)}`;
      const res = await fetch(url);
      const d = await res.json();
      if (!d.ok) {
        execError = d.error ?? "Query failed";
        columns = [];
        rows = [];
        truncated = false;
      } else {
        const rowObjects: Record<string, unknown>[] = d.rows ?? [];
        columns = rowObjects[0] ? Object.keys(rowObjects[0]) : [];
        rows = rowObjects.map((r) => columns.map((c) => r[c]));
        truncated = d.truncated ?? false;
        execError = null;
      }
    } catch (e) {
      execError = String(e);
    } finally {
      execLoading = false;
    }
  }

  async function handleAddShare(actorId: string, canEdit: boolean) {
    const { data } = await client.POST(
      "/{database}/-/api/town/queries/{query_id}/shares/add",
      {
        params: { path: pathParams },
        body: { actor_id: actorId, can_edit: canEdit },
        parseAs: "json",
      },
    );
    if ((data as any)?.ok) {
      shares = [
        ...shares,
        {
          id: (data as any).id,
          query_id: query.id,
          actor_id: actorId,
          can_edit: canEdit,
          created_at: new Date().toISOString(),
        },
      ];
    }
  }

  async function handleRemoveShare(shareId: string) {
    const { data } = await client.POST(
      "/{database}/-/api/town/queries/{query_id}/shares/{share_id}/remove",
      {
        params: { path: { ...pathParams, share_id: shareId } },
        parseAs: "json",
      },
    );
    if ((data as any)?.ok) {
      shares = shares.filter((s) => s.id !== shareId);
    }
  }

  async function handleToggleShare(shareId: string, canEdit: boolean) {
    const { data } = await client.POST(
      "/{database}/-/api/town/queries/{query_id}/shares/{share_id}/update",
      {
        params: { path: { ...pathParams, share_id: shareId } },
        body: { can_edit: canEdit },
        parseAs: "json",
      },
    );
    if ((data as any)?.ok) {
      shares = shares.map((s) =>
        s.id === shareId ? { ...s, can_edit: canEdit } : s,
      );
    }
  }

  async function handlePublicChange(newIsPublic: boolean) {
    await patchField({ is_public: newIsPublic });
  }
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="query-detail" onclick={() => (menuOpen = false)}>
  <div class="header">
    <a href="/{db}/-/town" class="back-link">&larr; Back to Town</a>
  </div>

  {#if error}
    <div class="error-banner">{error}</div>
  {/if}

  <div class="title-row">
    {#if editingTitle}
      <input
        class="inline-edit inline-edit-title"
        type="text"
        bind:value={editTitle}
        onkeydown={(e) => {
          if (e.key === "Enter") saveTitle();
          if (e.key === "Escape") editingTitle = false;
        }}
        autofocus
        onblur={saveTitle}
      />
    {:else}
      <h2>
        {query.title || "Untitled"}
        {#if canEdit}
          <button class="icon-btn" onclick={startEditTitle} title="Edit title">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="14"
              height="14"
              fill="currentColor"
              viewBox="0 0 16 16"
              ><path
                d="M12.854.146a.5.5 0 0 0-.707 0L10.5 1.793 14.207 5.5l1.647-1.646a.5.5 0 0 0 0-.708zm.646 6.061L9.793 2.5 3.293 9H3.5a.5.5 0 0 1 .5.5v.5h.5a.5.5 0 0 1 .5.5v.5h.5a.5.5 0 0 1 .5.5v.5h.5a.5.5 0 0 1 .5.5v.207zm-7.468 7.468A.5.5 0 0 1 6 13.5V13h-.5a.5.5 0 0 1-.5-.5V12h-.5a.5.5 0 0 1-.5-.5V11h-.5a.5.5 0 0 1-.5-.5V10h-.5a.5.5 0 0 1-.175-.032l-.179.178a.5.5 0 0 0-.11.168l-2 5a.5.5 0 0 0 .65.65l5-2a.5.5 0 0 0 .168-.11z"
              /></svg
            >
          </button>
        {/if}
      </h2>
    {/if}
    <div class="title-actions">
      {#if isOwner}
        <button class="btn btn-secondary" onclick={() => (shareOpen = true)}
          >Share</button
        >
        <div class="menu-container">
          <button
            class="icon-btn menu-trigger"
            onclick={(e) => {
              e.stopPropagation();
              menuOpen = !menuOpen;
            }}
            title="More actions"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="18"
              height="18"
              fill="currentColor"
              viewBox="0 0 16 16"
              ><path
                d="M9.5 13a1.5 1.5 0 1 1-3 0 1.5 1.5 0 0 1 3 0m0-5a1.5 1.5 0 1 1-3 0 1.5 1.5 0 0 1 3 0m0-5a1.5 1.5 0 1 1-3 0 1.5 1.5 0 0 1 3 0"
              /></svg
            >
          </button>
          {#if menuOpen}
            <!-- svelte-ignore a11y_no_static_element_interactions -->
            <div class="dropdown-menu" onclick={(e) => e.stopPropagation()}>
              <button class="dropdown-item danger" onclick={handleDelete}
                >Delete query</button
              >
            </div>
          {/if}
        </div>
      {/if}
    </div>
  </div>

  <div class="description-row">
    {#if editingDescription}
      <textarea
        class="inline-edit"
        bind:value={editDescription}
        rows="2"
        onkeydown={(e) => {
          if (e.key === "Escape") editingDescription = false;
        }}
        autofocus
        onblur={saveDescription}
      ></textarea>
    {:else}
      <p class="description">
        {query.description || "No description"}
        {#if canEdit}
          <button
            class="icon-btn"
            onclick={startEditDescription}
            title="Edit description"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="12"
              height="12"
              fill="currentColor"
              viewBox="0 0 16 16"
              ><path
                d="M12.854.146a.5.5 0 0 0-.707 0L10.5 1.793 14.207 5.5l1.647-1.646a.5.5 0 0 0 0-.708zm.646 6.061L9.793 2.5 3.293 9H3.5a.5.5 0 0 1 .5.5v.5h.5a.5.5 0 0 1 .5.5v.5h.5a.5.5 0 0 1 .5.5v.5h.5a.5.5 0 0 1 .5.5v.207zm-7.468 7.468A.5.5 0 0 1 6 13.5V13h-.5a.5.5 0 0 1-.5-.5V12h-.5a.5.5 0 0 1-.5-.5V11h-.5a.5.5 0 0 1-.5-.5V10h-.5a.5.5 0 0 1-.175-.032l-.179.178a.5.5 0 0 0-.11.168l-2 5a.5.5 0 0 0 .65.65l5-2a.5.5 0 0 0 .168-.11z"
              /></svg
            >
          </button>
        {/if}
      </p>
    {/if}
  </div>

  <div class="meta">
    <a class="author" href="/-/profile/{query.actor_id}">
      <img
        class="meta-avatar"
        src="/-/profile/pic/{query.actor_id}"
        alt={query.actor_id}
      />
      by {query.actor_id}
    </a>
    {#if query.is_public}<span class="badge public">Public</span>{/if}
    <span class="timestamp"
      ><Timestamp value={query.updated_at} prefix="Updated " /></span
    >
  </div>

  <div class="sql-section">
    {#if editingSql}
      <SqlEditor bind:value={editSql} onexecute={handleExecute} />
      <div class="sql-edit-actions">
        <button
          class="btn btn-sm btn-secondary"
          onclick={() => (editingSql = false)}>Cancel</button
        >
        <button class="btn btn-sm btn-primary" onclick={saveSql}>Save</button>
      </div>
    {:else}
      <div class="sql-view">
        <SqlEditor
          value={query.sql}
          readonly={true}
          onexecute={handleExecute}
        />
        {#if canEdit}
          <button
            class="icon-btn sql-edit-btn"
            onclick={startEditSql}
            title="Edit SQL"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="14"
              height="14"
              fill="currentColor"
              viewBox="0 0 16 16"
              ><path
                d="M12.854.146a.5.5 0 0 0-.707 0L10.5 1.793 14.207 5.5l1.647-1.646a.5.5 0 0 0 0-.708zm.646 6.061L9.793 2.5 3.293 9H3.5a.5.5 0 0 1 .5.5v.5h.5a.5.5 0 0 1 .5.5v.5h.5a.5.5 0 0 1 .5.5v.5h.5a.5.5 0 0 1 .5.5v.207zm-7.468 7.468A.5.5 0 0 1 6 13.5V13h-.5a.5.5 0 0 1-.5-.5V12h-.5a.5.5 0 0 1-.5-.5V11h-.5a.5.5 0 0 1-.5-.5V10h-.5a.5.5 0 0 1-.175-.032l-.179.178a.5.5 0 0 0-.11.168l-2 5a.5.5 0 0 0 .65.65l5-2a.5.5 0 0 0 .168-.11z"
              /></svg
            >
          </button>
        {/if}
      </div>
    {/if}
  </div>

  <div class="execute-row">
    <button
      class="btn btn-primary"
      onclick={handleExecute}
      disabled={execLoading}
    >
      {execLoading ? "Running..." : "Execute"}
    </button>
  </div>

  <QueryResults
    {columns}
    {rows}
    error={execError}
    loading={execLoading}
    {truncated}
  />

  <ShareDialog
    {shares}
    open={shareOpen}
    isPublic={query.is_public}
    onclose={() => (shareOpen = false)}
    onadd={handleAddShare}
    onremove={handleRemoveShare}
    ontoggle={handleToggleShare}
    onpublicchange={handlePublicChange}
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
    margin-bottom: 0.25rem;
    gap: 8px;
  }
  .title-row h2 {
    margin: 0;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .title-actions {
    display: flex;
    gap: 0.5rem;
    align-items: center;
    flex-shrink: 0;
  }
  .inline-edit {
    font-size: 14px;
    padding: 6px 10px;
    border: 1px solid #2563eb;
    border-radius: 4px;
    outline: none;
    width: 100%;
    box-sizing: border-box;
  }
  .inline-edit-title {
    font-size: 1.5em;
    font-weight: 600;
    flex: 1;
  }
  .inline-edit:focus {
    box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.15);
  }
  textarea.inline-edit {
    resize: vertical;
    font-family: inherit;
  }

  /* Icon button */
  .icon-btn {
    background: none;
    border: none;
    cursor: pointer;
    padding: 4px;
    border-radius: 4px;
    color: #9ca3af;
    display: inline-flex;
    align-items: center;
    line-height: 1;
  }
  .icon-btn:hover {
    background: #f3f4f6;
    color: #4b5563;
  }

  /* Three-dot menu */
  .menu-container {
    position: relative;
  }
  .menu-trigger {
    padding: 6px;
  }
  .dropdown-menu {
    position: absolute;
    right: 0;
    top: 100%;
    margin-top: 4px;
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
    min-width: 160px;
    z-index: 100;
    padding: 4px;
  }
  .dropdown-item {
    display: block;
    width: 100%;
    text-align: left;
    padding: 8px 12px;
    border: none;
    background: none;
    cursor: pointer;
    font-size: 14px;
    border-radius: 4px;
    color: #374151;
  }
  .dropdown-item:hover {
    background: #f3f4f6;
  }
  .dropdown-item.danger {
    color: #dc2626;
  }
  .dropdown-item.danger:hover {
    background: #fef2f2;
  }

  .description-row {
    margin-bottom: 0.5rem;
  }
  .description {
    color: #6b7280;
    margin: 0;
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .meta {
    display: flex;
    gap: 12px;
    align-items: center;
    font-size: 0.85em;
    color: #888;
    margin-bottom: 1rem;
  }
  .author {
    display: flex;
    align-items: center;
    gap: 6px;
    text-decoration: none;
    color: inherit;
  }
  .author:hover {
    text-decoration: underline;
  }
  .meta-avatar {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    object-fit: cover;
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
  .sql-view {
    position: relative;
  }
  .sql-edit-btn {
    position: absolute;
    top: 8px;
    right: 8px;
    z-index: 10;
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 4px;
    padding: 4px 6px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  }
  .sql-edit-btn:hover {
    background: #f3f4f6;
    border-color: #d1d5db;
  }
  .sql-edit-actions {
    display: flex;
    gap: 0.5rem;
    justify-content: flex-end;
    margin-top: 8px;
  }
  .execute-row {
    margin-bottom: 1rem;
  }
  .btn {
    padding: 8px 16px;
    border-radius: 4px;
    font-size: 14px;
    cursor: pointer;
    border: none;
  }
  .btn-sm {
    padding: 5px 12px;
    font-size: 13px;
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
