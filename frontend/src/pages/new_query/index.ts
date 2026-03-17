import { mount } from "svelte";
import NewQueryPage from "./NewQueryPage.svelte";

const app = mount(NewQueryPage, {
  target: document.getElementById("app-root")!,
});

export default app;
