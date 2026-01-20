#!/usr/bin/env python3
"""Debug-Script für Such- und Extraktionsprobleme"""

import sys
sys.path.insert(0, 'src')

from directmedia_mcp.library import DirectmediaLibrary

def debug_search_issues():
    lib = DirectmediaLibrary(r"L:\Multimedia Files\Written Word\Digitale Bibliothek")

    print("=== DIRECTMEDIA MCP - PROBLEMANALYSE ===")
    print()

    # 1. Teste Suche
    print("1. SUCHFUNKTION - AKTUELLER STAND:")
    results = lib.search_text('Nietzsche', 'DB002', 5)
    print(f'Suche nach "Nietzsche" in DB002:')
    print(f'Gefunden: {len(results)} Treffer')

    if results:
        for i, r in enumerate(results[:3]):
            print(f'  Treffer {i+1} - Position {r.position}:')
            print(f'    {r.content_preview[:100]}...')
    else:
        print("  KEINE Treffer gefunden!")
    print()

    # 2. Teste Text-Extraktion
    print("2. TEXT-EXTRAKTION - AKTUELLER STAND:")
    content = lib.get_text_content('DB002', 0, 10000)
    if 'content' in content:
        text = content['content']
        print(f'Extrahiert: {len(text)} Zeichen')
        print(f'Erste 200 Zeichen:')
        print(repr(text[:200]))
        print()

        # Suche manuell im Text
        nietzsche_count = text.lower().count('nietzsche')
        print(f'Manueller Suchzähler: "nietzsche" erscheint {nietzsche_count} mal im Text')
    else:
        print(f'Fehler bei Extraktion: {content}')
    print()

    # 3. Analysiere warum Suche nicht funktioniert
    print("3. WARUM GEHT DIE SUCHE NICHT?")
    print("- Aktuelle Suche lädt nur erste 50KB Text")
    print("- Richtige Suche sollte INDEX-Dateien verwenden")
    print("- INDEX.SWX (Search Word Index) ist 62MB groß!")
    print("- TREE.DKI enthält Navigationsstruktur")
    print()

    # 4. Zeige INDEX-Dateien
    print("4. VERFÜGBARE INDEX-DATEIEN:")
    import os
    from pathlib import Path

    data_path = Path(r"L:\Multimedia Files\Written Word\Digitale Bibliothek\DB002\Data")
    if data_path.exists():
        index_files = [f for f in os.listdir(data_path) if f.startswith('INDEX.')]
        for idx_file in sorted(index_files):
            filepath = data_path / idx_file
            size = filepath.stat().st_size
            print("12s")

if __name__ == '__main__':
    debug_search_issues()






