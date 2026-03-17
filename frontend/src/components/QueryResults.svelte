<script lang="ts">
  interface Props {
    columns: string[];
    rows: unknown[][];
    error?: string | null;
    loading?: boolean;
    truncated?: boolean;
  }

  let {
    columns = [],
    rows = [],
    error = null,
    loading = false,
    truncated = false,
  }: Props = $props();
</script>

{#if loading}
  <p class="loading">Running query...</p>
{:else if error}
  <div class="error">
    <strong>Error:</strong>
    {error}
  </div>
{:else if columns.length > 0}
  <div class="results-wrapper">
    <table>
      <thead>
        <tr>
          {#each columns as col}
            <th>{col}</th>
          {/each}
        </tr>
      </thead>
      <tbody>
        {#each rows as row}
          <tr>
            {#each row as cell}
              <td>{cell === null ? "" : cell}</td>
            {/each}
          </tr>
        {/each}
      </tbody>
    </table>
    {#if truncated}
      <p class="truncated">Results truncated (showing first 1,000 rows)</p>
    {/if}
  </div>
{/if}

<style>
  .results-wrapper {
    overflow-x: auto;
    margin-top: 1rem;
  }
  table {
    border-collapse: collapse;
    width: 100%;
    font-size: 14px;
  }
  th,
  td {
    border: 1px solid #ddd;
    padding: 6px 10px;
    text-align: left;
    white-space: nowrap;
  }
  th {
    background: #f5f5f5;
    font-weight: 600;
  }
  tr:hover {
    background: #fafafa;
  }
  .error {
    color: #c00;
    padding: 0.5rem;
    background: #fff0f0;
    border: 1px solid #fcc;
    border-radius: 4px;
    margin-top: 1rem;
  }
  .loading {
    color: #666;
    font-style: italic;
  }
  .truncated {
    color: #888;
    font-size: 0.9em;
    margin-top: 0.5rem;
  }
</style>
