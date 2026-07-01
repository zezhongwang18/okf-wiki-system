const fs = require('fs');
const path = require('path');

const ASSET_FILE_EXTENSIONS = new Set([
  '.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp', '.tif', '.tiff', '.svg',
  '.mp4', '.mov', '.mp3', '.wav', '.m4a', '.pdf',
]);

const MIME_TYPES = {
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.webp': 'image/webp',
  '.gif': 'image/gif',
  '.bmp': 'image/bmp',
  '.tif': 'image/tiff',
  '.tiff': 'image/tiff',
  '.svg': 'image/svg+xml',
  '.mp4': 'video/mp4',
  '.mov': 'video/quicktime',
  '.mp3': 'audio/mpeg',
  '.wav': 'audio/wav',
  '.m4a': 'audio/mp4',
  '.pdf': 'application/pdf',
};

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

function sectionBody(markdown, heading) {
  const lines = markdown.split(/\r?\n/);
  const target = String(heading).trim().toLowerCase();
  const out = [];
  let inside = false;
  for (const line of lines) {
    const h1 = line.match(/^#\s+(.+?)\s*$/);
    if (h1) {
      if (inside) break;
      inside = h1[1].trim().toLowerCase() === target;
      continue;
    }
    if (inside) out.push(line);
  }
  return out.join('\n').trim();
}

function markdownSectionLinks(markdown, heading) {
  return markdownLinks(sectionBody(markdown, heading)).map((link) => link.target);
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

function firstFrontmatterValue(frontmatter, key) {
  const value = frontmatter[key];
  return Array.isArray(value) ? value[0] : value;
}

function readAssetMetadata(root, relPath) {
  const concept = readConcept(root, relPath);
  const resource = firstFrontmatterValue(concept.frontmatter, 'resource') || '';
  const hasTodo = /\bTODO\b|Source Page TODO|Concept TODO|Context unavailable/i.test(concept.content);
  const sourceContextAvailable = String(firstFrontmatterValue(concept.frontmatter, 'source_context_available') || '').toLowerCase() === 'true'
    || /^# Source Context[\s\S]*?Binding confidence:/m.test(concept.content);
  let absoluteAssetPath = '';
  if (resource && !/^[a-z]+:\/\//i.test(resource)) {
    absoluteAssetPath = safeResolve(root, resource);
  } else {
    absoluteAssetPath = resource;
  }
  return {
    ...concept,
    resource,
    absolute_asset_path: absoluteAssetPath,
    has_todo: hasTodo,
    source_context_available: sourceContextAvailable,
    applicable_questions: sectionBody(concept.content, 'Applicable Questions'),
    not_applicable_to: sectionBody(concept.content, 'Not Applicable To'),
    completion_status: hasTodo ? 'draft' : 'ready',
  };
}

function resolveAssetReference(root, assetIdOrPath) {
  const value = String(assetIdOrPath || '').trim();
  if (!value) throw new Error('asset_id_or_path is required');
  if (/^assets\/.+\.md$/i.test(value)) {
    const metadata = readAssetMetadata(root, value);
    if (!metadata.resource) throw new Error(`Asset metadata has no resource: ${value}`);
    return {
      asset_page: value,
      resource: metadata.resource,
      title: metadata.title,
      completion_status: metadata.completion_status,
      absolute_asset_path: metadata.absolute_asset_path,
    };
  }
  if (!value.startsWith('raw/assets/')) {
    throw new Error(`Asset file references must be under raw/assets/ or an asset metadata page: ${value}`);
  }
  return {
    asset_page: '',
    resource: value,
    title: path.basename(value),
    completion_status: 'unknown',
    absolute_asset_path: safeResolve(root, value),
  };
}

function readAssetFile(root, assetIdOrPath, options = {}) {
  const resolved = resolveAssetReference(root, assetIdOrPath);
  const full = safeResolve(root, resolved.resource);
  const rel = path.relative(root, full).replaceAll(path.sep, '/');
  if (!rel.startsWith('raw/assets/')) {
    throw new Error(`Resolved asset is outside raw/assets/: ${rel}`);
  }
  if (!fs.existsSync(full)) throw new Error(`Asset file not found: ${resolved.resource}`);
  const stat = fs.statSync(full);
  if (!stat.isFile()) throw new Error(`Asset reference is not a file: ${resolved.resource}`);
  const ext = path.extname(full).toLowerCase();
  if (!ASSET_FILE_EXTENSIONS.has(ext)) {
    throw new Error(`Unsupported asset file type: ${ext || '(none)'}`);
  }
  const maxBytes = Number(options.max_bytes || 10 * 1024 * 1024);
  const includeData = options.include_data !== false;
  const result = {
    asset_page: resolved.asset_page,
    title: resolved.title,
    resource: rel,
    absolute_asset_path: full,
    mime_type: MIME_TYPES[ext] || 'application/octet-stream',
    size_bytes: stat.size,
    completion_status: resolved.completion_status,
    data_base64: null,
    truncated: false,
  };
  if (includeData) {
    if (stat.size > maxBytes) {
      result.truncated = true;
      result.data_base64 = null;
      result.note = `Asset is larger than max_bytes (${stat.size} > ${maxBytes}); use absolute_asset_path for display.`;
    } else {
      result.data_base64 = fs.readFileSync(full).toString('base64');
    }
  }
  return result;
}

function isNotAssigned(text) {
  const normalized = String(text || '').replace(/\s+/g, ' ').trim().toLowerCase();
  return ['not assigned', 'not assigned.', 'none', 'none.', '未分配', '未分配。'].includes(normalized);
}

function tokenOverlapScore(question, text) {
  const questionTokens = new Set(tokenize(question).filter((token) => token.length > 1));
  const textTokens = new Set(tokenize(text).filter((token) => token.length > 1));
  if (!questionTokens.size || !textTokens.size) return 0;
  let score = 0;
  for (const token of questionTokens) {
    if (textTokens.has(token)) score += 1;
  }
  return score;
}

function normalizeMatchText(text) {
  return String(text || '')
    .replace(/\[[^\]]+\]\(([^)]+)\)/g, '$1')
    .replace(/[`*_#>-]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .toLowerCase();
}

function exactApplicableMatch(applicable, question, pagePaths = [], pageTitles = []) {
  const haystack = normalizeMatchText(applicable);
  const needles = [
    question,
    ...pagePaths,
    ...pageTitles,
  ].map(normalizeMatchText).filter((value) => value.length >= 2);
  return needles.some((needle) => haystack.includes(needle));
}

function findApplicableAssets(root, question, pagePaths = []) {
  const accepted = new Map();
  const rejected = [];
  const pageTitles = [];

  for (const pagePath of pagePaths) {
    let page;
    try {
      page = readConcept(root, pagePath);
    } catch {
      continue;
    }
    pageTitles.push(page.title);
    const assetsUsed = markdownSectionLinks(page.content, 'Assets Used')
      .map((target) => normalizeReference(page.path, target))
      .filter((target) => target.startsWith('assets/'));
    for (const assetPath of assetsUsed) {
      try {
        const asset = readAssetMetadata(root, assetPath);
        if (asset.completion_status !== 'ready') {
          rejected.push({asset_page: assetPath, reason: 'Asset metadata is draft and requires OCR/image review', confidence: 'low'});
          continue;
        }
        if (!exactApplicableMatch(asset.applicable_questions, question, [page.path], [page.title])) {
          rejected.push({asset_page: assetPath, reason: 'Asset is referenced by the page but lacks reciprocal # Applicable Questions binding', confidence: 'medium'});
          continue;
        }
        accepted.set(assetPath, {
          asset_page: assetPath,
          title: asset.title,
          reason: `Referenced by ${page.path} # Assets Used`,
          confidence: 'high',
          absolute_asset_path: asset.absolute_asset_path,
          completion_status: asset.completion_status,
        });
      } catch (error) {
        rejected.push({asset_page: assetPath, reason: `Referenced asset could not be read: ${error.message}`, confidence: 'low'});
      }
    }
  }

  const assetPages = loadConcepts(root).filter((item) => item.path.startsWith('assets/') && !item.path.endsWith('/index.md'));
  for (const assetPage of assetPages) {
    if (accepted.has(assetPage.path)) continue;
    let asset;
    try {
      asset = readAssetMetadata(root, assetPage.path);
    } catch {
      continue;
    }
    const applicable = asset.applicable_questions || '';
    const notApplicable = asset.not_applicable_to || '';
    if (!applicable || isNotAssigned(applicable)) {
      rejected.push({asset_page: assetPage.path, reason: 'Applicable Questions is not assigned', confidence: 'low'});
      continue;
    }
    if (exactApplicableMatch(notApplicable, question, pagePaths, pageTitles) || tokenOverlapScore(question, notApplicable) >= 2) {
      rejected.push({asset_page: assetPage.path, reason: 'Question overlaps Not Applicable To', confidence: 'medium'});
      continue;
    }
    if (asset.completion_status !== 'ready') {
      rejected.push({asset_page: assetPage.path, reason: 'Asset metadata is draft and requires OCR/image review', confidence: 'low'});
      continue;
    }
    const exactMatch = exactApplicableMatch(applicable, question, pagePaths, pageTitles);
    if (exactMatch) {
      accepted.set(assetPage.path, {
        asset_page: assetPage.path,
        title: asset.title,
        reason: 'Question exactly matches asset # Applicable Questions',
        confidence: 'high',
        absolute_asset_path: asset.absolute_asset_path,
        completion_status: asset.completion_status,
      });
    } else {
      rejected.push({asset_page: assetPage.path, reason: 'Applicable Questions does not exactly match question or matched page path', confidence: 'low'});
    }
  }

  return {
    question,
    assets: [...accepted.values()],
    rejected_assets: rejected,
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
  readAssetMetadata,
  readAssetFile,
  findApplicableAssets,
  getRelatedLinks,
  getBacklinks,
  getPageAssets,
  loadGraph,
};
