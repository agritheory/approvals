import vue from '@vitejs/plugin-vue'
import { existsSync, readFileSync } from 'fs'
import { join, resolve } from 'path'
import { ServerOptions, defineConfig } from 'vite'

export default defineConfig({
	plugins: [vue()],
	build: {
		outDir: './approvals/public/dist/js',
		target: 'esnext',
		lib: {
			entry: resolve(__dirname, './approvals/approvals.ts'),
			name: 'approvals',
			formats: ['es'], // only create module output for Frappe
		},
		emptyOutDir: false,
		sourcemap: true,
	},
	define: {
		'process.env': process.env,
	},
})
