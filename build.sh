#!/bin/bash
set -e

cd "$(dirname "$0")"

mkdir -p bin/wheelhouse bin/py_ucan_lib

# Build wheel to bin/wheelhouse using hatch
uvx hatchling build -d bin/wheelhouse

# Extract wheel
python3 -c "
import zipfile, os
whl = 'bin/wheelhouse/' + [f for f in os.listdir('bin/wheelhouse') if f.endswith('.whl')][0]
with zipfile.ZipFile(whl, 'r') as z:
    z.extractall('bin/py_ucan_lib')
"

# Create launcher script
cat > bin/py-ucan << 'EOF'
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHONPATH="$SCRIPT_DIR/py_ucan_lib" exec python3 -m py_screw "$@"
EOF
chmod +x bin/py-ucan

echo "Built py-ucan to bin/py-ucan"
