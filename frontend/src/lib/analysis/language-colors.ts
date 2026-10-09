/**
 * GitHub Linguist's colour for a language, so the bar and its legend read the
 * way a GitHub repository page does.
 *
 * Two things this file has to get right beyond the table itself.
 *
 * ## The table has to be wide
 *
 * It used to hold 45 entries and fall back to a single indigo for everything
 * else, so a repository containing shell, Powershell, Makefile, CMake, SCSS,
 * Jupyter and VimL showed five distinguishable colours and seven identical
 * ones. "Which of these is which" is the entire job of a language legend, and a
 * shared fallback silently takes it away.
 *
 * ## The fallback has to be stable *and* distinct
 *
 * A language with no entry still needs a colour, and that colour has to be the
 * same on every render, every card and every reload -- a legend that reshuffles
 * between paints cannot be read. It also cannot be one colour shared by every
 * unknown, which is what it was. Hashing the name into the palette below gives
 * both: repeatable per language, and different between them.
 */
const COLORS: Record<string, string> = {
  // ── Systems ────────────────────────────────────────────
  python: '#3572A5',
  typescript: '#3178C6',
  javascript: '#f1e05a',
  go: '#00ADD8',
  rust: '#dea584',
  java: '#b07219',
  kotlin: '#A97BFF',
  swift: '#F05138',
  ruby: '#701516',
  php: '#4F5D95',
  // Both spellings. `_LANGUAGE_EXTENSIONS` reports Linguist's *slug*
  // (`cpp`, `csharp`) while the colour table is keyed on Linguist's *display*
  // name (`C++`, `C#`), and a slug that misses falls through to the hash
  // palette -- so the two languages a reader most expects to recognise were
  // the two that got a random colour.
  'c#': '#178600',
  csharp: '#178600',
  'c++': '#f34b7d',
  cpp: '#f34b7d',
  c: '#555555',
  'objective-c': '#438eff',
  'objective-c++': '#438eff',
  scala: '#c22d40',
  dart: '#00B4AB',
  zig: '#ec915c',
  crystal: '#000100',
  nim: '#ffc200',
  lua: '#000080',
  perl: '#0298c3',
  raku: '#0000cc',
  assembly: '#6E4C13',
  fortran: '#4d41b1',
  cobol: '#B6A94B',

  // ── Functional / academic ──────────────────────────────
  elixir: '#6e4a7e',
  erlang: '#B83998',
  clojure: '#db5855',
  haskell: '#5e5086',
  ocaml: '#ef7a08',
  'f#': '#b845fc',
  julia: '#a270ba',
  elm: '#60B5CC',
  racket: '#9c7',
  scheme: '#1e4aec',
  lisp: '#3fb68b',
  r: '#198CE7',
  matlab: '#e16737',
  mathematica: '#dd2b49',

  // ── Web ────────────────────────────────────────────────
  html: '#e34c26',
  css: '#563d7c',
  scss: '#c6538c',
  sass: '#a7315f',
  less: '#1d366d',
  stylus: '#ff6363',
  vue: '#41b883',
  svelte: '#ff3e00',
  react: '#61dafb',
  astro: '#ff5a03',
  pug: '#986844',
  handlebars: '#f7931e',
  mustache: '#f7931e',
  'styled-components': '#db70b0',
  graphql: '#e10098',

  // ── Data & config ──────────────────────────────────────
  json: '#292929',
  json5: '#292929',
  yaml: '#cb171e',
  yml: '#cb171e',
  toml: '#9c4221',
  xml: '#0060ac',
  csv: '#33691D',
  tsv: '#33691D',
  sql: '#e38c00',
  markdown: '#083fa1',
  restructuredtext: '#585858',
  // Both spellings: the backend buckets `.rst` under `rst` (the Linguist
  // slug) while the display name it has always shown is `restructuredtext`.
  rst: '#585858',
  tex: '#3D6117',
  latex: '#3D6117',
  // Not a language: the remainder bucket for files no extension entry maps.
  // Given one fixed neutral rather than a hashed one, so it reads as "the
  // rest" in every repository instead of as a distinct language that happens
  // to change colour between runs.
  other: '#8b949e',

  // ── Shell & build ──────────────────────────────────────
  shell: '#89e051',
  bash: '#89e051',
  zsh: '#89e051',
  fish: '#4daff3',
  powershell: '#012456',
  batchfile: '#C1F12E',
  makefile: '#427819',
  cmake: '#DA3434',
  dockerfile: '#384d54',
  nix: '#7e7eff',
  terraform: '#5C4EE5',
  hcl: '#844FBA',
  ansible: '#EE0000',
  groovy: '#e69f56',

  // ── Markup & scripting ─────────────────────────────────
  jupyter: '#DA5B0B',
  coffeescript: '#244776',
  pascal: '#E3F171',
  solidity: '#AA6746',
  protobuf: '#3c8527',
  thrift: '#D12121',
  'vim script': '#199f4b',
  viml: '#199f4b',
};

/**
 * Chosen to stay apart on a `bg-card` background and against each other: none
 * of these are near-black, and no two are within a few degrees of hue.
 *
 * Deliberately not Linguist's. The table above is Linguist because that is the
 * colour a GitHub reader already associates with a language; this palette only
 * ever draws names Linguist has no opinion about, where the only thing that
 * matters is that two unknowns are told apart.
 */
const FALLBACK = [
  '#6366f1',
  '#22d3ee',
  '#f472b6',
  '#a3e635',
  '#fbbf24',
  '#fb923c',
  '#f87171',
  '#818cf8',
  '#2dd4bf',
  '#c084fc',
  '#4ade80',
  '#38bdf8',
];

/** A repeatable index into `FALLBACK`, so a language never changes colour. */
function hashIndex(language: string, modulo: number): number {
  let hash = 0;
  for (let i = 0; i < language.length; i++) {
    hash = (hash * 31 + language.charCodeAt(i)) | 0;
  }
  return (hash >>> 0) % modulo;
}

export function getLanguageColor(language: string): string {
  const known = COLORS[language.toLowerCase().trim()];
  if (known) return known;
  return FALLBACK[hashIndex(language, FALLBACK.length)];
}
