import { loadPageData } from "./page_data/load";

interface BasePageData {
  database_name: string;
}

const pageData = loadPageData<BasePageData>();

export const appState = $state({
  selectedDatabase: pageData.database_name,
});
