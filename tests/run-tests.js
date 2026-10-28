// Compatibility with the existing Node/CI entry point. Tests themselves are offline Python.
const {spawnSync} = require('child_process');
const path = require('path');
const result = spawnSync('python3', ['-m','unittest','discover','-s','tests','-p','test_*.py','-v'], {cwd:path.resolve(__dirname,'..'),stdio:'inherit'});
process.exit(result.status === null ? 1 : result.status);
