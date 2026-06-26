const fs = require('fs');
const path = require('path');

function resolveBundleRoot() {
  const root = process.env.OKF_BUNDLE_ROOT || path.resolve(__dirname, '../../bundle');
  if (!fs.existsSync(path.join(root, 'index.md'))) {
    throw new Error(`OKF_BUNDLE_ROOT must point to a bundle containing index.md: ${root}`);
  }
  return root;
}

function walkFiles(dir, predicate = () => true) {
  const out = [];
  for (const entry of fs.readdirSync(dir, {withFileTypes: true})) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) out.push(...walkFiles(full, predicate));
    if (entry.isFile() && predicate(full)) out.push(full);
  }
  return out;
}

function safeResolve(root, relPath) {
  const normalized = relPath.replace(/^\/+/, '');
  const full = path.resolve(root, normalized);
  const rootResolved = path.resolve(root);
  if (!full.startsWith(rootResolved + path.sep) && full !== rootResolved) {
    throw new Error(`Path escapes bundle root: ${relPath}`);
  }
  return full;
}

function parseFrontmatter(markdown) {
  if (!markdown.startsWith('---\n')) return {frontmatter: {}, body: markdown};
  const end = markdown.indexOf('\n---\n', 4);
  if (end === -1) return {frontmatter: {}, body: markdown};
  const yaml = markdown.slice(4, end).trim();
  const body = markdown.slice(end + 5);
  const frontmatter = {};
  let currentKey = null;
  for (const line of yaml.split('\n')) {
    const kv = line.match(/^([A-Za-z0-9_-]+):\s*(.*)$/);
    if (kv) {
      currentKey = kv[1];
      frontmatter[currentKey] = kv[2].trim().replace(/^['"]|['"]$/g, '') || [];
      continue;
    }
    const item = line.match(/^\s*-\s*(.*)$/);
    if (item && currentKey) {
      if (!Array.isArray(frontmatter[currentKey])) frontmatter[currentKey] = [];
      frontmatter[currentKey].push(item[1].trim().replace(/^['"]|['"]$/g, ''));
    }
  }
  return {frontmatter, body};
}

function titleFrom(body, frontmatter, fallback) {
  if (frontmatter.title) return String(frontmatter.title);
  const h1 = body.match(/^#\s+(.+)$/m);
  return h1 ? h1[1].trim() : fallback;
}

function headingsFrom(body) {
  return [...body.matchAll(/^(#{1,4})\s+(.+)$/gm)].map((m) => m[2].trim());
}

function tokenize(text) {
  const latin = text.toLowerCase().match(/[a-z0-9][a-z0-9_-]*/g) || [];
  const cjk = text.match(/[\u3400-\u9fff]/g) || [];
  return [...latin, ...cjk];
}

function loadConcepts(root) {
  return walkFiles(root, (file) => file.endsWith('.md'))
    .filter((file) => !file.endsWith(`${path.sep}log.md`))
    .map((file) => {
      const markdown = fs.readFileSync(file, 'utf8');
      const {frontmatter, body} = parseFrontmatter(markdown);
      const relPath = path.relative(root, file).replaceAll(path.sep, '/');
      const isReserved = path.basename(file) === 'index.md';
      return {
        path: relPath,
        id: relPath.replace(/\.md$/, ''),
        title: titleFrom(body, frontmatter, path.basename(file, '.md')),
        type: frontmatter.type || (isReserved ? 'Index' : 'Concept'),
        description: frontmatter.description || '',
        resource: frontmatter.resource || '',
        tags: Array.isArray(frontmatter.tags) ? frontmatter.tags : [],
        timestamp: frontmatter.timestamp || '',
        headings: headingsFrom(body),
        text: markdown,
      };
    });
}

function searchBundle(root, query, topK = 5) {
  const tokens = tokenize(query);
  return loadConcepts(root)
    .map((concept) => {
      const haystack = `${concept.path}\n${concept.title}\n${concept.description}\n${concept.tags.join(' ')}\n${concept.headings.join('\n')}\n${concept.text}`.toLowerCase();
      const reasons = [];
      let score = typeBoost(concept.type);
      for (const token of tokens) {
        if (!haystack.includes(token.toLowerCase())) continue;
        const value = token.length > 1 ? 2 : 0.3;
        score += value;
        if (concept.title.toLowerCase().includes(token.toLowerCase())) {
          score += value * 2;
          reasons.push(`title:${token}`);
        } else if (concept.description.toLowerCase().includes(token.toLowerCase())) {
          score += value * 1.5;
          reasons.push(`description:${token}`);
        } else if (concept.tags.join(' ').toLowerCase().includes(token.toLowerCase())) {
          score += value;
          reasons.push(`tag:${token}`);
        } else if (concept.path.toLowerCase().includes(token.toLowerCase())) {
          score += value * 0.5;
          reasons.push(`path:${token}`);
        } else {
          reasons.push(`text:${token}`);
        }
      }
      return {...concept, score: Number(score.toFixed(2)), reasons: [...new Set(reasons)]};
    })
    .filter((concept) => concept.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, topK)
    .map(({text, ...concept}) => concept);
}

function typeBoost(type) {
  const normalized = String(type).toLowerCase();
  if (normalized.includes('durable')) return 3;
  if (normalized.includes('concept')) return 2;
  if (normalized.includes('map')) return 1.5;
  if (normalized.includes('image') || normalized.includes('asset')) return 1.2;
  if (normalized.includes('source')) return 1;
  return 0.5;
}

function markdownLinks(markdown) {
  const links = [];
  for (const match of markdown.matchAll(/(?<!!)\[([^\]]+)\]\(([^)]+)\)/g)) {
    links.push({label: match[1], target: match[2]});
  }
  return links;
}

function markdownImages(markdown) {
  const images = [];
  for (const match of markdown.matchAll(/!\[([^\]]*)\]\(([^)]+)\)/g)) {
    images.push({alt: match[1], target: match[2]});
  }
  return images;
}

function normalizeReference(pagePath, reference) {
  if (/^[a-z]+:\/\//i.test(reference)) return reference;
  if (path.isAbsolute(reference)) return reference.replaceAll(path.sep, '/');
  const joined = path.normalize(path.join(path.dirname(pagePath), reference)).replaceAll(path.sep, '/');
  const parts = [];
  for (const part of joined.split('/')) {
    if (!part || part === '.') continue;
    if (part === '..') parts.pop();
    else parts.push(part);
  }
  return parts.join('/');
}

function readConcept(root, relPath) {
  const full = safeResolve(root, relPath);
  if (!fs.existsSync(full)) throw new Error(`Concept not found: ${relPath}`);
  const content = fs.readFileSync(full, 'utf8');
  const {frontmatter, body} = parseFrontmatter(content);
  return {
    path: relPath,
    frontmatter,
    title: titleFrom(body, frontmatter, path.basename(relPath, '.md')),
    content,
  };
}

function getRelatedLinks(root, relPath) {
  const concept = readConcept(root, relPath);
  return {
    path: relPath,
    links: markdownLinks(concept.content).map((link) => ({
      ...link,
      normalized_target: normalizeReference(relPath, link.target),
    })),
  };
}

function getBacklinks(root, relPath) {
  const concepts = loadConcepts(root);
  const backlinks = [];
  for (const concept of concepts) {
    for (const link of markdownLinks(concept.text)) {
      if (normalizeReference(concept.path, link.target) === relPath) {
        backlinks.push({from_path: concept.path, from_title: concept.title, label: link.label});
      }
    }
  }
  return {path: relPath, backlinks};
}

function getPageAssets(root, relPath) {
  const concept = readConcept(root, relPath);
  return {
    path: relPath,
    assets: markdownImages(concept.content).map((image) => {
      const normalized = normalizeReference(relPath, image.target);
      return {
        alt: image.alt,
        asset_path: normalized,
        raw_reference: image.target,
        absolute_asset_path: /^[a-z]+:\/\//i.test(normalized) ? normalized : safeResolve(root, normalized),
      };
    }),
  };
}

function loadGraph(root) {
  const graphPath = path.join(root, 'graph.yml');
  if (!fs.existsSync(graphPath)) return {nodes: [], edges: []};
  const text = fs.readFileSync(graphPath, 'utf8');
  const nodes = [];
  const edges = [];
  let section = null;
  let current = null;
  for (const rawLine of text.split('\n')) {
    const line = rawLine.trimEnd();
    if (line === 'nodes:') section = 'nodes';
    if (line === 'edges:') section = 'edges';
    const item = line.match(/^\s*-\s+([A-Za-z_]+):\s*(.*)$/);
    if (item) {
      current = {[item[1]]: item[2]};
      if (section === 'nodes') nodes.push(current);
      if (section === 'edges') edges.push(current);
      continue;
    }
    const kv = line.match(/^\s+([A-Za-z_]+):\s*(.*)$/);
    if (kv && current) current[kv[1]] = kv[2];
  }
  return {nodes, edges};
}

module.exports = {
  resolveBundleRoot,
  safeResolve,
  loadConcepts,
  searchBundle,
  readConcept,
  getRelatedLinks,
  getBacklinks,
  getPageAssets,
  loadGraph,
};
