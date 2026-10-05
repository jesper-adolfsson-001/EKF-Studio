import {build} from 'esbuild';
await build({entryPoints:['frontend/markdown.jsx'],bundle:true,minify:true,format:'esm',target:['es2022'],outfile:'web/dist/markdown.js',legalComments:'linked',define:{'process.env.NODE_ENV':'"production"'},logLevel:'info'});
