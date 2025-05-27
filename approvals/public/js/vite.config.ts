import vue from '@vitejs/plugin-vue'
import { existsSync, readFileSync, writeFileSync } from 'fs'
import { resolve } from 'path'
import { defineConfig, PluginOption } from 'vite'

function frappeAssetsPlugin(): PluginOption {
	return {
		name: 'frappe-assets',
		writeBundle(options, bundle) {
			const sitesDir = resolve(__dirname, '../../../../../sites')
			const assetsJsonPath = resolve(sitesDir, 'assets', 'assets.json')
			if (existsSync(assetsJsonPath)) {
				const assetsJson = JSON.parse(readFileSync(assetsJsonPath, 'utf-8'))
				for (const [filename, chunk] of Object.entries(bundle)) {
					if (chunk.type === 'chunk' && chunk.isEntry) {
						assetsJson[`${chunk.name}.bundle.js`] = `/assets/approvals/dist/js/${filename}`
					}
				}

				writeFileSync(assetsJsonPath, JSON.stringify(assetsJson, null, 4))
				console.log('Updated assets.json with new bundle paths')
			}
		},
	}
}

export default defineConfig({
	plugins: [vue(), frappeAssetsPlugin()],
	build: {
		outDir: './approvals/public/dist/js',
		target: 'esnext',
		sourcemap: true,
		rollupOptions: {
			input: resolve(__dirname, './approvals/approvals.ts'),
			output: {
				entryFileNames: '[name].[hash].js',
				chunkFileNames: '[name].[hash].js',
				assetFileNames: '[name].[ext]',
			},
		},
	},
	define: {
		'process.env': process.env,
	},
})
