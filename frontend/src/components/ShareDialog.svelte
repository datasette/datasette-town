<script lang="ts">
  import { appState } from "../store.svelte";

  interface Share {
    id: string;
    query_id: string;
    actor_id: string;
    can_edit: boolean;
    created_at: string;
  }

  interface Props {
    queryId: string;
    shares: Share[];
    open: boolean;
    onclose: () => void;
    onadd: (actorId: string, canEdit: boolean) => Promise<void>;
    onremove: (shareId: string) => Promise<void>;
    ontoggle: (shareId: string, canEdit: boolean) => Promise<void>;
  }

  let { queryId, shares, open, onclose, onadd, onremove, ontoggle }: Props =
    $props();

  let newActorId = $state("");
  let newCanEdit = $state(false);
  let adding = $state(false);

  async function handleAdd() {
    if (!newActorId.trim()) return;
    adding = true;
    await onadd(newActorId.trim(), newCanEdit);
    newActorId = "";
    newCanEdit = false;
    adding = false;
  }
</script>

{#if open}
  <div class="overlay" onclick={onclose} onkeydown={() => {}}>
    <div
      class="dialog"
      onclick={(e) => e.stopPropagation()}
      onkeydown={() => {}}
    >
      <h3>Share Query</h3>

      {#if shares.length > 0}
        <table>
          <thead>
            <tr>
              <th>Actor</th>
              <th>Can Edit</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {#each shares as share}
              <tr>
                <td>{share.actor_id}</td>
                <td>
                  <input
                    type="checkbox"
                    checked={share.can_edit}
                    onchange={() => ontoggle(share.id, !share.can_edit)}
                  />
                </td>
                <td>
                  <button class="remove-btn" onclick={() => onremove(share.id)}>
                    Remove
                  </button>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      {:else}
        <p class="empty">Not shared with anyone yet.</p>
      {/if}

      <div class="add-form">
        <h4>Add share</h4>
        <div class="form-row">
          <input
            type="text"
            placeholder="Actor ID"
            bind:value={newActorId}
            onkeydown={(e) => e.key === "Enter" && handleAdd()}
          />
          <label>
            <input type="checkbox" bind:checked={newCanEdit} />
            Can edit
          </label>
          <button onclick={handleAdd} disabled={adding || !newActorId.trim()}>
            Add
          </button>
        </div>
      </div>

      <div class="actions">
        <button onclick={onclose}>Close</button>
      </div>
    </div>
  </div>
{/if}

<style>
  .overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.4);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
  }
  .dialog {
    background: white;
    border-radius: 8px;
    padding: 1.5rem;
    min-width: 400px;
    max-width: 600px;
    box-shadow: 0 4px 24px rgba(0, 0, 0, 0.2);
  }
  h3 {
    margin-top: 0;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 1rem;
  }
  th,
  td {
    padding: 6px 8px;
    text-align: left;
    border-bottom: 1px solid #eee;
  }
  .remove-btn {
    color: #c00;
    background: none;
    border: 1px solid #c00;
    border-radius: 3px;
    cursor: pointer;
    padding: 2px 8px;
    font-size: 0.85em;
  }
  .empty {
    color: #888;
    font-style: italic;
  }
  .add-form {
    border-top: 1px solid #eee;
    padding-top: 1rem;
  }
  .add-form h4 {
    margin: 0 0 0.5rem 0;
  }
  .form-row {
    display: flex;
    gap: 0.5rem;
    align-items: center;
  }
  .form-row input[type="text"] {
    flex: 1;
    padding: 6px 8px;
    border: 1px solid #ccc;
    border-radius: 4px;
  }
  .actions {
    margin-top: 1rem;
    text-align: right;
  }
</style>
