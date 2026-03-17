<script lang="ts">
  import { loadPageData } from "../../page_data/load";
  import { appState } from "../../store.svelte";
  import type { TownListPageData } from "../../page_data/TownListPageData.types";

  const pageData = loadPageData<TownListPageData>();
  const db = appState.selectedDatabase;

  let myQueries = $state([...(pageData.my_queries ?? [])]);
  let sharedQueries = $state([...(pageData.shared_queries ?? [])]);
  let publicQueries = $state([...(pageData.public_queries ?? [])]);

  function sqlPreview(sql: string): string {
    const trimmed = sql.trim();
    return trimmed.length > 120 ? trimmed.substring(0, 120) + "…" : trimmed;
  }
</script>

<div class="town-list">
  <div class="header">
    <h2>Town</h2>
    <a href="/{db}/-/town/new" class="btn btn-primary">New Query</a>
  </div>

  {#if myQueries.length > 0}
    <section>
      <h3>My Queries</h3>
      <div class="query-list">
        {#each myQueries as q}
          <a href="/{db}/-/town/q/{q.id}" class="query-card">
            <div class="query-title">{q.title || "Untitled"}</div>
            <div class="query-sql">{sqlPreview(q.sql)}</div>
            <div class="query-meta">
              {#if q.is_public}<span class="badge public">Public</span>{/if}
              <span class="timestamp">{q.updated_at}</span>
            </div>
          </a>
        {/each}
      </div>
    </section>
  {/if}

  {#if sharedQueries.length > 0}
    <section>
      <h3>Shared with Me</h3>
      <div class="query-list">
        {#each sharedQueries as q}
          <a href="/{db}/-/town/q/{q.id}" class="query-card">
            <div class="query-title">{q.title || "Untitled"}</div>
            <div class="query-sql">{sqlPreview(q.sql)}</div>
            <div class="query-meta">
              <span class="badge shared">by {q.actor_id}</span>
              {#if q.can_edit}<span class="badge edit">Can edit</span>{/if}
              <span class="timestamp">{q.updated_at}</span>
            </div>
          </a>
        {/each}
      </div>
    </section>
  {/if}

  {#if publicQueries.length > 0}
    <section>
      <h3>Public Queries</h3>
      <div class="query-list">
        {#each publicQueries as q}
          <a href="/{db}/-/town/q/{q.id}" class="query-card">
            <div class="query-title">{q.title || "Untitled"}</div>
            <div class="query-sql">{sqlPreview(q.sql)}</div>
            <div class="query-meta">
              <span class="badge shared">by {q.actor_id}</span>
              <span class="timestamp">{q.updated_at}</span>
            </div>
          </a>
        {/each}
      </div>
    </section>
  {/if}

  {#if myQueries.length === 0 && sharedQueries.length === 0 && publicQueries.length === 0}
    <p class="empty">No queries yet. <a href="/{db}/-/town/new">Create one</a>.</p>
  {/if}
</div>

<style>
  .town-list {
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
  .btn {
    display: inline-block;
    padding: 8px 16px;
    border-radius: 4px;
    text-decoration: none;
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
  section {
    margin-bottom: 2rem;
  }
  h3 {
    margin-bottom: 0.75rem;
    color: #333;
  }
  .query-list {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }
  .query-card {
    display: block;
    padding: 12px 16px;
    border: 1px solid #e5e7eb;
    border-radius: 6px;
    text-decoration: none;
    color: inherit;
    transition: border-color 0.15s;
  }
  .query-card:hover {
    border-color: #2563eb;
  }
  .query-title {
    font-weight: 600;
    margin-bottom: 4px;
  }
  .query-sql {
    font-family: monospace;
    font-size: 0.85em;
    color: #666;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .query-meta {
    margin-top: 6px;
    font-size: 0.8em;
    color: #888;
    display: flex;
    gap: 8px;
    align-items: center;
  }
  .badge {
    padding: 1px 6px;
    border-radius: 3px;
    font-size: 0.85em;
  }
  .badge.public {
    background: #dcfce7;
    color: #166534;
  }
  .badge.shared {
    background: #dbeafe;
    color: #1e40af;
  }
  .badge.edit {
    background: #fef3c7;
    color: #92400e;
  }
  .empty {
    color: #888;
    text-align: center;
    padding: 2rem;
  }
</style>
