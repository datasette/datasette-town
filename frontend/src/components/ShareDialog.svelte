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
    isPublic: boolean;
    onclose: () => void;
    onadd: (actorId: string, canEdit: boolean) => Promise<void>;
    onremove: (shareId: string) => Promise<void>;
    ontoggle: (shareId: string, canEdit: boolean) => Promise<void>;
    onpublicchange: (isPublic: boolean) => Promise<void>;
  }

  let {
    queryId,
    shares,
    open,
    isPublic,
    onclose,
    onadd,
    onremove,
    ontoggle,
    onpublicchange,
  }: Props = $props();

  let newActorId = $state("");
  let adding = $state(false);
  let copied = $state(false);

  async function handleAdd() {
    if (!newActorId.trim()) return;
    adding = true;
    await onadd(newActorId.trim(), false);
    newActorId = "";
    adding = false;
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === "Escape") onclose();
  }

  async function copyLink() {
    const url = window.location.href;
    await navigator.clipboard.writeText(url);
    copied = true;
    setTimeout(() => (copied = false), 2000);
  }

  function roleLabel(share: Share): string {
    return share.can_edit ? "Editor" : "Viewer";
  }
</script>

{#if open}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="overlay" onclick={onclose} onkeydown={handleKeydown}>
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="dialog" onclick={(e) => e.stopPropagation()} onkeydown={handleKeydown}>
      <div class="dialog-header">
        <h3>Share this query</h3>
      </div>

      <div class="add-section">
        <div class="add-row">
          <input
            type="text"
            class="actor-input"
            placeholder="Add people by actor ID"
            bind:value={newActorId}
            onkeydown={(e) => e.key === "Enter" && handleAdd()}
          />
          <button
            class="btn btn-primary"
            onclick={handleAdd}
            disabled={adding || !newActorId.trim()}
          >
            {adding ? "Adding..." : "Share"}
          </button>
        </div>
      </div>

      <div class="people-section">
        <h4>People with access</h4>

        <div class="person-list">
          {#each shares as share}
            <div class="person-row">
              <div class="person-info">
                <div class="avatar">{share.actor_id.charAt(0).toUpperCase()}</div>
                <span class="person-name">{share.actor_id}</span>
              </div>
              <div class="person-actions">
                <select
                  class="role-select"
                  value={roleLabel(share)}
                  onchange={(e) => {
                    const target = e.target as HTMLSelectElement;
                    const newCanEdit = target.value === "Editor";
                    if (newCanEdit !== share.can_edit) {
                      ontoggle(share.id, newCanEdit);
                    }
                  }}
                >
                  <option value="Viewer">Viewer</option>
                  <option value="Editor">Editor</option>
                </select>
                <button
                  class="remove-icon"
                  title="Remove access"
                  onclick={() => onremove(share.id)}
                >&#x2715;</button>
              </div>
            </div>
          {/each}

          {#if shares.length === 0}
            <p class="empty">Only you have access.</p>
          {/if}
        </div>
      </div>

      <div class="general-access">
        <h4>General access</h4>
        <div class="access-row">
          <div class="access-icon">{isPublic ? "🌐" : "🔒"}</div>
          <div class="access-info">
            <select
              class="access-select"
              value={isPublic ? "public" : "restricted"}
              onchange={(e) => {
                const target = e.target as HTMLSelectElement;
                onpublicchange(target.value === "public");
              }}
            >
              <option value="restricted">Restricted</option>
              <option value="public">Anyone with the link</option>
            </select>
            <span class="access-description">
              {isPublic ? "Anyone can view this query" : "Only people with access can open"}
            </span>
          </div>
        </div>
      </div>

      <div class="dialog-footer">
        <button class="btn btn-link-copy" onclick={copyLink}>
          {copied ? "Copied!" : "Copy link"}
        </button>
        <button class="btn btn-primary" onclick={onclose}>Done</button>
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
    border-radius: 12px;
    padding: 0;
    width: 480px;
    max-width: 90vw;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.24);
    overflow: hidden;
  }
  .dialog-header {
    padding: 20px 24px 0;
  }
  .dialog-header h3 {
    margin: 0;
    font-size: 18px;
    font-weight: 600;
    color: #1f1f1f;
  }

  /* Add people section */
  .add-section {
    padding: 16px 24px;
  }
  .add-row {
    display: flex;
    gap: 8px;
  }
  .actor-input {
    flex: 1;
    padding: 10px 14px;
    border: 1px solid #dadce0;
    border-radius: 8px;
    font-size: 14px;
    outline: none;
    transition: border-color 0.15s;
  }
  .actor-input:focus {
    border-color: #2563eb;
    box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.15);
  }
  .actor-input::placeholder {
    color: #80868b;
  }

  /* People with access */
  .people-section {
    padding: 0 24px;
  }
  .people-section h4 {
    margin: 0 0 8px 0;
    font-size: 13px;
    font-weight: 500;
    color: #5f6368;
  }
  .person-list {
    max-height: 200px;
    overflow-y: auto;
  }
  .person-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 6px 0;
    gap: 8px;
  }
  .person-info {
    display: flex;
    align-items: center;
    gap: 10px;
    min-width: 0;
  }
  .avatar {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: #e8eaed;
    color: #5f6368;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
    font-weight: 500;
    flex-shrink: 0;
  }
  .person-name {
    font-size: 14px;
    color: #1f1f1f;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .person-actions {
    display: flex;
    align-items: center;
    gap: 4px;
    flex-shrink: 0;
  }
  .role-select {
    padding: 4px 8px;
    border: none;
    border-radius: 4px;
    font-size: 13px;
    color: #5f6368;
    background: transparent;
    cursor: pointer;
    appearance: auto;
  }
  .role-select:hover {
    background: #f1f3f4;
  }
  .remove-icon {
    background: none;
    border: none;
    cursor: pointer;
    padding: 4px 6px;
    font-size: 14px;
    color: #80868b;
    border-radius: 50%;
    line-height: 1;
  }
  .remove-icon:hover {
    background: #f1f3f4;
    color: #5f6368;
  }
  .empty {
    color: #80868b;
    font-size: 14px;
    font-style: italic;
    padding: 8px 0;
    margin: 0;
  }

  /* General access */
  .general-access {
    padding: 16px 24px;
    border-top: 1px solid #e8eaed;
  }
  .general-access h4 {
    margin: 0 0 8px 0;
    font-size: 13px;
    font-weight: 500;
    color: #5f6368;
  }
  .access-row {
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .access-icon {
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    flex-shrink: 0;
  }
  .access-info {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  .access-select {
    padding: 4px 8px;
    border: none;
    border-radius: 4px;
    font-size: 14px;
    font-weight: 500;
    color: #1f1f1f;
    background: transparent;
    cursor: pointer;
    appearance: auto;
    margin-left: -8px;
  }
  .access-select:hover {
    background: #f1f3f4;
  }
  .access-description {
    font-size: 12px;
    color: #80868b;
  }

  /* Footer */
  .dialog-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 24px;
    border-top: 1px solid #e8eaed;
  }

  /* Buttons */
  .btn {
    padding: 8px 20px;
    border-radius: 20px;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    border: none;
    transition: background 0.15s;
  }
  .btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  .btn-primary {
    background: #2563eb;
    color: white;
  }
  .btn-primary:hover:not(:disabled) {
    background: #1d4ed8;
  }
  .btn-link-copy {
    background: transparent;
    color: #2563eb;
    border: 1px solid #dadce0;
    padding: 8px 16px;
  }
  .btn-link-copy:hover {
    background: #f0f4ff;
  }
</style>
