import { vitePreprocess } from '@sveltejs/vite-plugin-svelte'

export default {
  preprocess: vitePreprocess(),
  compilerOptions: {
    // Required so svelte-check accepts <svelte:options customElement="...">
    // in src/pages/profile_section/ProfileSection.svelte. The actual build
    // scopes customElement compilation to that one file via
    // dynamicCompileOptions in vite.config.ts.
    customElement: true,
  },
}
