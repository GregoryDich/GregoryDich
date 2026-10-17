// node dump_scene.js scene.js catalog.js > scene.json  — the scene as the engine sees it (+ coral catalog)
global.window = {};
require(require('path').resolve(process.argv[2]));
require(require('path').resolve(process.argv[3]));
const s = Object.assign({}, window.AQUARIUM_SCENE, { _catalog: window.CORAL_CATALOG });
process.stdout.write(JSON.stringify(s));
