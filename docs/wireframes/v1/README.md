# Household task list — version 1

Layout corresponding to the shared task-list template used for the assignment.

```text
+-----------------------------------------------------------+
| Hestia — AI-Powered Household Coordination                 |
+-----------------------------------------------------------+
| Household tasks                                           |
+-----------------------------------------------------------+
| Household Tasks                                           |
| Introductory text                                          |
| Assignment view label                                     |
| [HttpResponse] [render()] [Base CBV] [Generic CBV]           |
| Find a task                                               |
| [Search tasks by title................] [Search tasks]     |
| Your responsibilities / Search results                    |
| +----------------+ +----------------+ +----------------+  |
| | Title Priority | | Title Priority | | Title Priority |  |
| | Description    | | Description    | | Description    |  |
| | Type           | | Type           | | Type           |  |
| | Location       | | Location       | | Location       |  |
| | Recurrence     | | Recurrence     | | Recurrence     |  |
| | Added date     | | Added date     | | Added date     |  |
| +----------------+ +----------------+ +----------------+  |
+-----------------------------------------------------------+
| Hestia — INFO 490 — Team 12                                |
+-----------------------------------------------------------+
```

On narrow screens, cards stack and the search controls wrap. When the tasks
iterable is empty, the card grid becomes a full-width message: "No tasks found".
A no-match search offers "Show all tasks"; an empty database explains that new
responsibilities appear once created. The four demonstration links are shown
only when a view provides `view_style`.
