import React from 'react';
import { Folder, Pickaxe, ChartCandlestick, Dices, Megaphone, Globe, PieChart, Trophy, Swords, Tv, Fingerprint, Coins, Sparkles, UserRound, BookOpen, ShieldCheck, Briefcase, RadioTower, Activity, Database, Compass, Rss, Gem, Wallet, Mail, GitBranch, Command, Settings, Archive, FileText } from 'lucide-react';
import { lineOf } from './icon3d';
import '../styles/folderArt.css';

// 📁 Folder art, every desk (owner 2026-11-12: "the classic windows folders we cool but the icons werent"). Each folder carries BOTH looks and the
// desk's `data-folders` (Desktop settings › Folder look) picks one in CSS: classic / mono = the coloured folder box (its sheet) with a clean line icon,
// outline = a dark glass folder drawn in the look's accent with a lit LED on the proof folders. Tone (good / bad / none / live) swaps the outline stroke.
const BY_KEY = { vault: Archive, pow: Pickaxe, pop: ChartCandlestick, bids: Dices, pob: Dices, poc: Megaphone, postatic: Globe, poe: PieChart, proofs: Trophy,
  debate: Swords, watch: Tv, print: Fingerprint, boost: Coins, features: Sparkles, character: UserRound, manual: BookOpen, terms: ShieldCheck, jobs: Briefcase,
  engines: RadioTower, command: Activity, db: Database, browser: Compass, sources: Rss, honey: Gem, collective: Gem, colony: Gem, wallet: Wallet, mail: Mail,
  github: GitBranch, cmds: Command, deskset: Settings, files: FileText };
export const PROOF_KEYS = new Set(['pow', 'pop', 'bids', 'pob', 'poc', 'postatic', 'poe']);
export const folderGlyph = (k, ic) => BY_KEY[k] || lineOf(ic) || Folder;

export function FolderArt({ k = '', ic = '', lit = PROOF_KEYS.has(k), file = false }) {
  const G = folderGlyph(k, ic);
  return <><em className="fa-cl"><G strokeWidth={2} /></em><FolderSvg G={G} lit={lit} file={file} /></>;
}
function FolderSvg({ G, lit, file }) {
  if (file) return <svg className="fa fa-file" viewBox="0 0 44 52" aria-hidden="true" focusable="false">
    <path className="fa-front" d="M8 3h20l10 10v33a3 3 0 0 1-3 3H8a3 3 0 0 1-3-3V6a3 3 0 0 1 3-3Z" /><path className="fa-ear" d="M28 3v10h10" />
    <G x="12" y="20" width="20" height="20" strokeWidth={1.75} className="fa-g" /></svg>;
  return <svg className="fa" viewBox="0 0 56 44" aria-hidden="true" focusable="false">
    <path className="fa-back" d="M4 8a3 3 0 0 1 3-3h12.5a3 3 0 0 1 2.1.9L25 9h24a3 3 0 0 1 3 3v26a3 3 0 0 1-3 3H7a3 3 0 0 1-3-3Z" />
    <rect className="fa-paper" x="9" y="12" width="38" height="10" rx="1.5" />
    <path className="fa-front" d="M4 17.5A2.5 2.5 0 0 1 6.5 15h43a2.5 2.5 0 0 1 2.5 2.5V38a3 3 0 0 1-3 3H7a3 3 0 0 1-3-3Z" />
    <path className="fa-hi" d="M7 16.6h42" />
    {lit ? <circle className="fa-led" cx="12" cy="8.6" r="1.6" /> : null}
    <G x="18" y="19" width="20" height="20" strokeWidth={1.75} className="fa-g" /></svg>;
}
