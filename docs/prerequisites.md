# Glean Agent Toolkit: Glean Instance Prerequisites

This guide summarizes requirements for your organization's Glean instance to use the built-in tools. Ensure your Glean Admin has enabled the relevant features and connectors.

## Global requirements

- Environment variables

  - `GLEAN_API_TOKEN`
  - `GLEAN_INSTANCE`

- Glean instance access
  - Client API and Tools enabled
  - Users have access to underlying content/apps (authorization enforced by Glean)

## Tool-specific requirements

### `search`

- Connectors: Any content sources your organization has connected to Glean
- Admin toggles: Client API enabled

### `employee_search`

- Connectors: Directory/HR sources (e.g., Google Workspace Directory, Azure AD, HRIS if applicable)
- Admin toggles: People/Directory data available to Client API

### `calendar_search`

- Connectors: Google Calendar and/or Microsoft 365 Calendar
- Admin toggles: Calendar search enabled for Client API

### `gmail_search`

- Connectors: Google Workspace Gmail
- Admin toggles: Gmail search enabled for Client API

### `outlook_search`

- Connectors: Microsoft 365 (Outlook Mail)
- Admin toggles: Outlook search enabled for Client API

### `code_search`

- Connectors: One or more code hosts (GitHub, GitLab, Bitbucket, Azure Repos)
- Admin toggles: Code Search enabled for your organization's Glean instance and available to Client API

## Verification checklist

- Confirm Client API access with a simple `glean_search` call
- Verify each connector is authorized and indexed in Admin
- Test per-user scoping by running a tool with a least-privilege account

## Troubleshooting

- 401/403 errors: validate `GLEAN_API_TOKEN`, `GLEAN_INSTANCE`, and user permissions
- Empty results: confirm connector indexing status and that the feature is enabled for Client API
- Code search gaps: ensure all relevant orgs/repos are connected and indexing completed
