"""🎮 GAME LAB — the owner's desktop folder for testing and porting games (owner 2026-11-13 / 11-15: "a place in desktop for game testing,
porting and etc like for gta rp, and possibly psvita … the game desk is suppose to be a folder in desktop").

Three parts, all real and all saved owner-only on the server:
  · PLAYTEST LOG   every session: game, platform, build, frame rate, bugs, verdict
  · PORT           one checklist per target, with the real open tools each one uses; ticks are saved
  · GTA RP         a working FiveM / RedM resource starter (fxmanifest.lua + client + server Lua), made here, no model and no cost
Only your own games and legal homebrew: no DRM cracking, no piracy, no online-game cheats. Pure; rep_admin_routes does the I/O.
"""
import re
import time
import uuid

LOG_MAX = 500
PLATFORMS = {   # key → (name, what it is, its real open tools, the porting steps)
    'fivem': ('GTA V RP · FiveM', 'Roleplay servers for GTA V on Cfx.re (owned by Rockstar since 2023)', ['FiveM client', 'txAdmin', 'Qbox / QBCore / ESX', 'Lua 5.4', 'oxmysql'],
              ['Rent or host a server and set up txAdmin', 'Pick one framework (Qbox, QBCore or ESX) and stay on it', 'Add each resource with its own fxmanifest.lua',
               'Wire the database through oxmysql', 'Test every resource alone, then together, with resmon open', 'Keep frame time under 0.5 ms a resource', 'Read the Cfx.re rules before you sell anything']),
    'redm': ('Red Dead RP · RedM', 'Roleplay servers for Red Dead Redemption 2 on Cfx.re', ['RedM client', 'txAdmin', 'VORP / RSG framework', 'Lua 5.4'],
             ['Host a RedM server with txAdmin', 'Pick VORP or RSG', 'Every fxmanifest needs the rdr3_warning line', 'Port GTA scripts by swapping natives, not copying them', 'Test on a clean profile']),
    'vita': ('PS Vita homebrew', 'Your own games and apps on a Vita you own, tested in the Vita3K emulator first', ['VitaSDK', 'Vita3K emulator', 'vita-toolchain', 'VitaShell'],
             ['Install VitaSDK (CMake toolchain)', 'Build a VPK from your own code', 'Boot it in Vita3K first and log frame rate', 'Keep it under the Vita\'s memory (512 MB RAM)',
              'Install on your own console only, where homebrew is legal', 'No commercial games: no dumps, no piracy']),
    'deck': ('Steam Deck', 'PC games on SteamOS and Proton', ['Proton', 'SteamOS', 'Steam Input', 'gamescope'],
             ['Run it under Proton and note the version', 'Set a 1280x800 default', 'Map every action in Steam Input', 'Hold 40 fps or better on battery', 'Check text size from arm\'s length']),
    'web': ('Web (WebGL)', 'Games that run in any browser', ['three.js', 'Phaser', 'Godot web export', 'WebGPU'],
            ['Export a web build', 'Keep the first load under 20 MB', 'Touch controls for phones', 'Hold 60 fps on a mid phone', 'Save to the browser, never lose progress']),
}
VERDICTS = ('ship', 'fix', 'blocked')
_NAME = re.compile(r'[^a-z0-9_]+')


def platforms():
    return [{'id': k, 'name': n, 'what': w, 'tools': t, 'steps': s} for k, (n, w, t, s) in PLATFORMS.items()]


def clean_row(b, now=None):
    """A playtest row from the page. Raises ValueError on a bad one. Pure."""
    game = str(b.get('game') or '').strip()[:60]
    if not game:
        raise ValueError('Name the game.')
    plat = b.get('platform') if b.get('platform') in PLATFORMS else None
    if not plat:
        raise ValueError('Pick a platform.')
    verdict = b.get('verdict') if b.get('verdict') in VERDICTS else 'fix'
    fps = b.get('fps'); fps = max(0, min(1000, int(fps))) if isinstance(fps, (int, float)) else None
    bugs = [str(x).strip()[:140] for x in (b.get('bugs') or []) if str(x).strip()][:12]
    return {'id': uuid.uuid4().hex[:10], 'at': round(now or time.time()), 'game': game, 'platform': plat, 'build': str(b.get('build') or '').strip()[:30],
            'fps': fps, 'bugs': bugs, 'verdict': verdict, 'notes': str(b.get('notes') or '').strip()[:400]}


def apply(state, b, now=None):
    """One change from the page → the new state. Pure."""
    st = {'log': list((state or {}).get('log') or []), 'checks': dict((state or {}).get('checks') or {})}
    if b.get('log'):
        st['log'] = [clean_row(b['log'], now)] + st['log'][:LOG_MAX - 1]
    elif b.get('drop'):
        st['log'] = [r for r in st['log'] if r.get('id') != b['drop']]
    elif b.get('check') in PLATFORMS:
        n = len(PLATFORMS[b['check']][3]); i = b.get('step')
        if not isinstance(i, int) or not 0 <= i < n:
            raise ValueError('No such step.')
        on = set(st['checks'].get(b['check']) or []); on.symmetric_difference_update({i}); st['checks'][b['check']] = sorted(on)
    else:
        raise ValueError('Nothing to change.')
    return st


def view(state):
    st = state or {}
    log = st.get('log') or []
    return {'platforms': platforms(), 'log': log[:100], 'checks': st.get('checks') or {},
            'stats': {'sessions': len(log), 'bugs': sum(len(r.get('bugs') or []) for r in log), 'ship': sum(1 for r in log if r.get('verdict') == 'ship')}}


RDR3_WARNING = 'I acknowledge that this is a prerelease build of RedM, and I am aware my resources *will* become incompatible once RedM ships.'


def resource(name, game='gta5', what='', command=True):
    """🧱 A working FiveM / RedM resource starter: {filename: text}. Pure, no model.
    name → a safe folder name; game 'gta5' (FiveM) or 'rdr3' (RedM)."""
    rid = _NAME.sub('_', str(name or '').lower()).strip('_')[:32] or 'my_resource'
    game = 'rdr3' if game == 'rdr3' else 'gta5'
    about = str(what or 'A FEELESS game lab resource').replace("'", '')[:120]
    manifest = (f"fx_version 'cerulean'\ngame '{game}'\n" + (f"rdr3_warning '{RDR3_WARNING}'\n" if game == 'rdr3' else '')
                + f"lua54 'yes'\n\nauthor 'FEELESS Game Lab'\ndescription '{about}'\nversion '1.0.0'\n\nshared_script 'config.lua'\nclient_script 'client.lua'\nserver_script 'server.lua'\n")
    config = f"Config = {{}}\nConfig.Name = '{rid}'\nConfig.Debug = false\n"
    client = (f"-- {rid}: client side. Runs on each player's game.\n"
              + (f"RegisterCommand('{rid}', function()\n    TriggerServerEvent('{rid}:hello')\nend, false)\n\n" if command else '')
              + f"RegisterNetEvent('{rid}:say', function(text)\n    print(('[{rid}] %s'):format(text))\nend)\n")
    server = (f"-- {rid}: server side. Never trust the client: check every value it sends.\n"
              f"RegisterNetEvent('{rid}:hello', function()\n    local src = source\n    TriggerClientEvent('{rid}:say', src, ('Hello, %s'):format(GetPlayerName(src)))\nend)\n")
    return {'name': rid, 'files': {'fxmanifest.lua': manifest, 'config.lua': config, 'client.lua': client, 'server.lua': server},
            'install': f"Put the {rid} folder in resources/, add 'ensure {rid}' to server.cfg, then restart the server (or 'refresh' then 'ensure {rid}' in txAdmin)."}
