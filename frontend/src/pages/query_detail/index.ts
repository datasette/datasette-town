import { mount } from "svelte";
import QueryDetailPage from "./QueryDetailPage.svelte";

const app = mount(QueryDetailPage, {
  target: document.getElementById("app-root")!,
});

export default app;
