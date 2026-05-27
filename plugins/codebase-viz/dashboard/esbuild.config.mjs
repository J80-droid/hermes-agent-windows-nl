import * as esbuild from 'esbuild';
import { copyFileSync, existsSync } from 'fs';
import { dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const watch = args.includes('--watch');

async function build() {
  const opts = {
    entryPoints: ['src/index.jsx'],
    outfile: 'dist/index.js',
    bundle: true,
    format: 'iife',
    globalName: 'CodebaseVizPlugin',
    loader: { '.jsx': 'jsx' },
    jsx: 'transform',
    jsxFactory: 'React.createElement',
    jsxFragment: 'React.Fragment',
    external: ['react'],
    minify: false,
    sourcemap: watch ? 'inline' : false,
  };
  if (watch) {
    const ctx = await esbuild.context(opts);
    await ctx.watch();
    console.log('Watching...');
    return;
  }
  await esbuild.build(opts);

  if (existsSync('src/style.css')) {
    copyFileSync('src/style.css', 'dist/style.css');
    console.log('Copied style.css');
  }

  if (!watch) {
    console.log('Build complete');
  }
}

build().catch(() => process.exit(1));
