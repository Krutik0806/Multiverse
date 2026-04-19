import re

path = r'c:\Users\Krutik\OneDrive\Desktop\UserFiles\MultiVerse Bot\game\characters.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

new_content = re.sub(r'"img": _cld\("(\w+)"\)', lambda m: f'"img": _img("{m.group(1)}")', content)
changed = content.count('"img": _cld(') - new_content.count('"img": _cld(')

with open(path, 'w', encoding='utf-8') as f:
    f.write(new_content)
print(f"Replaced {changed} image URLs from _cld to _img")
