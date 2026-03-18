<script lang="ts">
  import { loadPageData } from "../../page_data/load";
  import { appState } from "../../store.svelte";
  import Timestamp from "../../components/Timestamp.svelte";
  import type { TownListPageData } from "../../page_data/TownListPageData.types";

  const pageData = loadPageData<TownListPageData>();
  const db = appState.selectedDatabase;

  let myQueries = $state([...(pageData.my_queries ?? [])]);
  let sharedQueries = $state([...(pageData.shared_queries ?? [])]);
  let publicQueries = $state([...(pageData.public_queries ?? [])]);

  let search = $state("");

  function matches(q: { title: string; description: string }): boolean {
    if (!search.trim()) return true;
    const term = search.trim().toLowerCase();
    return (
      q.title.toLowerCase().includes(term) ||
      q.description.toLowerCase().includes(term)
    );
  }

  let filteredMy = $derived(myQueries.filter(matches));
  let filteredShared = $derived(sharedQueries.filter(matches));
  let filteredPublic = $derived(publicQueries.filter(matches));

  function sqlLines(sql: string): string {
    return sql.trim();
  }
</script>

<div class="town-list">
  <div class="header">
    <h2>Town</h2>
    <a href="/{db}/-/town/new" class="btn btn-primary">New Query</a>
  </div>

  <div class="search-bar">
    <input
      type="text"
      placeholder="Search queries..."
      bind:value={search}
    />
  </div>

  {#if filteredMy.length > 0}
    <section>
      <h3>My Queries</h3>
      <div class="query-grid">
        {#each filteredMy as q}
          <a href="/{db}/-/town/q/{q.id}" class="query-card">
            <pre class="card-sql">{sqlLines(q.sql)}</pre>
            <div class="card-body">
              <div class="card-title">{q.title || "Untitled"}</div>
              <div class="card-footer">
                <div class="author">
                  {#if q.actor_profile_picture_url}
                    <img class="avatar" src={q.actor_profile_picture_url} alt={q.actor_id} />
                  {:else}
                    <span class="avatar avatar-letter">{q.actor_id.charAt(0).toUpperCase()}</span>
                  {/if}
                  <span class="author-name">{q.actor_id}</span>
                </div>
                {#if q.is_public}<span class="badge public">Public</span>{/if}
                <span class="timestamp"><Timestamp value={q.updated_at} /></span>
              </div>
            </div>
          </a>
        {/each}
      </div>
    </section>
  {/if}

  {#if filteredShared.length > 0}
    <section>
      <h3>Shared with Me</h3>
      <div class="query-grid">
        {#each filteredShared as q}
          <a href="/{db}/-/town/q/{q.id}" class="query-card">
            <pre class="card-sql">{sqlLines(q.sql)}</pre>
            <div class="card-body">
              <div class="card-title">{q.title || "Untitled"}</div>
              <div class="card-footer">
                <div class="author">
                  {#if q.actor_profile_picture_url}
                    <img class="avatar" src={q.actor_profile_picture_url} alt={q.actor_id} />
                  {:else}
                    <span class="avatar avatar-letter">{q.actor_id.charAt(0).toUpperCase()}</span>
                  {/if}
                  <span class="author-name">{q.actor_id}</span>
                </div>
                {#if q.can_edit}<span class="badge edit">Can edit</span>{/if}
                <span class="timestamp"><Timestamp value={q.updated_at} /></span>
              </div>
            </div>
          </a>
        {/each}
      </div>
    </section>
  {/if}

  {#if filteredPublic.length > 0}
    <section>
      <h3>Public Queries</h3>
      <div class="query-grid">
        {#each filteredPublic as q}
          <a href="/{db}/-/town/q/{q.id}" class="query-card">
            <pre class="card-sql">{sqlLines(q.sql)}</pre>
            <div class="card-body">
              <div class="card-title">{q.title || "Untitled"}</div>
              <div class="card-footer">
                <div class="author">
                  {#if q.actor_profile_picture_url}
                    <img class="avatar" src={q.actor_profile_picture_url} alt={q.actor_id} />
                  {:else}
                    <span class="avatar avatar-letter">{q.actor_id.charAt(0).toUpperCase()}</span>
                  {/if}
                  <span class="author-name">{q.actor_id}</span>
                </div>
                <span class="timestamp"><Timestamp value={q.updated_at} /></span>
              </div>
            </div>
          </a>
        {/each}
      </div>
    </section>
  {/if}

  {#if filteredMy.length === 0 && filteredShared.length === 0 && filteredPublic.length === 0}
    {#if search.trim()}
      <p class="empty">No queries matching "{search.trim()}".</p>
    {:else}
      <p class="empty">No queries yet. <a href="/{db}/-/town/new">Create one</a>.</p>
    {/if}
  {/if}
</div>

<style>
  .town-list {
    max-width: 900px;
    margin: 0 auto;
  }
  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin: 0.5rem 0 1rem;
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
  .search-bar {
    margin-bottom: 1rem;
  }
  .search-bar input {
    width: 100%;
    padding: 10px 14px;
    border: 1px solid #dadce0;
    border-radius: 8px;
    font-size: 14px;
    outline: none;
    transition: border-color 0.15s;
    box-sizing: border-box;
  }
  .search-bar input:focus {
    border-color: #2563eb;
    box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.15);
  }
  .search-bar input::placeholder {
    color: #9ca3af;
  }
  section {
    margin-bottom: 1.25rem;
  }
  h3 {
    margin: 0 0 0.5rem 0;
    color: #1f1f1f;
    font-size: 16px;
    font-weight: 600;
  }
  .query-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 420px));
    gap: 12px;
  }
  .query-card {
    display: flex;
    flex-direction: column;
    max-width: 420px;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    text-decoration: none;
    color: inherit;
    transition: border-color 0.15s, box-shadow 0.15s;
    overflow: hidden;
  }
  .query-card:hover {
    border-color: #c7d2fe;
    box-shadow: 0 2px 8px rgba(37, 99, 235, 0.1);
  }
  .card-sql {
    font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
    font-size: 13px;
    color: #4b5563;
    line-height: 1.5;
    margin: 0;
    padding: 12px 16px;
    background: #f8f9fb;
    overflow: hidden;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    white-space: pre-wrap;
    word-break: break-all;
  }
  .card-body {
    padding: 12px 16px;
  }
  .card-title {
    font-weight: 600;
    font-size: 14px;
    color: #1f1f1f;
    margin-bottom: 6px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .card-footer {
    display: flex;
    gap: 8px;
    align-items: center;
    font-size: 13px;
    color: #9ca3af;
  }
  .author {
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .avatar {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    flex-shrink: 0;
    object-fit: cover;
  }
  .avatar-letter {
    display: flex;
    align-items: center;
    justify-content: center;
    background: #e8eaed;
    color: #5f6368;
    font-size: 11px;
    font-weight: 500;
  }
  .author-name {
    color: #6b7280;
  }
  .badge {
    padding: 1px 7px;
    border-radius: 3px;
    font-size: 12px;
    font-weight: 500;
  }
  .badge.public {
    background: #dcfce7;
    color: #166534;
  }
  .badge.edit {
    background: #fef3c7;
    color: #92400e;
  }
  .timestamp {
    margin-left: auto;
    white-space: nowrap;
  }
  .empty {
    color: #888;
    text-align: center;
    padding: 2rem;
  }
</style>
