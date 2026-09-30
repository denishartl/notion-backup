# Synced database rows

## What they are

Notion can mirror data from other tools into a *synced database*. Supported sources include GitHub, Jira, Asana and GitLab. The sync runs one way: the source tool owns the data, and Notion shows a read-only copy. Every row is a page that mirrors one object in the source tool, such as a GitHub pull request.

Notion also creates synced databases by itself. Adding a "GitHub Pull Requests" property to a database makes Notion create an unnamed synced database of the linked pull requests, nested under that database. It holds two more unnamed synced databases, one for PR states and one for GitHub users.

Internally Notion stores these rows as blocks of type `external_object_instance_page` rather than `page`. They carry properties only and have no page body.

## How the API treats them

- Search returns synced rows as ordinary page objects, with all their properties. They look like any other page in the results.
- Querying the synced database returns the rows like any other data source.
- Asking for a row's child blocks fails with a `validation_error`: `Block type external_object_instance_page is not supported via the API.`

## What the backup stores

- `json/pages/{page-id}.json` holds the full page object with its properties and an empty `blocks` list.
- `markdown/` holds a file at its top level, like every database row, with the properties as frontmatter, the title as heading and no body.
- `json/databases/{data-source-id}.json` holds the synced database schema and all its rows.

The backup recognises a synced row by this rejection. It makes the children request for every page and treats this specific rejection as an empty body, which does not count as an error. The match is on the type name. Any other block type the API refuses still ends up in the manifest's error list, so new unsupported content is noticed.

Restoring a synced row into Notion is not meaningful, because the source tool recreates it when the sync runs. The backup keeps the properties as a readable record of what was linked.
