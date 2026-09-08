# draft document JSON keys use snake_case

The draft document is a stable, reusable external contract (consumed by
`render` and any future changelog tool), modeled with pydantic. Field names
use snake_case (`affected_file`, `project_context`, `change_statement`)
matching the pydantic model directly, rather than kebab-case or camelCase,
avoiding alias mapping.
