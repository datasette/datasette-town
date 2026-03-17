<script lang="ts">
  import { onMount } from "svelte";
  import { EditorView, keymap } from "@codemirror/view";
  import { EditorState } from "@codemirror/state";
  import { basicSetup } from "codemirror";
  import { sql } from "@codemirror/lang-sql";

  interface Props {
    value: string;
    readonly?: boolean;
    onchange?: (value: string) => void;
    onexecute?: () => void;
  }

  let { value = $bindable(""), readonly = false, onchange, onexecute }: Props =
    $props();

  let container: HTMLDivElement;
  let view: EditorView;

  onMount(() => {
    const updateListener = EditorView.updateListener.of((update) => {
      if (update.docChanged) {
        value = update.state.doc.toString();
        onchange?.(value);
      }
    });

    const executeKeymap = keymap.of([
      {
        key: "Ctrl-Enter",
        mac: "Cmd-Enter",
        run: () => {
          onexecute?.();
          return true;
        },
      },
    ]);

    view = new EditorView({
      state: EditorState.create({
        doc: value,
        extensions: [
          basicSetup,
          sql(),
          updateListener,
          executeKeymap,
          EditorState.readOnly.of(readonly),
          EditorView.theme({
            "&": { fontSize: "14px" },
            ".cm-editor": { border: "1px solid #ddd", borderRadius: "4px" },
            ".cm-content": { minHeight: "100px" },
          }),
        ],
      }),
      parent: container,
    });

    return () => view.destroy();
  });

  $effect(() => {
    if (view && value !== view.state.doc.toString()) {
      view.dispatch({
        changes: { from: 0, to: view.state.doc.length, insert: value },
      });
    }
  });
</script>

<div bind:this={container} class="sql-editor"></div>

<style>
  .sql-editor {
    width: 100%;
  }
</style>
