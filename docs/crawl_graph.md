# Crawl & Link Graph

`crawl(base_url, *, max_pages=200, max_depth=3, ...) -> LinkGraph` runs a
bounded BFS starting from *base_url*, extracts `<a href>` links from each
internal HTML page, and builds a directed link graph.

## Parameters

| Parameter       | Default | Description |
|-----------------|---------|-------------|
| `max_pages`     | 200     | Maximum internal pages fetched. |
| `max_depth`     | 3       | Maximum BFS depth from the seed. |
| `same_domain`   | True    | Restrict enqueuing to the same host (`www.` treated as equivalent). |
| `use_sitemap`   | True    | Seed additional URLs from the site's sitemaps. |
| `respect_robots`| True    | Honour `Disallow` rules from robots.txt. |
| `delay`         | None    | Fixed inter-fetch delay (overrides `Crawl-delay` from robots.txt). |
| `timeout`       | 30.0    | Per-request timeout in seconds. |

## LinkGraph

```python
graph.nodes          # dict[str, Node]
graph.adjacency      # dict[str, set[str]]
graph.internal       # set[str]
graph.external       # set[str]
graph.edges()        # iterator[(src, dst)]
graph.domains()      # dict[host, count]  — outgoing external links
graph.to_dict()
graph.to_json(indent=2)
graph.to_dot()       # Graphviz digraph string
graph.summary()      # human-readable text
```

## Node

```python
node.url          # str
node.internal     # bool
node.depth        # int
node.status       # int | None  — HTTP status of the fetch
node.content_type # str | None
node.title        # str | None  — <title> text
```

`out_degree` and `in_degree` appear in `to_dict()` output.

## Asset filtering

Links to obvious non-HTML resources (`.jpg`, `.css`, `.js`, `.pdf`, etc.)
are recorded as edges but never enqueued for crawling.

## Graphviz export

```python
dot_str = graph.to_dot()
# render: dot -Tsvg out.dot -o out.svg
```
