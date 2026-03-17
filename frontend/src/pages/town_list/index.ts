import { mount } from "svelte";
import TownListPage from "./TownListPage.svelte";

const app = mount(TownListPage, {
  target: document.getElementById("app-root")!,
});

export default app;
