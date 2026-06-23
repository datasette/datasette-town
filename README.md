# datasette-town

[![PyPI](https://img.shields.io/pypi/v/datasette-town.svg)](https://pypi.org/project/datasette-town/)
[![Changelog](https://img.shields.io/github/v/release/datasette/datasette-town?include_prereleases&label=changelog)](https://github.com/datasette/datasette-town/releases)
[![Tests](https://github.com/datasette/datasette-town/actions/workflows/test.yml/badge.svg)](https://github.com/datasette/datasette-town/actions/workflows/test.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/datasette/datasette-town/blob/main/LICENSE)

Experimental plugin for sharing SQL queries

## Screenshots

Browse and search the queries you own and ones shared with you:

![The Town query list, with "My Queries" and "Shared with Me" sections](docs/screenshots/town-list.png)

Open a query to view its SQL, run it, and (if you own it) share it:

![A query detail page](docs/screenshots/query-detail.png)

![Query results rendered as a table](docs/screenshots/query-results.png)

Sharing is handled by [datasette-acl](https://github.com/datasette/datasette-acl)
via the `<datasette-acl-share-dialog>` component — share with people, groups, or
the public:

![The share dialog, showing people with access and general access](docs/screenshots/share-dialog.png)

Write a new query with a live SQL editor:

![The new query form](docs/screenshots/new-query.png)

The committed screenshots are regenerated with `just shots` (see the `shots`
recipe in the [Justfile](Justfile)).

## Permissions and sharing

Access to individual queries is managed by
[datasette-acl](https://github.com/datasette/datasette-acl), with sharing UI
provided by
[datasette-acl-share](https://github.com/datasette/datasette-acl-share) (both
hard dependencies).

Each query is an acl resource of type `town-query`, addressed as
`(parent=database_name, child=query_id)`. The creator is seeded the **Manager**
role; the standard Viewer / Editor / Manager roles map to the `datasette-town-view`,
`datasette-town-edit`, and `datasette-town-manage` actions. The query detail page
hosts the `<datasette-acl-share-dialog>` component, which is how queries are shared
with people, groups, or the public — making a query public is an `everyone` (or
`authenticated`) grant rather than a flag on the query.

Two coarse, instance-level gates are configured through Datasette's normal
permissions config:

- `datasette-town-access` — can use the town feature at all
- `datasette-town-create` — can create new queries

```yaml
permissions:
  datasette-town-access:
    id: "*"
  datasette-town-create:
    id: "*"
```