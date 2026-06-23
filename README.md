# datasette-town

[![PyPI](https://img.shields.io/pypi/v/datasette-town.svg)](https://pypi.org/project/datasette-town/)
[![Changelog](https://img.shields.io/github/v/release/datasette/datasette-town?include_prereleases&label=changelog)](https://github.com/datasette/datasette-town/releases)
[![Tests](https://github.com/datasette/datasette-town/actions/workflows/test.yml/badge.svg)](https://github.com/datasette/datasette-town/actions/workflows/test.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/datasette/datasette-town/blob/main/LICENSE)

Experimental plugin for sharing SQL queries

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