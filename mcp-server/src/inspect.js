const {resolveBundleRoot, loadConcepts, searchBundle, loadGraph} = require('./okf');

const root = resolveBundleRoot();
const query = process.argv.slice(2).join(' ') || 'LLM Wiki RAG MCP';
const concepts = loadConcepts(root);
const graph = loadGraph(root);

console.log(JSON.stringify({
  bundle_root: root,
  concepts: concepts.length,
  graph_nodes: graph.nodes.length,
  graph_edges: graph.edges.length,
  query,
  matches: searchBundle(root, query, 8),
}, null, 2));
