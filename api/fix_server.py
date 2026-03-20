import io
import os

filepath = os.path.join(os.path.dirname(__file__), "server.py")

with io.open(filepath, "r", encoding="utf-8") as f:
    lines = f.readlines()

# The duplicates are exactly from line 1140 to 1212.
# 0-indexed, this is lines[1139:1212]
new_lines = lines[:1139] + lines[1212:]

with io.open(filepath, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("Removed duplicate api_health and create_alerts from server.py!")
