import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'
import { defineConfig } from 'vite'

export default defineConfig({
	plugins: [vue()],
	build: {
		outDir: './approvals/public/dist/js',
		target: 'esnext',
		emptyOutDir: false,
		sourcemap: true,
		lib: {
			entry: resolve(__dirname, './approvals/approvals.ts'),
			name: 'approvals',
			formats: ['es'], // only create module output for Frappe
		},
	},
	define: {
		'process.env': process.env,
	},
})
