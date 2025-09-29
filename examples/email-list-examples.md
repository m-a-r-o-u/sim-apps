# Email list examples

The following scenarios demonstrate how to use the email list pipeline.

## Project groups with AI companion

```
sim-apps email-list --service AI --project-groups-only --with-ai-c --stdout
```

Outputs a `;` separated list of best candidate emails for project groups that have a matching `-ai-c` functional group.

## Identify gaps between AI companions

```
sim-apps email-list --service AI --with-ai-c-but-without-ai-h-mcml --dry-run
```

Shows a preview of project groups that are missing an `-ai-h-mcml` companion.

## Export CSV with deduplicated members

```
sim-apps email-list --service AI --project-groups-only --dedup by-best-email --csv email-list.csv
```

Generates a CSV file containing group name, person ID, display name, selected email, all candidates, and selection reason.

## Debug a minimal subset with unique emails

```
sim-apps email-list --service AI --minimal-run --with-ai-c --unique-emails --dry-run
```

Limits processing to the first few groups and members while printing detailed logs for each step. Duplicate email addresses are
collapsed into a single entry in the final list, making it easier to inspect the selection logic during troubleshooting.
