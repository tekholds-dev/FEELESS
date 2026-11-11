// 🎨 AGT-7: syntax colours for the code views, line by line, no library (HTML, CSS, JS). Earliest match wins; anything unmatched stays plain.
const STR = /(['"`])(?:\\.|(?!\1).)*\1/;
const RULES = {
  js: [[/\/\/.*$/, 'c'], [/\/\*.*?\*\//, 'c'], [STR, 's'], [/\b(?:const|let|var|function|return|if|else|for|while|await|async|new|class|import|from|export|default|try|catch|throw|of|in|typeof|null|true|false|undefined|this|switch|case|break)\b/, 'k'], [/\b\d+(?:\.\d+)?\b/, 'n'], [/[A-Za-z_$][\w$]*(?=\s*\()/, 'f']],
  css: [[/\/\*.*?\*\//, 'c'], [STR, 's'], [/#[0-9a-fA-F]{3,8}\b/, 'n'], [/[a-z-]+(?=\s*:[^:])/, 'k'], [/-?\b\d+(?:\.\d+)?(?:px|%|em|rem|s|ms|vh|vw|deg|fr)?\b/, 'n'], [/[.#]?[a-zA-Z][\w-]*(?=[^{}]*\{)/, 'f']],
  html: [[/<!--.*?-->/, 'c'], [/<\/?[a-zA-Z][\w-]*/, 'k'], [/\s[a-zA-Z_:][\w:.-]*(?==)/, 'f'], [STR, 's'], [/\/?>/, 'k']],
};
export const langOf = (path = '') => (/\.css$/i.test(path) ? 'css' : /\.(m?js|jsx|ts|tsx)$/i.test(path) ? 'js' : 'html');
/** One line → [[text, kind]] where kind is '', 'k' keyword/tag, 's' string, 'n' number/colour, 'c' comment, 'f' name. */
export function tint(line, lang = 'html') {
  const rules = RULES[lang] || RULES.html; const out = []; let rest = String(line || '');
  for (let guard = 0; rest && guard < 400; guard++) {
    let best = null;
    for (const [re, kind] of rules) { const m = re.exec(rest); if (m && m[0] && (!best || m.index < best.i)) best = { i: m.index, t: m[0], kind }; }
    if (!best) { out.push([rest, '']); break; }
    if (best.i) out.push([rest.slice(0, best.i), '']);
    out.push([best.t, best.kind]); rest = rest.slice(best.i + best.t.length);
  }
  return out;
}
