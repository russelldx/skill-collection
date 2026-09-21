#!/usr/bin/env python3
"""Check source-image bytes against embedded DOCX media (not media filenames)."""
import argparse
import hashlib
from pathlib import Path
import sys
import zipfile


def missing_images(docx, images):
    """Return sources absent from word/media; repeated sources may share one part."""
    with zipfile.ZipFile(docx) as archive:
        hashes = {
            hashlib.sha1(archive.read(info)).digest()
            for info in archive.infolist()
            if info.filename.startswith('word/media/') and not info.is_dir()
        }
    return [str(image) for image in images
            if hashlib.sha1(Path(image).read_bytes()).digest() not in hashes]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('docx', type=Path)
    parser.add_argument('images', type=Path, nargs='+', help='Source-image paths (absolute recommended)')
    args = parser.parse_args()
    try:
        missing = missing_images(args.docx, args.images)
    except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 2
    for image in missing:
        print(f'MISSING: {image}')
    print(f'checked={len(args.images)} missing={len(missing)}')
    return 1 if missing else 0


if __name__ == '__main__':
    sys.exit(main())
