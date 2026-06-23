<svelte:options customElement="profile-town-queries" />

<script lang="ts">
  let {
    "actor-id": actorId,
    "is-own-profile": _isOwnProfile,
  } = $props<{
    "actor-id": string;
    "is-own-profile"?: string;
  }>();

  interface Query {
    id: string;
    database_name: string;
    title: string;
    description: string;
    updated_at: string;
    updated_duration_seconds: number;
  }

  let queries = $state<Query[]>([]);
  let loading = $state(true);

  function timeAgo(seconds: number): string {
    if (seconds < 60) return "just now";
    if (seconds < 3600) return Math.floor(seconds / 60) + "m ago";
    if (seconds < 86400) return Math.floor(seconds / 3600) + "h ago";
    return Math.floor(seconds / 86400) + "d ago";
  }

  $effect(() => {
    const params = new URLSearchParams();
    params.set("actorId", actorId);
    fetch(`/-/town/api/profile_queries?${params}`, { credentials: "include" })
      .then((r) => r.json())
      .then((data) => {
        queries = data.data || [];
        loading = false;
      })
      .catch(() => {
        loading = false;
      });
  });
</script>

{#if loading}
  <p class="empty">Loading...</p>
{:else if queries.length === 0}
  <p class="empty">No saved queries yet.</p>
{:else}
  <div class="query-list">
    {#each queries.slice(0, 20) as q}
      <div class="query-item">
        <a
          href={"/" + q.database_name + "/-/town/q/" + q.id}
          class="query-title"
        >
          {q.title || "Untitled"}
        </a>
        <span class="query-db">{q.database_name}</span>
        {#if q.description}
          <div class="query-desc">{q.description}</div>
        {/if}
        <div class="query-meta">
          {timeAgo(q.updated_duration_seconds)}
        </div>
      </div>
    {/each}
  </div>
{/if}

<style>
  .empty {
    color: #888;
    font-size: 0.9rem;
    margin: 0;
  }
  .query-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .query-item {
    border-bottom: 1px solid #eee;
    padding-bottom: 8px;
  }
  .query-title {
    font-weight: 600;
    color: #333;
    font-size: 0.9rem;
  }
  .query-db {
    color: #999;
    font-size: 0.8rem;
    margin-left: 8px;
  }
  .query-desc {
    font-size: 0.85rem;
    color: #666;
    margin-top: 2px;
  }
  .query-meta {
    font-size: 0.8rem;
    color: #999;
    margin-top: 2px;
  }
</style>
