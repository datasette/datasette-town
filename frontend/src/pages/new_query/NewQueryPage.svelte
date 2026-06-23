<script lang="ts">
  import { appState } from "../../store.svelte";
  import { client } from "../../api";
  import SqlEditor from "../../components/SqlEditor.svelte";
  import QueryResults from "../../components/QueryResults.svelte";

  const db = appState.selectedDatabase;

  let title = $state("");
  let description = $state("");
  let sqlValue = $state("");
  let saving = $state(false);
  let error: string | null = $state(null);

  // Preview results
  let previewColumns: string[] = $state([]);
  let previewRows: unknown[][] = $state([]);
  let previewError: string | null = $state(null);
  let previewLoading = $state(false);
  let previewTruncated = $state(false);

  async function handleSave() {
    saving = true;
    error = null;
    try {
      const { data } = await client.POST("/{database}/-/api/town/queries/new", {
        params: { path: { database: db } },
        body: { title, description, sql: sqlValue },
        parseAs: "json",
      });
      const d = data as any;
      if (d?.ok) {
        window.location.href = `/${db}/-/town/q/${d.id}`;
      } else {
        error = d?.error || "Failed to save";
      }
    } catch (e) {
      error = String(e);
    } finally {
      saving = false;
    }
  }

  async function handleExecutePreview() {
    if (!sqlValue.trim()) return;
    previewLoading = true;
    previewError = null;
    try {
      const url = `/${db}/-/query.json?sql=${encodeURIComponent(sqlValue)}`;
      const res = await fetch(url);
      const d = await res.json();
      if (!d.ok) {
        previewError = d.error ?? "Query failed";
        previewColumns = [];
        previewRows = [];
        previewTruncated = false;
      } else {
        const rowObjects: Record<string, unknown>[] = d.rows ?? [];
        previewColumns = rowObjects[0] ? Object.keys(rowObjects[0]) : [];
        previewRows = rowObjects.map((r) => previewColumns.map((c) => r[c]));
        previewTruncated = d.truncated ?? false;
        previewError = null;
      }
    } catch (e) {
      previewError = String(e);
    } finally {
      previewLoading = false;
    }
  }
</script>

<div class="new-query">
  <div class="header">
    <h2>New Query</h2>
    <a href="/{db}/-/town" class="back-link">← Back to Town</a>
  </div>

  {#if error}
    <div class="error-banner">{error}</div>
  {/if}

  <div class="form">
    <div class="field">
      <label for="title">Title</label>
      <input
        id="title"
        type="text"
        bind:value={title}
        placeholder="Query title"
      />
    </div>

    <div class="field">
      <label for="description">Description</label>
      <textarea
        id="description"
        bind:value={description}
        placeholder="Optional description"
        rows="2"
      ></textarea>
    </div>

    <div class="field">
      <!-- svelte-ignore a11y_label_has_associated_control -->
      <label>SQL</label>
      <SqlEditor bind:value={sqlValue} onexecute={handleExecutePreview} />
    </div>

    <div class="actions">
      <button
        class="btn btn-secondary"
        onclick={handleExecutePreview}
        disabled={!sqlValue.trim()}
      >
        Execute
      </button>
      <button class="btn btn-primary" onclick={handleSave} disabled={saving}>
        {saving ? "Saving..." : "Save"}
      </button>
    </div>
  </div>

  <QueryResults
    columns={previewColumns}
    rows={previewRows}
    error={previewError}
    loading={previewLoading}
    truncated={previewTruncated}
  />
</div>

<style>
  .new-query {
    max-width: 800px;
    margin: 0 auto;
  }
  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1.5rem;
  }
  .header h2 {
    margin: 0;
  }
  .back-link {
    color: #2563eb;
    text-decoration: none;
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
