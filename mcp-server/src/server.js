#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const {
  resolveBundleRoot,
  safeResolve,
  loadConcepts,
  searchBundle,
  readConcept,
  getRelatedLinks,
  getBacklinks,
  getPageAssets,
  loadGraph,
} = require('./okf');

const root = resolveBundleRoot();
let buffer = Buffer.alloc(0);

process.stdin.on('data', (chunk) => {
  buffer = Buffer.concat([buffer, chunk]);
  while (true) {
    const headerEnd = buffer.indexOf(Buffer.from('\r\n\r\n'));
    if (headerEnd === -1) return;
    const header = buffer.slice(0, headerEnd).toString('ascii');
    const match = header.match(/Content-Length:\s*(\d+)/i);
    if (!match) throw new Error('Missing Content-Length header');
    const length = Number(match[1]);
    const bodyStart = headerEnd + 4;
    if (buffer.length < bodyStart + length) return;
    const body = buffer.slice(bodyStart, bodyStart + length).toString('utf8');
    buffer = buffer.slice(bodyStart + length);
    handle(JSON.parse(body)).catch((error) => {
      respond(null, null, {code: -32603, message: error.message});
    });
  }
});

async function handle(message) {
  if (message.method === 'initialize') {
    return respond(message.id, {
      protocolVersion: '2024-11-05',
      capabilities: {tools: {}},
      serverInfo: {name: 'okf-wiki-mcp', version: '0.1.0'},
    });
  }
  if (message.method === 'notifications/initialized') return;
  if (message.method === 'tools/list') return respond(message.id, {tools: toolDefinitions()});
  if (message.method === 'tools/call') {
    const {name, arguments: args = {}} = message.params || {};
    return respond(message.id, {content: [{type: 'text', text: JSON.stringify(callTool(name, args), null, 2)}]});
  }
  return respond(message.id, null, {code: -32601, message: `Unknown method: ${message.method}`});
}

function callTool(name, args) {
  if (name === 'get_bundle_status') return getBundleStatus();
  if (name === 'list_bundle_index') return readIndex('index.md');
  if (name === 'list_directory_index') return readIndex(path.join(String(args.path || ''), 'index.md').replaceAll(path.sep, '/'));
  if (name === 'search_bundle') return {query: String(args.query || ''), matches: searchBundle(root, String(args.query || ''), Number(args.top_k || 5))};
  if (name === 'read_concept') return readConcept(root, String(args.path || ''));
  if (name === 'get_related_links') return getRelatedLinks(root, String(args.path || ''));
  if (name === 'get_backlinks') return getBacklinks(root, String(args.path || ''));
  if (name === 'get_page_assets') return getPageAssets(root, String(args.path || ''));
  if (name === 'search_assets') return searchAssets(args);
  if (name === 'read_asset_metadata') return readConcept(root, String(args.asset_id_or_path || args.path || ''));
  throw new Error(`Unknown tool: ${name}`);
}

function getBundleStatus() {
  const concepts = loadConcepts(root);
  const graph = loadGraph(root);
  return {
    bundle_root: root,
    read_only: true,
    concepts: concepts.filter((item) => !item.path.endsWith('index.md')).length,
    indexes: concepts.filter((item) => item.path.endsWith('index.md')).length,
    assets: concepts.filter((item) => String(item.type).toLowerCase().includes('asset')).length,
    graph_nodes: graph.nodes.length,
    graph_edges: graph.edges.length,
  };
}

function readIndex(relPath) {
  const full = safeResolve(root, relPath);
  if (!fs.existsSync(full)) throw new Error(`Index not found: ${relPath}`);
  return {path: relPath, content: fs.readFileSync(full, 'utf8')};
}

function searchAssets(args) {
  const matches = searchBundle(root, String(args.query || ''), Number(args.top_k || 5) * 3)
    .filter((item) => String(item.type).toLowerCase().includes('asset') || item.path.startsWith('assets/'))
    .slice(0, Number(args.top_k || 5));
  return {query: String(args.query || ''), matches};
}

function toolDefinitions() {
  return [
    tool('get_bundle_status', 'Return OKF bundle status, counts, graph counts, and read-only status.', {}),
    tool('list_bundle_index', 'Read the root index.md for progressive disclosure.', {}),
    tool('list_directory_index', 'Read a directory index.md by directory path.', {path: {type: 'string'}}),
    tool('search_bundle', 'Search OKF concepts by title, description, tags, path, headings, and body.', {query: {type: 'string'}, top_k: {type: 'number'}}, ['query']),
    tool('read_concept', 'Read a complete concept/source/question/asset Markdown page.', {path: {type: 'string'}}, ['path']),
    tool('get_related_links', 'Extract outgoing Markdown links from a concept page.', {path: {type: 'string'}}, ['path']),
    tool('get_backlinks', 'Find pages that link to a target page.', {path: {type: 'string'}}, ['path']),
    tool('get_page_assets', 'Return image/media references from a concept page.', {path: {type: 'string'}}, ['path']),
    tool('search_assets', 'Search image/media asset metadata pages.', {query: {type: 'string'}, top_k: {type: 'number'}}, ['query']),
    tool('read_asset_metadata', 'Read an asset metadata page. OCR should be handled by the company OCR/image skill.', {asset_id_or_path: {type: 'string'}}, ['asset_id_or_path']),
  ];
}

function tool(name, description, properties, required = []) {
  return {name, description, inputSchema: {type: 'object', properties, required}};
}

function respond(id, result, error) {
  const payload = JSON.stringify({jsonrpc: '2.0', id, ...(error ? {error} : {result})});
  process.stdout.write(`Content-Length: ${Buffer.byteLength(payload, 'utf8')}\r\n\r\n${payload}`);
}
