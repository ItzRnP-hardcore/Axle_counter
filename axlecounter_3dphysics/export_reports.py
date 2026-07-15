"""DEPRECATED one-time migration script.
The reports/ folder is now the canonical output location and every
generator writes there directly (see config.OUTPUT_DIR). Kept only for
historical reference; not needed in the current pipeline.
"""
import os
import shutil

src = r"C:\Users\rudra\.gemini\antigravity-ide\brain\c981317d-911b-42a2-b085-b99f9b9bf6a2"
dst = r"c:\Users\rudra\Axle_counter\axlecounter_3dphysics\reports"

os.makedirs(dst, exist_ok=True)

# Copy PNGs and CSVs
print("Copying images and data spreadsheets...")
for f in os.listdir(src):
    if f.endswith('.png') or f.endswith('.csv'):
        shutil.copy2(os.path.join(src, f), os.path.join(dst, f))
        print(f"Copied {f}")

# Copy MDs and fix links to make them portable
print("\nCopying markdown reports and converting links to relative...")
for f in os.listdir(src):
    if f.endswith('.md'):
        with open(os.path.join(src, f), 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Replace absolute links with relative links so they work perfectly in the local folder
        content = content.replace("C:/Users/rudra/.gemini/antigravity-ide/brain/c981317d-911b-42a2-b085-b99f9b9bf6a2/", "./")
        
        with open(os.path.join(dst, f), 'w', encoding='utf-8') as file:
            file.write(content)
        print(f"Exported {f}")

print(f"\nAll files successfully exported to {dst}!")
