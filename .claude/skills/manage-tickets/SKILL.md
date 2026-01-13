---
name: manage-tickets
description: Manage the tickets of of the project
---
# Manage Tickets


## Instructions

### Opening a Ticket

When the user wants to create a new ticket:

1. Ask the user for the ticket title if not provided
2. Run the command: `mise run open-ticket "<ticket title>"`
3. This will:
   - Create the ticket in SourceHut tracker `~radium226/variables`
   - Extract the ticket ID
   - Create a new branch named `ticket-{ticket_id}-{slugified-title}`
   - Checkout to that branch

Example:
```bash
mise run open-ticket "Add configuration validation"
```

### Closing a Ticket

When the user wants to close a ticket and merge the branch:

1. Ensure the user is on an ticket branch (format: `ticket-{ticket_id}-{title}`)
2. Optionally ask which branch to merge into (defaults to `main`)
3. Run the command: `mise run close-ticket`
4. This will:
   - Extract the ticket ID from the current branch name
   - Switch to the main branch
   - Squash and merge the ticket branch
   - Commit with message format `[#{ticket_id}] {first-commit-message}`
   - Resolve the ticket in SourceHut
   - Delete the merged branch

Example:
```bash
mise run close-ticket # Merge the current branch to main and close the ticket
```


## Important Notes

- Both tasks use the SourceHut tracker: `~radium226/variables`
- The `hut` CLI tool must be installed and authenticated
- Branch naming convention: `ticket-{ticket_id}-{slugified-title}`
- Close ticket only works when on an ticket branch
