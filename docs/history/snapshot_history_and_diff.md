# Snapshot History and Diff

The snapshot history feature allows you to store and compare project snapshots over time. This is useful for tracking changes in code quality, risk, and issues.

## Directory Structure

Historical snapshots are stored in the `.codesage/history` directory by default. Each project has its own subdirectory, and each snapshot is stored as a YAML file named after its snapshot ID (e.g., commit hash).

```
.codesage/history/
└── my-project/
    ├── index.yaml
    ├── abc1234.yaml
    └── def5678.yaml
```

## Usage

### Saving Snapshots

To save a snapshot to the history, use the `history-snapshot` command:

```bash
codesage history-snapshot --snapshot <path-to-snapshot.yaml> --project-name my-project --commit <commit-hash>
```

### Comparing Snapshots

To compare two snapshots, use the `history-diff` command:

```bash
codesage history-diff --project-name my-project --from-id <commit-hash-1> --to-id <commit-hash-2>
```

This will output a YAML report summarizing the differences between the two snapshots, including changes in risk, issues, and files.
