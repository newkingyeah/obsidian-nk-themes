"""Build, validate, and package NK themes using Python's standard library."""
from pathlib import Path
import argparse
import json
import sys
import zipfile

ROOT=Path(__file__).absolute().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from themes import COLLECTION, COMMON, END, KEYS, SPECIAL, VERSION

def render(spec):
    chunks=[f'/* {spec["name"]} | {spec["title"]} | v{VERSION} | MIT License */']
    for mode in ('dark','light'):
        palette=dict(zip(KEYS,spec[mode]))
        rows=[f'body.theme-{mode} {{']+[f'  --nk-{k}: {v};' for k,v in palette.items()]
        rows += [f'  --nk-code: {palette["deep"] if mode=="dark" else palette["side"]};',
                 f'  --nk-radius: {spec["radius"]};',f'  --nk-inner: {spec["inner"]};',f'  --nk-gap: {spec["gap"]};',
                 f'  --font-text-theme: {spec["font"]};',
                 '  --font-interface-theme: "Segoe UI Variable", "Segoe UI", "Microsoft YaHei", sans-serif;']
        rows += [f'  --h{i}-font: {spec["heading"]};' for i in range(1,7)]
        rows += [f'  --inline-title-font: {spec["heading"]};','}']
        chunks.append('\n'.join(rows))
    chunks += [COMMON,SPECIAL[spec['id']],END]
    return '\n\n'.join(chunks)

def luminance(color):
    channels=[int(color[i:i+2],16)/255 for i in (1,3,5)]
    linear=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in channels]
    return sum(v*w for v,w in zip(linear,(.2126,.7152,.0722)))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true',help='Verify tracked CSS is reproducible and text contrast passes 4.5:1')
    parser.add_argument('--package',action='store_true',help='Write per-theme and collection ZIPs in dist/')
    args=parser.parse_args()
    for spec in COLLECTION:
        for mode in ('dark','light'):
            bg,text=spec[mode][0],spec[mode][3]
            a,b=sorted((luminance(bg),luminance(text)))
            if (b+.05)/(a+.05)<4.5:
                raise SystemExit(f'Insufficient text contrast: {spec["name"]} ({mode})')
        folder=ROOT/'themes'/spec['name']
        expected={
            'theme.css':render(spec),
            'manifest.json':json.dumps(dict(name=spec['name'],version=VERSION,minAppVersion='1.10.6',author='newkingyeah',authorUrl='https://github.com/newkingyeah'),ensure_ascii=False,indent=2),
            'versions.json':json.dumps({VERSION:'1.10.6'},indent=2)+'\n',
        }
        if not args.check:
            folder.mkdir(parents=True,exist_ok=True)
        for filename,content in expected.items():
            target=folder/filename
            if args.check:
                if not target.exists() or target.read_text(encoding='utf-8')!=content:
                    raise SystemExit(f'Out of date: {target.relative_to(ROOT)}; run python scripts/build.py')
            else:
                target.write_text(content,encoding='utf-8')
        print(f'OK {spec["name"]} {VERSION}')
    if args.package:
        dist=ROOT/'dist'
        dist.mkdir(exist_ok=True)
        for spec in COLLECTION:
            with zipfile.ZipFile(dist/f'{spec["id"]}-{VERSION}.zip','w',zipfile.ZIP_DEFLATED) as archive:
                for p in (ROOT/'themes'/spec['name']).iterdir():
                    if p.is_file():archive.write(p,Path(spec['name'])/p.name)
                archive.write(ROOT/'LICENSE',Path(spec['name'])/'LICENSE')
        with zipfile.ZipFile(dist/f'NK-Obsidian-Themes-{VERSION}.zip','w',zipfile.ZIP_DEFLATED) as archive:
            for p in (ROOT/'themes').rglob('*'):
                if p.is_file():archive.write(p,p.relative_to(ROOT))
            archive.write(ROOT/'README.md','README.md')
            archive.write(ROOT/'LICENSE','LICENSE')
        print('Packages:',dist)

if __name__=='__main__':main()
