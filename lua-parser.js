const parser = require("luaparse"); // https://github.com/fstirlitz/luaparse
/* npm install luaparse */
const fs = require("fs");

const args = process.argv.slice(2);

if (args.length == 0) {
	throw new Error("You need to give the file to parse to the parser.");
} else if (args.length == 1) {
	throw new Error("You need to give the expected lua version to the parser.");
}

parser.luaVersion = args[1];
const code = fs.readFileSync(args[0], "utf8");
const ast = parser.parse(code);
console.log(JSON.stringify(ast));