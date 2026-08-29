# Coptic display font

The style in your screenshot (bulbous, decorative uncial letterforms) looks
like it matches **"Coptic-A"** by Nick Matavka - a free font licensed under
the SIL Open Font License 1.1 (free for commercial and non-commercial use,
redistribution allowed with the license text included).

I couldn't download the actual font binary automatically (this sandbox's
network access is locked to package registries, not font sites), so grab it
yourself:

1. Download it from either:
   - https://creazilla.com/media/font/7879205/coptic-a-a
   - https://www.dafont.com/nick-matavka.d5505 (browse his fonts, look for
     "Coptic")
2. Confirm it actually covers the Coptic Unicode block (U+2C80-U+2CFF) -
   some older "Coptic-styled" novelty fonts only cover Latin/Greek
   lookalike glyphs and will silently fall back to a system font for real
   Coptic characters, which defeats the point. Open the .ttf in a font
   viewer and check it renders `ⲁⲃⲅⲇⲉ` correctly before using it.
3. Rename the file to `coptic.ttf` (or `.otf`/`.woff2`, whichever you
   downloaded) and place it in this folder:
   `frontend/assets/fonts/coptic.ttf`
4. Include the font's license file alongside it here too (SIL OFL requires
   the license to travel with the font), e.g. `frontend/assets/fonts/OFL.txt`.
5. Restart Streamlit. `frontend/app.py` will automatically detect the file
   and apply it to Coptic-script output - no code changes needed.

If that particular font turns out not to be the right visual match, any
other Coptic Unicode font works the same way - just name it `coptic.ttf`
(etc.) in this folder. For scholarly accuracy (not decorative style), the
field's actual standard is **Antinoou**, commissioned by the International
Association of Coptic Studies - worth having as a fallback/alternate even
if you go decorative for the main UI:
https://sites.google.com/site/askelandchristian/copticlinks
