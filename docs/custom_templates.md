# Custom Markdown Templates

CodeSage allows you to create custom Markdown reports by providing your own Jinja2 templates. This guide explains how to create and use custom templates.

## Template Structure

A custom template is a Jinja2 template file that receives a `ProjectSnapshot` object in its context. You can access all the data from the snapshot within your template.

### The `snapshot` Object

The main object available in the template context is `snapshot`. It is an instance of the `ProjectSnapshot` model, and you can access its fields as described in the [Snapshot Schema Specification](./snapshot_format.md).

**Example:**

```jinja2
# My Custom Report

This project has {{ snapshot.files|length }} files.

The average complexity is {{ snapshot.global_metrics.avg_complexity }}.
```

## Using a Custom Template

To use a custom template, you need to specify the template file's name in your `.codesage.yaml` configuration file:

```yaml
snapshot:
  markdown:
    template: "my_custom_template.md.jinja2"
```

You also need to provide the path to the directory containing your custom templates. This is done by passing the `--template-dir` flag to the `codesage` command line interface.

**Example:**

```bash
codesage analyze --template-dir /path/to/my/templates
```

## Included Filters and Helpers

CodeSage provides a few helpful filters and variables in the template context:

*   `complexity_top10`: A list of the 10 most complex functions.
*   `dependency_mermaid`: A string containing the Mermaid.js syntax for the project's dependency graph.
*   `pattern_stats`: A dictionary with statistics about the detected patterns.

You can use these helpers to quickly add common sections to your report.
