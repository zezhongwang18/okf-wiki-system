# OKF MCP Tool Contract

## Tools

- `get_bundle_status`
- `list_bundle_index`
- `list_directory_index`
- `search_bundle`
- `read_concept`
- `get_related_links`
- `get_backlinks`
- `get_page_assets`
- `search_assets`
- `read_asset_metadata`

## Query Flow

```text
get_bundle_status
list_bundle_index
search_bundle
read_concept
get_related_links / get_backlinks
get_page_assets / search_assets
answer with citations
```

For image-heavy questions, use this extension:

```text
search_bundle
search_assets
read_asset_metadata
call company OCR/image skill if needed
answer with concept/source/asset citations
```

## Search Contract

Search is for locating candidate pages. It is not the final answer evidence.

The agent should read complete pages after search.

## Asset Contract

The MCP server returns asset metadata and file paths.

It does not perform local OCR.

If OCR is needed, the agent calls the company OCR/image skill.

Asset pages are first-class searchable knowledge objects. They should include:

- original file path in `resource`
- `mime_type`
- short description
- tags
- optional `# Visible Text`
- optional `# Visual Notes`
- links to source pages and concept pages

Binary files alone are not enough. If an image exists only in `raw/assets/`, the Agent can open it only when it already knows the path. If the image also has an `assets/asset-*.md` page, the Agent can discover it through keyword search.
