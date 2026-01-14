# Activity Tracker Skill

Track activities with Eisenhower matrix classification, duration, and tags.

## When to Use

When the user wants to log, review, search, or delete activities, including:
- What they did (description)
- How long it took
- Which Eisenhower quadrant it falls into
- Tags to categorize it
- Reviewing recent activity logs
- Searching logs by tags or description
- Removing incorrect entries

## Gathering Information

When invoked, infer or collect:

1. **Description** - What was the activity? (required)
2. **Duration** - How long in minutes? (required)
3. **Quadrant** - Which Eisenhower quadrant? (required, 1-4)
   - Q1: Urgent & Important (crises, deadlines) → Do first
   - Q2: Not Urgent & Important (planning, learning, health) → Schedule
   - Q3: Urgent & Not Important (interruptions, some meetings) → Delegate
   - Q4: Not Urgent & Not Important (distractions, time-wasters) → Eliminate
4. **When** - When did it happen? (optional, defaults to now)
5. **Tags** - Categories like `work`, `health`, `relationships`, `focus`, `distraction`, etc. (optional)

If the user provides info naturally, parse it. If not, ask briefly.

## Commands

### Add

```bash
uv run {workspace}/skills/activity-tracker/track.py add \
  --w "10:30" \
  --d 45 \
  --q 2 \
  --D "Deep work on project X" \
  --t "work,coding,focus"
```

### List

```bash
uv run {workspace}/skills/activity-tracker/track.py list --limit 20 --sort-by event
```

### Search

```bash
uv run {workspace}/skills/activity-tracker/track.py search --tags "work,focus" --desc "deep planning" --quadrant 2
```

### Remove

```bash
uv run {workspace}/skills/activity-tracker/track.py remove --id 42
```

## Arguments (All Commands)

| Command | Arg | Short | Required | Description |
|---------|-----|-------|----------|-------------|
| `add` | `--duration` | `-d` | Yes | Duration in minutes |
| `add` | `--quadrant` | `-q` | Yes | Eisenhower quadrant (1-4) |
| `add` | `--desc` | `-D` | Yes | Activity description |
| `add` | `--tags` | `-t` | No | Comma-separated tags |
| `add` | `--when` | `-w` | No | Timestamp (defaults to now) |
| `list` | `--limit` | `-l` | No | Number of activities to show (default: 10) |
| `list` | `--sort-by` |  | No | Sort by `id` (ASC), `added` (entry timestamp DESC), or `event` (activity timestamp DESC) |
| `search` | `--tags` | `-t` | No | Comma-separated tags to match (OR logic) |
| `search` | `--desc` | `-D` | No | Description keywords to match (OR logic) |
| `search` | `--quadrant` | `-q` | No | Filter by Eisenhower quadrant (1-4) |
| `remove` | `--id` |  | Yes | Activity ID to delete (prompts for confirmation) |

### Time Formats

- Full: `2024-01-04 10:30`
- Date only: `2024-01-04`
- Time only: `10:30` (uses today's date)
- ISO: `2024-01-04T10:30:00`

## Database

SQLite database stored at: `skills/activity-tracker/activities.db`

Schema:
- `entry_timestamp` - when the log was created
- `activity_timestamp` - when the activity happened
- `duration_minutes` - duration in minutes
- `quadrant` - Eisenhower quadrant (1-4)
- `description` - freeform description
- `tags` - comma-separated tags

## Example Interaction

User: "Just spent 30 minutes scrolling Twitter"

→ That's Q4 (not urgent, not important), tags might be `distraction,social`

```bash
uv run .../track.py add -d 30 -q 4 -D "Scrolled Twitter" -t "distraction,social"
```

User: "Had a 1-on-1 with my manager this morning for an hour"

→ Probably Q2 (important relationship building), tags: `work,relationships,1on1`

```bash
uv run .../track.py add -d 60 -q 2 -D "1-on-1 with manager" -t "work,relationships,1on1" -w "09:00"
```
