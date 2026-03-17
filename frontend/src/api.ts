import createClient from "openapi-fetch";
import type { paths } from "../api.d.ts";

export const client = createClient<paths>({ baseUrl: "/" });
